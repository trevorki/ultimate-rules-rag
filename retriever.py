from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
from pgvector.psycopg2 import register_vector
import logging

from openai import OpenAI
import json

from pydantic import BaseModel, Field
from typing import Dict

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self):
        self.client = OpenAI()
        self.db_settings = {
            "dbname": os.getenv('POSTGRES_DB'),
            "user": os.getenv('POSTGRES_USER'),
            "password": os.getenv('POSTGRES_PASSWORD'),
            "host": os.getenv('POSTGRES_HOST'),
            "port": os.getenv('POSTGRES_PORT')
        }

        print(f"DB Settings: {json.dumps(self.db_settings, indent=4)}")
        

    def create_embedding(self, text):
        response = self.client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding

    def query_db_sql(self, sql_query, args):
        try:
            with psycopg2.connect(**self.db_settings) as conn:
                register_vector(conn)  # Register the VECTOR type
                with conn.cursor() as cursor:
                    cursor.execute(sql_query, args)
                    return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")
            raise

    # Example: Query documents based on similarity to a given embedding
    def retrieve_similar_documents(self, query, limit=3, expand_context=False):
        query_embedding = self.create_embedding(query)
        sql_query = "SELECT * FROM query_similar_documents(%s::VECTOR, %s);"
        retrieved_docs = self.query_db_sql(sql_query, (query_embedding, limit))
        # logger.info(f"Retrieved {len(retrieved_docs)} documents")
        # logger.info("\n".join([f"ID: {doc[0]}, Content: {doc[1]}, Source: {doc[2]}" for doc in retrieved_docs]))
        

        formatted_docs = [{"id":doc[0], "content":doc[1], "source":doc[2]} for doc in retrieved_docs]

        if expand_context is True:
            retrieved_docs = self.get_expanded_context(formatted_docs)
        return formatted_docs
    
    def get_expanded_context(self, retrieved_docs):
        # Extract the IDs of the documents to expand
        doc_ids = [doc["id"] for doc in retrieved_docs if doc["source"] == "rules"]
        print("Getting expanded context")
        print(f"doc_ids: {doc_ids}")
        
        if not doc_ids:
            return retrieved_docs  # No documents to expand

        # Create a list of IDs to fetch, including adjacent documents
        doc_ids_to_fetch = set()
        for doc_id in doc_ids:
            doc_ids_to_fetch.update([doc_id - 1, doc_id, doc_id + 1])

        print(f"doc_ids_to_fetch: {doc_ids_to_fetch}")

        # Construct the SQL query
        sql_query = """
            SELECT id, content FROM documents 
            WHERE id IN %s
            AND source = 'rules'
            ORDER BY id
        """
        
        # Execute the query
        expanded_docs = self.query_db_sql(sql_query, (tuple(doc_ids_to_fetch),))

        # Process the results
        expanded_content = {}
        for i in range(1, len(expanded_docs) - 1):
            prev_content = expanded_docs[i-1][1]
            current_content = expanded_docs[i][1]
            next_content = expanded_docs[i+1][1]
            expanded_content[expanded_docs[i][0]] = f"{prev_content}\n\n{current_content}\n\n{next_content}"

        # Replace the content of the original documents with expanded content
        result = []
        for doc in retrieved_docs:
            if doc["id"] in expanded_content:
                result.append({"id":doc["id"], "content":expanded_content[doc["id"]], "source":doc["source"]})
            else:
                result.append(doc)

        return result


# Example usage
if __name__ == "__main__":
    
    queries = [
        # "what is a pick and what happens after a pick is called",
        "How many stall counts in ultimate?",
        # "How many stall counts in beach ultimate.",
    ]
    expand_context=True
    retriever = Retriever()
    for query in queries:
        print(f"\n\nQuery: '{query}'")
        retrieved_docs = retriever.retrieve_similar_documents(query, limit = 5, expand_context=expand_context)
        print(json.dumps(retrieved_docs, indent=4))

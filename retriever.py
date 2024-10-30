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

        # print(f"DB Settings: {json.dumps(self.db_settings, indent=4)}")
        

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
                

        retrieved_docs = [{"id":doc[0], "content":doc[1], "source":doc[2]} for doc in retrieved_docs]

        if expand_context is True:
            retrieved_docs = self.get_expanded_context(retrieved_docs)
        return retrieved_docs
    
    def get_expanded_context(self, retrieved_docs):
        # Extract the IDs of the documents to expand
        doc_ids = [doc["id"] for doc in retrieved_docs if doc["source"] == "rules"]
        
        if not doc_ids:
            return retrieved_docs  # No documents to expand

        # Create a list of IDs to fetch, including adjacent documents
        doc_ids_to_fetch = set()
        for doc_id in doc_ids:
            doc_ids_to_fetch.update([doc_id - 1, doc_id, doc_id + 1])

        # Fetch adjacent documents
        sql_query = """
            SELECT id, content FROM documents 
            WHERE id IN %s
            AND source = 'rules'
            ORDER BY id
        """.replace("    ", "")
        
        adjacent_docs = self.query_db_sql(sql_query, (tuple(doc_ids_to_fetch),))
        
        # Convert to dictionary for easier lookup
        doc_map = {doc[0]: doc[1] for doc in adjacent_docs}
        
        # Group consecutive IDs
        groups = []
        current_group = []
        
        sorted_ids = sorted(doc_map.keys())
        for id in sorted_ids:
            if not current_group or id == current_group[-1] + 1:
                current_group.append(id)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [id]
        if current_group:
            groups.append(current_group)

        # Create merged context documents with tracking of original positions
        result = []
        for group in groups:
            # Only include groups that contain at least one of our original retrieved doc_ids
            original_positions = [
                i for i, doc in enumerate(retrieved_docs) 
                if doc["source"] == "rules" and doc["id"] in group
            ]
            if original_positions:
                merged_content = "\n\n".join(doc_map[id] for id in group)
                # Use the middle ID from the group as the representative ID
                representative_id = group[len(group)//2]
                result.append({
                    "id": representative_id,
                    "content": merged_content,
                    "source": "rules",
                    "context_range": f"docs {group[0]}-{group[-1]}",
                    "first_appearance": min(original_positions)  # Track earliest appearance
                })

        # Sort by the original appearance order
        result.sort(key=lambda x: x["first_appearance"])
        
        # Remove the temporary sorting key
        for doc in result:
            doc.pop("first_appearance", None)

        # Add back any non-rules documents from the original results
        non_rules_docs = [doc for doc in retrieved_docs if doc["source"] != "rules"]
        result.extend(non_rules_docs)

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

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
    def retrieve_similar_documents(self, query: str, limit: int = 3, expand_context: bool|int = False) -> list[dict]:
        """
        Retrieve documents similar to the input query, with optional context expansion.

        Args:
            query (str): The search query to find similar documents
            limit (int, optional): Maximum number of documents to retrieve. Defaults to 3.
            expand_context (bool|int, optional): Controls context expansion around retrieved documents.
                - False or 0: No expansion
                - True: Expand by 1 document in each direction
                - n (positive int): Expand by n documents in each direction
                Defaults to False.

        Returns:
            list[dict]: List of documents, where each document is a dictionary containing:
                - id (int): Document ID
                - content (str): Document content
                - source (str): Document source
                If context is expanded, additional fields include:
                - context_range (str): Range of document IDs included
                - first_appearance (int): Original position in results
        """
        query_embedding = self.create_embedding(query)
        sql_query = "SELECT * FROM query_similar_documents(%s::VECTOR, %s);"
        retrieved_docs = self.query_db_sql(sql_query, (query_embedding, limit))
                

        retrieved_docs = [{"id":doc[0], "content":doc[1], "source":doc[2]} for doc in retrieved_docs]

        if expand_context is True or (isinstance(expand_context, int) and expand_context > 0):
            expansion_size = 1 if expand_context is True else expand_context
            retrieved_docs = self.get_expanded_context(retrieved_docs, expansion_size)
        return retrieved_docs
    
    def get_expanded_context(self, retrieved_docs: list[dict], expansion_size: int) -> list[dict]:
        """
        Expand the context of retrieved documents by including adjacent documents.

        For documents from the 'rules' source, this method will fetch additional documents
        before and after each retrieved document. Documents with consecutive IDs are
        merged into a single context block.

        Args:
            retrieved_docs (list[dict]): Original list of retrieved documents
            expansion_size (int): Number of documents to include before and after each result

        Returns:
            list[dict]: Expanded list of documents, where consecutive documents are merged.
                Non-rules documents are preserved as-is. Each merged document contains:
                - id (int): Representative document ID (middle of the group)
                - content (str): Concatenated content of all documents in the group
                - source (str): Document source
                - context_range (str): Range of document IDs included
                - first_appearance (int): Position of first occurrence in original results
        """
        # only expand rules docs
        rules_docs = [doc for doc in retrieved_docs if "rules" in doc.get("source")]
        if len(rules_docs) == 0:
            return retrieved_docs
        
        non_rules_docs = [doc for doc in retrieved_docs if "rules" not in doc.get("source")]

        doc_ids = [doc["id"] for doc in rules_docs]
        doc_ids_to_fetch = set()
        for doc_id in doc_ids:
            # Use the expansion_size parameter to determine range
            for offset in range(-expansion_size, expansion_size + 1):
                doc_ids_to_fetch.add(doc_id + offset)
        
        # Fetch adjacent documents
        sql_query = "SELECT id, content FROM documents WHERE id IN %s AND source='rules' ORDER BY id"
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
                if "rules" in doc.get("source") and doc.get("id") in group
            ]

            if original_positions:
                merged_content = "\n\n".join(doc_map[id] for id in group)
                representative_id = group[len(group)//2] # Use the middle ID from the group as the representative ID
                result.append({
                    "id": representative_id,
                    "content": merged_content,
                    "source": "rules",
                    "context_range": f"docs {group[0]}-{group[-1]}",
                    "first_appearance": min(original_positions)
                })

        # Sort by the original appearance order
        result.sort(key=lambda x: x["first_appearance"])

        result.extend(non_rules_docs)
        return result


# Example usage
if __name__ == "__main__":
    
    query = "How many stall counts in ultimate?"
    print(f"\nQuery: '{query}'")
      
    expand_context=True
    retriever = Retriever()
    for expand_context in [False, 0, True, 1, 2, 3]:
        
        retrieved_docs = retriever.retrieve_similar_documents(query, limit = 5, expand_context=expand_context)
        retrieved_str = "\n".join([doc["content"] for doc in retrieved_docs])
        print(f"\nexpand_context={expand_context}   length={len(retrieved_str)}")

from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
from pgvector.psycopg2 import register_vector
import logging
from openai import OpenAI
import json
import re

logger = logging.getLogger(__name__)

# FTS_JOIN_OPERATOR = " & "
FTS_JOIN_OPERATOR = " | "

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
        logger.debug("creating embedding...", end="\r")
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


    def search(self,
        query: str,
        search_type: str = "hybrid",
        limit: int = 3,
        expand_context: bool|int = False,
        fts_operator: str = "|",
        k: int = 60,
        semantic_weight: float = 0.5,
        fts_weight: float = 0.5,
        query_embedding: list|None = None
    ) -> list[dict]:
        """
        General search method that dispatches to specific search types.

        Args:
            query (str): The search query
            search_type (str): Type of search to perform. One of:
                - "semantic": Semantic similarity search
                - "fts": Full-text search
                - "hybrid": Combined semantic and full-text search (default)
            limit (int, optional): Maximum number of documents to retrieve. Defaults to 3.
            expand_context (bool|int, optional): Controls context expansion around retrieved documents.
            fts_operator(str): The operator ("|" or "&") to use for full-text search. Defaults to "|".
            k (int, optional): Parameter for RRF calculation in hybrid search. Defaults to 60.
            semantic_weight (float, optional): Weight for semantic results in hybrid search. Defaults to 0.5.
            fts_weight (float, optional): Weight for full-text results in hybrid search. Defaults to 0.5.
            query_embedding (list|None, optional): Pre-computed query embedding. If None, 
                embedding will be computed. Defaults to None.

        Returns:
            list[dict]: List of documents matching the search criteria

        Raises:
            ValueError: If an invalid search_type is provided
        """
        search_type = search_type.lower()

        if search_type == "semantic":
            retrieved_docs = self.similarity_search(query=query, limit=limit, query_embedding=query_embedding)
        elif search_type == "fts":
            retrieved_docs = self.fts_search(query=query, limit=limit, fts_operator=fts_operator)
        elif search_type == "hybrid":
            retrieved_docs = self.hybrid_search(
                query=query, limit=limit, fts_operator=fts_operator, 
                k=k, semantic_weight=semantic_weight, fts_weight=fts_weight,
                query_embedding=query_embedding
            )
        else:
            raise ValueError(f"Invalid search_type: {search_type}. Must be one of: 'semantic', 'fts', or 'hybrid'")

        retrieved_docs = [{"id":doc[0], "content":doc[1], "source":doc[3]} for doc in retrieved_docs]

        if expand_context is True or (isinstance(expand_context, int) and expand_context > 0):
            expansion_size = 1 if expand_context is True else expand_context
            retrieved_docs = self.get_expanded_context(retrieved_docs, expansion_size)
        
        return retrieved_docs
    

    def similarity_search(self, query: str, limit: int = 3, query_embedding: list|None = None) -> list[dict]:
        """
        Retrieve documents similar to the input query, with optional context expansion.

        Args:
            query (str): The search query to find similar documents
            limit (int, optional): Maximum number of documents to retrieve. Defaults to 3.
            query_embedding (list|None, optional): Pre-computed query embedding. If None, 
                embedding will be computed. Defaults to None.

        Returns:
            list[dict]: List of documents, where each document is a dictionary containing:
                - id (int): Document ID
                - content (str): Document content
                - source (str): Document source
        """
        if query_embedding is None:
            query_embedding = self.create_embedding(query)
        sql_query = "SELECT * FROM similarity_search(%s::VECTOR, %s);"
        retrieved_docs = self.query_db_sql(sql_query, (query_embedding, limit))
        
        return retrieved_docs
    

    def fts_search(self, query: str, limit: int = 3, fts_operator: str = "OR") -> list[dict]:
        """
        Perform full-text search on documents.

        Args:
            query (str): The search query
            limit (int, optional): Maximum number of documents to retrieve. Defaults to 3.
            fts_operator (str, optional): The operator ("OR" or "AND") to use for full-text search. Defaults to "OR".
        Returns:
            list[dict]: List of documents matching the search criteria
        """
        if fts_operator.upper() not in ["OR", "AND"]:
            raise ValueError(f"Invalid fts_operator: {fts_operator}. Must be one of: 'OR', 'AND'")
        internal_operator = "&" if fts_operator.upper() == "AND" else "|"
        
        # Clean and process the query for full-text search
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        processed_query = f" {internal_operator} ".join(word for word in cleaned_query.split() if word.isalnum())

        sql_query = "SELECT * FROM fts_search(%s, %s);"
        retrieved_docs = self.query_db_sql(sql_query, (processed_query, limit))
        
        return retrieved_docs


    def hybrid_search(self, query: str, limit: int = 3, fts_operator: str = "OR",
        k: int = 60, semantic_weight: float = 0.5, 
        fts_weight: float = 0.5,
        query_embedding: list|None = None) -> list[dict]:
        """
        Perform hybrid search combining semantic similarity and full-text search.

        Args:
            query (str): The search query
            limit (int, optional): Maximum number of documents to retrieve. Defaults to 3.
            fts_operator (str, optional): The operator ("OR" or "AND") to use for full-text search. Defaults to "OR".
            k (int, optional): Parameter for RRF calculation. Defaults to 60.
            semantic_weight (float, optional): Weight for semantic search results. Defaults to 0.5.
            fts_weight (float, optional): Weight for full-text search results. Defaults to 0.5.
            query_embedding (list|None, optional): Pre-computed query embedding. If None, 
                embedding will be computed. Defaults to None.

        Returns:
            list[dict]: List of documents matching the hybrid search criteria
        """
        # Convert operator to internal representation
        if fts_operator.upper() not in ["OR", "AND"]:
            raise ValueError(f"Invalid fts_operator: {fts_operator}. Must be one of: 'OR', 'AND'")
        internal_operator = "&" if fts_operator.upper() == "AND" else "|"
        
        # Convert the query to a format suitable for full-text search
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        processed_query = f" {internal_operator} ".join(word for word in cleaned_query.split() if word.isalnum())
    
        if query_embedding is None:
            query_embedding = self.create_embedding(query)
    
        sql_query = "SELECT * FROM hybrid_search(%s, %s::VECTOR, %s, %s, %s, %s);"
        args = (processed_query, query_embedding, limit, k, semantic_weight, fts_weight)
        retrieved_docs = self.query_db_sql(sql_query, args)
        
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

       
    retriever = Retriever()
    expand_context=0
    limit = 3
    
    query = "how many stall counts?"
    query_embedding = retriever.create_embedding(query)
    print(f"\nQuery: '{query}'")
      
 

    for search_type in ["semantic", "fts", "hybrid"]:
        for fts_operator in ["OR", "AND"]:
            print(f"\n{'*'*80}\n\n{search_type}{fts_operator if search_type in ['hybrid', 'fts'] else ''} search\n")
            retrieved_docs = retriever.search(
                query, 
                search_type=search_type, 
                limit = limit, 
                expand_context=expand_context, 
                fts_operator=fts_operator,
                query_embedding=query_embedding
            )
            for doc in retrieved_docs:
                print(f"ID: {doc['id']}")
                # print(f"CONTENT:\n{doc['content']}")
                # print("\n--------\n")

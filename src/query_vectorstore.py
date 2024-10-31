from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
from pgvector.psycopg2 import register_vector

from openai import OpenAI
import json


client = OpenAI()

def create_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

# Database connection parameters from environment variables
DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')
DB_PORT = os.getenv('POSTGRES_PORT')

# Example: Query documents based on similarity to a given embedding
def query_similar_documents(query_embedding, limit=5):
    
    with psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    ) as conn:
        register_vector(conn)  # Register the VECTOR type
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM query_similar_documents(%s::VECTOR, %s);", (query_embedding, limit))
            return cursor.fetchall()
    

queries = [
    "what is a pick and what happens after a pick is called",
    "How many stall counts in ultimate?",
    "How many stall counts in beach ultimate.",
]

# Example usage
if __name__ == "__main__":
    
    for query in queries:
        print(f"\n\nQuery: '{query}'")
        embedding = create_embedding(query)
        similar_docs = query_similar_documents(embedding, limit = 5)
        if similar_docs:
            for doc in similar_docs:
                print(f"  similarity={doc[2]:.3f}   content='{doc[1]}'")
        else:
            print("No similar documents found or an error occurred.")

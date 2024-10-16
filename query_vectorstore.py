from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
from pgvector.sqlalchemy import Vector
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
    

sentences = [
    "The morning mist rolled gently across the tranquil lake, reflecting the pink hues of dawn.",
    "Engineers unveiled a groundbreaking neural interface allowing direct communication between human brains and computers.",
    "After years of dedicated practice, Maria's violin performance at Carnegie Hall received a standing ovation.",
]

# Example usage
if __name__ == "__main__":
    
    for sentence in sentences:
        print(f"\n\nFinding similar docs for: '{sentence}'")
        # print("Creating embedding")
        embedding = create_embedding(sentence)
        # print("Searching for similar docs...")
        similar_docs = query_similar_documents(embedding)
        if similar_docs:
            # print("Similar Documents:")
            for doc in similar_docs:
                print(f"  similarity={doc[2]:.3f}   Content='{doc[1]}'")
        else:
            print("No similar documents found or an error occurred.")

from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
from pgvector.sqlalchemy import Vector

from openai import OpenAI
import json
import time
from psycopg2 import OperationalError
import argparse


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

# # Establish connection to the PostgreSQL database
# conn = psycopg2.connect(
#     dbname=DB_NAME,
#     user=DB_USER,
#     password=DB_PASSWORD,
#     host=DB_HOST,
#     port=DB_PORT
# )
# cursor = conn.cursor()


# Example: Insert a document with its embedding
def insert_document(content, context, source, embedding):
    with psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO documents (content, context, source, embedding)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (content, context, source, embedding))
            doc_id = cursor.fetchone()[0]
            conn.commit()
            return doc_id

def wait_for_db(max_retries=5, delay=5):
    retries = 0
    while retries < max_retries:
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            conn.close()
            print("Successfully connected to the database")
            return
        except OperationalError as e:
            print(f"Attempt {retries + 1}/{max_retries}: Unable to connect to the database. Retrying in {delay} seconds...")
            retries += 1
            time.sleep(delay)
    raise Exception("Max retries reached. Unable to connect to the database.")

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process embeddings with specified chunk size')
    parser.add_argument('--chunk_size', type=int, default=2000,
                       help='Size of chunks to process (default: 2000)')
    
    args = parser.parse_args()

    wait_for_db()

    expurgated = True
    
    paths = {
        "glossary": f"texts/chunked_embedded/glossary_embeddings.json",
        "rules": f"texts/chunked_embedded/rules_contextual_embeddings_chunk-{args.chunk_size}{'_expurgated' if expurgated else ''}.json"
    }
    for path in paths:
        print(f"Processing {path}...")
        with open(paths[path], "r") as f:
            chunks = json.load(f)

        for i, chunk in enumerate(chunks):
            print(f"{i+1} of {len(chunks)}   ", end = "\r")
            doc_id = insert_document(
                content = chunk["chunk"],
                context = chunk["context"] if "context" in chunk else "This is taken from Ultiworld's Ultimate Glosssary",
                source = path,
                embedding = chunk["embedding"]
            )
            print(f"Inserted document with ID: '{doc_id}' for sentence: '{chunk['chunk']}' ")
        
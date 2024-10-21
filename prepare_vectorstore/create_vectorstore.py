from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
from pgvector.sqlalchemy import Vector

from openai import OpenAI
import json
import time
from psycopg2 import OperationalError


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

# Establish connection to the PostgreSQL database
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
cursor = conn.cursor()


# Example: Insert a document with its embedding
def insert_document(content, source, embedding):
    with psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO documents (content, source, embedding)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (content ,source, embedding))
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
    wait_for_db()  # Add this line before processing the embeddings
    
    path = "prepare_vectorstore/sample_sentence_embeddings.json"
    with open(path, "r") as f:
        sentence_embeddings = json.load(f)

    for sentence, embedding in sentence_embeddings.items():
        source = "samples"
        doc_id = insert_document(sentence, source, embedding)
        print(f"Inserted document with ID: '{doc_id}' for sentence: '{sentence}' ")
    

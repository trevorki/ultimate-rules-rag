from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
from uuid import uuid4
from langchain.text_splitter import RecursiveCharacterTextSplitter
import psycopg2
from psycopg2.extras import register_vector

load_dotenv()

def split_text(text: str, chunk_size: int = 2000, separators: list[str] = ["\n# ","\n## ","\n### ","\n#### ","\n##### ","\n###### ","\n\n\n","\n\n","\n",".","!","?",",",]):
    splitter = RecursiveCharacterTextSplitter(
        separators=separators, chunk_size=chunk_size, chunk_overlap=0
    )
    return splitter.split_text(text)

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ultimate_rules (
                id UUID PRIMARY KEY,
                document TEXT,
                embedding VECTOR(768)  -- Adjust dimensions as per your embedding model
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_embedding ON ultimate_rules USING ivfflat (embedding vector_l2_ops);")
        conn.commit()

if __name__ == "__main__":
    
    # create collection
    collection_name="ultimate_rules"
    embedding_function=embedding_functions.OpenAIEmbeddingFunction(
        model_name="text-embedding-3-large", 
        api_key = os.environ.get("OPENAI_API_KEY")
    )
    persist_directory="./chroma_ultimate_rules_db"

    chroma_client = chromadb.PersistentClient(path=persist_directory)
    collection = chroma_client.get_or_create_collection(
        name=collection_name, 
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"vectorstore created: collection_name = {collection_name}, persist_directory={persist_directory}")

    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", 5432)
    )
    register_vector(conn)
    create_table(conn)

    # load rules text
    files = ["Official-Rules-of-Ultimate-2024-2025.md", "Ultiworld-Ultimate-Glossary.md"]
    for file in files:
        print(f"\nloading {file}")
        with open(f"texts/{file}", encoding="utf8") as f:
            text = f.read()

        # split into chunks
        chunks = split_text(text, chunk_size = 1800)
        
        # add to PostgreSQL
        with conn.cursor() as cur:
            for chunk in chunks:
                cur.execute(
                    "INSERT INTO ultimate_rules (id, document, embedding) VALUES (%s, %s, %s)",
                    (str(uuid4()), chunk, embedding_function.embed(chunk))
                )
        conn.commit()
        print(f"{conn.cursor().execute('SELECT COUNT(*) FROM ultimate_rules').fetchone()[0]} items added")

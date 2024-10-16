from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
from uuid import uuid4
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

def split_text(text: str, chunk_size: int = 2000, separators: list[str] = ["\n# ","\n## ","\n### ","\n#### ","\n##### ","\n###### ","\n\n\n","\n\n","\n",".","!","?",",",]):
    splitter = RecursiveCharacterTextSplitter(
        separators=separators, chunk_size=chunk_size, chunk_overlap=0
    )
    return splitter.split_text(text)

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


    # load rules text
    files = ["Official-Rules-of-Ultimate-2024-2025.md", "Ultiworld-Ultimate-Glossary.md"]
    for file in files:
        print(f"\nloading {file}")
        with open(f"texts/{file}", encoding="utf8") as f:
            text = f.read()

        # split into chunks
        chunks = split_text(text, chunk_size = 1800)
        
        # add to chroma
        collection.add(
            documents=chunks,
            metadatas=[{"source": file} for _ in chunks],
            ids=[str(uuid4()) for _ in chunks]
        )
        print(f"{collection.count()} items added")

import chromadb
from chromadb.utils import embedding_functions
import os
import json
from dotenv import load_dotenv
load_dotenv()


COLLECTION_NAME="ultimate_rules"
PERSIST_DIRECTORY="./chroma_ultimate_rules_db"
EMBEDDING_MODEL_NAME = "text-embedding-3-large"


chroma_client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
embedding_function=embedding_functions.OpenAIEmbeddingFunction(
    model_name=EMBEDDING_MODEL_NAME, 
    api_key = os.environ.get("OPENAI_API_KEY")
)
# load collection
collection = chroma_client.get_collection(
    name=COLLECTION_NAME, 
    embedding_function=embedding_function
)

question = "what do you do when a pick is called?"

response = collection.query(
    query_texts = question, 
    n_results=4, include=["documents", "distances", "metadatas"])


print(response)
docs = response["documents"][0]
metadatas = response["metadatas"][0]
distances = response["distances"][0]
context = [{"distance": distance, "source": metadata["source"], "text": doc} for doc, metadata, distance in zip(docs, metadatas, distances)]
print("\n", json.dumps(context, indent=2))
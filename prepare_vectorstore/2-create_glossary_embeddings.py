from dotenv import load_dotenv
load_dotenv()

import os
from openai import OpenAI
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter


client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def create_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding


# load the definitions
path = "texts/Ultiworld-Ultimate-Glossary.md"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

items = []

chunks = text.split("## ")
print(f"{len(chunks)} chunks")
for i, chunk in enumerate(chunks):
    if chunk == "":
        continue
    chunk = chunk.strip()
    print(f"chunk {i+1} of {len(chunks)}   ", end = "\r")
    embedding = create_embedding(chunk)
    item = {
        "chunk": chunk,
        "embedding": embedding
    }
    items.append(item)
   
with open("texts/glossary_embeddings.json", "w") as f:
    json.dump(items, f, indent = 2)

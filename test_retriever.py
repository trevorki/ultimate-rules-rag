from dotenv import load_dotenv
load_dotenv()

import os
from retriever import Retriever

# Example usage
if __name__ == "__main__":
    
    queries = [
        # "what is a pick and what happens after a pick is called",
        "How many stall counts in ultimate?",
        # "How many stall counts in beach ultimate.",
    ]

    retriever = Retriever()
    for query in queries:
        print(f"\n\nQuery: '{query}'")
        retrieved_docs = retriever.query_similar_documents(query, limit = 5)
        print(retrieved_docs)

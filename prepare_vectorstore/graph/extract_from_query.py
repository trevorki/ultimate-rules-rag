from src.ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
import json
from src.ultimate_rules_rag.db_client import DBClient
from dotenv import load_dotenv

load_dotenv()

query = "what happens when a fast count is contested?"

# model_name = "gpt-4o-2024-08-06"
model_name = "gpt-4o-mini"
entity_relationships_path = f"prepare_vectorstore/graph/entity_relationships_gpt-4o-mini.json"

db_client = DBClient()
abstract_client = get_abstract_client(default_model=model_name)

with open(entity_relationships_path, "r") as f:
    entity_relationships = json.load(f)

prompt = f"""You are translating a question about Ultimate Frisbee rules into a graph query.

Entities and relationships:
{entity_relationships}

User question: "{query}"

Identify:
1. Most relevant start node(s) from the available nodes
2. Most relevant end node(s) from the available nodes
3. Which types of relationships would answer this question

Only use nodes and relationships provided. 
If a concept in the question doesn't match any available nodes, match to the closest relevant node and note this in your explanation.
"""

response_format = {
    "start_nodes": ["node1", "node2"],
    "end_nodes": ["node3"],
    "relevant_relationships": ["rel1", "rel2"],
    "explanation": "brief explanation of why these nodes/relationships will answer the question"
}

response, usage = abstract_client.invoke(
    prompt,
    config={"model": model_name, "temperature": 0.1, "max_tokens": 1000},
    response_format=response_format,
    return_usage=True
)

cost = db_client.calculate_token_cost(model_name, usage["input_tokens"], usage["output_tokens"])

print(f"Model: {model_name}\nTokens: {json.dumps(usage, indent=2)}\nCost: {cost}\n")

print(json.dumps(response, indent=2))

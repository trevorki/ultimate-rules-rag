from src.ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
import json
from src.ultimate_rules_rag.db_client import DBClient

db_client = DBClient()


ENTITY_IDENTIFICATION_PROMPT = """
You are analyzing the rules of Ultimate Frisbee to create a knowledge graph. 
Review these rules and:

1. Identify key recurring entities/concepts. 
- Focus on:
  - key terms defined in section 3 
  - other named terms, especially violations
- Include common alternative terms for each concept, if any found in text
- There should be at least 30 entities

2. Identify common types of relationships between these concepts. 
- Focus on:
  - How concepts affect each other
  - Requirements or prerequisites
  - What causes things
  - What invalidates or prevents things
  - Temporal sequences
- Only include relationships that occur multiple times across different rules
- There should be at least 10 relationships, as general as possible

Avoid:
- One-off concepts that only appear in a single rule
- Very specific or compound relationships
- Relationships that only occur once

Here are the rules:
{rules}
"""
response_format = {
  "entities": [
    {
      "name": "primary term",
      "type": "physical|state|action|violation|role|concept|outcome",
      "alternatives": ["other terms", "that mean", "the same"],
      "description": "brief explanation of this concept in Ultimate"
    }
  ],
  "relationships": [
    {
      "name": "relationship type",
      "description": "what this relationship means in Ultimate",
      "example": "brief example linking two entities"
    }
  ]
}

rules_path = "texts/Official-Rules-of-Ultimate-2024-2025_expurgated.md"
with open(rules_path, "r") as f:
    rules_text = f.read()
output_folder = "prepare_vectorstore/graph"

model_names = [
    # "gpt-4o-mini", 
    "gpt-4o-2024-08-06",
    "claude-3-5-sonnet-20241022",
    # "claude-3-5-haiku-20241022"
]

for model_name in model_names:
    print(f"\n{'-'*30} Model: {model_name} {'-'*50}\n")

    abstract_client = get_abstract_client(default_model=model_name)

    prompt = ENTITY_IDENTIFICATION_PROMPT.format(rules=rules_text)

    config = {"temperature": 0.1, "max_tokens": 5000, "model": model_name}
    response, usage = abstract_client.invoke(prompt, config=config, response_format=response_format, return_usage=True)
    cost = db_client.calculate_token_cost(model_name, usage["input_tokens"], usage["output_tokens"])

    
    output_path = f"{output_folder}/entity_relationships_{model_name}.json"
    
    with open(output_path, "w") as f:
        json.dump(response, f, indent = 2)

    print(f"Model: {model_name}\nTokens: {json.dumps(usage, indent=2)}\nCost: {cost}\n")



from src.ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
import json
from src.ultimate_rules_rag.db_client import DBClient

db_client = DBClient()

type = "resolution_values"
IDENTIFICATION_PROMPT = """
You are analyzing the rules of Ultimate Frisbee to identify the outcomes when rule violations and fouls are resolved.
When a violation or foul is resolved, some entity is affected and changes its value.
For example, a stall count 
Review these rules and identify all the possible outcomes for each entity. Every entity should have at least one (possibley many) values

Here are the main types of rule violations:
{violations}

Here are the entities that are affected when violations and fouls are resolved:
{resolutions}

Here are the rules:
{rules}
"""
response_format = {
    f"{type}": [
        {
            "entity_name": "name of entity affected by resolution",
            "entity_value": "single possible value of many possible values after resolution",
            "explanation": "brief explanation of how the value of the entity is affected by the resolution"
        }
    ],
}

rules_path = "texts/Official-Rules-of-Ultimate-2024-2025_expurgated.md"
with open(rules_path, "r") as f:
    rules_text = f.read()
output_folder = "prepare_vectorstore/graph"

violations_path = "prepare_vectorstore/graph/violations.json"
with open(violations_path, "r") as f:
    violations = json.load(f)

resolutions_path = "prepare_vectorstore/graph/resolution_entities.json"
with open(resolutions_path, "r") as f:
    resolutions = json.load(f)

model_names = [
    # "gpt-4o-mini", 
    "gpt-4o-2024-08-06",
    "claude-3-5-sonnet-20241022",
    # "claude-3-5-haiku-20241022"
]

prompt = IDENTIFICATION_PROMPT.format(rules=rules_text, violations=violations, resolutions=resolutions)
# print(prompt)

for model_name in model_names:
    print(f"\n{'-'*30} Model: {model_name} {'-'*50}\n")

    abstract_client = get_abstract_client(default_model=model_name)

    

    config = {"temperature": 0.1, "max_tokens": 2000, "model": model_name}
    response, usage = abstract_client.invoke(prompt, config=config, response_format=response_format, return_usage=True)
    cost = db_client.calculate_token_cost(model_name, usage["input_tokens"], usage["output_tokens"])

    
    output_path = f"{output_folder}/{type}_{model_name}.json"
    
    with open(output_path, "w") as f:
        json.dump(response, f, indent = 2)

    print(f"Model: {model_name}\nTokens: {json.dumps(usage, indent=2)}\nCost: {cost}\n")



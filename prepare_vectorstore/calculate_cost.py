import json

model_name = "gpt-4o-mini"
path = "texts/rules_contextual_embeddings.json"
with open(path, "r") as f:
    data = json.load(f)

cost_dict = {
    "gpt-4o-mini": {
        "prompt": 0.15/1e6,
        "completion": 0.6/1e6
    }
}

def calculate_cost(model_name, prompt_tokens, completion_tokens):
    model_cost = cost_dict[model_name]
    input_cost = model_cost["prompt"] * prompt_tokens
    output_cost = model_cost["completion"] * completion_tokens
    return input_cost + output_cost

total_cost = 0
for item in data:
    prompt_tokens = item["tokens"]["prompt"]
    completion_tokens = item["tokens"]["completion"]
    cost = calculate_cost(model_name, prompt_tokens, completion_tokens)
    total_cost += cost

print(f"Total cost for {model_name}: ${total_cost:.6f}")

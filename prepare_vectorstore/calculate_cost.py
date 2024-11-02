import json
import argparse

# Add argument parser
parser = argparse.ArgumentParser(description='Calculate embedding costs for chunked text')
parser.add_argument('--chunk-size', type=int, required=True, help='Size of text chunks')
args = parser.parse_args()

model_name = "gpt-4o-mini"
path = f"texts/chunked_embedded/rules_contextual_embeddings_chunk-{args.chunk_size}.json"
with open(path, "r") as f:
    data = json.load(f)

print(f"Calculating cost for {model_name} with {len(data)} chunks")

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

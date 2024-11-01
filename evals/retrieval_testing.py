import json
import pandas as pd
from ultimate_rules_rag.retriever import Retriever  # Updated import to use Retriever class


def load_rules(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def process_eval(eval, retriever, limit, expand_context):
    target_rules = "\n" .join(eval.get("rules"))
    target_rule_numbers = extract_rule_numbers(target_rules)
    
    retrieved_docs = retriever.retrieve_similar_documents(eval.get("question"), limit=limit, expand_context=expand_context)
    retrieved_docs_str = "\n".join([doc["content"] for doc in retrieved_docs])
    retrieved_rule_numbers = extract_rule_numbers(retrieved_docs_str)

    return {
        "section": eval.get('section'),
        "question": eval.get('question'),
        "n_target_rules": len(target_rule_numbers),
        "n_retrieved_rules": len(set(target_rule_numbers) & set(retrieved_rule_numbers)),
        "len_context":  len(retrieved_docs_str)
    }


def extract_rule_numbers(text):
    lines = text.split("\n")
    rule_numbers = [line.split(" ")[0] for line in lines]
    return rule_numbers

def save_results(results, search, limit, expand, chunk_size, folder="evals/results", basename="retrieval"):
    path = f"{folder}/{basename}_chunk-{chunk_size}_search-{search}_lim-{limit}_expand-{expand}.csv"
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)

def test_retrieval(path, searches, limits, expand_contexts, chunk_size):
    for search in searches:
        for expand_context in expand_contexts:
            for limit in limits:
                print(f"search: {search}, expand: {expand_context}, limit: {limit}")
                retriever = Retriever()
                results = []
                evals = load_rules(path)
                for i, eval in enumerate(evals):
                    print(f"\titem {i+1} of {len(evals)}", end = "\r")
                    processed_eval = process_eval(eval, retriever, limit, expand_context)
                    results.append(processed_eval)
                    # if i == 5:
                    #     break
                save_results(results, search, limit, expand_context, chunk_size,
                             folder="evals/results", basename="retrieval")

if __name__ == "__main__":
    folder = "evals/datasets"
    eval_files = [
        'rules_dataset_gpt-4o-2024-08-06_10q.json'
    ]
    chunk_size = 1500
    searches = ["semantic"]#, "fts", "hybrid"]
    limits = [1,2,3,4,5,6]
    expand_contexts = [0,1,2]

    for file in eval_files:   
        path = f"{folder}/{file}"
        test_retrieval(path, searches, limits, expand_contexts, chunk_size) 
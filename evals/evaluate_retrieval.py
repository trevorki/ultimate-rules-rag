import json
import pandas as pd
from ultimate_rules_rag.retriever import Retriever
import argparse


def load_dataset(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def process_eval(eval, retriever, search_type, fts_operator, limit, expand_context):
    target_rules = "\n" .join(eval.get("rules"))
    target_rule_numbers = extract_rule_numbers(target_rules)
    
    retrieved_docs = retriever.search(
        eval.get("question"), 
        search_type = search_type, 
        fts_operator = fts_operator,
        limit=limit, 
        expand_context=expand_context,
        query_embedding = eval.get("question_embedding")
    )
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
        for fts_operator in ["AND", "OR"]:
            if fts_operator in search:
                search_type = search.split(fts_operator)[0]   
                break
            else:
                search_type = search
                fts_operator = None

        for expand_context in expand_contexts:
            for limit in limits:
                print(f"search: {search_type}{fts_operator if fts_operator else ''}, expand: {expand_context}, limit: {limit}")
                retriever = Retriever()
                results = []
                evals = load_dataset(path)
                for i, eval in enumerate(evals):
                    print(f"\titem {i+1} of {len(evals)}", end = "\r")
                    processed_eval = process_eval(eval, retriever, search_type, fts_operator, limit, expand_context)
                    results.append(processed_eval)
                #     # if i == 5:
                #     #     break
                save_results(results, search, limit, expand_context, chunk_size,
                             folder="evals/results/retrieval", basename="retrieval")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate retrieval with specified chunk size')
    parser.add_argument('--chunk_size', type=int, help='Size of chunks to process')
    args = parser.parse_args()

    folder = "evals/datasets"
    eval_file = 'rules_dataset_gpt-4o-2024-08-06_10q.json'
    searches = [
        "semantic", 
        "ftsOR", 
        "hybridAND", 
        "hybridOR"
    ]
    limits = [1,2,3,4,5,]
    expand_contexts = [0,1]

    path = f"{folder}/{eval_file}"
    test_retrieval(path, searches, limits, expand_contexts, args.chunk_size) 
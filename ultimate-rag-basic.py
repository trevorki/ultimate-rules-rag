from dotenv import load_dotenv
load_dotenv()

import os
from retriever import Retriever
import json
from pydantic import BaseModel, Field
from typing import Optional

from openai import OpenAI

openai_client = OpenAI()
MODEL = "gpt-4o-mini"
usage = []

def answer_question(query, context):
    prompt = f"""
    You are a helpful assistant that can answer questions about the rules of ultimate frisbee.
    You are given a question and a context of retrieved documents.
    Answer the question based on the context.
    Special Instructions:
    - The answer should be direct and to the point, preferably in one sentence. Only elaborate if necessary.
    - If you cannot answer the question based on the context, say "I don't know."
    - If the question is not about ultimate frisbee, say "That is not a question about ultimate frisbee."
    - If the context is from the rules, answer the question, then include the relevant rule(s) with rule numbers quoted verbatim in your answer.

    Question: {query}
    Context: {context}

    """
    class Answer(BaseModel):
        answer: str = Field(description="Your answer to the question.")
        rules: Optional[list[str]] = Field(description="The relevant rule(s) with rule numbers quoted verbatim in your answer.")

    response = openai_client.beta.chat.completions.parse(
        model=MODEL,
        messages=[{"role": "system", "content": prompt}],
        response_format=Answer,
    )
    usage.append(response.usage)
    return response.choices[0].message.parsed


queries = [
    # "what is a pick and what happens after a pick is called",
    # "How many stall counts in ultimate?",
    # "How many stall counts in beach ultimate.",
    # "How many stall counts in 4-on-4 ultimate.",
    # "What happens if the offensive team drops the pull while trying to catch it?",
    "if the pull lands and bounces then offense attempts to catch it but drops it, is it a turnover?"
    ]

# Example usage
if __name__ == "__main__":
    retriever = Retriever()
    
    # for query in queries:
    #     print(f"\n\nQuestion: '{query}'")
    #     retrieved_docs = retriever.retrieve_similar_documents(query, limit = 5, expand_context=True)
    #     context = [{'source': doc['source'], 'content': doc['content']} for doc in retrieved_docs]
    #     answer = answer_question(query, context)
    #     print(f"Answer: {answer.answer}")
    #     if answer.rules:
    #         print(f"Relevant rules:")
    #         print('\t' + ',\n- '.join(answer.rules))
    
    query = None
    print("Enter a question (or 'q' to quit): ")
    while query != "q":
        query = input("\n\nQUESTION: ")
        if query != "q":
            retrieved_docs = retriever.retrieve_similar_documents(query, limit = 5, expand_context=True)
            context = [{'source': doc['source'], 'content': doc['content']} for doc in retrieved_docs]
            answer = answer_question(query, context)
            print(f"\nANSWER: {answer.answer}")
            if answer.rules:
                print(f"\nRELEVANT RULES:")
                print('\t' + ',\n- '.join(answer.rules))


    prompt_tokens = sum([u.completion_tokens for u in usage])
    completion_tokens = sum([u.prompt_tokens for u in usage])
    token_costs = {
        "gpt-4o-2024-08-06": {
            "prompt": 2.5/1e6,
            "completion": 10/1e6
        },
        "gpt-4o-mini": {
            "prompt": 0.15/1e6,
            "completion": 0.60/1e6
        }
    }
    prompt_token_cost = prompt_tokens * token_costs[MODEL]["prompt"]
    completion_token_cost = completion_tokens * token_costs[MODEL]["completion"]
    cost = prompt_token_cost + completion_token_cost
    print(f"\n\ncost:\n\tprompt: ${prompt_token_cost:.6f}\n\tcompletion: ${completion_token_cost:.6f}\n\ttotal: ${cost:.5f}")

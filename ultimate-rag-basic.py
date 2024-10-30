from dotenv import load_dotenv
load_dotenv()

import os
from retriever import Retriever
import json
from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Dict

from openai import OpenAI

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

openai_client = OpenAI()
MODEL = "gpt-4o-mini"

class Reference(BaseModel):
    source: str = Field(description="The source of the context. Either 'rules' or 'glossary'.")
    content: str = Field(description="The verbatim content of the reference, including rule numbers for rules or terms for glossary.")

class Answer(BaseModel):
    answer: str = Field(description="Your answer to the question.")
    references: Optional[list[Reference]] = Field(description="The relevant references to the context that led to the answer. In the case of rules that refer to other rules, include the other rules if possible.")


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    
    TOKEN_COSTS: ClassVar[Dict[str, Dict[str, float]]] = {
        "gpt-4o-2024-08-06": {"prompt": 2.5/1e6, "completion": 10/1e6},
        "gpt-4o-mini": {"prompt": 0.15/1e6, "completion": 0.60/1e6}
    }

    def add_usage(self, usage_info):
        self.input_tokens += usage_info.prompt_tokens
        self.output_tokens += usage_info.completion_tokens

    def get_cost(self, model: str) -> dict:
        prompt_cost = self.input_tokens * self.TOKEN_COSTS[model]["prompt"]
        completion_cost = self.output_tokens * self.TOKEN_COSTS[model]["completion"]
        return {
            "prompt": prompt_cost,
            "completion": completion_cost,
            "total": prompt_cost + completion_cost
        }

class RagChatSession(BaseModel):
    model: str
    stream_output: bool
    retriever: Retriever
    usage: Usage
    model_config = {
        "arbitrary_types_allowed": True
    }

    def __init__(self, model=MODEL, stream_output=False):
        super().__init__(
            model=model,
            stream_output=stream_output,
            retriever=Retriever(),
            usage=Usage()
        )

    def _get_docs(self, query: str) -> list:
        logger.info(f"Getting similar documents")
        return self.retriever.retrieve_similar_documents(query, limit=5, expand_context=True)

    def _prepare_context(self, context: list) -> str:
        return "\n".join([f"{doc['source']}: {doc['content']}" for doc in context])

    def _get_llm_answer(self, query: str, context: list) -> Answer:
        logger.info(f"Getting answer with llm")
        prompt = f"""
        You are a helpful assistant that can answer questions about the rules of ultimate frisbee.
        You are given a question and a context of retrieved documents.
        Answer the question based on the context.
        Special Instructions:
        - The answer should be direct and to the point, preferably in one sentence. Only elaborate if necessary.
        - If you cannot answer the question based on the context, say "I don't know."
        - If the question is not about ultimate frisbee, say "That is not a question about ultimate frisbee."
        - If the context is from the rules, answer the question, then include the relevant rule(s) with rule numbers quoted verbatim in your answer.
        - If the context is from the glossary, do not include the relevant rule(s) in your answer.

        Question: {query}
        Context: {context}
        """.replace("    ", "")

        response = openai_client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
            response_format=Answer,
        )
        self.usage.add_usage(response.usage)
        return response.choices[0].message.parsed

    def answer_question(self, query: str):
        retrieved_docs = self._get_docs(query)
        context = self._prepare_context(retrieved_docs)
        answer = self._get_llm_answer(query, context)
        return answer

    def get_cost(self) -> dict:
        return self.usage.get_cost(self.model)



# Example usage
if __name__ == "__main__":
    session = RagChatSession()
    
    print("Enter a question (or 'q' to quit): ")
    query = None
    while query != "q":
        query = input("\n\nQUESTION: ")
        if query != "q":
            answer = session.answer_question(query)
            print(f"\nANSWER: {answer.answer}")
            if answer.references:
                print(f"\nRELEVANT REFERENCES:")
                print('\t' + ',\n- '.join([f"{r.source}: {r.content}" for r in answer.references]))

    costs = session.get_cost()
    print(f"\n\ncost:\n\t{costs.model_dump(indent=2)}")
  
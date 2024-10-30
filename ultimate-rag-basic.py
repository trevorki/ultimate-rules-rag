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

# Any questions not relevant to ultimate should not be answered
# - If the question is not about ultimate frisbee, say "Sorry, I can only answer questions about ultimate"
SYSTEM_PROMPT = f"""
You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 

Special Instructions:
- The answer should be direct and to the point, preferably in one sentence. Only elaborate if necessary.
- If you cannot answer the question based on the context, say "I don't know."
- You may consult previous messages for more context or to continue the conversation.
- If a rule was consulted to answer the question, state include the rule number and full text of the relevant rule or rules. 

The optional Relevant Rules section should be formatted like this:
Relevant Rules:
**Rule 1 number**: Rule 1 text
**Rule 2 number**: Rule 2 text
...


"""

class Usage(BaseModel):
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    n_calls: int = 0
    
    TOKEN_COSTS: ClassVar[Dict[str, Dict[str, float]]] = {
        "gpt-4o-2024-08-06": {"prompt": 2.5/1e6, "completion": 10/1e6},
        "gpt-4o-mini": {"prompt": 0.15/1e6, "completion": 0.60/1e6}
    }

    def add_usage(self, usage_info):
        self.input_tokens += usage_info.prompt_tokens
        self.output_tokens += usage_info.completion_tokens
        self.n_calls += 1

    def get_usage(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "n_calls": self.n_calls
        }

    def get_cost(self) -> dict:
        prompt_cost = self.input_tokens * self.TOKEN_COSTS[self.model]["prompt"]
        completion_cost = self.output_tokens * self.TOKEN_COSTS[self.model]["completion"]
        return {
            "input_cost": prompt_cost,
            "output_cost": completion_cost,
            "total_cost": prompt_cost + completion_cost
        }
    
    def pretty_print(self):
        costs = self.get_cost()
        print("USAGE:")
        print(f"\tmodel:    {self.model}")
        print(f"\tn_calls:  {self.n_calls}")
        print(f"\tinput_tokens:   {self.input_tokens}")
        print(f"\toutput_tokens:  {self.output_tokens}")
        print(f"\tinput_cost:   ${costs['input_cost']:.4f}")
        print(f"\toutput_cost:  ${costs['output_cost']:.4f}")
        print(f"\ttotal_cost:   ${costs['total_cost']:.4f}")

class ConversationHistory(BaseModel):
    messages: list[dict]
    memory_size: int

    def __init__(self, memory_size: int = 3):
        super().__init__(messages=[], memory_size=memory_size)
        self.add_message("system", SYSTEM_PROMPT)

    def add_message(self, role: str, message: str):
        self.messages.append({"role": role, "content": message})

    def prune_history(self):
        initial_length = len(self.messages)
        user_messages = [msg for msg in self.messages if msg["role"] == "user"]
        if len(user_messages) > self.memory_size:
            cutoff_index = self.messages.index(user_messages[-self.memory_size])
            self.messages = [self.messages[0]] + self.messages[cutoff_index:]
            final_length = len(self.messages)
            logger.info(f"Pruned history from {initial_length} to {final_length} messages")

    def pretty_print(self):
        print("\n\nCONVERSATION HISTORY:")
        for msg in self.messages:
            print(f"\n{msg['role'].upper()}: {msg['content']}")


class RagChatSession(BaseModel):
    model: str
    stream_output: bool
    retriever: Retriever
    history: ConversationHistory
    usage: Usage

    model_config = {
        "arbitrary_types_allowed": True
    }

    def __init__(self, model=MODEL, stream_output=True, memory_size: int = 3):
        super().__init__(
            model=model,
            stream_output=stream_output,
            retriever=Retriever(),
            history=ConversationHistory(memory_size=memory_size),
            usage=Usage(model=model)
        )

    def _get_docs(self, query: str) -> list:
        logger.info(f"Getting similar documents")
        return self.retriever.retrieve_similar_documents(query, limit=5, expand_context=False)

    def _prepare_context(self, context: list) -> str:
        return "\n\n".join([f"{doc['source']}:\n{doc['content']}" for doc in context])

    def _get_llm_answer(self, query: str, context: list) -> str:
        logger.info(f"Getting answer with llm")
        prompt = f"Question: {query}\nContext: {context}"
        self.history.add_message("user", prompt)

        response = openai_client.chat.completions.create(
            model=self.model,
            messages=self.history.messages,
            stream=self.stream_output
        )
        if self.stream_output:
            collected_chunks = []
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    collected_chunks.append(chunk.choices[0].delta.content)
                    print(chunk.choices[0].delta.content, end="", flush=True)
            
            # Collect the full response for usage tracking
            full_response = "".join(collected_chunks)

            self.history.add_message("assistant", full_response)
            self.history.prune_history()

            # Note: Usage is not available in streaming mode, so we'll need to estimate
            self.usage.add_usage(type('Usage', (), {'prompt_tokens': len(prompt) // 4, 'completion_tokens': len(full_response) // 4})())
            return full_response
        else:
            self.usage.add_usage(response.usage)
            return response.choices[0].message.content

    def answer_question(self, query: str):
        retrieved_docs = self._get_docs(query)
        context = self._prepare_context(retrieved_docs)
        answer = self._get_llm_answer(query, context)
        return answer



# Example usage
if __name__ == "__main__":
    session = RagChatSession(stream_output=True)  
    
    print("Enter a question (or 'q' to quit): ")
    query = None
    while query != "q":
        query = input("\n\nQUESTION: ")
        if query != "q":
            print("ANSWER:")
            answer = session.answer_question(query)
            if not session.stream_output:  
                print(answer)


    

    print(f"\n\nhistory:")
    session.history.pretty_print()

    print(f"\n\ncost:")
    session.usage.pretty_print()
  
import chromadb
from chromadb.utils import embedding_functions
import os
from openai import OpenAI
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
import json
from prompts import get_rag_prompts, get_assistant_prompt
from typing import Optional
from tools import get_tool_definitions

load_dotenv()

COLLECTION_NAME="ultimate_rules"
PERSIST_DIRECTORY="./chroma_ultimate_rules_db"
EMBEDDING_MODEL_NAME = "text-embedding-3-large"
# GENERATION_MODEL_NAME = "gpt-4o-mini-2024-07-18"
GENERATION_MODEL_NAME = "gpt-4o-2024-08-06"
RAG_SYSTEM_MESSAGE = """You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 
State the answer succinctly in plain language and include the full text of the relevant rule(s) used to generate your answer.
Structure your responses like this:
<answer>

**Relevant Rules:** (omit if no rules cited)

**<rule number 1>**: <rule text 1>
**<rule number 2>**: <rule text 2>
<etc...>

If a question is not relevant to ultimate, then say "I only know about ultimate :("
If you don't know the answer based on the provided context, DO NOT MAKE ANYTHING UP, just say "I don't know".
"""

class ConversationHistory:
    def __init__(self, user_message_memory_size = 3):
        self.history = []
        self.user_message_memory_size = user_message_memory_size

    def update(self, role, content, name = None):
        message = {"role": role, "content": content}
        if name:
            message["name"] = name
        self.history.append(message)

    def get_recent(self):
        system_message = next((msg for msg in self.history if msg["role"] == "system"), None)
        user_messages = [msg for msg in self.history if msg["role"] == "user"]
        recent_messages = user_messages[-self.user_message_memory_size:]
        
        start_index = self.history.index(recent_messages[0]) if recent_messages else len(self.history)
        recent_history = self.history[start_index:]
        
        if system_message:
            recent_history = [system_message] + recent_history
        
        return recent_history

    def get(self):
        return self.history

class RagChat(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

    model_name: str
    embedding_model_name: str
    collection_name: str
    collection_path: str
    n_results: int
    openai_client: OpenAI
    history: ConversationHistory
    chroma_client: Optional[chromadb.Client] = None
    collection: Optional[chromadb.Collection] = None
    tools: list = []
    token_count: dict = {"prompt": 0, "completion": 0}

    def __init__(self, server = False, user_message_memory_size = 3, n_results = 5):
        super().__init__(
            model_name=GENERATION_MODEL_NAME,
            embedding_model_name=EMBEDDING_MODEL_NAME,
            collection_name=COLLECTION_NAME,
            collection_path=PERSIST_DIRECTORY,
            n_results=n_results,
            openai_client=OpenAI(),
            history=ConversationHistory(user_message_memory_size)
        )
        self.history.update("system", RAG_SYSTEM_MESSAGE)
        self.load_collection(server=server)

    def load_collection(self, server = False):
        if server:
            self.chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        else:
            self.chroma_client = chromadb.PersistentClient(path=self.collection_path) 
        self.collection = self.chroma_client.get_collection(
            name=COLLECTION_NAME, 
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                model_name=EMBEDDING_MODEL_NAME, 
                api_key = os.environ.get("OPENAI_API_KEY")
                )
            )
        return

    def load_tools(self, tools_to_use):
        return get_tool_definitions(tools_to_use)
    
    def update_token_count(self, response):
        usage = response.usage
        self.token_count["prompt"] += usage.prompt_tokens
        self.token_count["completion"] += usage.completion_tokens
        # print(f"Tokens used - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}")
        # print(f"Total tokens - Prompt: {self.token_count['prompt']}, Completion: {self.token_count['completion']}")
    
    def calculate_session_cost(self, verbose = True):
        model_costs = {
            "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
            "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
            "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00}
        }
        input_price_per_million = model_costs[self.model_name]["input"]
        output_price_per_million = model_costs[self.model_name]["output"]
        input_cost = (self.token_count["prompt"] / 1_000_000) * input_price_per_million
        output_cost = (self.token_count["completion"] / 1_000_000) * output_price_per_million
        total_cost = input_cost + output_cost
        if verbose:
            print(f"Input cost: ${input_cost:.5f}\nOutput cost: ${output_cost:.5f}\nTotal cost: ${total_cost:.5f}")
        return input_cost, output_cost, total_cost

    def retrieval_activator(self, question: str):
        prompt = f"""You are an expert at the rules of Ultimate. 
        Given a question, determine if there is enough information in the given conversation 
        history to properly answer the question or if you need to retrieve more information. 
        If you can't answer the question with the information in the conversation, then say "RETRIEVE".
        If you can answer the question with the information in the conversation, then say "NO_RETRIEVE.
        Here is the conversation history: {self.history.get()}
        Here is the question: {question}
        Respond with one of 'RETRIEVE' or 'NO_RETRIEVE'.
        RESPONSE: """
        response = self.openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-2024-08-06",
            temperature=0.25,
        )
        self.update_token_count(response)
        return response.choices[0].message.content
    
    def query_rewrite_activator(self, query: str):
        prompt = f"""You are an expert at information retrieval and the rules of Ultimate. 
        Given a question, and the conversation history, determine if the question needs to 
        be rewritten in order to retrieve more information about the question.
        Respond with one of 'REWRITE' or 'NO_REWRITE'.
        
        For example:
        CONVERSATION HISTORY:
        [{{"role": "user", "content": "what color is the sky?"}},
        {{"role": "assistant", "content": "the sky is blue"}}]
        
        QUESTION: "what else is that same color?"
        
        RESPONSE: REWRITE
        
        REASONING:
        The question refers to a past item in the conversation, "that" so we need to look back 
        in the conversation history to determine what "that" is referring to.

        
        Here is the conversation history: {self.history.get()}
        Here is the question: {question}
        RESPONSE: """

        response = self.openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model_name,
            temperature=0.25,
        )
        self.update_token_count(response)
        return response.choices[0].message.content
    
    def query_rewriter(self, question: str):
        prompt = f"""You are an expert at information retrieval and the rules of Ultimate. 
        Given a question that contains a reference to a past part of the conversation, and the 
        conversation history, rewrite the question so that it contains all the necessary 
        information to retrieve information about it.
        Answer with one of only the re-written question and nothing else.
        
        For example:
        CONVERSATION HISTORY:
        [{{"role": "user", "content": "what color is the sky?"}},
        {{"role": "assistant", "content": "the sky is blue"}}]
        QUESTION: "what else is that same color?"
        REWRITTEN QUESTION: "what else is blue?
        
        Here is the conversation history: {self.history.get()}
        Here is the question: {question}
        REWRITTEN: """
        response = self.openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model_name,
            temperature=0.25,
        )
        return response.choices[0].message.content



    def retriever(self, query: str):
        response = self.collection.query(
            query_texts=query, 
            n_results=self.n_results, 
            include=["documents", "metadatas"]
        )
        docs = response["documents"]
        metadatas = response["metadatas"][0]
        context = [{"source": metadata["source"], "text": doc} for doc, metadata in zip(docs, metadatas)]
        return context
    

    def answer_question(self, question):
        prompt = f"""
        Use the information from the following context to answer the question. 
        If you don't know the answer, just say that you don't know. 

        QUESTION: 
        {question}

        CONTEXT: 
        {self.history.get_recent()}

        ANSWER: """


        response = self.openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model_name,
            temperature=0.25,
        )
        self.update_token_count(response)
        answer = response.choices[0].message.content
        return answer


def ultimate_rules_chat():
    chat = RagChat(server = False, user_message_memory_size = 3, n_results = 4)

    print("Welcome to Ultimate Rules Q&A!")
    print("Type 'quit' to end the session.")

    while True:
        question = input("\nHUMAN: ").strip()
        if question.lower() in ['quit', 'q']:
            break
        else:            

            question = chat.query_rewriter(question)
            print(f"\nQuery Rewriter: {question}")
            
            context = chat.retriever(question)
            print(f"Question: {question}")

            chat.history.update("user", question)
            chat.history.update("assistant", "I am retrieving some information to help answer the question")
            chat.history.update("tool", f"Here is some context: {context}", name = "get_context")

            answer = chat.answer_question(question)
            chat.history.update("assistant", answer)

            print(f"\nAnswer: {answer}")


    print("Chat history: \n", json.dumps(chat.history.get(), indent=2))


    chat.calculate_session_cost(verbose = True)


if __name__ == "__main__":
    ultimate_rules_chat()


    
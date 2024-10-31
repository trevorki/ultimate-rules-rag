import chromadb
from chromadb.utils import embedding_functions
import os
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import json

load_dotenv()

COLLECTION_NAME="ultimate_rules"
PERSIST_DIRECTORY="./chroma_ultimate_rules_db"
EMBEDDING_MODEL_NAME = "text-embedding-3-large"
USER_MESSAGE_MEMORY_SIZE = 3
GENERATION_MODEL_NAME = "gpt-4o-mini-2024-07-18"
# GENERATION_MODEL_NAME = "gpt-4o-2024-08-06"

class ChromaDBHandler:
    @staticmethod
    def load_collection(server=True):
        if server:
            chroma_client = chromadb.HttpClient(host="localhost",  port=8000)
        else:
            chroma_client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

        embedding_function=embedding_functions.OpenAIEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME, 
            api_key = os.environ.get("OPENAI_API_KEY")
        )
        return chroma_client.get_collection(name=COLLECTION_NAME, 
                                            embedding_function=embedding_function)

class PromptHandler:
    @staticmethod
    def prepare_prompt_messages(question: str, context: str):
        """
        Prepares the prompt messages for the LLM.

        Args:
            question (str): The question to answer.
            context (str): The context to use for answering the question.
        """
        system_message = """You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 
        Answer succinctly. Any questions not relevant to ultimate should not be answered"""
        special_instructions = """State the answer and include the full text of the relevant rule or rules used to generate your answer.
        Structure your responses like this:
        <answer>
        
        Relevant Rules:
        <relevant rule 1>
        <relevant rule 2>
        ..."""
        human_message = f"""Use the following pieces of retrieved context to answer the question. 
        If you don't know the answer, just say that you don't know. 

        QUESTION: 
        {question} 

        CONTEXT: 
        {'\n'.join(f'ITEM {i+1}: """\n{item}\n"""' for i, item in enumerate(context))} 

        SPECIAL INSTRUCTIONS: 
        {special_instructions}

        ANSWER: """.replace("    ", "")
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": human_message},
        ]
        return messages

class Answer(BaseModel):
    answer: str
    relevant_rules: list[str]

class CostCalculator:
    @staticmethod
    def calculate_session_cost(total_input_tokens, total_output_tokens, model_name):
        model_costs = {
            "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
            "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
            "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00}
        }
        input_price_per_million = model_costs[model_name]["input"]
        output_price_per_million = model_costs[model_name]["output"]
        input_cost = (total_input_tokens / 1_000_000) * input_price_per_million
        output_cost = (total_output_tokens / 1_000_000) * output_price_per_million
        total_cost = input_cost + output_cost
        return input_cost, output_cost, total_cost

class QASession:
    def __init__(self, stream_output=True):
        self.collection = ChromaDBHandler.load_collection()
        self.client = OpenAI()
        self.model = GENERATION_MODEL_NAME
        self.stream_output = stream_output
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.question_count = 0
        self.conversation_history = [
            {"role": "system", "content": "You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). Answer succinctly based on the conversation history."}
        ]

    def run(self):
        print("Welcome to the Ultimate Frisbee Rules Q&A System!")
        print("Type 'quit' or 'exit' to end the session.")

        while True:
            question = input("\nEnter your question: ").strip()
            if question.lower() in ['quit', 'exit']:
                break

            self.question_count += 1
            self.process_question(question)

        self.end_session()

    def process_question(self, question):
        decision = self.make_agent_decision(question)
        context = None

        if decision == "USE_HISTORY":
            print("\nDECISION: USE_HISTORY")
            messages = self.conversation_history + [{"role": "user", "content": question}]
        else:  # RETRIEVE_DOCUMENTS
            print("\nDECISION: RETRIEVE_DOCUMENTS")
            context = self.collection.query(query_texts=question, n_results=4, include=["documents"])["documents"]
            messages = PromptHandler.prepare_prompt_messages(question, context)

        answer = self.get_answer(messages)
        self.update_conversation_history(question, answer)

    def make_agent_decision(self, question):
        agent_decision_messages = [
            {
                "role": "system", 
                "content": "You are an agent deciding whether to use existing conversation history or retrieve new documents to answer a question about ultimate frisbee rules."
            },
            {
                "role": "user", 
                "content": f"""
                Question: {question}
                Conversation history: {self.conversation_history}
                Decide whether to use the existing conversation history or retrieve new documents. 
                Respond with either 'USE_HISTORY' or 'RETRIEVE_DOCUMENTS'."""
             }
        ]
        agent_decision = self.client.chat.completions.create(
            messages=agent_decision_messages,
            model=self.model,
            temperature=0.1,
            stream=False
        )
        decision = agent_decision.choices[0].message.content.strip()
        return decision

    def get_answer(self, messages):
        if self.stream_output:
            return self.stream_answer(messages)
        else:
            return self.non_stream_answer(messages)

    def stream_answer(self, messages):
        print("\nANSWER:")
        response = self.client.chat.completions.create(
            messages=messages, 
            model=self.model,
            temperature=0.1,
            stream=True
        )

        answer = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                answer += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end='', flush=True)
        print()  # New line after answer
        return answer

    def non_stream_answer(self, messages):
        response = self.client.chat.completions.create(
            messages=messages, 
            model=self.model,
            temperature=0.1,
            stream=False
        )
        answer = response.choices[0].message.content
        print("\nANSWER:")
        print(answer)

        self.total_input_tokens += response.usage.prompt_tokens
        self.total_output_tokens += response.usage.completion_tokens
        return answer

    def update_conversation_history(self, question, answer):
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": answer})

        user_messages = [msg for msg in self.conversation_history if msg["role"] == "user"]
        if len(user_messages) > USER_MESSAGE_MEMORY_SIZE:
            cutoff_index = self.conversation_history.index(user_messages[-USER_MESSAGE_MEMORY_SIZE])
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[cutoff_index:]

    def end_session(self):
        print("\nThank you for using the Ultimate Frisbee Rules Q&A System. Goodbye!")
        
        if self.question_count > 0 and not self.stream_output:
            self.print_session_summary()

        self.save_conversation_history()

    def print_session_summary(self):
        input_cost, output_cost, total_cost = CostCalculator.calculate_session_cost(self.total_input_tokens, self.total_output_tokens, self.model)
        print(f"\nSESSION SUMMARY:")
        print(f"Model: {self.model}")
        print(f"Questions asked: {self.question_count}")
        print(f"Total input tokens: {self.total_input_tokens}")
        print(f"Total output tokens: {self.total_output_tokens}")
        print(f"Input cost: ${input_cost:.6f}")
        print(f"Output cost: ${output_cost:.6f}")
        print(f"Total cost: ${total_cost:.6f}")

    def save_conversation_history(self):
        with open("conversation_history.txt", "w") as f:
            json.dump(self.conversation_history, f, indent=2)

if __name__ == "__main__":
    stream_output = False
    session = QASession(stream_output)
    session.run()
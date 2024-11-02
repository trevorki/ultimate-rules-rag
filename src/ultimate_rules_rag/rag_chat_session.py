from dotenv import load_dotenv
load_dotenv()

import os
from .retriever import Retriever
import json
from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Dict, Tuple
from anthropic import Anthropic
from .conversation_history import ConversationHistory
from .clients.base_client import BaseClient

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Any questions not relevant to ultimate should not be answered
# 
SYSTEM_PROMPT = """
You are Cal, an helpful assistant for question-answering tasks about the sport of ultimate (ultimate frisbee).
Your personality is friendly and just a little sassy when someone starts to stray from the topic.
The sport is called "ultimate" not "ultimate frisbee" so you refer to it as "ultimate".
Your tasks are to:
1. Answer questions based on the provided context
2. Respond to user follow-up questions based on the conversation history, as long as it is about ultimate
"""

class Context(BaseModel):
    context: list[str]
    context_size: int

    def __init__(self, context_size: int = 3):
        super().__init__(context=[], context_size=context_size)

    def add_context(self, context: str):
        self.context.append(context)

    def prune_context(self):
        if len(self.context) > self.context_size:
            self.context = self.context[-self.context_size:]

    def get_context(self) -> str:
        return "\n\n".join(self.context)

class RagChatSession(BaseModel):
    llm_client: BaseClient
    stream_output: bool
    retriever: Retriever
    context: Context
    history: ConversationHistory

    model_config = {
        "arbitrary_types_allowed": True
    }

    def __init__(self, llm_client: BaseClient, stream_output=True, memory_size: int = 3, context_size: int = 1):
        super().__init__(
            llm_client=llm_client,
            stream_output=stream_output,
            retriever=Retriever(),
            context=Context(context_size=context_size),
            history=ConversationHistory(memory_size=memory_size, system_prompt=SYSTEM_PROMPT),
        )

    def _get_docs(self, query: str, **kwargs) -> list:
        logger.info(f"Getting similar documents for query: {query}")
        return self.retriever.search(query, **kwargs)

    def _prepare_context(self, context: list) -> str:
        context_items = []
        for doc in context:
            item = {"source": doc['source'], "content": doc['content']}
            context_items.append(item)
        context_str = json.dumps(context_items)
        self.context.add_context(context_str)
        return context_str
    
    def _get_llm_answer(self, query: str) -> str:
        logger.info(f"Getting answer with LLM for query: {query}")
        context = self.context.get_context()

        prompt = f"""
        <context>
        {context}
        </context>

        <instructions>
        - Only use information from the provided context to answer the question
        - Say "I don't know" if the context doesn't contain the answer
        - Say "Sorry, I only know about ultimate" if the question is not about ultimate frisbee
        - Cite the rules used to answer the question
        </instructions>

        <question>
        {query}
        </question>
        """.replace("    ", "")

        class Answer(BaseModel):
            answer: str = Field(description="The answer to the question. It should be concise, preferably in one sentence. Exceptions are allowed if the answer includes a long list")
            relevant_rules: list[str] = Field(description="All the rules used to answer the question. Each rule should include the rule number (if present) and the full verbatim text of the rule.")
            error: Optional[str] = Field(description="There is a problem formulating an answer, then this field should be the reason why. Otherwise, it should be None.")
            
        response = self.llm_client.invoke(
            messages=self.history.messages + [{"role": "user", "content": prompt}],
            response_format=Answer
        )
        # print(f"\nresponse: {response}")

        answer = f"{response.answer}\n\nRelevant rules:\n{'\n'.join(response.relevant_rules)}"

        self.history.add_message("user", query)
        self.history.add_message("assistant", answer)
        return answer
    

    def process_user_input(self, user_input: str) -> Tuple[str, str]:
        """
        Processes the user input and determines whether to retrieve more information or use existing history.
        """
        class Response(BaseModel):
            retrieve_more_info: bool = Field(description="Whether to retrieve more information")
            query: str = Field(description="The possibly reworded query")

        system_prompt = f"""You are an assistant for question-answering tasks about the sport of ultimate (ultimate frisbee). 
        All questions are in the context of ultimate frisbee."""

        user_prompt = f"""
        Given the following conversation history, retrieved context, and the current user input, decide whether to retrieve more information or use existing information in the context. 

        Retrieval rules:
        - If the user's question cannot answered by the context, then retrieve more information.
        - if there is no context you must retrieve more information

        Rewording rules:
        - If retrieve_more_info=True, then examine the past few questions and possibly reword the user input to make it suitable for document retrieval. This is just to ensure that anything previously discussed is referred to by name and not as "it".
        - If the question does not contain any references to previously discussed concepts, then do not reword it.
        - If the last few questions discuss a concept and the latest question refers to the concept as "it", make it clear what "it" is.
        - It is assumed we are talking about ultimate frisbee so DO NOT say "in ultimate frisbee" in the rewording
    
        Conversation History:
        {self.history.messages}

        Retrieved Context:
        {self.context.get_context()}
        
        User Input: {user_input}
        """
        try:
            response = self.llm_client.invoke(
                messages=[
                    {"role": "assistant", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                config={"max_tokens": 100, "temperature": 0.05},
                response_format=Response
            )

            # print(f"processed input: {response.model_dump()}")
            return (response.retrieve_more_info, response.query)
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return (True, user_input)

    def answer_question(self, query: str, retriever_kwargs: dict = {}):
        """
        Answers the user's question by deciding whether to retrieve more information or use existing history.
        
        Parameters:
            query (str): The user's question.
        
        Returns:
            The assistant's answer as a string.
        """
        retrieve_more_info, processed_query = self.process_user_input(query)
        
        if retrieve_more_info:
            retrieved_docs = self._get_docs(processed_query, **retriever_kwargs)
            self._prepare_context(retrieved_docs)

        answer = self._get_llm_answer(query)
        return answer

# # Example usage
# if __name__ == "__main__":
#     # model = "claude-3-5-sonnet-20240620"
#     # client = AnthropicAbstractedClient(model=model)

#     model = "gpt-4o-mini"
#     # model = "gpt-4o-2024-08-06"
#     client = OpenaiAbstractedClient(model=model)

#     retriever_kwargs = {
#         "limit": 5,
#         "expand_context": True
#     }

#     print(f"client: {client.__repr__()}")
#     session = RagChatSession(
#         llm_client=client,
#         stream_output=False,
#         memory_size=5,
#         context_size=1
#     )
    
#     print("Enter a question (or 'q' to quit): ")
#     query = None
#     while query != "q":
#         query = input("\n\nQUESTION: ")
#         if query != "q":
            
#             answer = session.answer_question(query, retriever_kwargs=retriever_kwargs)
#             if not session.stream_output: 
#                 print("\nANSWER:") 
#                 print(answer)

#     print(f"\n\nhistory:")
#     session.history.pretty_print()

#     # print(f"\n\ncost:")
#     # session.usage.pretty_print()
  


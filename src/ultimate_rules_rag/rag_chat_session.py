from dotenv import load_dotenv
load_dotenv()

import os
from .retriever import Retriever
import json
from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Dict, Tuple, Union, Iterator
from .conversation_history import ConversationHistory
from .clients.base_client import BaseClient
from .prompts import get_rag_prompt, get_process_prompt, RAG_SYSTEM_PROMPT
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Any questions not relevant to ultimate should not be answered
# 


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
            history=ConversationHistory(memory_size=memory_size, system_prompt=RAG_SYSTEM_PROMPT),
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
    
    def _get_llm_answer(self, query: str) -> Union[str, Iterator[str]]:
        """Get answer from LLM with optional streaming support."""
        logger.info(f"Getting answer with LLM for query: {query}")
        context = self.context.get_context()

        if self.stream_output:
            # For streaming, we use plain text format
            prompt = get_rag_prompt(query, context, response_format=None)
            messages = self.history.messages + [{"role": "user", "content": prompt}]
            
            # Return the stream iterator
            response = self.llm_client.invoke(
                messages=messages,
                config={"max_tokens": 1000, "temperature": 0.1, "stream": True}
            )
            
            # Add to history after streaming completes
            def capture_stream():
                full_response = []
                for chunk in response:
                    full_response.append(chunk)
                    yield chunk
                # Add to history after stream completes
                answer = "".join(full_response)
                self.history.add_message("user", query)
                self.history.add_message("assistant", answer)
            
            return capture_stream()

        else:
            # For non-streaming, use structured output
            class Answer(BaseModel):
                answer: str = Field(description="The answer to the question. It should be concise, preferably in one sentence. Exceptions are allowed if the answer includes a long list")
                relevant_rules: list[str] = Field(description="All the rules used to answer the question. Each rule should include the rule number (if present) and the full verbatim text of the rule.")
                error: Optional[str] = Field(description="There is a problem formulating an answer, then this field should be the reason why. Otherwise, it should be None.")
        
            prompt = get_rag_prompt(query, context, response_format=Answer)

            response = self.llm_client.invoke(
                messages=self.history.messages + [{"role": "user", "content": prompt}],
                config={"temperature": 0.1, "max_tokens": 1000},
                response_format=Answer
            )

            try:
                answer = response.answer
                if len(response.relevant_rules) > 0:
                    answer += f"\n\n**Relevant rules:**\n\n- " + "\n- ".join(response.relevant_rules)
            except Exception as e:
                logger.error(f"Error formatting answer: {e}")
                logger.error(f"Using plain response: {response}")
                answer = response

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

        prompt = get_process_prompt(self.history.messages, self.context.get_context(), user_input)
        try:
            response = self.llm_client.invoke(
                messages=[{"role": "user", "content": prompt}],
                config={"max_tokens": 100, "temperature": 0.05},
                response_format=Response
            )

            # print(f"processed input: {response.model_dump()}")
            return (response.retrieve_more_info, response.query)
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return (True, user_input)

    def answer_question(self, query: str, retriever_kwargs: dict = {}) -> Union[str, Iterator[str]]:
        """
        Answers the user's question by deciding whether to retrieve more information or use existing history.
        
        Parameters:
            query (str): The user's question.
            retriever_kwargs (dict): Optional arguments for the retriever
        
        Returns:
            Union[str, Iterator[str]]: Either a string response or a stream of text chunks
        """
        retrieve_more_info, processed_query = self.process_user_input(query)
        
        if retrieve_more_info:
            retrieved_docs = self._get_docs(processed_query, **retriever_kwargs)
            self._prepare_context(retrieved_docs)

        return self._get_llm_answer(query)

# Example usage
if __name__ == "__main__":
    from .clients.get_abstract_client import get_abstract_client
    # model = "claude-3-5-sonnet-20240620"
    # client = AnthropicAbstractedClient(model=model)

    model = "gpt-4o-mini"
    # model = "gpt-4o-2024-08-06"
    client = get_abstract_client(model=model)

    stream_output=True


    retriever_kwargs = {
        "limit": 5,
        "expand_context": True,
        "search_type": "hybrid",
        "fts_operator": "OR"
    }

    for stream_output in [True, False]:
        print(f"\n\n{'*'*10} STREAM OUTPUT: {stream_output} {'*'*10}")
        question = "What is a callahan?"
        print(f"\n\nQUESTION: {question}\n\nANSWER: \n")
        session = RagChatSession(
            llm_client=client,
            stream_output=stream_output,
            memory_size=5,
            context_size=1
        )
        
        response = session.answer_question(question, retriever_kwargs=retriever_kwargs)
        if not stream_output:
            print(response)
        else:
            for chunk in response:
                print(chunk, end="", flush=True)

    # print(f"\n\nhistory:")
    # session.history.pretty_print()
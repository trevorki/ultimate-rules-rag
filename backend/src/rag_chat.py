from dotenv import load_dotenv
load_dotenv()

import re
from .retriever import Retriever
import json
from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Dict, Tuple, Union, Iterator, Type
from .clients.base_client import BaseClient
from .clients.get_abstract_client import get_abstract_client
from .clients.llm_models import CLIENT_MODEL_MAP
from .prompts import get_rag_prompt, get_reword_query_prompt, RAG_SYSTEM_PROMPT
from .db_client import DBClient
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
 

class RagChat(BaseModel):
    llm_client: BaseClient
    retriever: Retriever
    db_client: DBClient  
    memory_size: int
    default_model: str
    light_model: str

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, 
                 llm_client_type: str,
                 memory_size: int = 3):
        super().__init__(
            llm_client=get_abstract_client(llm_client_type),
            retriever=Retriever(),
            db_client=DBClient(),
            memory_size=memory_size,
            default_model=CLIENT_MODEL_MAP[llm_client_type]["default"],
            light_model=CLIENT_MODEL_MAP[llm_client_type]["light"]
        )

    def _get_docs(self, query: str, **kwargs) -> list:
        logger.info(f"Getting similar documents for query: {query}")
        return self.retriever.search(query, **kwargs)

    def _prepare_context(self, context: list[dict]) -> str:
        context_items = []
        for doc in context:
            item = {"source": doc['source'], "content": doc['content']}
            context_items.append(item)
        return context_items
    
    def _reword_query(self, query: str, conversation_id: str) -> str:
        """Reword the query if needed."""
        history = self.db_client.get_conversation_history(conversation_id, message_limit=self.memory_size)
        prompt = get_reword_query_prompt(history, query)
        response, usage = self.llm_client.invoke(prompt, return_usage=True)

        if response.lower() == "none":
            reworded_query = query
        else:
            print(f"reworded_query: {response}")
            reworded_query = response

        self.db_client.add_message(
            conversation_id, query, reworded_query,
            message_type="reword",
            model=self.light_model,
            input_tokens=usage.get("input_tokens"), 
            output_tokens=usage.get("output_tokens") 
        )
        return reworded_query
    
    def _get_llm_answer(self, query: str, context: list[dict], conversation_id: str) -> str:
        """Get answer from LLM without streaming support."""
        logger.info(f"Getting answer with LLM for query: {query}")     
        history = self.db_client.get_conversation_history(conversation_id, message_limit=self.memory_size)

        class Answer(BaseModel):
            answer: str = Field(description="The answer to the question. It should be concise, preferably in one sentence. Exceptions are allowed if the answer includes a long list")
            relevant_rules: list[str] = Field(description="All the rules used to answer the question (rule numbers only), sorted in alphanumeric order")
            error: Optional[str] = Field(description="There is a problem formulating an answer, then this field should be the reason why. Otherwise, it should be None.")
        
        prompt = get_rag_prompt(query, context, response_format=Answer)

        response, usage = self.llm_client.invoke(
            messages=history + [{"role": "user", "content": prompt}],
            config={"temperature": 0.1, "max_tokens": 1000, "model": self.default_model},
            response_format=Answer,
            return_usage=True
        )
        try:
        # if True:
            answer = response.answer
            if len(response.relevant_rules) > 0:
                rules_list_str = self._extract_rules_list(response.relevant_rules, context)
                if len(rules_list_str) > 0:
                    answer += f"\n\n**Relevant rules:**\n\n{rules_list_str}"
        except Exception as e:
            logger.error(f"Error formatting answer: {e}")
            logger.error(f"Using plain response: {response}")
            answer = response

        # Save message to DB
        print("saving to messages table")
        logger.info(f"Saving message to DB: {query} -> {answer[0:50]}")
        self.db_client.add_message(
            conversation_id, query, answer,
            message_type="conversation",
            model=self.llm_client.default_model,
            input_tokens=usage.get("input_tokens"), 
            output_tokens=usage.get("output_tokens") 
        )  
        return answer

    
    def _extract_rules_list(self, rule_numbers: list[str], context: list[dict]) -> dict[str, str]:
        """Extracts full text of rules based on rule numbers from the context and returns a dictionary."""
        context_str = ""
        for item in context:
            if item.get("source") == "rules":
                context_str += "\n" + item["content"]

        rules_dict = self._extract_rules_from_text(context_str, rule_numbers)

        rules_list_str = ""
        for rule_num, rule_body in rules_dict.items():
            if rule_body is not None:  # Only include rules that were found
                formatted_rule_body = rule_body.replace('\n- ', '\n  - ')
                rules_list_str += f"- **{rule_num}**: {formatted_rule_body}" + "\n"
            else:
                print(f"Rule {rule_num} not found in rules_dict")
                print(f"rules_dict: {rules_dict.keys()}")
                print(f"{rule_num} in context_str: {rule_num in context_str}")


        return rules_list_str
    
    def _extract_rules_from_text(self, text, rule_numbers):
        """
        Extract rule bodies for specific rule numbers from a text containing ultimate frisbee rules.
        
        Args:
            text (str): The text containing the rules
            rule_numbers (list): List of rule numbers to extract
        
        Returns:
            dict: Dictionary mapping rule numbers to their rule bodies
        """
        # Split the text into chunks at rule boundaries
        pattern = r"\n\b(\d+\.[A-Z](?:\.\d+)*(?:\.[a-z](?:\.\d+)?)*\.)"
        chunks = re.split(pattern, text)
        
        # Create a temporary dictionary of all rules
        temp_dict = {}
        for i in range(1, len(chunks)-1, 2):
            rule_num = chunks[i].rstrip('.')  # Remove trailing dot
            rule_body = chunks[i+1].strip()
            temp_dict[rule_num] = rule_body
                
        rules_dict = {num: temp_dict.get(num) for num in rule_numbers}
        return rules_dict
    

    def answer_question(self, query: str, conversation_id: str, retriever_kwargs: dict = {}) -> Union[str, Iterator[str]]:
        """
        Answers the user's question by deciding whether to retrieve more information or use existing history.
        
        Parameters:
            query (str): The user's question.
            conversation_id (str): Unique identifier for the conversation
            retriever_kwargs (dict): Optional arguments for the retriever
        
        Returns:
            Union[str, Iterator[str]]: Either a string response or a stream of text chunks
        """
        reworded_query = self._reword_query(query, conversation_id)
        retrieved_docs = self._get_docs(reworded_query, **retriever_kwargs)
        context = self._prepare_context(retrieved_docs)
        return self._get_llm_answer(query, context, conversation_id)
    
    def create_conversation(self, user_email: str):
        conversation_id = self.db_client.create_conversation(user_email=user_email)
        return conversation_id


if __name__ == "__main__":
    rag_chat = RagChat(llm_client_type="openai")
    print(rag_chat.answer_question("What is the rule about the goal circle?", "1234"))

from dotenv import load_dotenv
load_dotenv()

import re
from .retriever import Retriever
import json
from pydantic import BaseModel, Field
from typing import Optional, Union, Iterator
from .clients.base_client import BaseClient
from .clients.get_abstract_client import get_abstract_client
from .clients.llm_models import CLIENT_MODEL_MAP
from .prompts import *
from .db_client import DBClient
import logging

logging.basicConfig(level=logging.INFO,)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
 

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

    def answer_question(
            self, 
            query: str, 
            conversation_id: str, 
            retriever_kwargs: dict = {}
        ) -> Union[str, Iterator[str]]:
        """Answers the user's question by deciding whether to retrieve more information or use existing history."""
        # Log the user's question at the start
        message_id = self.db_client.add_message(
            conversation_id,
            "user",
            query
        )
        print(f"message created with message_id: {message_id}")

        conversation_history = self._get_conversation_history(
            conversation_id, 
            message_limit=self.memory_size, 
            system_prompt=False
        )
        next_step = self._get_next_step(message_id, conversation_history, query)
        logger.info(f"next_step: '{next_step}' ")
        if next_step.lower() == "retrieve":
            reworded_query = self._reword_query(
                query,
                message_id,
                conversation_history,
                light_model=True
            )
            logger.info(f"reworded_query: '{reworded_query[0:75]}...'")
            retrieved_docs = self._get_docs(
                reworded_query, **retriever_kwargs
            )
            context = self._prepare_context(retrieved_docs)
            logger.info(f"{len(context['rules'])} raw rules,    {len(context['definitions'])} raw definitions")
            
            relevant_rules_definitions = self._select_relevant_rules_definitions(
                reworded_query, 
                context, 
                conversation_id,
                message_id,
                conversation_history, 
                light_model=True
            )
            context = self._filter_context(context, relevant_rules_definitions)
            logger.info(f"{len(context['rules'])} filtered rules, {len(context['definitions'])} filtered definitions")
            
        elif next_step.lower() == "answer":
            context = {}
        else:
            logger.warning(f"Invalid next step: {next_step}")
            context = {}
        
        answer = self._get_llm_answer(
            query, 
            context, 
            message_id,
            conversation_history, 
            light_model=False,
            verify=True
        )

        # Log the final answer
        self.db_client.add_message(
            conversation_id,
            "assistant",
            answer
        )
        
        return answer

    def _get_conversation_history(
            self, 
            conversation_id: str, 
            message_limit: int = 10,
            system_prompt: bool = True
        ) -> list[dict]:
        """Get the conversation history from the database."""
        history = self.db_client.get_conversation_history(conversation_id, message_limit)
        if system_prompt:
            history = [{"role": "system", "content": RAG_SYSTEM_PROMPT}] + history
        return history
    
    def _get_docs(self, query: str, **kwargs) -> list:
        logger.debug(f"Getting similar documents for query: {query[0:100]}")
        return self.retriever.search(query, **kwargs)

    def _prepare_context(self, documents: list[dict]) -> list[dict]:
        """Prepare context by organizing rules and definitions separately and in order."""
        # Sort rules by rule number 
        documents.sort(key=lambda x: x['id'])
        rules_docs = []
        definitions_docs = []
        
        # Separate rules and definitions
        for doc in documents:
            if doc['source'] == 'rules':
                rules_docs.append(doc)
            elif doc['source'] == 'glossary':
                definitions_docs.append(doc)
        
        # create dict with keys=rule numbers and values=rule text
        rules_str = '\n'.join(doc['content'] for doc in rules_docs)
        rules_dict = self._extract_rules_dict(rules_str)
        
        # create dict with keys=term and values=definition
        definition_dict = {}
        for doc in definitions_docs:
            term = doc['content'].split("\n")[0]
            definition = "\n".join(doc['content'].split("\n")[1:])
            definition_dict[term] = definition
        context = {
            "rules": rules_dict,
            "definitions": definition_dict
        }
        return context
    

    def _get_next_step(
            self,
            message_id: str,
            conversation_history: list[dict], 
            query: str
        ) -> str:
        """Get the next step for the conversation."""
        prompt = get_next_step_prompt(conversation_history, query)
        response, usage = self.llm_client.invoke(
            prompt, 
            config={"model": self.light_model, "temperature": 0.1, "max_tokens": 10},
            return_usage=True
        )

        # Log LLM call
        self.db_client.add_llm_call(
            message_id=message_id,
            message_type="next_step",
            prompt=prompt,
            response=response,
            model=self.light_model,
            usage=usage
        )
        return response.lower()

    def _reword_query(
            self, 
            query: str, 
            message_id: str,
            conversation_history: list[dict],
            light_model: bool = True
        ) -> str:
        """Reword the query if needed."""
        model = self.light_model if light_model else self.default_model
        prompt = get_reword_query_prompt(conversation_history, query)
        response, usage = self.llm_client.invoke(
            prompt, 
            config={"model": model, "temperature": 0.1, "max_tokens": 100},
            return_usage=True
        )

        if response.lower() == "none":
            reworded_query = query
        else:
            logger.debug(f"reworded_query: {response}")
            reworded_query = response

        self.db_client.add_llm_call(
            message_id=message_id,
            message_type="reword",
            prompt=prompt,
            response=reworded_query,
            model=model,
            usage=usage
        )
        return reworded_query
    
    def _select_relevant_rules_definitions(
            self, 
            query: str, 
            context: list[dict], 
            conversation_id: str,
            message_id: str,
            conversation_history: list[dict],
            light_model: bool = True
        ) -> list[str]:
        """Select relevant rules based on the query."""
        model = self.light_model if light_model else self.default_model
        prompt = get_relevant_rules_definitions_prompt(query, conversation_history, context)

        class RulesDefinitions(BaseModel):
            rules: list[str] = Field(description="The relevant rules (rule numbers only) that are needed to answer the current question.")
            definitions: list[str] = Field(description="The relevant definitions (term names only) that are needed to answer the current question.")

        relevant_rules_definitions, usage = self.llm_client.invoke(
            prompt, 
            config={"temperature": 0.1, "max_tokens": 1000, "model": model},
            return_usage=True, 
            response_format=RulesDefinitions
        )

        self.db_client.add_llm_call(
            message_id=message_id,
            message_type="select_rules",
            prompt=prompt,
            response=repr(relevant_rules_definitions),
            model=model,
            usage=usage
        )
        
        return relevant_rules_definitions.model_dump()
    
    def _extract_rules_dict(self, rules_text: str) -> dict[str, str]:
        """
        Convert rules text into a dictionary with rule numbers as keys and rule text as values.
        """
        # Split on section headers (e.g., "Appendix B: Misconduct System")
        sections = re.split(r'\n\n[A-Z][a-z]+(?:\s+[A-Z])?[^:]*:', rules_text)
        
        # Use only the first section (before any appendix/section headers)
        rules_text = sections[0]
        
        # Rest of the existing code...
        pattern = r"\n\b([A-Z]?\d+(?:\.[A-Z]+)?(?:\.\d+)?(?:\.[a-z])?(?:\.\d+)?(?:\.\d+)?\.)"
        chunks = re.split(pattern, rules_text)
        
        # Create dictionary of rules
        rules_dict = {}
        for i in range(1, len(chunks)-1, 2):
            rule_num = chunks[i].rstrip('.')  # Remove trailing dot
            rule_body = chunks[i+1].strip()
            rules_dict[rule_num] = rule_body
        
        # Sort dictionary by rule number, handling all rule types
        def sort_key(rule_num):
            # Split into components
            parts = re.split(r'([A-Z]+|\d+)', rule_num)
            # Convert to comparable values (empty string for missing appendix letter)
            parts = [p for p in parts if p and p != '.']
            # Ensure appendix letter sorts after regular rules
            if parts[0].isalpha():
                return [parts[0]] + [int(p) if p.isdigit() else p for p in parts[1:]]
            return [''] + [int(p) if p.isdigit() else p for p in parts]
        
        sorted_rules = dict(sorted(rules_dict.items(), key=lambda x: sort_key(x[0])))
        
        return sorted_rules
    

    def _get_llm_answer(
            self,
            query: str,
            context: list[dict],
            message_id: str,
            conversation_history: list[dict],
            light_model: bool = False,
            verify: bool = True
        ) -> str:
        """Get answer to question from llm."""

        model = self.light_model if light_model else self.default_model
        logger.debug(f"Getting answer with LLM for query: {query}")     

        class Answer(BaseModel):
            answer: str = Field(description="The answer to the question. It should be concise, preferably in one sentence. Exceptions are allowed if the answer includes a long list")
            relevant_rules: list[str] = Field(description="All the rules used to answer the question (rule numbers only), sorted in alphanumeric order. If one rule ends in a colon indicating a lots of subrules follows, then include all the subrules in the list.")
        prompt = get_rag_prompt(query, context, conversation_history, response_format=Answer)
        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        response, usage = self.llm_client.invoke(
            messages=messages,
            config={"temperature": 0.2, "max_tokens": 1000, "model": model},
            response_format=Answer,
            return_usage=True
        )
        # logger.info(f"raw answer: '{response.answer}'")
        # Format answer with rules loaded from context
        try:
            answer = response.answer
            if len(response.relevant_rules) > 0 and "rules" in context:
                rules_list_str = self._extract_rules_list(response.relevant_rules, context["rules"])
                if len(rules_list_str) > 0:
                    answer += f"\n\n**Relevant rules:**\n\n{rules_list_str}" 
        except Exception as e:
            logger.error(f"Error formatting answer: {e}")
            logger.error(f"Using plain response: {response}")
            import traceback
            traceback.print_exc()
            answer = response

        logger.debug(f"Saving initial LLM response to DB")
        self.db_client.add_llm_call(
            message_id=message_id,
            message_type="answer",
            prompt=prompt,
            response=repr(response),
            model=model,
            usage=usage
        )

        if verify:
            answer = self._verify_answer(
                answer,
                query,
                message_id,
                conversation_history,
                light_model=True
            )
        return answer

    
    def _verify_answer(
            self,
            answer_with_rules: str,
            query: str,
            message_id: str,
            conversation_history: list[dict],
            light_model: bool = True
        ) -> str:
        """Verify that the answer is supported by the rules and conversation history."""
        model = self.light_model if light_model else self.default_model

        if "\n\n**Relevant rules:**\n\n" in answer_with_rules:
            rules = answer_with_rules.split("\n\n**Relevant rules:**\n\n")[1]
        else:
            rules = None

        class Verification(BaseModel):
            is_correct: bool = Field(description="Whether the answer is fully supported by the rules and conversation history (do not include the rules in your answer)")
            revised_answer: Optional[str] = Field(description="If is_correct is False, provide the corrected answer, omitting the rules. Otherwise, leave as None.")
            explanation: Optional[str] = Field(description="If is_correct is False, provide an explanation for why the answer is incorrect. Otherwise, leave as None.")

        # Remove the last message from conversation history
        if len(conversation_history) > 1:
            conversation_history = conversation_history[:-1]
        else:
            conversation_history = []

        prompt = get_verify_answer_prompt(query, answer_with_rules, conversation_history)

        response, usage = self.llm_client.invoke(
            prompt,
            config={"temperature": 0.1, "max_tokens": 1000, "model": model},
            response_format=Verification,
            return_usage=True,
        )
        logger.info(f"raw verification response:\n{repr(response)}")

        # If the answer is not supported, revise it and insert the rules
        if not response.is_correct:
            logger.info(f"Revised answer: {response.revised_answer}")
            verified_answer_with_rules = response.revised_answer
            if rules:
                verified_answer_with_rules += f"\n\n**Relevant rules:**\n\n{rules}"
        else:
            logger.info(f"Original answer verified")
            verified_answer_with_rules = answer_with_rules

        # Then log the LLM call with the message_id
        self.db_client.add_llm_call(
            message_id=message_id,
            message_type="verify",
            prompt=prompt,
            response=repr(response),
            model=model,
            usage=usage
        )

        return verified_answer_with_rules

    def _extract_rules_list(self, rule_numbers: list[str], rules_dict: dict[str, str]) -> dict[str, str]:
        """Extracts full text of rules based on rule numbers from the context and returns a dictionary."""
        rules_list_str = ""
        for rule_num in rule_numbers:
            if rule_num in rules_dict:  
                formatted_rule_body = rules_dict[rule_num].replace('\n- ', '\n  - ')
                rules_list_str += f"- **{rule_num}**: {formatted_rule_body}" + "\n"
            else:
                print(f"Rule {rule_num} not found in rules_dict")
                print(f"rules_dict: {rules_dict.keys()}")
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
    

    
    
    def _filter_context(self, context: list[dict], relevant_rules_definitions: dict) -> list[dict]:
        """Focus the context on the relevant rules."""
        # select relevant rules
        rules_list = relevant_rules_definitions["rules"]
        focused_rules = {k:v for k,v in context["rules"].items() if k in rules_list}
        context["rules"] = focused_rules

        # select relevant definitions
        definitions_list = relevant_rules_definitions["definitions"]
        focused_definitions = {k:v for k,v in context["definitions"].items() if k in definitions_list}
        context["definitions"] = focused_definitions
        
        return context

    def create_conversation(self, user_email: str):
        """Create a new conversation entry in database."""
        # First get or create user
        user_id = self.db_client.get_user_id(user_email)
        if not user_id:
            logger.warning(f"User {user_email} not found, creating new user")
        
        # Then create conversation with user_id
        conversation_id = self.db_client.create_conversation(user_id=user_id)
        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id

    def calculate_conversation_cost(self, conversation_id):
        """Calculate the total cost of a conversation by summing all LLM call costs."""
        sql_query = """
        SELECT COALESCE(SUM(cost), 0) as total_cost
        FROM llm_calls
        WHERE message_id IN (
            SELECT id FROM messages WHERE conversation_id = %s
        )
        """
        args = (conversation_id,)
        response = self.db_client.query_db_sql(sql_query, args)
        return response[0]['total_cost'] if response else 0


if __name__ == "__main__":
    user_email = "trevorkinsey@gmail.com"
    client_type = "openai"
    rag_chat = RagChat(llm_client_type=client_type)
    conversation_id = rag_chat.create_conversation(user_email)
    print(f"created conversation_id: {conversation_id}")
    retriever_kwargs = {
        "search_type": "hybrid",
        "fts_operator": "OR",
        "limit": 4,
        "expand_context": 0,
        "semantic_weight": 0.75,
        "fts_weight": 0.25
    }
    questions = [
        # "what is a technical foul?",
        # "how big is the playing field?",
        # "What are the dimensions of the playing field in yards?"
        # "what is a double team?",
        # "how do you resolve it when it is called?",
        "what is a callahan?",
        "tell me more",
        # "what does the stall count resume at after a contested foul?"
        # "what are the field dimensions as shown in appendix a?"


    ]
    for question in questions:
        print(f"{'*'*80}\n{question}\n")
        answer = rag_chat.answer_question(
            question, 
            conversation_id, 
            retriever_kwargs=retriever_kwargs
        )
        print(f"\n{answer}\n")

    history = rag_chat._get_conversation_history(conversation_id, message_limit=10)
    for entry in history:
        print(f"\n{'-'*40} {entry['role'].upper()} {'-'*40}\n{entry['content']}\n")

    cost = rag_chat.calculate_conversation_cost(conversation_id)
    print(f"\ncost: ${cost:.5f}\n")

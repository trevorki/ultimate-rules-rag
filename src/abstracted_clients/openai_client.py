import os
from typing import Dict, Any, Optional, Union, Type
import json
from pydantic import BaseModel, Field
from openai import OpenAI
from .base_client import BaseClient
import logging
from dotenv import load_dotenv
from typing import List

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_MAX_TOKENS = 1000
DEFAULT_OPENAI_MODEL = "gpt-4o-2024-08-06"  # Add default model constant

class OpenaiAbstractedClient(BaseClient):
    """OpenAI-specific implementation of the LLM provider.
    
    This client provides a standardized interface for interacting with OpenAI's API,
    supporting both simple text generation and structured outputs via JSON or Pydantic models.
    
    The client automatically handles:
    - API authentication via environment variables
    - Message formatting for chat completions
    - System prompt management
    - Response parsing into requested formats
    - Error handling and logging
    
    Attributes:
        client: The underlying OpenAI client instance
        default_model: The default model to use for completions
    """
    
    def initialize_client(self):
        """Initialize the OpenAI client with API credentials.
        
        Requires OPENAI_API_KEY environment variable to be set.
        Sets up the client and default model configuration.
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.default_model = os.getenv("DEFAULT_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

    def invoke(self, 
              messages: Union[str, List[Dict[str, str]]],
              config: Optional[Dict[str, Any]] = None, 
              response_format: Optional[Union[dict, Type[BaseModel]]] = None) -> Union[str, dict, BaseModel]:
        """Generate a response using OpenAI's API.
        
        Args:
            messages: The input prompt, either as:
                - A simple string for single-turn interactions
                - A list of message dicts with 'role' and 'content' for multi-turn chats
            config: Optional configuration parameters for the API call, such as:
                - temperature: Float between 0 and 2 (default varies by model)
                - max_tokens: Maximum tokens in response (default varies by model)
                - model: Override the default model
            response_format: Optional output format specification:
                - If dict: Response will be formatted as a JSON object matching the schema
                - If Type[BaseModel]: Response will be parsed into the specified Pydantic model
                - If None: Response will be returned as plain text
        
        Returns:
            Union[str, dict, BaseModel]: The model's response in the requested format:
                - String for plain text responses
                - Dict for JSON format responses
                - Pydantic model instance for structured responses
            In case of errors, returns the error message as a string.
        """
        config = config or {}
        config['model'] = config.get('model', DEFAULT_OPENAI_MODEL)
        logger.debug(f"Generating OpenAI response with model: {config.get('model')}")
        
        # Convert string input to messages format
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        try:
            if isinstance(response_format, type) and issubclass(response_format, BaseModel):
                # For Pydantic models
                config['response_format'] = response_format
                completion = self.client.beta.chat.completions.parse(messages=messages, **config)
                return completion.choices[0].message.parsed
            
            elif isinstance(response_format, dict):
                # For openai JSON format must include "JSON" in prompt
                config['response_format'] = {"type": "json_object"}
                format_instruction = f"You must respond with a valid JSON object in this format: {json.dumps(response_format)}"
                
                # Insert format instruction as system message if none exists
                if not any(msg["role"] == "system" for msg in messages):
                    messages.insert(0, {"role": "system", "content": format_instruction})
                else:
                    # Append to existing system message
                    for msg in messages:
                        if msg["role"] == "system":
                            msg["content"] = f"{msg['content']}\n\n{format_instruction}"
                            break

                completion = self.client.chat.completions.create(messages=messages, **config)
                return json.loads(completion.choices[0].message.content)
            
            else:
                # For regular text responses
                completion = self.client.chat.completions.create(
                    messages=messages,
                    **config
                )
                return completion.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {str(e)}", exc_info=True)
            return str(e)

    def load_dict(self, json_string: str) -> dict:
        """Parse a JSON string response into a dictionary.
        
        Args:
            json_string: The JSON-formatted string to parse
            
        Returns:
            dict: The parsed JSON object
            str: The original string if parsing fails
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return json_string

    def load_pydantic(self, json_string: str, pydantic_model: Type[BaseModel]) -> Optional[BaseModel]:
        """Parse a JSON string response into a Pydantic model instance.
        
        Args:
            json_string: The JSON-formatted string to parse
            pydantic_model: The Pydantic model class to parse into
            
        Returns:
            BaseModel: An instance of the specified Pydantic model
            None: If parsing fails
        """
        try:
            return pydantic_model.parse_raw(json_string)
        except Exception:
            return None

if __name__ == "__main__":
    client = OpenaiAbstractedClient()
    
    response_format = {
        "name": "<the country name>",
        "capital": "<the capital city of the country>",
        "language": "<the official language of the country>"
    }

    class Country(BaseModel):
        name: str = Field(description="The country name")
        capital: str = Field(description="The capital city of the country")
        language: str = Field(description="The official language of the country")

    # Example with different formats using both string and message list inputs
    formats = [None,response_format, Country]
    messages = [
        {"role": "system", "content": "You are a helpful geography expert who answers only in UPPERCASE"},
        {"role": "user", "content": "Please name a country at random"},
        {"role": "assistant", "content": "France"},
        {"role": "user", "content": "Tell me about France"}
    ]

    for format in formats:
        print(f"\nResponse format: {format}")
        print(client.invoke(messages, response_format=format))
        print("-------------------------------")

    print("\n\n"+client.invoke("tell me a joke about a watermelon"))
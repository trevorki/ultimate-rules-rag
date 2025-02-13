import os
from typing import Dict, Any, Optional, Union, Type
import json
from pydantic import BaseModel, Field
from openai import OpenAI
from .base_client import BaseClient
import logging
from dotenv import load_dotenv
from typing import List
from typing import Generator, Iterator

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_MAX_TOKENS = 1000
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"  # Add default model constant

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
    def initialize_client(self, default_model: str|None):
        """Initialize the OpenAI client with API credentials.
        
        Requires OPENAI_API_KEY environment variable to be set.
        Sets up the client and default model configuration.
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.default_model = default_model or DEFAULT_OPENAI_MODEL

    def get_text_stream(self, stream) -> Iterator[str]:
        """Convert OpenAI stream to standardized text stream."""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def invoke(self, 
              messages: Union[str, List[Dict[str, str]]],
              config: Optional[Dict[str, Any]] = None, 
              response_format: Optional[Union[dict, Type[BaseModel]]] = None,
              return_usage: bool = False) -> Union[str, dict, BaseModel, Iterator[str]]:
        """Generate a response using OpenAI's API.
        
        Args:
            messages: The input prompt, either as:
                - A simple string for single-turn interactions
                - A list of message dicts with 'role' and 'content' for multi-turn chats
            config: Optional configuration parameters for the API call, such as:
                - temperature: Float between 0 and 2 (default varies by model)
                - max_tokens: Maximum tokens in response (default varies by model)
                - model: Override the default model
                - stream: bool = False - Whether to stream the response
                Note: Streaming only works with plain text responses (response_format=None)
            response_format: Optional output format specification
        
        Returns:
            Union[str, dict, BaseModel, Iterator[str]]: Model response in one of four formats:
                - str: Plain text response when no response_format is specified
                - dict: JSON object when response_format is a dict
                - BaseModel: Pydantic model instance when response_format is a Pydantic model class
                - Iterator[str]: Stream of text chunks when config['stream']=True
        """
        config = config or {}
        config['model'] = config.get('model', self.default_model)
        logger.debug(f"Generating OpenAI response with model: {config.get('model')}")
        
        # Convert string input to messages format
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        # Check if streaming is requested with structured output
        if config.get('stream', False) and response_format is not None:
            raise ValueError("Streaming is only supported for plain text responses (response_format=None)")


        if config.get('stream', False):
            return self.get_streaming_response(messages, config, response_format, return_usage)
        else:
            return self.get_non_streaming_response(messages, config, response_format, return_usage)


    def get_streaming_response(self, messages, config):
        # Handle streaming response
        stream = self.client.chat.completions.create(
            messages=messages,
            stream=True,
            **{k:v for k,v in config.items() if k != 'stream'}
        )
        return self.get_text_stream(stream)
    
    def get_non_streaming_response(self, messages, config, response_format=None, return_usage=False):
        
        if isinstance(response_format, type) and issubclass(response_format, BaseModel):
            # For Pydantic models
            config['response_format'] = response_format
            response = self.client.beta.chat.completions.parse(messages=messages, **config)
            output =  response.choices[0].message.parsed
        
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

            response = self.client.chat.completions.create(messages=messages, **config)
            output =  json.loads(response.choices[0].message.content)
        
        else:
            # For regular text responses
            response = self.client.chat.completions.create(
                messages=messages,
                **config
            )
            output = response.choices[0].message.content

        if return_usage:
            usage =  {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
            return output, usage
        else:
            return output
            

    

    # def load_dict(self, json_string: str) -> dict:
    #     """Parse a JSON string response into a dictionary.
        
    #     Args:
    #         json_string: The JSON-formatted string to parse
            
    #     Returns:
    #         dict: The parsed JSON object
    #         str: The original string if parsing fails
    #     """
    #     try:
    #         return json.loads(json_string)
    #     except json.JSONDecodeError:
    #         return json_string

    # def load_pydantic(self, json_string: str, pydantic_model: Type[BaseModel]) -> Optional[BaseModel]:
    #     """Parse a JSON string response into a Pydantic model instance.
        
    #     Args:
    #         json_string: The JSON-formatted string to parse
    #         pydantic_model: The Pydantic model class to parse into
            
    #     Returns:
    #         BaseModel: An instance of the specified Pydantic model
    #         None: If parsing fails
    #     """
    #     try:
    #         return pydantic_model.model_validate_json(json_string)
    #     except Exception:
    #         return None



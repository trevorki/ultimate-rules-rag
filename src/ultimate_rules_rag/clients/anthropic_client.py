import os
from typing import Dict, Any, List, Union, Optional, Type, Iterator
import json
from pydantic import BaseModel, Field
from anthropic import Anthropic
from .base_client import BaseClient
import logging
from dotenv import load_dotenv
import re

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_MAX_TOKENS = 1000

class AnthropicAbstractedClient(BaseClient):
    """Anthropic-specific implementation of the LLM provider.
    
    This client provides a standardized interface for interacting with Anthropic's API,
    supporting both simple text generation and structured outputs via JSON or Pydantic models.
    
    The client automatically handles:
    - API authentication via environment variables
    - Message formatting for chat completions
    - System prompt management
    - Response parsing into requested formats
    - Error handling and logging
    
    Attributes:
        client: The underlying Anthropic client instance
        default_model: The default model to use for completions
    """
    
    def __init__(self, model: str = None):
        """Initialize the client with optional model override.
        
        Args:
            model: Optional model to use instead of environment variable default
        """
        super().__init__(default_model=model)
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the Anthropic client with API credentials.
        
        Requires ANTHROPIC_API_KEY environment variable to be set.
        Sets up the client and default model configuration.
        """
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        if not self.default_model:
            self.default_model = os.getenv("DEFAULT_ANTHROPIC_MODEL")

    def get_text_stream(self, stream) -> Iterator[str]:
        """Convert Anthropic stream to standardized text stream."""
        for text in stream.text_stream:
            yield text

    def invoke(self, 
              messages: Union[str, List[Dict[str, str]]],
              config: Optional[Dict[str, Any]] = None, 
              response_format: Optional[Union[dict, Type[BaseModel]]] = None,
              return_usage: bool = False) -> Union[str, dict, BaseModel, Iterator[str]]:
        """Generate a response using Anthropic's API.
        
        Args:
            messages: The input prompt, either as:
                - A simple string for single-turn interactions
                - A list of message dicts with 'role' and 'content' for multi-turn chats
            config: Optional configuration parameters for the API call, such as:
                - temperature: Float between 0 and 1
                - max_tokens: Maximum tokens in response (default: 1000)
                - model: Override the default model
                - stream: bool = False - Whether to stream the response
                Note: Streaming only works with plain text responses (response_format=None)
            response_format: Optional output format specification
            return_usage: Whether to return the usage metrics from the API call
        """
        config = config or {}
        config['model'] = config.get('model', self.default_model)
        config['max_tokens'] = config.get('max_tokens', DEFAULT_MAX_TOKENS)
        
        logger.debug(f"Generating Anthropic response with model: {config.get('model')}")
        
        # Convert string input to messages format
        if isinstance(messages, str):
            message_list = [{"role": "user", "content": messages}]
        else:
            message_list = messages.copy()

        # Check if streaming is requested with structured output
        if config.get('stream', False) and response_format is not None:
            raise ValueError("Streaming is only supported for plain text responses (response_format=None)")

        # Handle system message
        system_prompt = None
        for i, msg in enumerate(message_list):
            if msg["role"] == "system":
                system_prompt = msg["content"]  
                message_list.pop(i)
                break
        
        if system_prompt:
            config['system'] = system_prompt

        # Prepare system prompt with format instructions if needed
        if response_format:
            format_instruction = ""
            if isinstance(response_format, dict):
                format_instruction = f"You must respond with only a valid JSON object (no other text) in this format: {json.dumps(response_format)}"
            elif isinstance(response_format, type) and issubclass(response_format, BaseModel):
                schema = response_format.model_json_schema()
                format_instruction = f"You must respond with only a valid JSON object (no other text) matching this schema: {json.dumps(schema)}"
            
            # Add format instruction to system message
            system_prompt = config.get('system', '')
            system_prompt = (system_prompt + f"\n\n{format_instruction}").strip()
            config['system'] = system_prompt
        
        if config.get('stream', False):
            return self.get_streaming_response(message_list, config)
        else:
            return self.get_non_streaming_response(message_list, config, response_format, return_usage)
            
            
    def get_streaming_response(self, messages, config):
            stream = self.client.messages.stream(
                messages=messages,
                **{k:v for k,v in config.items() if k != 'stream'}
            )
            # Return a generator that uses the context manager
            def stream_with_context():
                with stream as managed_stream:
                    for text in managed_stream.text_stream:
                        yield text
            return stream_with_context()
    
    def get_non_streaming_response(self, messages, config, response_format, return_usage):
        response = self.client.messages.create(
            messages=messages,
            **config
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        try:
            output = response.content[0].text
            if response_format:
                output = re.sub(r'^[^{]*', '', output) # filter out any non-json outside the braces

            # Parse response based on format
            if isinstance(response_format, dict):
                output = self.load_dict(output)
            elif isinstance(response_format, type) and issubclass(response_format, BaseModel):
                output = self.load_pydantic(output, response_format)

            if return_usage:
                return output, usage
            else:
                return output

        except Exception as e:
            logger.error(f"Error parsing Anthropic response: {str(e)}")
            logger.error(f"Raw response: {response}")
            return response

    def load_dict(self, json_string: str) -> dict:
        """Parse a JSON string response into a dictionary.
        
        Args:
            json_string: The JSON-formatted string to parse
            
        Returns:
            dict: The parsed JSON object
            str: The original string if parsing fails
        """
        logger.debug("Attempting to parse JSON response to dict")
        try:
            return json.loads(json_string)
        except Exception as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            logger.debug(f"Failed JSON string: {json_string}")
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
        logger.debug(f"Attempting to JSON response into Pydantic model: {pydantic_model.__name__}")
        try:
            return pydantic_model.model_validate_json(json_string)
        except Exception as e:
            logger.error(f"Error parsing json_string into Pydantic model: {str(e)}")
            logger.error(f"Failed json_string: {json_string}")
            return None
        


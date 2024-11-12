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
              response_format: Optional[Union[dict, Type[BaseModel]]] = None) -> Union[str, dict, BaseModel, Iterator[str]]:
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

        try:
            if config.get('stream', False):
                # Create the stream with context manager
                stream = self.client.messages.stream(
                    messages=message_list,
                    **{k:v for k,v in config.items() if k != 'stream'}
                )
                # Return a generator that uses the context manager
                def stream_with_context():
                    with stream as managed_stream:
                        for text in managed_stream.text_stream:
                            yield text
                return stream_with_context()

            # Make API call
            response = self.client.messages.create(
                messages=message_list,
                **config
            )
            try:
                result = response.content[0].text

                # filter out any non-json outside the braces
                result = re.sub(r'^[^{]*', '', result)

                # Parse response based on format
                if isinstance(response_format, dict):
                    return self.load_dict(result)
                elif isinstance(response_format, type) and issubclass(response_format, BaseModel):
                    return self.load_pydantic(result, response_format)
                else:
                    return result
            except Exception as e:
                logger.error(f"Error parsing Anthropic response: {str(e)}")
                logger.error(f"Raw response: {result}")
                return result
        except Exception as e:
            logger.error(f"Error generating Anthropic response: {str(e)}")
            logger.error(f"Raw response: {result}")
            return result
            

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
        


###############################
def test_structured_output(client):
    # Test Stuctured output
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


def test_streaming(client, model):
    # For streaming:
    prompt = "Tell me a joke about France"
    config={
        "stream": True,
        "model": model    
    }
    for chunk in client.invoke(prompt, config=config):
        print(chunk, end="", flush=True)


if __name__ == "__main__":
    model = "claude-3-5-sonnet-20241022"
    client = AnthropicAbstractedClient(model)

    test_streaming(client, model)

    
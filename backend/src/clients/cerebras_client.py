import os
from typing import Dict, Any, Optional, Union, Type, List, Iterator
import json
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
from .base_client import BaseClient
from cerebras.cloud.sdk import Cerebras
import re

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_MAX_TOKENS = 1000
DEFAULT_CEREBRAS_MODEL = "llama3.1-70b"
DEFAULT_CEREBRAS_LIGHT_MODEL = "llama3.1-8b"

class CerebrasAbstractedClient(BaseClient):
    """Cerebras-specific implementation of the LLM provider.
    
    This client provides a standardized interface for interacting with Cerebras's API,
    supporting both simple text generation and structured outputs via JSON or Pydantic models.
    
    The client automatically handles:
    - API authentication via environment variables
    - Message formatting for chat completions
    - System prompt management
    - Response parsing into requested formats
    - Error handling and logging
    
    Attributes:
        client: The underlying Cerebras client instance
        default_model: The default model to use for completions
    """   
    def initialize_client(self, default_model: str|None):
        """Initialize the Cerebras client with API credentials.
        
        Requires CEREBRAS_API_KEY environment variable to be set.
        Sets up the client and default model configuration.
        """
        self.client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))
        self.default_model = default_model or DEFAULT_CEREBRAS_MODEL

    def get_text_stream(self, stream) -> Iterator[str]:
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def invoke(self, 
              messages: Union[str, List[Dict[str, str]]],
              config: Optional[Dict[str, Any]] = None, 
              response_format: Optional[Union[dict, Type[BaseModel]]] = None,
              return_usage: bool = False) -> Union[str, dict, BaseModel, Iterator[str]]:
        """Generate a response using Cerebras's API.
        
        Args:
            messages: The input prompt, either as:
                - A simple string for single-turn interactions
                - A list of message dicts with 'role' and 'content' for multi-turn chats
            config: Optional configuration parameters for the API call
            response_format: Optional output format specification
        
        Returns:
            Union[str, dict, BaseModel, Iterator[str]]: Model response in requested format
        """
        config = config or {}
        config['model'] = config.get('model', self.default_model)
        logger.debug(f"Generating Cerebras response with model: {config.get('model')}")
        
        # Convert string input to messages format
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        # Check if streaming is requested with structured output
        if config.get('stream', False) and response_format is not None:
            raise ValueError("Streaming is only supported for plain text responses (response_format=None)")

        # Add format instructions to system message if needed
        if response_format:
            format_instruction = ""
            if isinstance(response_format, dict):
                format_instruction = f"You must respond with only a valid JSON object (no other text) in this format: {json.dumps(response_format)}"
            elif isinstance(response_format, type) and issubclass(response_format, BaseModel):
                schema = response_format.model_json_schema()
                format_instruction = f"You must respond with only a valid JSON object (no other text) matching this schema: {json.dumps(schema)}"
            
            # Insert or append format instruction to system message
            if not any(msg["role"] == "system" for msg in messages):
                messages.insert(0, {"role": "system", "content": format_instruction})
            else:
                for msg in messages:
                    if msg["role"] == "system":
                        msg["content"] = f"{msg['content']}\n\n{format_instruction}"
                        break

        if config.get('stream', False):
            return self.get_streaming_response(messages, config)
        else:
            return self.get_non_streaming_response(messages, config, response_format, return_usage)

    def get_streaming_response(self, messages, config):
        """Handle streaming response."""
        stream = self.client.chat.completions.create(
            messages=messages,
            stream=True,
            **{k:v for k,v in config.items() if k != 'stream'}
        )
        return self.get_text_stream(stream)
    
    def get_non_streaming_response(self, messages, config, response_format=None, return_usage=False):
        response = self.client.chat.completions.create(
            messages=messages,
            **config
        )
        
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        
        try:
            output = response.choices[0].message.content
            if response_format:
                # Clean the output to extract just the JSON part
                output = re.sub(r'^[^{]*', '', output)  # Remove any text before the first {
                output = re.sub(r'}[^}]*$', '}', output)  # Remove any text after the last }

                # First load as dict (and correct if needed)
                if isinstance(response_format, dict):
                    output = self.load_dict(output, response_format)
                elif isinstance(response_format, type) and issubclass(response_format, BaseModel):
                    # Use the model's schema as the format for correction
                    dict_output = self.load_dict(output, response_format.model_json_schema())
                    try:
                        output = response_format.model_validate(dict_output)
                    except Exception as e:
                        logger.error(f"Error validating dict into Pydantic model: {str(e)}")
                        return None

            if return_usage:
                return output, usage
            return output

        except Exception as e:
            logger.error(f"Error parsing Cerebras response: {str(e)}")
            logger.error(f"Raw response: {response}")
            return response.choices[0].message.content

    def _correct_json(self, failed_json_string: str, response_format: dict) -> str:
        """Attempt to correct malformed JSON using the LLM.
        
        Args:
            failed_json_string: The malformed JSON string
            response_format: The expected format as a dictionary
            
        Returns:
            str: Corrected JSON string
        """
        prompt = [
            {"role": "system", "content": "You are a JSON correction assistant. Fix the provided JSON to match the specified format exactly. Return only the corrected JSON with no additional text."},
            {"role": "user", "content": f"""
Format specification:
{json.dumps(response_format, indent=2)}

Failed JSON string to correct:
{failed_json_string}

Please provide the corrected JSON that matches the format specification exactly."""}
        ]
        logger.info(f"Correcting JSON with prompt: {prompt}")
        try:
            corrected = self.invoke(prompt)
            # Clean the response to ensure we only get JSON
            corrected = re.sub(r'^[^{]*', '', corrected)  # Remove any text before the first {
            corrected = re.sub(r'}[^}]*$', '}', corrected)  # Remove any text after the last }
            # Validate that it's valid JSON
            json.loads(corrected)
            return corrected
        except Exception as e:
            logger.error(f"Failed to correct JSON: {str(e)}")
            return failed_json_string

    def load_dict(self, json_string: str, response_format: dict) -> dict:
        """Parse a JSON string response into a dictionary."""
        logger.debug("Attempting to parse JSON response to dict")
        try:
            return json.loads(json_string)
        except Exception as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            print(f"Failed JSON string: {json_string}")
            # Try to correct the JSON
            corrected = self._correct_json(json_string, response_format)
            print(f"Corrected JSON: {corrected}")
            try:
                return json.loads(corrected)
            except Exception:
                return json_string



if __name__ == "__main__":
    client = CerebrasAbstractedClient(default_model="llama3.1-70b")
    class Stats(BaseModel):
        goal: int
        assists: int
        rebounds: int
        points: int

    class Player(BaseModel):
        name: str
        age: int
        stats: Stats
    response_format = Player

    prompt = """James Wilson's game performance:

28 points (9/15 FG, 4/7 3PT, 6/8 FT)
7 rebounds (2 offensive, 5 defensive)
6 assists
2 steals
1 block
2 turnovers
34 minutes played
+12 plus/minus rating

This represents a strong all-around performance from a starting shooting guard, 
with efficient scoring from all areas of the floor and solid contributions in other aspects of the game."""
    response = client.invoke(
        prompt, 
        config = {"temperature": 0.1, "model": "llama3.1-8b"},
        response_format=response_format)
    print(response)


from typing import Dict, Any, Optional, Type, Union
from pydantic import BaseModel
import logging
from typing import Any, List
from typing import Generator, Iterator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BaseClient(BaseModel):
    """Base class the abstracted clients inherit from.
    
    Provides common functionality for handling text inputs across different LLM providers.
    
    Args:
        client: The abstracted client instance for the specific provider
    """
    client: Any = None
    default_model: str = None
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, default_model: str, **data):
        super().__init__(**data)
        self.initialize_client(default_model)

    def initialize_client(self, default_model: str):
        """Initialize the client and default model. Must be implemented by subclasses."""
        raise NotImplementedError

    def _process_user_input(self, user_input: str) -> List[Dict]:
        """Process user prompts into a format suitable for LLM API calls.
        
        Args:
            user_input: A string containing the user's prompt
            
        Returns:
            List[Dict]: Processed content items with type and data
        """
        logger.debug(f"Processing user input of type: {type(user_input)}")
        return [{"type": "text", "text": user_input}]
    
    def get_text_stream(self, stream) -> Iterator[str]:
        """Convert provider-specific stream to standardized text stream.
        
        Args:
            stream: The raw stream from the provider's API
            
        Returns:
            Iterator[str]: Stream of text chunks
        """
        raise NotImplementedError

    def invoke(self, 
            messages: Union[str, List[Dict[str, str]]], 
            config: Optional[Dict[str, Any]] = None,
            response_format: Optional[Union[dict, Type[BaseModel]]] = None, 
            return_usage: bool = False) -> Union[str, dict, BaseModel, Iterator[str]]:
        """Get response from the language model.
        
        Args:
            messages: Either a simple string prompt or a list of message dictionaries.
                     If string: Will be converted to a single user message
                     If list: Each dict should contain 'role' and 'content' keys.
                     Common roles are 'system', 'user', and 'assistant'.
            config: Optional configuration parameters for the API call including:
                   - stream: bool = False - Whether to stream the response
                   Note: Streaming only works with plain text responses (response_format=None)
            response_format: Optional output format specification:
                - If dict: Response will be formatted as a JSON object matching the schema
                - If Type[BaseModel]: Response will be parsed into the specified Pydantic model
                - If None: Response will be returned as plain text
            return_usage: Whether to return the usage metrics from the API call
        
        Returns:
            Union[str, dict, BaseModel, Iterator[str]]: Model response in one of four formats:
                - str: Plain text response when no response_format is specified
                - dict: JSON object when response_format is a dict
                - BaseModel: Pydantic model instance when response_format is a Pydantic model class
                - Iterator[str]: Stream of text chunks when config['stream']=True
                - dict: Usage metrics when return_usage=True
        Raises:
            NotImplementedError: Must be implemented by provider-specific classes
        """            
        raise NotImplementedError
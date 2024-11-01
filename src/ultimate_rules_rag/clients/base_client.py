from typing import Dict, Any, Optional, Type, Union
from pydantic import BaseModel
import logging
from typing import Any, List

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

    def __init__(self, **data):
        super().__init__(**data)
        self.initialize_client()

    def initialize_client(self):
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

    def invoke(self, 
            messages: Union[str, List[Dict[str, str]]], 
            config: Optional[Dict[str, Any]] = None,
            response_format: Optional[Union[dict, Type[BaseModel]]] = None) -> Union[str, dict, BaseModel]:
        """Get response from the language model.
        
        Args:
            messages: Either a simple string prompt or a list of message dictionaries.
                     If string: Will be converted to a single user message
                     If list: Each dict should contain 'role' and 'content' keys.
                     Common roles are 'system', 'user', and 'assistant'.
            config: Optional configuration parameters for the API call
            response_format: Optional output format specification:
                - If dict: Response will be formatted as a JSON object matching the schema
                - If Type[BaseModel]: Response will be parsed into the specified Pydantic model
                - If None: Response will be returned as plain text
        
        Returns:
            Union[str, dict, BaseModel]: Model response in one of three formats:
                - str: Plain text response when no response_format is specified
                - dict: JSON object when response_format is a dict
                - BaseModel: Pydantic model instance when response_format is a Pydantic model class
        
        Raises:
            NotImplementedError: Must be implemented by provider-specific classes
        """
        # Convert string input to messages format
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
            
        raise NotImplementedError
from .openai_client import OpenaiAbstractedClient
from .anthropic_client import AnthropicAbstractedClient

def get_abstract_client(client_type: str, **kwargs):
    if client_type == "openai":
        return OpenaiAbstractedClient(**kwargs)
    elif client_type == "anthropic":
        return AnthropicAbstractedClient(**kwargs)
    else:
        raise ValueError(f"Invalid client type: {client_type}")

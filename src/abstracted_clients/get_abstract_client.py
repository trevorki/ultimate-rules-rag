from abstracted_clients.openai_client import OpenaiAbstractedClient
from abstracted_clients.anthropic_client import AnthropicAbstractedClient

def get_abstract_client(client_type: str):
    if client_type == "openai":
        return OpenaiAbstractedClient()
    elif client_type == "anthropic":
        return AnthropicAbstractedClient()
    else:
        raise ValueError(f"Invalid client type: {client_type}")

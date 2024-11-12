from .openai_client import OpenaiAbstractedClient
from .anthropic_client import AnthropicAbstractedClient

MODEL_CLIENT_MAP = {
    "gpt-4o-mini": "openai",
    "gpt-4o-2024-08-06": "openai",
    "claude-3-5-haiku-20241022": "anthropic",
    "claude-3-5-sonnet-20241022": "anthropic",
}

def get_abstract_client(model: str, **kwargs):
    if model not in MODEL_CLIENT_MAP:
        raise ValueError(f"Invalid model: {model}. Must be one of {list(MODEL_CLIENT_MAP.keys())}.")
    
    client_type = MODEL_CLIENT_MAP[model]
    
    if client_type == "openai":
        return OpenaiAbstractedClient(model=model, **kwargs)
    elif client_type == "anthropic":
        return AnthropicAbstractedClient(model=model, **kwargs)
    else:
        raise ValueError(f"Unknown client type: {client_type}")

DEFAULT_CLIENT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "cerebras": "llama3.1-70b"
}

CLIENT_MODEL_MAP = {
    "openai": {
        "default": "gpt-4o-2024-08-06", 
        "light": "gpt-4o-mini"
    },
    "anthropic": {
        "default": "claude-3-5-sonnet-20241022", 
        "light": "claude-3-5-haiku-20241022"
    },
    "cerebras": {
        "default": "llama3.1-70b", 
        "light": "llama3.1-8b"
    }
}

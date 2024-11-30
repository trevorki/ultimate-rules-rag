from .openai_client import OpenaiAbstractedClient
from .anthropic_client import AnthropicAbstractedClient
from .cerebras_client import CerebrasAbstractedClient
from .llm_models import CLIENT_MODEL_MAP


def get_abstract_client(client_type: str, **kwargs):
    if client_type not in CLIENT_MODEL_MAP:
        raise ValueError(f"Invalid model: {client_type}. Must be one of {list(CLIENT_MODEL_MAP.keys())}.")
    
    default_model = CLIENT_MODEL_MAP[client_type]["default"]
    
    if client_type == "openai":
        return OpenaiAbstractedClient(default_model=default_model, **kwargs)
    elif client_type == "anthropic":
        return AnthropicAbstractedClient(default_model=default_model, **kwargs)
    elif client_type == "cerebras":
        return CerebrasAbstractedClient(default_model=default_model, **kwargs)
    else:
        raise ValueError(f"Unknown client type: {client_type}")


############################# TESTS ##############################
from pydantic import BaseModel, Field

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
    
    messages = [
        {"role": "system", "content": "You are a helpful geography expert who answers only in UPPERCASE"},
        {"role": "user", "content": "Please name a country at random"},
        {"role": "assistant", "content": "France"},
        {"role": "user", "content": "Tell me about France"}
    ]
    formats = [None,response_format, Country]
    for format in formats:
        print(f"\nResponse format: {format}")
        print(client.invoke(messages, response_format=format))
        print("-------------------------------")



def test_streaming(client, model):
    # For streaming:
    prompt = "Tell me a joke about cookies"
    config={
        "stream": True,
        "model": model    
    }
    stream =  client.invoke(prompt, config=config)
    for chunk in stream:
        print(chunk, end="", flush=True)




if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    client_types = [
        "openai", 
        "anthropic", 
        "cerebras"
    ]
    for client_type in client_types:
        model = CLIENT_MODEL_MAP[client_type]["default"]
        print(f"\n\n{'-'*50}\nTesting model: {model}\n{'-'*50}\n")
        client = get_abstract_client(client_type)

        class Country(BaseModel):
            name: str = Field(description="The country name")
            capital: str = Field(description="The capital city of the country")
            language: str = Field(description="The official language of the country")
            
        response_formats = [
            {
                "name": "<the country name>",
                "capital": "<the capital city of the country>",
                "language": "<the official language of the country>"
            },
            Country,
            None
        ]
        
        for response_format in response_formats:
            print(f"\n---------Response format: {type(response_format)}---------")
            prompt = "Tell me about France?"
            response, usage = client.invoke(prompt, response_format=response_format, return_usage=True)
            print(f"response: {response}")
            print(f"usage: {usage}")



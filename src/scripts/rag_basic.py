from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
from ultimate_rules_rag.rag_chat_session import RagChatSession
import os
from dotenv import load_dotenv

load_dotenv()


def main(model_name: str, stream_output: bool = False):
    client = get_abstract_client(model=model_name)

    retriever_kwargs = {
        "limit": 5,
        "expand_context": 0,
        "search_type": "hybrid",
        "fts_operator": "OR"
    }

    print(f"Client: {client.__repr__()}")
    print(f"Stream output: {stream_output}")
    
    session = RagChatSession(
        llm_client=client,
        stream_output=stream_output,
        memory_size=3,
        context_size=1
    )

    print("\nEnter a question (or 'q' to quit): ")
    query = None
    while query != "q":
        query = input("\n\nQUESTION: ")
        if query != "q":
            print("\nANSWER:", end=" " if stream_output else "\n")
            response = session.answer_question(query, retriever_kwargs=retriever_kwargs)
            
            if stream_output:
                for chunk in response:
                    print(chunk, end="", flush=True)
                print()  # Add newline after streaming completes
            else:
                print(response)

    print(f"\n\nChat History:")
    session.history.pretty_print()


if __name__ == "__main__":
    # Available models:
    # - "gpt-4o-mini"
    # - "gpt-4o-2024-08-06"
    # - "claude-3-5-haiku-20241022"
    # - "claude-3-5-sonnet-20241022"
    
    model_name = "gpt-4o-mini"
    stream_output = True  # Set to False for structured output with relevant rules
    
    main(model_name, stream_output)

  
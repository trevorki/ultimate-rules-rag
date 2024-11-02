from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
from ultimate_rules_rag.rag_chat_session import RagChatSession
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


# Example usage
if __name__ == "__main__":
    # model = "claude-3-5-sonnet-20240620"
    # client = AnthropicAbstractedClient(model=model)

    model = "gpt-4o-mini"
    # model = "gpt-4o-2024-08-06"
    client = get_abstract_client(client_type="openai", model=model)

    retriever_kwargs = {
        "limit": 5,
        "expand_context": 0,
        "search_type": "hybrid",
        "fts_operator": "OR"
    }

    print(f"client: {client.__repr__()}")
    session = RagChatSession(
        llm_client=client,
        stream_output=False,
        memory_size=0,
        context_size=1
    )
    print(session.__dict__)
    print("Enter a question (or 'q' to quit): ")
    query = None
    while query != "q":
        query = input("\n\nQUESTION: ")
        if query != "q":
            answer = session.answer_question(query, retriever_kwargs=retriever_kwargs)
            if not session.stream_output: 
                print("\nANSWER:") 
                print(answer)

    print(f"\n\nhistory:")
    session.history.pretty_print()

  
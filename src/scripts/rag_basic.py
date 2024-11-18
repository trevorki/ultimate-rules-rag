from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
# from ultimate_rules_rag.rag_chat_session import RagChatSession
from ultimate_rules_rag.rag_chat import RagChat
from ultimate_rules_rag.db_client import DBClient
import os
from dotenv import load_dotenv

load_dotenv()


def main(default_model: str):
    llm_client = get_abstract_client(default_model=default_model)
    db_client = DBClient()
    memory_size = 3

    rag_chat = RagChat(
        llm_client=llm_client,
        memory_size=memory_size
    )
    print(f"llm_client: {rag_chat.llm_client.__dict__}")

    
    user_email = "trevorkinsey@gmail.com"
    conversation_id = rag_chat.create_conversation(user_email=user_email)

    print(f"user_id: {user_email}")
    print(f"created conversation_id: {conversation_id}")

    retriever_kwargs = {
        "limit": 5,
        "expand_context": 0,
        "search_type": "hybrid",
        "fts_operator": "OR"
    }

    print("\nEnter a question (or 'q' to quit): ")
    query = None
    while query != "q":
        query = input("\n\nQUESTION: ")
        if query != "q":
            print("\nANSWER:", end="\n")
            response = rag_chat.answer_question(query, conversation_id, retriever_kwargs=retriever_kwargs)
            print(response)


    def pretty_print(history):
        print("\n\nCONVERSATION HISTORY:")
        for msg in history:
            if msg["role"] in ["user", "assistant"]:
                print(f"\n{msg['role'].upper()}: {msg['content']}")
    
    

    history = db_client.get_conversation_history(conversation_id, message_limit=memory_size)
    pretty_print(history)
    print(f"conversation_id: {conversation_id}")


if __name__ == "__main__":
    from uuid import uuid4
    # Available models:
    # - "gpt-4o-mini"
    # - "gpt-4o-2024-08-06"
    # - "claude-3-5-haiku-20241022"
    # - "claude-3-5-sonnet-20241022"
    
    default_model = "gpt-4o-mini"
    # default_model = "claude-3-5-sonnet-20241022"
    
    main(default_model)

    

  
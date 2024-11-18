from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
# from ultimate_rules_rag.rag_chat_session import RagChatSession
from ultimate_rules_rag.rag_chat_session_db import RagChatSession
from ultimate_rules_rag.db_client import DBClient
import os
from dotenv import load_dotenv

load_dotenv()


def main(model_name: str, stream_output: bool = False):
    llm_client = get_abstract_client(model=model_name)
    
    db_client = DBClient()
    memory_size = 3
    user_email = "trevorkinsey@gmail.com"
    
    conversation_id = db_client.create_conversation(user_email=user_email)

    retriever_kwargs = {
        "limit": 5,
        "expand_context": 0,
        "search_type": "hybrid",
        "fts_operator": "OR"
    }

    print(f"Client: {llm_client.__repr__()}")
    print(f"Stream output: {stream_output}")
    print(f"user_id: {user_email}")
    print(f"conversation_id: {conversation_id}")

    
    session = RagChatSession(
        llm_client=llm_client,
        memory_size=memory_size,
        conversation_id=conversation_id,
        username=user_email
    )

    print("\nEnter a question (or 'q' to quit): ")
    query = None
    while query != "q":
        query = input("\n\nQUESTION: ")
        if query != "q":
            print("\nANSWER:", end=" " if stream_output else "\n")
            response = session.answer_question(query, retriever_kwargs=retriever_kwargs)
            print(response)


    def pretty_print(history):
        print("\n\nCONVERSATION HISTORY:")
        for msg in history:
            if msg["role"] in ["user", "assistant"]:
                print(f"\n{msg['role'].upper()}: {msg['content']}")
    
    
    print(f"\n\nChat History:")
    history = db_client.get_conversation_history(conversation_id, message_limit=memory_size)
    pretty_print(history)


if __name__ == "__main__":
    from uuid import uuid4
    # Available models:
    # - "gpt-4o-mini"
    # - "gpt-4o-2024-08-06"
    # - "claude-3-5-haiku-20241022"
    # - "claude-3-5-sonnet-20241022"
    
    model_name = "gpt-4o-mini"
    stream_output = True  # Set to False for structured output with relevant rules
   
    
    main(model_name, stream_output)

    

  
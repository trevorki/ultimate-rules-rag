import requests
import json

BASE_URL = "http://localhost:8000"

def test_chat_session():
    # Test creating a new chat session
    chat_data = {
        "message": "What is a callahan?",
        "model_name": "gpt-4o-mini",
        "stream": False  # Set to False for simpler testing
    }
    
    print("\n1. Testing new chat session...")
    response = requests.post(f"{BASE_URL}/chat", json=chat_data)
    if response.status_code == 200:
        result = response.json()
        session_id = result["session_id"]
        print(f"Session ID: {session_id}")
        print(f"Response: {result['response']}\n")
    else:
        print(f"Error: {response.status_code}")
        return

    # Test continuing the conversation
    print("2. Testing follow-up question...")
    chat_data = {
        "session_id": session_id,
        "message": "How many players are on the field during play?",
        "stream": False
    }
    response = requests.post(f"{BASE_URL}/chat", json=chat_data)
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result['response']}\n")
    
    # Test getting chat history
    print("3. Testing history retrieval...")
    response = requests.get(f"{BASE_URL}/sessions/{session_id}/history")
    if response.status_code == 200:
        history = response.json()
        print("Chat history:")
        print(json.dumps(history, indent=2))
    
    # Test deleting the session
    print("\n4. Testing session deletion...")
    response = requests.delete(f"{BASE_URL}/sessions/{session_id}")
    if response.status_code == 200:
        print("Session successfully deleted")

if __name__ == "__main__":
    test_chat_session()
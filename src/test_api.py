import requests
import json

BASE_URL = "http://localhost:8000"

def login(username, password):
    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": username, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def create_conversation(headers):
    conv_response = requests.post(
        f"{BASE_URL}/conversation",
        headers=headers
    )
    assert conv_response.status_code == 200
    conversation_id = conv_response.json()["conversation_id"]
    print("Created conversation:", conversation_id)
    return conversation_id

def send_chat_message(headers, message, conversation_id):
    chat_response = requests.post(
        f"{BASE_URL}/chat",
        headers=headers,
        json={
            "message": message,
            "conversation_id": conversation_id
        }
    )
    assert chat_response.status_code == 200
    print("Chat response:", json.dumps(chat_response.json(), indent=2))
    return chat_response.json()

def get_conversation_history(headers, conversation_id):
    history_response = requests.get(
        f"{BASE_URL}/conversation/{conversation_id}",
        headers=headers
    )
    print(f"Status code: {history_response.status_code}")
    print(f"Response: {history_response.json()}")
    assert history_response.status_code == 200
    print("Conversation history:", json.dumps(history_response.json(), indent=2))
    return history_response.json()

def change_password(headers, email, old_password, new_password):
    change_response = requests.post(
        f"{BASE_URL}/change-password",
        headers=headers,
        json={"email": email, "old_password": old_password, "new_password": new_password}
    )
    print(f"Status code: {change_response.status_code}")
    print(f"Response: {change_response.json()}")
    assert change_response.status_code == 200
    return change_response.json()

def test_api():
    # Login and setup
    username = "trevorkinsey@gmail.com"
    password = "ultimaterulesrag"
    token = login(username, password)
    headers = get_headers(token)
    
    # # Create conversation
    # conversation_id = create_conversation(headers)
    
    # # Send messages
    # send_chat_message(headers, "What is a callahan?", conversation_id)
    # send_chat_message(headers, "What is a pull?", conversation_id)
    
    # # Get history
    # get_conversation_history(headers, conversation_id)

    # Change password
    old_password = "ultimaterulesrag2"
    new_password = "ultimaterulesrag"
    change_password(headers, "trevorkinsey@gmail.com", old_password, new_password)

if __name__ == "__main__":
    test_api()
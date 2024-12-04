import pytest
from uuid import uuid4
from datetime import datetime, UTC
from .db_client import DBClient

@pytest.fixture
def db_client():
    return DBClient()

@pytest.fixture
def test_user(db_client):
    email = f"test_{uuid4()}@test.com"
    password = "test_password_123"
    user_id = db_client.create_user(email, password)
    return {"id": user_id, "email": email, "password": password}

@pytest.fixture
def test_conversation(db_client, test_user):
    conversation_id = db_client.create_conversation(user_email=test_user["email"])
    return conversation_id

@pytest.fixture
def test_message(db_client, test_conversation):
    message_id = db_client.add_message(
        conversation_id=test_conversation,
        conversation_role="user",
        content="Test message"
    )
    return message_id

def test_create_user(db_client):
    email = f"test_{uuid4()}@test.com"
    password = "test_password_123"
    
    # Test creating new user
    user_id = db_client.create_user(email, password)
    assert user_id is not None
    
    # Test duplicate user
    duplicate_id = db_client.create_user(email, password)
    assert duplicate_id == user_id  # Should return existing user's ID

def test_get_user_id(db_client, test_user):
    user_id = db_client.get_user_id(test_user["email"])
    assert user_id == test_user["id"]
    
    # Test non-existent user
    non_existent = db_client.get_user_id("nonexistent@test.com")
    assert non_existent is None

def test_check_password(db_client, test_user):
    # Test correct password
    assert db_client.check_password(test_user["email"], test_user["password"]) is True
    
    # Test incorrect password
    assert db_client.check_password(test_user["email"], "wrong_password") is False

def test_change_password(db_client, test_user):
    new_password = "new_password_123"
    db_client.change_password(test_user["email"], new_password)
    
    # Verify new password works
    assert db_client.check_password(test_user["email"], new_password) is True
    # Verify old password doesn't work
    assert db_client.check_password(test_user["email"], test_user["password"]) is False

def test_create_conversation(db_client, test_user):
    # Test with email
    conv_id1 = db_client.create_conversation(user_email=test_user["email"])
    assert conv_id1 is not None
    
    # Test with user_id
    conv_id2 = db_client.create_conversation(user_id=test_user["id"])
    assert conv_id2 is not None
    
    # Test with specific conversation_id
    specific_id = str(uuid4())
    conv_id3 = db_client.create_conversation(
        user_email=test_user["email"],
        conversation_id=specific_id
    )
    assert conv_id3 == specific_id

def test_add_message(db_client, test_conversation):
    content = "Test message"
    message_id = db_client.add_message(
        conversation_id=test_conversation,
        conversation_role="user",
        content=content
    )
    assert message_id is not None

    # Test with specific timestamp using timezone-aware datetime
    timestamp = datetime.now(UTC)
    message_id2 = db_client.add_message(
        conversation_id=test_conversation,
        conversation_role="assistant",
        content=content,
        created_at=timestamp
    )
    assert message_id2 is not None

def test_add_llm_call(db_client, test_message):
    llm_call = db_client.add_llm_call(
        message_id=test_message,
        message_type="answer",
        prompt="Test prompt",
        response="Test response",
        model="claude-3-5-sonnet-20241022",
        usage={"input_tokens": 10, "output_tokens": 20}
    )
    assert llm_call is not None
    assert "cost" in llm_call
    assert llm_call["cost"] > 0  # Should have some cost for this model

def test_get_conversation_history(db_client, test_conversation):
    # Add some messages
    messages = [
        ("user", "Message 1"),
        ("assistant", "Response 1"),
        ("user", "Message 2"),
        ("assistant", "Response 2"),
    ]
    
    for role, content in messages:
        db_client.add_message(test_conversation, role, content)
    
    # Test with different limits
    history = db_client.get_conversation_history(test_conversation, 2)
    assert len(history) == 2
    
    full_history = db_client.get_conversation_history(test_conversation, 10)
    assert len(full_history) == len(messages)
    
    # Verify chronological order
    assert full_history[0]["content"] == "Message 1"
    assert full_history[-1]["content"] == "Response 2"

def test_get_conversation(db_client, test_conversation):
    # Add message with LLM call
    message_id = db_client.add_message(
        test_conversation,
        "user",
        "Test message"
    )
    
    db_client.add_llm_call(
        message_id=message_id,
        message_type="answer",
        prompt="Test prompt",
        response="Test response",
        model="claude-3-5-sonnet-20241022",
        usage={"input_tokens": 10, "output_tokens": 20}
    )
    
    conversation = db_client.get_conversation(test_conversation)
    assert len(conversation) > 0
    
    # Verify message and LLM call are linked
    message = next(msg for msg in conversation if msg["id"] == message_id)
    assert message is not None
    assert message["content"] == "Test message"
    assert "model" in message  # Should include LLM call details

def test_verify_user_email(db_client, test_user):
    assert db_client.verify_user_email(test_user["email"]) is True
    
    # Test non-existent user
    assert db_client.verify_user_email("nonexistent@test.com") is False

def test_update_password(db_client, test_user):
    new_password = "updated_password_123"
    assert db_client.update_password(test_user["email"], new_password) is True
    
    # Verify new password works
    assert db_client.check_password(test_user["email"], new_password) is True
    
    # Test non-existent user
    assert db_client.update_password("nonexistent@test.com", "any_password") is False 
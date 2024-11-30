from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from ..response_formats import PasswordChange, ChatRequest, ChatResponse, ConversationHistory, ChatMessage
from ..db_client import DBClient
from ..rag_chat import RagChat
from ..clients.get_abstract_client import get_abstract_client
import jwt
from datetime import datetime, timedelta
import os
from typing import Optional
from uuid import UUID

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DEFAULT_CLIENT_TYPE = "openai"
DEFAULT_CLIENT_TYPE = "cerebras"
DEFAULT_MEMORY_SIZE = 3

# Initialize clients
db_client = DBClient()
rag_chat = RagChat(llm_client_type=DEFAULT_CLIENT_TYPE, memory_size=DEFAULT_MEMORY_SIZE)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return email
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not db_client.check_password(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token({"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: str = Depends(get_current_user)
):
    if not db_client.check_password(password_change.email, password_change.old_password):
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    db_client.change_password(password_change.email, password_change.new_password)
    return {"message": "Password changed successfully"}

@app.post("/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    current_user: str = Depends(get_current_user)
):
    try:
        # Create new conversation if none exists
        conversation_id = chat_request.conversation_id or rag_chat.create_conversation(current_user)
        
        # Get response from RAG system
        response = rag_chat.answer_question(
            chat_request.message,
            str(conversation_id),
            retriever_kwargs={
                "limit": 5,
                "expand_context": 0,
                "search_type": "hybrid",
                "fts_operator": "OR"
            }
        )
        
        return ChatResponse(message=response, conversation_id=conversation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(
    conversation_id: UUID,
):
    try:
        messages = db_client.get_conversation_history(str(conversation_id), rag_chat.memory_size)
        chat_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]
        return ConversationHistory(messages=chat_messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation")
async def create_conversation(
    current_user: str = Depends(get_current_user)
) -> dict:
    try:
        conversation_id = rag_chat.create_conversation(user_email=current_user)
        return {"conversation_id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ultimate_rules_rag.clients.get_abstract_client import get_abstract_client
from ultimate_rules_rag.rag_chat_session import RagChatSession
from contextlib import asynccontextmanager
import uuid

# Store active sessions
chat_sessions: Dict[str, RagChatSession] = {}

# Pydantic models
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model_name: str = "gpt-4o-mini"
    stream: bool = True
    retriever_kwargs: Optional[Dict[Any, Any]] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str

# Default retriever settings
DEFAULT_RETRIEVER_KWARGS = {
    "limit": 5,
    "expand_context": 0,
    "search_type": "hybrid",
    "fts_operator": "OR"
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load any necessary resources
    yield
    # Shutdown: Clear all chat sessions
    chat_sessions.clear()

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Get or create session
        session_id = request.session_id or str(uuid.uuid4())
        
        if session_id not in chat_sessions:
            client = get_abstract_client(model=request.model_name)
            chat_sessions[session_id] = RagChatSession(
                llm_client=client,
                stream_output=request.stream,
                memory_size=3,
                context_size=1
            )
        
        # Get session
        session = chat_sessions[session_id]
        
        # Use provided retriever kwargs or defaults
        retriever_kwargs = request.retriever_kwargs or DEFAULT_RETRIEVER_KWARGS
        
        # Get response
        if request.stream:
            # For streaming, collect chunks into final response
            response = ""
            for chunk in session.answer_question(request.message, retriever_kwargs=retriever_kwargs):
                response += chunk
        else:
            response = session.answer_question(request.message, retriever_kwargs=retriever_kwargs)
        
        return ChatResponse(
            session_id=session_id,
            response=response
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/history")
async def get_chat_history(session_id: str):
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_id]
    return {"history": session.history.messages}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return {"status": "success"}

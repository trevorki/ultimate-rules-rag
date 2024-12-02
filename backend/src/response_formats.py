from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str = Field(..., min_length=8)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    message: str
    conversation_id: UUID

class ConversationHistory(BaseModel):
    messages: List[ChatMessage]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SignupRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str 

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
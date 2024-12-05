from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from ..response_formats import (
    PasswordChange, 
    ChatRequest, 
    ChatResponse, 
    SignupRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from ..db_client import DBClient
from ..rag_chat import RagChat
from ..simple_gmail_client import SimpleGmailClient
import jwt
from datetime import datetime, timedelta, UTC
import os
import traceback
import logging
import secrets
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI()
gmail_client = SimpleGmailClient()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://172.18.0.4:3000",
        "http://192.168.0.163:3000",
        "http://192.168.0.163"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FRONTEND_URL = "http://localhost:3000"
FRONTEND_URL = "http://192.168.0.163:3000"

DEFAULT_CLIENT_TYPE = "openai"
# DEFAULT_CLIENT_TYPE = "anthropic"
DEFAULT_MEMORY_SIZE = 5
RETRIEVER_KWARGS = {
    "search_type": "semantic",
    "fts_operator": "OR",
    "limit": 3,
    "expand_context": 1,
    "semantic_weight": 0.8,
    "fts_weight": 0.2
}

# Initialize clients
db_client = DBClient()
rag_chat = RagChat(
    llm_client_type=DEFAULT_CLIENT_TYPE, 
    memory_size=DEFAULT_MEMORY_SIZE
)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DELTA = timedelta(hours=1)
EMAIL_VERIFICATION_EXPIRE_DELTA = timedelta(hours=24)
PASSWORD_RESET_EXPIRE_DELTA = timedelta(hours=1)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        # Default to 24 hours if not specified
        expire = datetime.now(UTC) + timedelta(hours=24)
        
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
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not db_client.check_password(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token({"sub": form_data.username}, expires_delta=ACCESS_TOKEN_EXPIRE_DELTA)
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
            retriever_kwargs=RETRIEVER_KWARGS
        )
        
        return ChatResponse(message=response, conversation_id=conversation_id)
    except Exception as e:
        # Log the full error traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in chat endpoint: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}\n{error_details}")


@app.post("/conversation")
async def create_conversation(
    current_user: str = Depends(get_current_user)
) -> dict:
    try:
        conversation_id = rag_chat.create_conversation(user_email=current_user)
        logger.info(f"Created conversation: {conversation_id}")
        return {"conversation_id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/signup")
async def signup(request: SignupRequest):
    try:
        logger.info(f"Attempting to signup user: {request.email}")
        
        # Check if user already exists
        existing_user = db_client.get_user_id(request.email)
        if existing_user:
            logger.info(f"User already exists: {request.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user with unverified status
        logger.info(f"Creating new user: {request.email}")
        user_id = db_client.create_user(request.email, request.password)
        if not user_id:
            logger.error(f"Failed to create user: {request.email}")
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        try:
            # Generate verification token using JWT
            logger.info(f"Generating verification token for: {request.email}")
            verification_token = create_access_token(
                data={"sub": request.email, "type": "email_verification"},
                expires_delta=EMAIL_VERIFICATION_EXPIRE_DELTA
            )
            
            # Send verification email
            logger.info(f"Sending verification email to: {request.email}")
            email_client = SimpleGmailClient()
            email_sent = email_client.send_validation_email(
                email_address=request.email,
                base_url=FRONTEND_URL,
                token=verification_token
            )
            
            if not email_sent:
                logger.error(f"Failed to send verification email to: {request.email}")
                # Don't fail the signup, just log the error
                return {
                    "message": "Account created but verification email could not be sent. "
                              "Please contact support for assistance."
                }
            
        except Exception as e:
            logger.error(f"Email error: {str(e)}")
            # Don't fail the signup, just log the error
            return {
                "message": "Account created but verification email could not be sent. "
                          "Please contact support for assistance."
            }
        
        logger.info(f"Successfully signed up user: {request.email}")
        return {"message": "Please check your email to verify your account"}
        
    except Exception as e:
        logger.error(f"Error in signup: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verify")
async def verify_email(token: str):
    try:
        # Decode and verify the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check if this is an email verification token
        if payload.get("type") != "email_verification":
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Update user's verified status
        if not db_client.verify_user_email(email):
            raise HTTPException(status_code=400, detail="Failed to verify email")
        
        return {"message": "Email verified successfully"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Verification link has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    try:
        logger.info(f"Processing forgot password request for: {request.email}")
        
        # Check if user exists
        user_id = db_client.get_user_id(request.email)
        if not user_id:
            logger.info(f"No user found for email: {request.email}")
            return {"message": "If the email exists, you will receive a password reset link"}
        
        # Generate password reset token using JWT
        logger.info("Generating reset token")
        reset_token = create_access_token(
            data={"sub": request.email, "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # Send password reset email
        logger.info(f"Attempting to send password reset email to: {request.email}")
        email_client = SimpleGmailClient()
        
        # Debug: Print the token and URL being used
        logger.info(f"Using frontend URL: {FRONTEND_URL}")
        logger.info(f"Generated reset token: {reset_token[:20]}...")  # Only log first 20 chars for security
        
        email_sent = email_client.send_forgot_password_email(
            email_address=request.email,
            base_url=FRONTEND_URL,
            token=reset_token
        )
        
        if not email_sent:
            logger.error(f"Failed to send password reset email to: {request.email}")
            raise HTTPException(status_code=500, detail="Failed to send password reset email")
        
        logger.info(f"Successfully sent password reset email to: {request.email}")
        return {"message": "If the email exists, you will receive a password reset link"}
        
    except Exception as e:
        logger.error(f"Error in forgot password: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    try:
        logger.info(f"Processing password reset request")
        
        # Verify and decode token
        try:
            payload = jwt.decode(request.token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=400, detail="Reset link has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=400, detail="Invalid reset token")
            
        # Check if this is a password reset token
        if payload.get("type") != "password_reset":
            logger.error("Invalid token type")
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        email = payload.get("sub")
        if not email:
            logger.error("No email in token")
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Update password in database
        db_client = DBClient()
        success = db_client.update_password(email, request.new_password)
        
        if not success:
            logger.error(f"Failed to update password for {email}")
            raise HTTPException(status_code=500, detail="Failed to update password")
        
        logger.info(f"Successfully reset password for {email}")
        return {"message": "Password has been reset successfully"}
        
    except Exception as e:
        logger.error(f"Error in reset password: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
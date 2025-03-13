from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Base User class
class UserBase(BaseModel):
    email: EmailStr

# User creation schema
class UserCreate(UserBase):
    password: str

# Schema for user information returned to client
class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Login schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str

# Token data schema
class TokenData(BaseModel):
    email: Optional[str] = None 
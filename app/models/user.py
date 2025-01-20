from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="The name of the user")
    email: EmailStr = Field(..., description="A valid email address")
    password: str = Field(..., min_length=8, max_length=100, description="The user's password")

class UserResponse(BaseModel):
    id: str
    name: str
    email: str

    class Config:
        orm_mode = True  # This allows using ORM objects directly with the model

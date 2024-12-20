from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import List

authRouter = APIRouter()

@authRouter.get("/register")
async def register():
   
    return "created_user"

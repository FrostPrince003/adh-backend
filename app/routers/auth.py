from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_database
from app.utils.token import create_access_token, create_refresh_token

authRouter = APIRouter()

# Models
class RegisterData(BaseModel):
    firebaseUID: str
    name: str
    email: EmailStr
    password: str  # Ideally, passwords should be hashed before storage

    class Config:
        min_anystr_length = 1
        anystr_strip_whitespace = True

class LoginData(BaseModel):
    firebaseUID: str

# Register route
@authRouter.post("/register", response_model=dict)
async def register(data: RegisterData, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Register a new user in the database.
    """
    collection = db["users"]
    existing_user = await collection.find_one({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    user_data = data.dict()
    result = await collection.insert_one(user_data)

    if result.inserted_id:
        return {"id": str(result.inserted_id), "message": "User registered successfully"}
    
    raise HTTPException(status_code=500, detail="Failed to register the user.")

# Login route
@authRouter.post("/login", response_model=dict)
async def login(data: LoginData, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Authenticate user and issue tokens.
    """
    collection = db["users"]
    user = await collection.find_one({"firebaseUID": data.firebaseUID})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Generate tokens
    access_token = create_access_token(data={"sub": user["email"]})
    refresh_token = create_refresh_token(data={"sub": user["email"]})
    
    await collection.update_one(
        {"firebaseUID": data.firebaseUID},
        {"$set": {"access_token": access_token, "refresh_token": refresh_token}}
    )
    return {
      "data" : { "id": str(user["_id"]),
        "fid": user["firebaseUID"],
        "username": user["name"],
        "email": user["email"],
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
      },
      "status": 200,
    }

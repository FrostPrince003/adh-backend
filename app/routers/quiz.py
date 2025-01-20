from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_database

quizRouter = APIRouter()

@quizRouter.post("/topics")
async def create_topics(data: dict, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Insert topics into the database.
    """
    try:
        collection = db["quiz"]  # Collection name: "topics"
        print(f"Received data: {data}")  # Log received data
        result = await collection.insert_one(data)
        print(f"Insert result: {result.inserted_id}")  # Log insert result
        return {"message": "Topics created successfully", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"❌ Error creating topics: {e}")  # Log the error
        raise HTTPException(status_code=500, detail=f"Error creating topics: {e}")



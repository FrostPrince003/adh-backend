from fastapi import APIRouter, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
import json
from app.dependencies import get_database

analyticsRouter = APIRouter()

@analyticsRouter.post("/store_result")
async def store_result(
    totalQuestions: int = Form(...), 
    correctCount: int = Form(...), 
    incorrectCount: int = Form(...),
    resultDetails: str = Form(...),  # Receive the result details as a JSON string
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Store quiz results in MongoDB.
    """
    try:
        # Log the received data
        print(f"Received data: totalQuestions={totalQuestions}, correctCount={correctCount}, incorrectCount={incorrectCount}, resultDetails={resultDetails}")
        
        # Parse the resultDetails as JSON
        result_details = json.loads(resultDetails)
        
        # Create a dictionary to store in the database
        result_data = {
            "totalQuestions": totalQuestions,
            "correctCount": correctCount,
            "incorrectCount": incorrectCount,
            "resultDetails": result_details
        }

        collection = db["quiz"]  # MongoDB collection name
        result = await collection.insert_one(result_data)  # Insert result data
        print(f"Insert result: {result.inserted_id}")  # Log the inserted ID
        return JSONResponse(content={"message": "Quiz result stored successfully", "id": str(result.inserted_id)})
    except Exception as e:
        print(f"❌ Error storing quiz result: {e}")  # Log the error
        raise HTTPException(status_code=500, detail=f"Error storing quiz result: {e}")


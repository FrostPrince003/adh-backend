from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_database
import datetime

analytics_Router = APIRouter()

# Models
class AfterQuizData(BaseModel):
    quiz: dict
    username: str
    correct_questions: int
    wrong_questions: int
    time_taken_per_question: list[float]
    upload_time: datetime.datetime

@analytics_Router.post("/store_result")
async def add_after_quiz_data(
    data: AfterQuizData,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    total_questions = data.correct_questions + data.wrong_questions
    accuracy = (data.correct_questions / total_questions * 100) if total_questions else 0

    record = {
        "quiz": data.quiz,
        "correct_questions": data.correct_questions,
        "wrong_questions": data.wrong_questions,
        "time_taken_per_question": data.time_taken_per_question,
        "accuracy": accuracy,
        "upload_time": data.upload_time
    }

    result = await db["after_quiz_collection"].insert_one(record)
    return {"message": "Data inserted", "id": str(result.inserted_id)}

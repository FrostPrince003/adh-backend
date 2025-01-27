from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import random
from typing import Optional, Dict, List
from fastapi.middleware.cors import CORSMiddleware
from app.routers.db_connectq import fetch_questions_by_topics, transform_questions, save_questions_to_json, fetch_and_transform_questions
from fastapi import Request, HTTPException

reinRouter = APIRouter()

class AnswerRequest(BaseModel):
    answer: str  # Only the answer is required now

class QuizResponse(BaseModel):
    id: int
    correct: bool
    correct_answer: str
    reward: int
    new_toughness: float
    next_question: str
    options: List[str]

class AdaptiveQuizEnvironment():
    def __init__(self, questions_file: str):
        try:
            with open(questions_file, 'r') as f:
                self.questions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: {e}")
            self.questions = []

        self.min_toughness = 1.0
        self.max_toughness = 100.0
        self.current_toughness = 25.0
        self.asked_questions = set()
        self.current_question = None
        # Select initial question
        self._select_next_question()

    def _select_next_question(self) -> None:
        """Selects the next question based on current toughness."""
        candidates = [
            q for q in self.questions
            if abs(float(q["toughness"]) - self.current_toughness) <= 10
            and q["id"] not in self.asked_questions
        ]

        if not candidates:
            # Reset if we've run out of questions
            self.asked_questions.clear()
            candidates = [q for q in self.questions]

        if candidates:
            self.current_question = random.choice(candidates)
            self.asked_questions.add(self.current_question["id"])
        else:
            self.current_question = None

    def check_answer(self, user_answer: str) -> QuizResponse:
        """Checks answer and returns response with next question."""
        if not self.current_question:
            raise HTTPException(status_code=500, detail="No question available")

        # Check answer
        correct = user_answer.strip().lower() == self.current_question["answer"].strip().lower()

        # Adjust difficulty
        if correct:
            self.current_toughness = min(self.max_toughness, self.current_toughness + 10)
        else:
            self.current_toughness = max(self.min_toughness, self.current_toughness - 10)

        # Get current question's details before selecting next
        current_id = self.current_question["id"]
        current_answer = self.current_question["answer"]
        current_options = self.current_question["options"]

        # Select next question
        self._select_next_question()
        if not self.current_question:
            raise HTTPException(status_code=404, detail="No more questions available")

        return QuizResponse(
            id=current_id,
            correct=correct,
            correct_answer=current_answer,
            reward=1 if correct else -1,
            new_toughness=self.current_toughness,
            next_question=self.current_question["question"],
            options=current_options
        )

    def get_current_question(self) -> Dict:
        """Returns the current question."""
        if not self.current_question:
            self._select_next_question()
        return {
            "id": self.current_question["id"],
            "question": self.current_question["question"],
            "toughness": float(self.current_question["toughness"]),
            "options": self.current_question["options"]
        }

# Defer quiz initialization
quiz_env: Optional[AdaptiveQuizEnvironment] = None

def get_quiz_env() -> AdaptiveQuizEnvironment:
    """Lazily initializes and returns the quiz environment."""
    global quiz_env
    if quiz_env is None:
        quiz_env = AdaptiveQuizEnvironment(r"D:\Hackathons\AIT\adhyayan-backend\adhyayan-backend\adaptive_quiz\q.json")
    else:
        quiz_env = None
        quiz_env = AdaptiveQuizEnvironment(r"D:\Hackathons\AIT\adhyayan-backend\adhyayan-backend\adaptive_quiz\q.json")
    return quiz_env
    
    

@reinRouter.get("/current-question")
async def get_current_question():
    """Get the current question without answering."""
    quiz_env = get_quiz_env()
    question = quiz_env.get_current_question()
    if not question:
        raise HTTPException(status_code=404, detail="No questions available")
    return {
        "id": question["id"],
        "question": question["question"],
        "toughness": float(question["toughness"]),
        "options": question["options"]
    }

@reinRouter.post("/current-answer", response_model=QuizResponse)
async def submit_answer(request: Request):
    raw_body = await request.body()
    print(raw_body)
    try:
        answer_request = AnswerRequest.parse_raw(raw_body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    quiz_env = get_quiz_env()
    return quiz_env.check_answer(answer_request.answer)

# Request Body Model
class TopicRequest(BaseModel):
    topics: List[str]

# Response Model
class QuestionResponse(BaseModel):
    id: int
    question: str
    options: List[str]
    answer: str
    toughness: float

@reinRouter.post("/get-questions-by-topics", response_model=List[QuestionResponse])
def get_questions_by_topics(request: TopicRequest):
    """
    Fetch and transform questions based on given topics.
    """
    try:
        # Call the database handler function
        questions = fetch_and_transform_questions(request.topics, r"D:\Hackathons\AIT\adhyayan-backend\adhyayan-backend\adaptive_quiz\q.json")

        if not questions:
            raise HTTPException(status_code=404, detail="No questions found for the given topics.")
        
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@reinRouter.get("/")
async def home():
    return {
        "message": "Welcome to the Adaptive Quiz API!",
        "endpoints": {
            "GET /current-question": "Get the current question",
            "POST /answer": "Submit answer and get next question",
            "POST /get-questions-by-topics": "Fetch questions by topics"
        }
    }
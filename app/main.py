from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Database
from app.routers import quiz, auth, quiz_gen,reinforcement
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with a list of allowed origins for better security
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)

@app.on_event("startup")
async def startup():
    """Startup event: Initialize database connection."""
    await Database.connect()

@app.on_event("shutdown")
async def shutdown():
    """Shutdown event: Close database connection."""
    await Database.close()

# Include routers for different endpoints
app.include_router(quiz.quizRouter, prefix="/api/v1/quiz", tags=["Quiz"])
app.include_router(auth.authRouter, prefix="/api/v1/user", tags=["Authentification"])
app.include_router(quiz_gen.genRouter, prefix="/api/v1/qgen", tags=["Quiz Generation"])
app.include_router(reinforcement.reinRouter, prefix="/api/v1/rein", tags=["Reinforcement Learning"])
# Mount the uploaded_files directory to serve files publicly
app.mount("/uploads", StaticFiles(directory="uploaded_files"), name="uploads")

# Include the upload router


@app.get("/")
async def root():
    return {"message": "Welcome to Adhyayan Backend"}

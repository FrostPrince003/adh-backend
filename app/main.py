from fastapi import FastAPI
from app.database import connect_to_mongo, close_mongo_connection, get_db
from app.routers.auth import authRouter

app = FastAPI()

# Include authentication routes
app.include_router(authRouter, prefix="/api/v1/auth", tags=["auth"])

@app.on_event("startup")
async def startup_event():
    """Event triggered when the application starts."""
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    """Event triggered when the application shuts down."""
    await close_mongo_connection()

# Example endpoint to verify database connection
@app.get("/check-connection")
async def check_db_connection():
    """Endpoint to check database connection."""
    db = get_db()
    if db:
        return {"status": "Connected to MongoDB"}
    else:
        raise HTTPException(status_code=500, detail="Could not connect to MongoDB.")

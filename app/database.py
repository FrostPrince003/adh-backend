from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
import os

# MongoDB Connection URL from environment or default
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = "adhyayan"

# Initialize the MongoDB client as None
mongo_client = None

async def connect_to_mongo():
    """Establish connection to MongoDB."""
    global mongo_client
    if mongo_client is None:
        try:
            mongo_client = AsyncIOMotorClient(MONGO_URL)
            # Test the connection by accessing server info
            await mongo_client.server_info()
            print("Connected to MongoDB successfully!")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            raise HTTPException(status_code=500, detail="Could not connect to MongoDB.")

async def close_mongo_connection():
    """Close the MongoDB connection."""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        print("MongoDB connection closed.")

def get_db():
    """Return the database instance."""
    if not mongo_client:
        raise HTTPException(status_code=500, detail="Database connection is not initialized.")
    return mongo_client[DATABASE_NAME]

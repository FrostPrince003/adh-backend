from motor.motor_asyncio import AsyncIOMotorClient
import os

class Database:
    client: AsyncIOMotorClient = None

    @classmethod
    async def connect(cls):
        """Initialize the MongoDB connection."""
        try:
            # db_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            db_uri = "mongodb+srv://Dev1:Dev1dotcom@cluster0.aym5w.mongodb.net/"
            cls.client = AsyncIOMotorClient(db_uri)
            print("✅ Connected to MongoDB")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def close(cls):
        """Close the MongoDB connection."""
        if cls.client:
            cls.client.close()
            print("🛑 MongoDB connection closed.")

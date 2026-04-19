"""
Nova AI - Database Adapter
"""
from pymongo import MongoClient
import sys

from config import config

client = None
db = None

def get_db():
    global client, db
    if db is not None:
        return db
        
    if not config.MONGO_URI:
        print("WARNING: MONGO_URI is missing from .env! Make sure to replace <db_password> and provide the connection string.")
        sys.exit(1)
        
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
        # Check connection
        client.admin.command('ping')
        # Extract DB name from URI or default to 'nova'
        db_name = client.get_database().name or "nova"
        db = client[db_name]
        return db
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        print("Have you replaced <db_password> with your actual Atlas password?")
        sys.exit(1)

# Export the DB instance
db = get_db()

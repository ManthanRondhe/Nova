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
        print("WARNING: MONGO_URI is missing from environment variables!")
        return None
        
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
        # Check connection
        client.admin.command('ping')
        
        # Safely determine database name
        try:
            default_db = client.get_default_database()
            db = default_db if default_db is not None else client["nova"]
        except Exception:
            db = client["nova"]
            
        print(f"[+] Successfully connected to MongoDB database: {db.name}")
        return db
    except Exception as e:
        print(f"[!] Error connecting to MongoDB: {e}")
        print("[!] Ensure MONGO_URI is set correctly in environment variables.")
        # Fallback to local mock/in-memory or allow app to start so Render port binding succeeds
        try:
            db = client["nova"] if client else None
        except Exception:
            db = None
        return db

# Export the DB instance
db = get_db()


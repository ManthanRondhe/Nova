"""
AutoMech AI - CSV to MongoDB Migration Script
Run this script once to migrate all your existing CSV data to MongoDB.
"""
import os, sys, csv
from database import db

# Use the same data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def read_csv(filename):
    filepath = os.path.join(DATA_DIR, filename)
    rows = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    return rows

def migrate_collection(filename, collection_name):
    print(f"Migrating {filename} to collection '{collection_name}'...")
    rows = read_csv(filename)
    if not rows:
        print(f"  -> Skipping. No data in {filename}")
        return
    
    col = db[collection_name]
    # Drop existing to prevent duplicates during testing/migration
    col.delete_many({})
    
    # Insert everything
    col.insert_many(rows)
    print(f"  -> Successfully migrated {len(rows)} records!")

def run_migration():
    if db is None:
        print("Failed to map database. Check MONGO_URI in .env")
        sys.exit(1)
        
    print(f"Connected to MongoDB. Starting migration from {DATA_DIR}...")
    
    # Map CSV filename -> MongoDB collection name
    migrations = {
        "jobcards.csv": "jobcards",
        "inventory.csv": "inventory",
        "orders.csv": "orders",
        "dealers.csv": "dealers",
        "mechanics.csv": "mechanics",
        "pipeline.csv": "pipeline",
        "attendance.csv": "attendance",
        "salaries.csv": "salaries",
        "insurance.csv": "insurance",
        "admin_users.csv": "admin_users"
    }
    
    for filename, col_name in migrations.items():
        migrate_collection(filename, col_name)
        
    print("\n✅ Migration complete! Your project is now running on MongoDB.")

if __name__ == "__main__":
    run_migration()

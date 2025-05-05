#!/usr/bin/env python3

import os
import sys
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

# Try to import from app context
try:
    from flask import current_app
    app = current_app._get_current_object()
    with app.app_context():
        db = app.extensions['sqlalchemy'].db
except (RuntimeError, AttributeError, KeyError):
    # If not in app context, import directly
    try:
        from app import app, db, Recording
    except ImportError as e:
        print(f"Error: Could not import 'app' and 'db': {e}")
        print("Make sure migrate_original_filename.py is runnable and PYTHONPATH is set.")
        sys.exit(1)

def migrate_database():
    """
    Migrate the database schema to add original_filename column without losing data
    """
    print("Starting database migration for original_filename column...")
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check if Recording.original_filename column exists
        recording_columns = [column['name'] for column in inspector.get_columns('recording')]
        if 'original_filename' not in recording_columns:
            print("Adding original_filename column to Recording table...")
            try:
                # Add original_filename column to Recording table
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE recording ADD COLUMN original_filename VARCHAR(500)"))
                print("original_filename column added successfully!")
            except OperationalError as e:
                print(f"Error adding original_filename column: {e}")
                print("Attempting alternative approach...")
                try:
                    # SQLite doesn't support ALTER TABLE ADD COLUMN with foreign keys
                    # So we need to create a new table, copy data, drop old table, rename new table
                    
                    # 1. Create temporary table with new schema
                    with db.engine.begin() as conn:
                        conn.execute(db.text("""
                            CREATE TABLE recording_new (
                                id INTEGER PRIMARY KEY,
                                title VARCHAR(200),
                                participants VARCHAR(500),
                                notes TEXT,
                                transcription TEXT,
                                summary TEXT,
                                status VARCHAR(50),
                                audio_path VARCHAR(500),
                                created_at DATETIME,
                                meeting_date DATE,
                                file_size INTEGER,
                                user_id INTEGER REFERENCES user(id),
                                original_filename VARCHAR(500)
                            )
                        """))
                    
                    # 2. Copy data from old table to new table
                    with db.engine.begin() as conn:
                        conn.execute(db.text("""
                            INSERT INTO recording_new (
                                id, title, participants, notes, transcription, summary, 
                                status, audio_path, created_at, meeting_date, file_size, user_id
                            )
                            SELECT 
                                id, title, participants, notes, transcription, summary, 
                                status, audio_path, created_at, meeting_date, file_size, user_id
                            FROM recording
                        """))
                    
                    # 3. Drop old table
                    with db.engine.begin() as conn:
                        conn.execute(db.text("DROP TABLE recording"))
                    
                    # 4. Rename new table
                    with db.engine.begin() as conn:
                        conn.execute(db.text("ALTER TABLE recording_new RENAME TO recording"))
                    
                    print("original_filename column added successfully using table recreation!")
                except Exception as e2:
                    print(f"Error during table recreation: {e2}")
                    sys.exit(1)
        else:
            print("original_filename column already exists in Recording table.")
        
        print("Database migration completed successfully!")

if __name__ == "__main__":
    print("Attempting to migrate the database to add original_filename column...")
    migrate_database()
    print("Database migration process finished.")

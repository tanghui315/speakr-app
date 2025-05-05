#!/usr/bin/env python3

import os
import sys
from sqlalchemy import inspect, Column, Integer, ForeignKey
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
        from app import app, db, User, Recording
    except ImportError as e:
        print(f"Error: Could not import 'app' and 'db': {e}")
        print("Make sure migrate_db.py is runnable and PYTHONPATH is set.")
        sys.exit(1)

def migrate_database():
    """
    Migrate the database schema without losing data:
    1. Check if User table exists, create it if not
    2. Check if Recording.user_id column exists, add it if not
    """
    print("Starting database migration...")
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # Check if User table exists
        if 'user' not in existing_tables:
            print("Creating User table...")
            # Create User table
            class TempUser(db.Model):
                __tablename__ = 'user'
                id = db.Column(db.Integer, primary_key=True)
                username = db.Column(db.String(20), unique=True, nullable=False)
                email = db.Column(db.String(120), unique=True, nullable=False)
                password = db.Column(db.String(60), nullable=False)
            
            # Create only the User table
            db.create_all(tables=[TempUser.__table__])
            print("User table created successfully!")
        else:
            print("User table already exists.")
        
        # Check if Recording.user_id column exists
        recording_columns = [column['name'] for column in inspector.get_columns('recording')]
        if 'user_id' not in recording_columns:
            print("Adding user_id column to Recording table...")
            try:
                # Add user_id column to Recording table
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE recording ADD COLUMN user_id INTEGER REFERENCES user(id)"))
                print("user_id column added successfully!")
            except OperationalError as e:
                print(f"Error adding user_id column: {e}")
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
                                user_id INTEGER REFERENCES user(id)
                            )
                        """))
                    
                    # 2. Copy data from old table to new table
                    with db.engine.begin() as conn:
                        conn.execute(db.text("""
                            INSERT INTO recording_new (
                                id, title, participants, notes, transcription, summary, 
                                status, audio_path, created_at, meeting_date, file_size
                            )
                            SELECT 
                                id, title, participants, notes, transcription, summary, 
                                status, audio_path, created_at, meeting_date, file_size
                            FROM recording
                        """))
                    
                    # 3. Drop old table
                    with db.engine.begin() as conn:
                        conn.execute(db.text("DROP TABLE recording"))
                    
                    # 4. Rename new table
                    with db.engine.begin() as conn:
                        conn.execute(db.text("ALTER TABLE recording_new RENAME TO recording"))
                    
                    print("user_id column added successfully using table recreation!")
                except Exception as e2:
                    print(f"Error during table recreation: {e2}")
                    sys.exit(1)
        else:
            print("user_id column already exists in Recording table.")
        
        print("Database migration completed successfully!")

if __name__ == "__main__":
    print("Attempting to migrate the database...")
    migrate_database()
    print("Database migration process finished.")

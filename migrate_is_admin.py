#!/usr/bin/env python3

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Boolean

# Try to import from app context
try:
    from flask import current_app
    app = current_app._get_current_object()
    with app.app_context():
        db = app.extensions['sqlalchemy'].db
        User = app.extensions['sqlalchemy'].db.metadata.tables['user']
except (RuntimeError, AttributeError, KeyError):
    # If not in app context, import directly
    try:
        from app import app, db, User
    except ImportError as e:
        print(f"Error: Could not import required modules: {e}")
        print("Make sure migrate_is_admin.py is runnable and PYTHONPATH is set.")
        sys.exit(1)

def migrate_is_admin_field():
    """
    Add is_admin field to User model if it doesn't exist
    """
    print("Migrating database to add is_admin field to User model")
    print("=====================================================")
    
    with app.app_context():
        # Check if is_admin column exists
        inspector = db.inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('user')]
        
        if 'is_admin' in columns:
            print("is_admin column already exists in User table.")
            return
        
        # Add is_admin column
        print("Adding is_admin column to User table...")
        try:
            db.engine.execute('ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0')
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
            sys.exit(1)
        
        print("\nMigration completed successfully!")
        print("You can now use the create_admin.py script to create admin users.")

if __name__ == "__main__":
    migrate_is_admin_field()

#!/usr/bin/env python3

# Add this near the top if you run this standalone often outside app context
import os
import sys
# Add project root to path if necessary for 'app' import
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Adjust path as needed

# Check if running within app context already (e.g., via Flask command)
try:
    from flask import current_app
    app = current_app._get_current_object()
    db = app.extensions['sqlalchemy'].db # Access db via extensions typical pattern
except RuntimeError:
    # If not in app context, import directly (assuming reset_db.py is at the same level as app.py)
    # This might be needed if running `python reset_db.py` directly
    try:
        from app import app, db
    except ImportError:
        print("Error: Could not import 'app' and 'db'. Ensure reset_db.py is runnable.")
        print("Make sure your PYTHONPATH includes the project directory or run using 'flask run <command>'")
        sys.exit(1)


def reset_database():
    # Determine the database path relative to the instance folder
    # Assuming app is configured with instance_relative_config=True (default)
    # or manually construct path if instance folder is known
    instance_path = app.instance_path if hasattr(app, 'instance_path') else os.path.join(os.getcwd(), 'instance')
    db_filename = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/transcriptions.db').split('/')[-1]
    db_path = os.path.join(instance_path, db_filename)

    # Ensure instance directory exists
    os.makedirs(instance_path, exist_ok=True)

    # Remove existing database if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database at {db_path}")
        try:
            os.remove(db_path)
        except OSError as e:
            print(f"Error removing database file: {e}. Check permissions or if it's in use.")
            # Optionally exit or continue to create tables anyway
            # sys.exit(1)

    # Create application context to work with the database
    with app.app_context():
        print("Creating new database schema...")
        # Create all tables defined in models
        try:
            db.create_all()
            print("Database schema created successfully!")
        except Exception as e:
            print(f"Error creating database schema: {e}")
            sys.exit(1)

if __name__ == "__main__":
    print("Attempting to reset the database...")
    reset_database()
    print("Database reset process finished.")
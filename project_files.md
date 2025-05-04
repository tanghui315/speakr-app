# Project Files

Generated documentation of all project files.


## reset_db.py

```python

#!/usr/bin/env python3

# Add this near the top if you run this standalone often outside app context
import os
import sys
# Add project root to path if necessary for 'app' import
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables in case DB path relies on them (optional here)
# from dotenv import load_dotenv
# load_dotenv()

# Check if running within app context already (e.g., via Flask command)
try:
    from flask import current_app
    # Ensure app context is pushed if needed for config access
    app = current_app._get_current_object()
    # Make sure db is initialized within the app context if needed
    # (SQLAlchemy initialization in app.py handles this mostly)
    with app.app_context():
      db = app.extensions['sqlalchemy'].db # Access db via extensions
except (RuntimeError, AttributeError, KeyError):
     # If not in app context, import directly
    try:
        # Ensure this import reflects the updated app.py with the new model
        from app import app, db
    except ImportError as e:
        print(f"Error: Could not import 'app' and 'db': {e}")
        print("Make sure reset_db.py is runnable and PYTHONPATH is set.")
        sys.exit(1)

def reset_database():
    # Determine the database path relative to the instance folder
    # Use app config if available
    instance_path = app.instance_path if hasattr(app, 'instance_path') else os.path.join(os.getcwd(), 'instance')
    try:
        # Ensure app context for config access if not already present
        with app.app_context():
             # Use absolute path from config
             db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/transcriptions.db')
             # Handle relative vs absolute paths specified in URI
             if db_uri.startswith('sqlite:///'):
                 # Assume absolute path from URI root if starts with '///'
                 db_path = db_uri.replace('sqlite:///', '/', 1) # Replace only first
                 # Ensure instance path reflects the directory containing the DB
                 instance_path = os.path.dirname(db_path)
             elif db_uri.startswith('sqlite://'):
                 # Assume relative path from instance folder
                 db_filename = db_uri.split('/')[-1]
                 db_path = os.path.join(instance_path, db_filename)
             else: # Handle other DB types or formats if needed
                 print(f"Warning: Non-SQLite URI detected: {db_uri}. Deletion logic might need adjustment.")
                 # Attempt to parse or fallback
                 db_filename = db_uri.split('/')[-1] # Best guess
                 db_path = os.path.join(instance_path, db_filename)

    except Exception as config_e:
        print(f"Error accessing app config for DB path: {config_e}. Using default.")
        # Fallback if config access fails
        instance_path = os.path.join(os.getcwd(), 'instance')
        db_filename = 'transcriptions.db'
        db_path = os.path.join(instance_path, db_filename)

    # Ensure instance directory exists
    print(f"Ensuring instance directory exists: {instance_path}")
    os.makedirs(instance_path, exist_ok=True)
    print(f"Database path identified as: {db_path}")

    # Remove existing database if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database at {db_path}")
        try:
            os.remove(db_path)
            # Also remove journal file if it exists
            journal_path = db_path + "-journal"
            if os.path.exists(journal_path):
                os.remove(journal_path)
                print(f"Removing existing journal file at {journal_path}")
        except OSError as e:
            print(f"Error removing database file: {e}. Check permissions or if it's in use.")
            # Decide whether to exit or continue
            # sys.exit(1)

    # Create application context to work with the database
    try:
        with app.app_context():
            print("Creating new database schema (including 'summary' column)...")
            # Create all tables defined in models (app.py)
            db.create_all()
            print("Database schema created successfully!")
    except Exception as e:
        print(f"Error creating database schema: {e}")
        # Attempt rollback if possible (though less relevant for create_all)
        try:
             db.session.rollback()
        except Exception as rb_e:
             print(f"Rollback attempt failed: {rb_e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Attempting to reset the database...")
    reset_database()
    print("Database reset process finished.")
```


## app.py

```python

# app.py
import os
import sys
from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from openai import OpenAI # Keep using the OpenAI library
import json
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import select
import threading
from dotenv import load_dotenv # Import load_dotenv
import httpx 

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Ensure the path uses the directory structure from your setup script
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////opt/transcription-app/instance/transcriptions.db'
app.config['UPLOAD_FOLDER'] = '/opt/transcription-app/uploads' # Use absolute path based on setup
app.config['MAX_CONTENT_LENGTH'] = 250 * 1024 * 1024  # 250MB max file size
db = SQLAlchemy()
db.init_app(app)

# Ensure upload and instance directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Assuming the instance folder is handled correctly by Flask or created by setup.sh
# os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '/')), exist_ok=True)


# --- Database Models ---
class Recording(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Title will now often be AI-generated, maybe start with filename?
    title = db.Column(db.String(200), nullable=True) # Allow Null initially
    participants = db.Column(db.String(500))
    notes = db.Column(db.Text)
    transcription = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True) # <-- ADDED: Summary field
    status = db.Column(db.String(50), default='PENDING') # PENDING, PROCESSING, SUMMARIZING, COMPLETED, FAILED
    audio_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)  # Store file size in bytes

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'participants': self.participants,
            'notes': self.notes,
            'transcription': self.transcription,
            'summary': self.summary, # <-- ADDED: Include summary
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'file_size': self.file_size
        }

with app.app_context():
    db.create_all()

# --- API client setup for OpenRouter ---
# Use environment variables from .env
openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
openrouter_model_name = os.environ.get("OPENROUTER_MODEL_NAME", "openai/gpt-3.5-turbo") # Default if not set

http_client_no_proxy = httpx.Client(verify=True) # verify=True is default, but good to be explicit

if not openrouter_api_key:
    app.logger.warning("OPENROUTER_API_KEY not found. Title/Summary generation DISABLED.")
else:
    try:
        # ---> Pass the custom httpx_client <---
        client = OpenAI(
            api_key=openrouter_api_key,
            base_url=openrouter_base_url,
            http_client=http_client_no_proxy # Pass the proxy-disabled client
        )
        app.logger.info(f"OpenRouter client initialized. Using model: {openrouter_model_name}")
    except Exception as client_init_e:
         app.logger.error(f"Failed to initialize OpenRouter client: {client_init_e}", exc_info=True)

# Store details for the transcription client (potentially different)
transcription_api_key = os.environ.get("OPENAI_API_KEY", "cant-be-empty")
transcription_base_url = os.environ.get("OPENAI_BASE_URL", "http://192.168.68.85:1611/v1/")

app.logger.info(f"Using OpenRouter model for summaries: {openrouter_model_name}")

# --- Background Transcription & Summarization Task ---
def transcribe_audio_task(app_context, recording_id, filepath, original_filename):
    """Runs the transcription and summarization in a background thread."""
    with app_context: # Need app context for db operations in thread
        recording = db.session.get(Recording, recording_id)
        if not recording:
            app.logger.error(f"Error: Recording {recording_id} not found for transcription.")
            return

        try:
            app.logger.info(f"Starting transcription for recording {recording_id} ({original_filename})...")
            recording.status = 'PROCESSING'
            db.session.commit()

            # --- Step 1: Transcription ---
            with open(filepath, 'rb') as audio_file:
                # NOTE: This still uses the hardcoded Whisper model.
                # If you want OpenRouter for transcription too, change the model here
                # and potentially adjust the API call if needed.
                # For now, assuming Whisper via a local compatible endpoint.
                # You might need a *separate* client for Whisper if it's at a different URL.
                # Example using the configured client (assuming it points to Whisper or OpenRouter handles it):
                transcription_client = OpenAI(
                    api_key=transcription_api_key,
                    base_url=transcription_base_url,
                    http_client=http_client_no_proxy # Reuse the same client configuration
                )
                transcript = transcription_client.audio.transcriptions.create(
                    model="Systran/faster-distil-whisper-large-v3", # Your Whisper model
                    file=audio_file,
                    language="en" # Specify language if known
                )
            recording.transcription = transcript.text
            app.logger.info(f"Transcription completed for recording {recording_id}. Text length: {len(recording.transcription)}")
            # Don't commit yet, proceed to summarization

            # --- Step 2: Title & Summary Generation using OpenRouter ---
            if client is None: # Check if OpenRouter client initialized successfully earlier
                app.logger.warning(f"Skipping summary for {recording_id}: OpenRouter client not configured.")
                recording.summary = "[Summary skipped: OpenRouter client not configured]"
                recording.status = 'COMPLETED'
                db.session.commit()
                return # Exit cleanly
            
            recording.status = 'SUMMARIZING' # Update status
            db.session.commit()
            app.logger.info(f"Requesting title and summary from OpenRouter for recording {recording_id} using model {openrouter_model_name}...")

            if not recording.transcription or len(recording.transcription.strip()) < 10: # Basic check for valid transcript
                 app.logger.warning(f"Transcription for recording {recording_id} is too short or empty. Skipping summarization.")
                 recording.status = 'COMPLETED' # Mark as completed even without summary
                 recording.summary = "[Summary skipped due to short transcription]"
                 db.session.commit()
                 return # Exit the task cleanly

            # Prepare the prompt for OpenRouter
            prompt_text = f"""Analyze the following audio transcription and generate a concise title and a brief summary.

Transcription:
\"\"\"
{recording.transcription[:30000]}
\"\"\"

Respond STRICTLY with a JSON object containing two keys: "title" (a short, descriptive title, max 15 words) and "summary" (a paragraph summarizing the key points, max 150 words).
Example Format:
{{
  "title": "Example Meeting Discussion on Q3 Results",
  "summary": "The meeting covered the financial results for Q3, highlighting key achievements and areas for improvement. Action items were assigned for follow-up."
}}

JSON Response:""" # The prompt guides the model towards the desired output

            try:
                # Use the OpenRouter client configured earlier
                completion = client.chat.completions.create(
                    model=openrouter_model_name,
                    messages=[
                        {"role": "system", "content": "You are an AI assistant that generates titles and summaries for meeting transcripts. Respond only with the requested JSON object."},
                        {"role": "user", "content": prompt_text}
                    ],
                    temperature=0.5, # Adjust temperature as needed
                    max_tokens=300, # Adjust based on expected title+summary length
                    response_format={"type": "json_object"} # Request JSON output
                )

                response_content = completion.choices[0].message.content
                app.logger.debug(f"Raw OpenRouter response for {recording_id}: {response_content}")

                # Parse the JSON response
                try:
                    summary_data = json.loads(response_content)
                    generated_title = summary_data.get("title")
                    generated_summary = summary_data.get("summary")

                    if generated_title and generated_summary:
                        # Update recording with AI generated content
                        recording.title = generated_title.strip()
                        recording.summary = generated_summary.strip()
                        recording.status = 'COMPLETED'
                        app.logger.info(f"Title and summary generated successfully for recording {recording_id}.")
                    else:
                        app.logger.warning(f"OpenRouter response for {recording_id} lacked 'title' or 'summary' key. Response: {response_content}")
                        recording.summary = "[AI summary generation failed: Invalid JSON structure]"
                        recording.status = 'COMPLETED' # Still completed, but summary failed

                except json.JSONDecodeError as json_e:
                    app.logger.error(f"Failed to parse JSON response from OpenRouter for {recording_id}: {json_e}. Response: {response_content}")
                    recording.summary = f"[AI summary generation failed: Invalid JSON response ({json_e})]"
                    recording.status = 'COMPLETED' # Mark as completed, summary failed

            except Exception as summary_e:
                app.logger.error(f"Error calling OpenRouter API for summary ({recording_id}): {str(summary_e)}")
                # Keep transcription, but mark summary failed. Don't change status from SUMMARIZING yet.
                recording.summary = f"[AI summary generation failed: API Error ({str(summary_e)})]"
                recording.status = 'COMPLETED' # Even if summary fails, transcription worked.


            db.session.commit() # Final commit for this step

        except Exception as e:
            db.session.rollback() # Rollback if any step failed critically
            app.logger.error(f"Processing FAILED for recording {recording_id}: {str(e)}", exc_info=True)
            # Retrieve recording again in case session was rolled back
            recording = db.session.get(Recording, recording_id)
            if recording:
                 # Ensure status reflects failure even after rollback/retrieve attempt
                if recording.status not in ['COMPLETED', 'FAILED']: # Avoid overwriting final state
                    recording.status = 'FAILED'
                if not recording.transcription: # If transcription itself failed
                     recording.transcription = f"Processing failed: {str(e)}"
                # Add error note to summary if appropriate stage was reached
                if recording.status == 'SUMMARIZING' and not recording.summary:
                     recording.summary = f"[Processing failed during summarization: {str(e)}]"

                db.session.commit()


# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recordings', methods=['GET'])
def get_recordings():
    try:
        stmt = select(Recording).order_by(Recording.created_at.desc())
        recordings = db.session.execute(stmt).scalars().all()
        return jsonify([recording.to_dict() for recording in recordings])
    except Exception as e:
        app.logger.error(f"Error fetching recordings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST'])
def save_metadata():
    try:
        data = request.json
        if not data: return jsonify({'error': 'No data provided'}), 400
        recording_id = data.get('id')
        if not recording_id: return jsonify({'error': 'No recording ID provided'}), 400

        recording = db.session.get(Recording, recording_id)
        if not recording: return jsonify({'error': 'Recording not found'}), 404

        # Update fields if provided
        if 'title' in data: recording.title = data['title']
        if 'participants' in data: recording.participants = data['participants']
        if 'notes' in data: recording.notes = data['notes']
        if 'summary' in data: recording.summary = data['summary'] # <-- ADDED: Allow saving edited summary

        # Do not update transcription or status here
        db.session.commit()
        return jsonify({'success': True, 'recording': recording.to_dict()})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving metadata for recording {recording_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filename = secure_filename(file.filename)
        # Ensure filepath uses the configured UPLOAD_FOLDER
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")

        # Get file size before saving
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        # Check size limit again
        if file_size > app.config['MAX_CONTENT_LENGTH']:
            raise RequestEntityTooLarge()

        file.save(filepath)
        app.logger.info(f"File saved to {filepath}")

        # Create initial database entry with PENDING status and filename as placeholder title
        recording = Recording(
            audio_path=filepath,
            # Use filename (without path part) as initial title
            title=f"Recording - {filename}",
            file_size=file_size,
            status='PENDING' # Explicitly set status
        )
        db.session.add(recording)
        db.session.commit()
        app.logger.info(f"Initial recording record created with ID: {recording.id}")

        # --- Start transcription & summarization in background thread ---
        thread = threading.Thread(
            target=transcribe_audio_task,
            # Pass original filename for logging clarity
            args=(app.app_context(), recording.id, filepath, filename)
        )
        thread.start()
        app.logger.info(f"Background processing thread started for recording ID: {recording.id}")

        # Return the initial recording data and ID immediately
        return jsonify(recording.to_dict()), 202 # 202 Accepted

    except RequestEntityTooLarge:
        max_size_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
        app.logger.warning(f"Upload failed: File too large (>{max_size_mb}MB)")
        return jsonify({
            'error': f'File too large. Maximum size is {max_size_mb:.0f} MB.',
            'max_size_mb': max_size_mb
        }), 413
    except Exception as e:
        db.session.rollback() # Rollback if initial save failed
        app.logger.error(f"Error during file upload: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# Status Endpoint (no changes needed, it returns the full recording dict)
@app.route('/status/<int:recording_id>', methods=['GET'])
def get_status(recording_id):
    """Endpoint to check the transcription/summarization status."""
    try:
        recording = db.session.get(Recording, recording_id)
        if not recording:
            return jsonify({'error': 'Recording not found'}), 404
        return jsonify(recording.to_dict())
    except Exception as e:
        app.logger.error(f"Error fetching status for recording {recording_id}: {e}")
        return jsonify({'error': str(e)}), 500

# Get Audio Endpoint (no changes needed)
@app.route('/audio/<int:recording_id>')
def get_audio(recording_id):
    try:
        recording = db.session.get(Recording, recording_id)
        if not recording or not recording.audio_path:
            return jsonify({'error': 'Recording or audio file not found'}), 404
        if not os.path.exists(recording.audio_path):
            app.logger.error(f"Audio file missing from server: {recording.audio_path}")
            return jsonify({'error': 'Audio file missing from server'}), 404
        return send_file(recording.audio_path)
    except Exception as e:
        app.logger.error(f"Error serving audio for recording {recording_id}: {e}")
        return jsonify({'error': str(e)}), 500

# Delete Recording Endpoint (no changes needed functionally)
@app.route('/recording/<int:recording_id>', methods=['DELETE'])
def delete_recording(recording_id):
    try:
        recording = db.session.get(Recording, recording_id)
        if not recording:
            return jsonify({'error': 'Recording not found'}), 404

        # Delete the audio file first
        try:
            if recording.audio_path and os.path.exists(recording.audio_path):
                os.remove(recording.audio_path)
                app.logger.info(f"Deleted audio file: {recording.audio_path}")
        except Exception as e:
            app.logger.error(f"Error deleting audio file {recording.audio_path}: {e}")

        # Delete the database record
        db.session.delete(recording)
        db.session.commit()
        app.logger.info(f"Deleted recording record ID: {recording_id}")

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting recording {recording_id}: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Consider using waitress or gunicorn for production
    # waitress-serve --host 0.0.0.0 --port 8899 app:app
    # For development:
    app.run(host='0.0.0.0', port=8899, debug=True) # Set debug=False if thread issues arise
```


## create_docs.py

```python

import os
from pathlib import Path

def create_markdown_doc(base_dir):
    output = []
    
    # Add header
    output.append("# Project Files\n")
    output.append("Generated documentation of all project files.\n")

    # Function to read and format file content
    def add_file_content(filepath, relative_path):
        output.append(f"\n## {relative_path}\n")
        output.append("```" + get_file_extension(filepath) + "\n")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                output.append(f.read())
        except Exception as e:
            output.append(f"Error reading file: {e}")
        output.append("```\n")

    def get_file_extension(filepath):
        ext = os.path.splitext(filepath)[1][1:].lower()
        # Map file extensions to markdown code block languages
        extension_map = {
            'py': 'python',
            'html': 'html',
            'js': 'javascript',
            'css': 'css',
            'sh': 'bash',
            'md': 'markdown',
            'txt': 'text'
        }
        return extension_map.get(ext, '')

    # List of important file patterns to include
    patterns = [
        '*.py',
        '*.html',
        '*.js',
        '*.css',
        '*.sh',
        'requirements.txt'
    ]

    # Walk through directory and add files
    for root, _, _ in os.walk(base_dir):
        for pattern in patterns:
            for filepath in Path(root).glob(pattern):
                if 'venv' not in str(filepath) and '__pycache__' not in str(filepath):
                    relative_path = os.path.relpath(filepath, base_dir)
                    add_file_content(filepath, relative_path)

    # Write to output file
    output_path = os.path.join(base_dir, 'project_files.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    return output_path

if __name__ == "__main__":
    # Get the current directory
    current_dir = os.getcwd()
    
    # Create the markdown file
    output_file = create_markdown_doc(current_dir)
    print(f"Created markdown documentation at: {output_file}")
```


## requirements.txt

```text

flask==2.3.3
flask-sqlalchemy==3.1.1
openai==1.3.0
werkzeug==2.3.7
gunicorn==21.2.0
python-dotenv==1.0.0
```


## templates/index.html

```html

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audio Transcription App</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        /* Existing styles... */
        .drag-area { transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out; }
        .custom-scrollbar::-webkit-scrollbar { width: 8px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #c5c5c5; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
        html, body { height: 100%; margin: 0; }
        #app { min-height: 100%; display: flex; flex-direction: column; }
        main { flex-grow: 1; position: relative; }
        .progress-popup { position: fixed; bottom: 1rem; left: 1rem; z-index: 100; transition: all 0.3s ease-in-out; min-width: 300px; }
        .progress-popup.minimized { transform: translateY(calc(100% - 45px)); }
        .progress-list-item { display: grid; grid-template-columns: auto 1fr auto; gap: 0.5rem; align-items: center; }
         /* Add style for summary pre */
        .summary-box {
            background-color: #f9fafb; /* bg-gray-50 */
            padding: 0.75rem; /* p-3 */
            border-radius: 0.375rem; /* rounded */
            border: 1px solid #e5e7eb; /* border-gray-200 */
            min-height: 60px; /* min-h-[60px] or adjust as needed */
            max-height: 20rem; /* Limit height */
            overflow-y: auto;
            white-space: pre-wrap;
            font-family: inherit; /* Use body font */
            font-size: 0.875rem; /* text-sm */
            line-height: 1.25rem;
        }
         .status-badge {
             display: inline-block;
             padding: 0.125rem 0.5rem; /* px-2 py-0.5 */
             font-size: 0.75rem; /* text-xs */
             font-weight: 600; /* font-semibold */
             border-radius: 9999px; /* rounded-full */
             margin-top: 0.5rem; /* mt-2 */
         }
         .status-processing { color: #1d4ed8; background-color: #dbeafe; } /* text-blue-800 bg-blue-100 */
         .status-summarizing { color: #92400e; background-color: #fef3c7; } /* text-amber-800 bg-amber-100 */
         .status-completed { color: #065f46; background-color: #d1fae5; } /* text-green-800 bg-green-100 */
         .status-failed { color: #991b1b; background-color: #fee2e2; } /* text-red-800 bg-red-100 */
         .status-pending { color: #57534e; background-color: #f5f5f4; } /* text-stone-700 bg-stone-100 */

    </style>
</head>
<body class="bg-gray-100">
    <div id="app" class="container mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col">
        <header class="flex justify-between items-center mb-6 pb-4 border-b border-gray-200">
             <h1 class="text-3xl font-bold text-gray-800 cursor-pointer" @click="switchToGalleryView" title="Go to Gallery">
                Audio Transcription & Summary
            </h1>
            <div>
                <button @click="switchToUploadView" class="px-4 py-2 mr-2 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-150 ease-in-out">
                    <i class="fas fa-plus mr-1"></i> New Recording
                </button>
                 <button
                    @click="switchToGalleryView"
                    :class="{
                        'bg-white text-gray-700 border border-gray-300': currentView !== 'gallery',
                        'bg-blue-100 text-blue-700 border border-blue-300': currentView === 'gallery'
                    }"
                    class="px-4 py-2 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 transition duration-150 ease-in-out">
                    <i class="fas fa-images mr-1"></i> Gallery
                </button>
            </div>
        </header>

        <div v-if="globalError" class="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg" role="alert">
             <div class="flex justify-between items-center">
                <div>
                    <strong class="font-bold">Error:</strong>
                    <span class="block sm:inline ml-2">${ globalError }</span>
                </div>
                <button @click="globalError = null" class="text-red-700 hover:text-red-900 font-bold">&times;</button>
            </div>
        </div>

        <main class="flex-grow"
             @dragover.prevent="dragover = true"
             @dragleave.prevent="handleDragLeave"
             @drop.prevent="handleDrop">

            <div v-if="dragover" class="absolute inset-0 flex items-center justify-center bg-blue-500 bg-opacity-20 z-10 rounded-lg pointer-events-none border-4 border-dashed border-blue-600">
                <div class="text-center p-6 bg-white rounded-lg shadow-xl">
                    <i class="fas fa-upload text-4xl text-blue-500 mb-3"></i>
                    <p class="text-xl font-semibold text-gray-700">Drop audio file(s) here to upload</p>
                </div>
            </div>

            <div v-if="currentView === 'gallery'" class="flex-grow flex flex-col rounded-lg">
                 <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-grow">
                    <div class="lg:col-span-1 bg-white p-4 rounded-lg shadow-md flex flex-col">
                        <h3 class="text-lg font-semibold mb-4 sticky top-0 bg-white pb-3 border-b border-gray-200">Recordings</h3>
                         <div v-if="isLoadingRecordings" class="text-center text-gray-500 py-4">
                            <i class="fas fa-spinner fa-spin mr-2"></i> Loading recordings...
                        </div>
                        <div v-else-if="recordings.length === 0 && uploadQueue.length === 0" class="text-center text-gray-500 py-4 flex-grow flex flex-col items-center justify-center">
                             <i class="fas fa-folder-open text-4xl text-gray-400 mb-3"></i>
                            <p>No recordings yet.</p>
                            <p>Upload one or drag & drop anywhere!</p>
                        </div>
                        <div v-else class="space-y-4 overflow-y-auto custom-scrollbar flex-grow pr-1">
                            <div v-for="group in groupedRecordings" :key="group.title" class="mb-3">
                                <h4 class="font-medium text-gray-500 text-xs uppercase tracking-wider mb-2 sticky top-0 bg-white py-1">${ group.title }</h4>
                                <ul class="space-y-1">
                                    <li v-for="recording in group.items"
                                        :key="recording.id"
                                        @click="selectRecording(recording)"
                                        class="cursor-pointer p-3 rounded-md flex justify-between items-center transition duration-150 ease-in-out"
                                        :class="{
                                            'bg-blue-100 hover:bg-blue-200 ring-1 ring-blue-300': selectedRecording?.id === recording.id,
                                            'hover:bg-gray-100': selectedRecording?.id !== recording.id
                                        }">
                                         <div class="flex items-center overflow-hidden mr-2">
                                            <i class="fas fa-file-audio text-blue-500 mr-2 flex-shrink-0"></i>
                                            <span class="text-sm font-medium text-gray-800 truncate" :title="recording.title || 'Loading title...'">${ recording.title || '(Processing...)' }</span>
                                        </div>
                                        <div class="flex space-x-2 flex-shrink-0 items-center">
                                            <span v-if="recording.status === 'PROCESSING'" class="text-xs text-blue-600 italic flex items-center" title="Transcribing...">
                                                 <i class="fas fa-spinner fa-spin mr-1"></i> Transcribing
                                            </span>
                                             <span v-else-if="recording.status === 'SUMMARIZING'" class="text-xs text-amber-600 italic flex items-center" title="Generating Summary...">
                                                <i class="fas fa-spinner fa-spin mr-1"></i> Summarizing
                                            </span>
                                            <span v-else-if="recording.status === 'PENDING'" class="text-xs text-gray-500 italic flex items-center" title="Waiting...">
                                                <i class="fas fa-clock mr-1"></i> Pending
                                            </span>
                                            <span v-else-if="recording.status === 'FAILED'" class="text-xs text-red-600 italic flex items-center" title="Processing Failed">
                                                <i class="fas fa-exclamation-triangle mr-1"></i> Failed
                                            </span>
                                            <span v-else-if="recording.status === 'COMPLETED'" class="text-xs text-green-600" title="Completed">
                                                <i class="fas fa-check-circle"></i>
                                            </span>
                                             <button @click.stop="editRecording(recording)" class="text-gray-500 hover:text-blue-600 text-xs p-1 rounded hover:bg-gray-200" title="Edit Details">
                                                <i class="fas fa-edit"></i>
                                            </button>
                                            <button @click.stop="confirmDelete(recording)" class="text-gray-500 hover:text-red-600 text-xs p-1 rounded hover:bg-gray-200" title="Delete Recording">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        </div>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                     <div class="lg:col-span-3 bg-white p-6 rounded-lg shadow-md flex flex-col">
                        <div v-if="selectedRecording" class="flex-grow flex flex-col">
                            <div class="flex flex-col sm:flex-row justify-between items-start mb-4 border-b border-gray-200 pb-4">
                                <div class="mb-3 sm:mb-0 max-w-lg">
                                     <h3 class="text-2xl font-semibold text-gray-900">${ selectedRecording.title || 'Loading...' }</h3>
                                    <p class="text-sm text-gray-500 mt-1">
                                        Created: ${ new Date(selectedRecording.created_at).toLocaleString() } | Size: ${ formatFileSize(selectedRecording.file_size) }
                                    </p>
                                     <span :class="getStatusClass(selectedRecording.status)" class="status-badge">
                                        Status: ${ formatStatus(selectedRecording.status) }
                                     </span>
                                </div>
                                <div class="flex space-x-2 flex-shrink-0">
                                    <button @click="editRecording(selectedRecording)" class="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm shadow-sm">
                                        <i class="fas fa-edit mr-1"></i> Edit Details
                                    </button>
                                    <button @click="confirmDelete(selectedRecording)" class="px-3 py-1.5 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm shadow-sm">
                                        <i class="fas fa-trash mr-1"></i> Delete
                                    </button>
                                </div>
                            </div>

                            <div class="grid md:grid-cols-2 gap-6 flex-grow overflow-hidden">
                                <div class="flex flex-col overflow-hidden">
                                    <h4 class="font-semibold text-gray-700 mb-2 flex-shrink-0">Transcription</h4>
                                    <div class="flex-grow overflow-y-auto p-4 bg-gray-50 rounded border border-gray-200 text-sm custom-scrollbar">
                                        <div v-if="selectedRecording.status === 'COMPLETED' || selectedRecording.status === 'SUMMARIZING'">
                                            <pre class="whitespace-pre-wrap font-sans">${ selectedRecording.transcription || 'No transcription available.' }</pre>
                                        </div>
                                        <div v-else-if="selectedRecording.status === 'FAILED'" class="text-red-700">
                                             <p class="font-medium mb-2">Processing Failed:</p>
                                             <pre class="whitespace-pre-wrap font-sans">${ selectedRecording.transcription || 'An unknown error occurred.' }</pre>
                                        </div>
                                        <div v-else class="flex items-center justify-center text-gray-500 h-full">
                                            <i class="fas fa-spinner fa-spin mr-2"></i> Transcription in progress...
                                        </div>
                                    </div>
                                </div>

                                 <div class="flex flex-col space-y-4 overflow-hidden">
                                    <div>
                                        <h4 class="font-semibold text-gray-700 mb-2">Audio Player</h4>
                                        <audio controls class="w-full" :key="selectedRecording.id" :src="'/audio/' + selectedRecording.id">
                                            Your browser does not support the audio element.
                                        </audio>
                                    </div>

                                    <div class="flex flex-col overflow-hidden">
                                        <h4 class="font-semibold text-gray-700 mb-2 flex-shrink-0">Summary</h4>
                                         <div class="flex-grow overflow-hidden">
                                            <div v-if="selectedRecording.status === 'COMPLETED'" class="summary-box custom-scrollbar">
                                                ${ selectedRecording.summary || 'No summary generated.' }
                                            </div>
                                             <div v-else-if="selectedRecording.status === 'FAILED'" class="summary-box text-red-700 custom-scrollbar">
                                                ${ selectedRecording.summary || 'Summary generation failed or was skipped.' }
                                            </div>
                                            <div v-else class="h-24 flex items-center justify-center p-4 bg-gray-50 rounded border border-gray-200 text-gray-500">
                                                <i class="fas fa-spinner fa-spin mr-2"></i> Summary pending...
                                            </div>
                                        </div>
                                    </div>

                                    <div>
                                        <h4 class="font-semibold text-gray-700 mb-1">Participants</h4>
                                        <p class="text-sm bg-gray-50 p-3 rounded border border-gray-200 min-h-[40px]">${ selectedRecording.participants || 'None specified' }</p>
                                    </div>
                                    <div class="flex flex-col overflow-hidden flex-grow">
                                         <h4 class="font-semibold text-gray-700 mb-1 flex-shrink-0">Notes</h4>
                                        <div class="flex-grow overflow-hidden">
                                            <pre class="text-sm bg-gray-50 p-3 rounded border border-gray-200 whitespace-pre-wrap h-40 overflow-y-auto custom-scrollbar font-sans">${ selectedRecording.notes || 'No notes' }</pre>
                                        </div>
                                    </div>
                                </div>
                            </div>
                         </div>
                        <div v-else class="flex flex-col items-center justify-center text-center text-gray-500 flex-grow">
                             <i class="fas fa-hand-pointer text-4xl text-gray-400 mb-4"></i>
                            <p class="text-lg font-medium mb-2">Select a recording from the list to view details.</p>
                            <p>Or, drag and drop audio file(s) anywhere on this page to upload.</p>
                        </div>
                    </div>
                </div>
            </div>

             <div v-if="currentView === 'upload'"
                 class="flex-grow flex items-center justify-center p-4">
                 <div class="w-full max-w-lg bg-white p-8 rounded-xl shadow-lg border border-gray-200 text-center drag-area"
                     :class="{'border-blue-500 bg-blue-50': dragover}">
                    <div class="py-8">
                        <i class="fas fa-cloud-upload-alt text-5xl mb-5 text-blue-500"></i>
                         <h2 class="text-xl font-semibold text-gray-700 mb-2">Upload New Recordings</h2>
                        <p class="text-gray-500 mb-4">Drag & drop your audio files here or click below.</p>
                         <input type="file" @change="handleFileSelect" accept="audio/*" class="hidden" ref="fileInput" multiple>
                        <button @click="$refs.fileInput.click()" class="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-sm transition duration-150 ease-in-out">
                            <i class="fas fa-file-import mr-2"></i> Select Files
                        </button>
                         <p class="text-xs text-gray-400 mt-4">Max file size per file: ${ maxFileSizeMB } MB</p>
                    </div>
                </div>
            </div>

             </main>

        <footer class="text-center py-4 mt-8 text-xs text-gray-400 border-t border-gray-200">
            Audio Transcription App &copy; ${ new Date().getFullYear() }
        </footer>

         <div v-if="showEditModal" class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
             <div class="bg-white p-6 rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto custom-scrollbar">
                 <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-semibold text-gray-800">Edit Recording Details</h3>
                    <button @click="cancelEdit" class="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
                </div>
                <div v-if="editingRecording" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Title</label>
                        <input v-model="editingRecording.title" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-200 focus:ring-opacity-50">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Participants</label>
                        <input v-model="editingRecording.participants" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-200 focus:ring-opacity-50">
                    </div>
                     <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Summary</label>
                        <textarea v-model="editingRecording.summary" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-200 focus:ring-opacity-50" rows="5"></textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                        <textarea v-model="editingRecording.notes" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-200 focus:ring-opacity-50" rows="4"></textarea>
                    </div>
                    <div class="flex justify-end space-x-3 pt-4">
                        <button @click="cancelEdit" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">Cancel</button>
                        <button @click="saveEdit" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>

        <div v-if="showDeleteModal" class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
             <div class="bg-white p-6 rounded-lg shadow-xl max-w-md w-full">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">Confirm Delete</h3>
                 <p v-if="recordingToDelete" class="mb-2 text-gray-600">Are you sure you want to permanently delete the recording titled "<strong>${ recordingToDelete.title }</strong>"?</p>
                <p class="text-sm text-red-600 mb-6">This action cannot be undone and will delete the record, transcription, summary, and the audio file.</p>
                <div class="flex justify-end space-x-3">
                    <button @click="cancelDelete" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">Cancel</button>
                    <button @click="deleteRecording" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700">Delete Permanently</button>
                </div>
            </div>
        </div>

        <div v-if="uploadQueue.length > 0 || currentlyProcessingFile"
             class="progress-popup bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden"
             :class="{ 'minimized': progressPopupMinimized }">

            <div class="flex justify-between items-center p-2 bg-gray-100 border-b border-gray-200 cursor-pointer" @click="progressPopupMinimized = !progressPopupMinimized">
                <h4 class="text-sm font-semibold text-gray-700">
                    <i class="fas fa-upload mr-2 text-blue-500"></i>
                    Upload & Process Progress (${ completedInQueue }/${ totalInQueue } completed)
                </h4>
                <button class="text-gray-500 hover:text-gray-700">
                    <i :class="progressPopupMinimized ? 'fa-chevron-up' : 'fa-chevron-down'" class="fas fa-fw"></i>
                </button>
            </div>

             <div class="p-3 max-h-60 overflow-y-auto custom-scrollbar" v-show="!progressPopupMinimized">
                 <div v-if="currentlyProcessingFile" class="mb-3 pb-3 border-b border-dashed border-gray-200">
                    <div class="flex items-center justify-between mb-1">
                        <p class="text-xs font-medium text-gray-800 truncate mr-2" :title="currentlyProcessingFile.file.name">
                            <i class="fas fa-spinner fa-spin text-blue-500 mr-1"></i> Processing: ${ currentlyProcessingFile.file.name }
                        </p>
                        <span class="text-xs text-gray-500 flex-shrink-0">${ formatFileSize(currentlyProcessingFile.file.size) }</span>
                    </div>
                     <p class="text-xs text-gray-600 mb-1 italic">${ processingMessage }</p>
                    <div class="w-full bg-gray-200 rounded-full h-1.5">
                         <div class="bg-blue-500 h-1.5 rounded-full transition-all duration-300" :style="{ width: processingProgress + '%' }"></div>
                    </div>
                </div>

                 <div v-if="queuedFiles.length > 0" class="mb-2">
                    <p class="text-xs font-semibold text-gray-500 mb-1">${ queuedFiles.length } file(s) queued:</p>
                    <ul class="space-y-1">
                        <li v-for="item in queuedFiles" :key="item.clientId" class="text-xs text-gray-600 progress-list-item">
                            <i class="fas fa-clock text-gray-400 fa-fw"></i>
                            <span class="truncate" :title="item.file.name">${ item.file.name }</span>
                            <span class="text-gray-400 flex-shrink-0">${ formatFileSize(item.file.size) }</span>
                        </li>
                    </ul>
                </div>

                <div v-if="finishedFilesInQueue.length > 0" class="mt-2 pt-2 border-t border-dashed border-gray-200">
                    <p class="text-xs font-semibold text-gray-500 mb-1">Recently finished:</p>
                    <ul class="space-y-1">
                         <li v-for="item in finishedFilesInQueue.slice(-5)" :key="item.clientId" class="text-xs progress-list-item">
                             <i v-if="item.status === 'completed'" class="fas fa-check-circle text-green-500 fa-fw"></i>
                            <i v-else-if="item.status === 'failed'" class="fas fa-exclamation-triangle text-red-500 fa-fw"></i>
                             <i v-else class="fas fa-question-circle text-gray-400 fa-fw"></i>
                            <span class="truncate" :title="item.file.name">${ item.file.name }</span>
                             <span v-if="item.status === 'failed'" class="text-red-500 text-xs italic flex-shrink-0">Failed</span>
                            <span v-else class="text-gray-400 flex-shrink-0">${ formatFileSize(item.file.size) }</span>
                        </li>
                    </ul>
                </div>

                 <div v-if="uploadQueue.length > 0 && queuedFiles.length === 0 && !currentlyProcessingFile" class="text-xs text-center text-gray-500 py-2">
                    All uploads processed.
                </div>
            </div>
        </div>

    </div> <script>
        const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue

        createApp({
            setup() {
                const currentView = ref('gallery');
                const dragover = ref(false);
                const recordings = ref([]);
                const selectedRecording = ref(null);
                // const currentRecording = ref(null); // Less used now with modal editing

                // --- Multi-Upload State ---
                // Status: 'queued'|'uploading'|'processing'|'summarizing'|'completed'|'failed'
                const uploadQueue = ref([]);
                const currentlyProcessingFile = ref(null);
                const processingProgress = ref(0);
                const processingMessage = ref('');
                const isProcessingActive = ref(false);
                const pollInterval = ref(null);
                const progressPopupMinimized = ref(false);

                const showEditModal = ref(false);
                const showDeleteModal = ref(false);
                const editingRecording = ref(null); // Holds a *copy* for the modal
                const recordingToDelete = ref(null);
                // const autoSaveTimeout = ref(null); // Autosave not implemented for modal
                const isLoadingRecordings = ref(true);
                const globalError = ref(null);
                const maxFileSizeMB = ref(250); // Default, could fetch from config if needed

                // --- Computed Properties ---
                const groupedRecordings = computed(() => {
                    const sortedRecordings = [...recordings.value].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                    // Grouping logic (same as before)...
                    const groups = { today: [], yesterday: [], thisWeek: [], older: [] };
                    const now = new Date();
                    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                    const yesterdayStart = new Date(todayStart);
                    yesterdayStart.setDate(todayStart.getDate() - 1);
                    const currentDayOfWeek = now.getDay();
                    const daysToSubtract = currentDayOfWeek === 0 ? 6 : currentDayOfWeek - 1;
                    const weekStart = new Date(todayStart);
                    weekStart.setDate(todayStart.getDate() - daysToSubtract);

                    sortedRecordings.forEach(r => {
                         const date = new Date(r.created_at);
                        if (date >= todayStart) groups.today.push(r);
                        else if (date >= yesterdayStart) groups.yesterday.push(r);
                        else if (date >= weekStart) groups.thisWeek.push(r);
                        else groups.older.push(r);
                    });
                     return [
                        { title: 'Today', items: groups.today },
                        { title: 'Yesterday', items: groups.yesterday },
                        { title: 'This Week', items: groups.thisWeek },
                        { title: 'Older', items: groups.older }
                    ].filter(g => g.items.length > 0);
                });

                 const totalInQueue = computed(() => uploadQueue.value.length);
                const completedInQueue = computed(() => uploadQueue.value.filter(item => item.status === 'completed' || item.status === 'failed').length);
                const queuedFiles = computed(() => uploadQueue.value.filter(item => item.status === 'queued'));
                // Filter finished: includes completed and failed
                 const finishedFilesInQueue = computed(() => uploadQueue.value.filter(item => ['completed', 'failed'].includes(item.status)));


                // --- Methods ---
                const setGlobalError = (message, duration = 7000) => {
                     globalError.value = message;
                     if (duration > 0) {
                        setTimeout(() => { if (globalError.value === message) globalError.value = null; }, duration);
                    }
                };

                 const formatFileSize = (bytes) => {
                     if (bytes == null || bytes === 0) return '0 Bytes';
                    const k = 1024;
                    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
                     if (bytes < 0) bytes = 0;
                    const i = bytes === 0 ? 0 : Math.max(0, Math.floor(Math.log(bytes) / Math.log(k)));
                     const size = i === 0 ? bytes : parseFloat((bytes / Math.pow(k, i)).toFixed(2));
                    return size + ' ' + sizes[i];
                };

                // Helper for status display
                 const formatStatus = (status) => {
                     if (!status) return 'Unknown';
                     // Capitalize first letter, handle 'SUMMARIZING' specifically
                     return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
                };

                // Helper for status badge class
                const getStatusClass = (status) => {
                    switch(status) {
                        case 'PENDING': return 'status-pending';
                        case 'PROCESSING': return 'status-processing';
                        case 'SUMMARIZING': return 'status-summarizing';
                        case 'COMPLETED': return 'status-completed';
                        case 'FAILED': return 'status-failed';
                        default: return 'status-pending'; // Default or unknown
                    }
                };


                const resetCurrentFileProcessingState = () => {
                    if (pollInterval.value) clearInterval(pollInterval.value);
                    pollInterval.value = null;
                    currentlyProcessingFile.value = null;
                    processingProgress.value = 0;
                    processingMessage.value = '';
                };

                const switchToUploadView = () => {
                    currentView.value = 'upload';
                    selectedRecording.value = null;
                 };

                const switchToGalleryView = async () => {
                    currentView.value = 'gallery';
                     await loadRecordings(); // Refresh recordings when switching back
                };

                const handleDragLeave = (e) => {
                    if (e.relatedTarget && e.currentTarget.contains(e.relatedTarget)) {
                         return;
                    }
                    dragover.value = false;
                }

                const handleDrop = (e) => {
                    dragover.value = false;
                    addFilesToQueue(e.dataTransfer.files);
                 };

                const handleFileSelect = (e) => {
                    addFilesToQueue(e.target.files);
                    e.target.value = null; // Reset input
                };

                // --- Queue Management ---
                const addFilesToQueue = (files) => {
                    let filesAdded = 0;
                    for (const file of files) {
                        if (file && file.type.startsWith('audio/')) {
                             if (file.size > maxFileSizeMB.value * 1024 * 1024) {
                                setGlobalError(`File "${file.name}" exceeds the maximum size of ${maxFileSizeMB.value} MB and was skipped.`);
                                continue;
                            }
                             const clientId = `client-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
                            uploadQueue.value.push({
                                file: file, status: 'queued', recordingId: null, clientId: clientId, error: null
                            });
                            filesAdded++;
                        } else if (file) {
                            setGlobalError(`Invalid file type "${file.name}". Only audio files are accepted. File skipped.`);
                        }
                    }
                     if(filesAdded > 0) {
                        console.log(`Added ${filesAdded} file(s) to the queue.`);
                        progressPopupMinimized.value = false; // Show popup
                        if (!isProcessingActive.value) {
                            startProcessingQueue();
                        }
                    }
                };

                 const startProcessingQueue = async () => {
                    console.log("Attempting to start processing queue...");
                    if (isProcessingActive.value) {
                        console.log("Queue processor already active.");
                        return;
                    }

                    isProcessingActive.value = true;
                    resetCurrentFileProcessingState();

                     const nextFileItem = uploadQueue.value.find(item => item.status === 'queued');

                    if (nextFileItem) {
                        console.log(`Processing next file: ${nextFileItem.file.name} (Client ID: ${nextFileItem.clientId})`);
                        currentlyProcessingFile.value = nextFileItem;
                        nextFileItem.status = 'uploading';
                        processingMessage.value = 'Preparing upload...';
                        processingProgress.value = 5;

                        try {
                            const formData = new FormData();
                            formData.append('file', nextFileItem.file);

                            processingMessage.value = 'Uploading file...';
                            processingProgress.value = 10;

                            const response = await fetch('/upload', { method: 'POST', body: formData });
                            const data = await response.json();

                            if (!response.ok) {
                                let errorMsg = data.error || `Upload failed with status ${response.status}`;
                                if (response.status === 413) errorMsg = data.error || `File too large. Max: ${data.max_size_mb?.toFixed(0) || maxFileSizeMB.value} MB.`;
                                throw new Error(errorMsg);
                            }

                             if (response.status === 202 && data.id) {
                                console.log(`File ${nextFileItem.file.name} uploaded. Recording ID: ${data.id}. Starting status poll.`);
                                // Status is now 'PENDING' on backend, will be updated by poll
                                nextFileItem.status = 'pending'; // Reflect initial backend status
                                nextFileItem.recordingId = data.id;
                                processingMessage.value = 'Upload complete. Waiting for processing...';
                                processingProgress.value = 30;

                                 // Add preliminary record to gallery immediately
                                recordings.value.unshift(data);
                                // Optionally select the new item
                                // selectRecording(data);

                                pollProcessingStatus(nextFileItem); // Start polling

                            } else {
                                throw new Error('Unexpected success response from server after upload.');
                            }

                        } catch (error) {
                            console.error(`Upload/Processing Error for ${nextFileItem.file.name} (Client ID: ${nextFileItem.clientId}):`, error);
                            nextFileItem.status = 'failed';
                            nextFileItem.error = error.message;
                             // Find the potentially added preliminary record and mark it failed
                             const failedRecordIndex = recordings.value.findIndex(r => r.id === nextFileItem.recordingId);
                             if(failedRecordIndex !== -1) {
                                recordings.value[failedRecordIndex].status = 'FAILED';
                                recordings.value[failedRecordIndex].transcription = `Upload/Processing failed: ${error.message}`;
                             } else {
                                // If record wasn't even created, add a note
                                setGlobalError(`Failed to process "${nextFileItem.file.name}": ${error.message}`);
                             }

                             // Reset state and try next file
                             resetCurrentFileProcessingState();
                             isProcessingActive.value = false;
                             await nextTick();
                             startProcessingQueue();
                         }
                    } else {
                        console.log("Upload queue is empty or no files are queued.");
                        isProcessingActive.value = false;
                        // Optional: Auto-minimize popup after a delay
                         // setTimeout(() => {
                        //     if (!isProcessingActive.value && uploadQueue.value.every(f => ['completed', 'failed'].includes(f.status))) {
                         //         progressPopupMinimized.value = true;
                        //     }
                         // }, 5000);
                    }
                };

                const pollProcessingStatus = (fileItem) => {
                     if (pollInterval.value) clearInterval(pollInterval.value);

                    const recordingId = fileItem.recordingId;
                    if (!recordingId) {
                        console.error("Cannot poll status without recording ID for", fileItem.file.name);
                        fileItem.status = 'failed';
                        fileItem.error = 'Internal error: Missing recording ID for polling.';
                        resetCurrentFileProcessingState();
                        isProcessingActive.value = false;
                        nextTick(startProcessingQueue); // Try next file
                        return;
                    }

                    // Initial message based on fileItem status (should be 'pending' initially)
                    processingMessage.value = 'Waiting for transcription...';
                    processingProgress.value = 40;

                    pollInterval.value = setInterval(async () => {
                        // Check if the item is still the one being processed and hasn't finished/failed
                         if (!currentlyProcessingFile.value || currentlyProcessingFile.value.clientId !== fileItem.clientId || ['completed', 'failed'].includes(fileItem.status)) {
                             console.log(`Polling stopped for ${fileItem.clientId} as it's no longer active or finished.`);
                            clearInterval(pollInterval.value);
                            pollInterval.value = null;
                             // If this was the active file, allow queue to restart
                            if (currentlyProcessingFile.value && currentlyProcessingFile.value.clientId === fileItem.clientId) {
                                resetCurrentFileProcessingState();
                                isProcessingActive.value = false;
                                await nextTick();
                                startProcessingQueue();
                            }
                            return;
                        }

                        try {
                            console.log(`Polling status for recording ID: ${recordingId} (${fileItem.file.name})`);
                            const response = await fetch(`/status/${recordingId}`);
                            if (!response.ok) throw new Error(`Status check failed with status ${response.status}`);

                            const data = await response.json();
                             const galleryIndex = recordings.value.findIndex(r => r.id === recordingId);

                            // Update item in the main recordings list
                            if (galleryIndex !== -1) {
                                recordings.value[galleryIndex] = data;
                                if(selectedRecording.value?.id === recordingId) {
                                    selectedRecording.value = data; // Update selection if viewing details
                                }
                            }

                            // Update the status in the uploadQueue item as well
                            fileItem.status = data.status;

                            // Update progress display based on backend status
                            if (data.status === 'COMPLETED') {
                                console.log(`Processing COMPLETED for ${fileItem.file.name} (ID: ${recordingId})`);
                                processingMessage.value = 'Processing complete!';
                                processingProgress.value = 100;
                                fileItem.status = 'completed'; // Final status for queue item
                                // Stop polling, reset state, and trigger next item
                                clearInterval(pollInterval.value);
                                pollInterval.value = null;
                                resetCurrentFileProcessingState();
                                isProcessingActive.value = false;
                                await nextTick();
                                startProcessingQueue();

                            } else if (data.status === 'FAILED') {
                                console.log(`Processing FAILED for ${fileItem.file.name} (ID: ${recordingId})`);
                                processingMessage.value = 'Processing failed.';
                                processingProgress.value = 100; // Show 100% but failed state
                                fileItem.status = 'failed'; // Final status for queue item
                                fileItem.error = data.transcription || data.summary || 'Processing failed on server.';
                                setGlobalError(`Processing failed for "${data.title || fileItem.file.name}".`);
                                // Stop polling, reset state, and trigger next item
                                clearInterval(pollInterval.value);
                                pollInterval.value = null;
                                resetCurrentFileProcessingState();
                                isProcessingActive.value = false;
                                await nextTick();
                                startProcessingQueue();

                            } else if (data.status === 'PROCESSING') {
                                processingMessage.value = 'Transcription in progress...';
                                processingProgress.value = Math.min(65, processingProgress.value + Math.random() * 5); // Mid-range progress
                            } else if (data.status === 'SUMMARIZING') {
                                processingMessage.value = 'Generating title & summary...';
                                processingProgress.value = Math.min(95, processingProgress.value + Math.random() * 5); // Higher progress
                            } else { // PENDING
                                processingMessage.value = 'Waiting in queue...';
                                processingProgress.value = 45; // Keep progress indication while pending
                            }
                        } catch (error) {
                            console.error(`Polling Error for ${fileItem.file.name} (ID: ${recordingId}):`, error);
                             // Assume failed if polling error occurs
                            fileItem.status = 'failed';
                            fileItem.error = `Error checking status: ${error.message}`;
                            setGlobalError(`Error checking status for "${fileItem.file.name}": ${error.message}.`);
                             // Update record in gallery if found
                             const galleryIndex = recordings.value.findIndex(r => r.id === recordingId);
                            if (galleryIndex !== -1) recordings.value[galleryIndex].status = 'FAILED';

                            clearInterval(pollInterval.value);
                            pollInterval.value = null;
                            resetCurrentFileProcessingState();
                            isProcessingActive.value = false;
                            await nextTick();
                            startProcessingQueue(); // Process the next file
                        }
                    }, 5000); // Poll every 5 seconds (adjust as needed)
                };

                // --- Gallery and Detail Methods ---
                // AutoSave removed in favor of explicit save in modal
                // const autoSave = () => { ... };

                 const saveMetadata = async (recordingDataToSave) => {
                    globalError.value = null;
                    if (!recordingDataToSave || !recordingDataToSave.id) return null;
                    console.log('Saving metadata for:', recordingDataToSave.id);
                    try {
                        const payload = {
                            id: recordingDataToSave.id,
                            title: recordingDataToSave.title,
                            participants: recordingDataToSave.participants,
                            notes: recordingDataToSave.notes,
                            summary: recordingDataToSave.summary // <-- ADDED: Include summary
                        };
                        const response = await fetch('/save', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Failed to save metadata');

                        console.log('Save successful:', data.recording.id);
                        // Update the master recordings list
                        const index = recordings.value.findIndex(r => r.id === data.recording.id);
                        if (index !== -1) {
                            // Update only the editable fields, preserve others like status/transcription from backend
                             recordings.value[index].title = payload.title;
                             recordings.value[index].participants = payload.participants;
                             recordings.value[index].notes = payload.notes;
                             recordings.value[index].summary = payload.summary;
                         }
                         // Update selected if it's the one being saved
                         if (selectedRecording.value?.id === data.recording.id) {
                            selectedRecording.value.title = payload.title;
                            selectedRecording.value.participants = payload.participants;
                            selectedRecording.value.notes = payload.notes;
                            selectedRecording.value.summary = payload.summary;
                         }
                        return data.recording; // Return the full updated object from backend
                    } catch (error) {
                        console.error('Save Metadata Error:', error);
                        setGlobalError(`Save failed: ${error.message}`);
                        return null;
                    }
                };

                const loadRecordings = async () => {
                     globalError.value = null;
                    isLoadingRecordings.value = true;
                    try {
                        const response = await fetch('/recordings');
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Failed to load recordings');
                        recordings.value = data;

                         // On load, check for any recordings stuck in PENDING, PROCESSING, or SUMMARIZING
                         // and ensure polling is active if the queue processor isn't running.
                         const incompleteRecordings = recordings.value.filter(r => ['PENDING', 'PROCESSING', 'SUMMARIZING'].includes(r.status));

                         if (incompleteRecordings.length > 0 && !isProcessingActive.value) {
                             console.warn(`Found ${incompleteRecordings.length} incomplete recording(s) on load. Attempting to resume polling if not already queued.`);
                             for (const recording of incompleteRecordings) {
                                 // Is this item already being tracked in the queue?
                                 let queueItem = uploadQueue.value.find(item => item.recordingId === recording.id);
                                if (!queueItem) {
                                    // If not in queue (likely page reload), create a placeholder to track polling
                                    console.log(`Re-attaching poll for recording ${recording.id}.`);
                                    queueItem = {
                                        // Mock file object, size might be useful for display
                                        file: { name: recording.title || `Recording ${recording.id}`, size: recording.file_size },
                                        status: recording.status, // Use current status from DB
                                        recordingId: recording.id,
                                        clientId: `reload-${recording.id}`, // Unique ID for tracking
                                        error: null
                                    };
                                    // Add to the *beginning* of the visual queue *if* we want to show it there
                                    // Or just manage polling without adding to queue visually?
                                    // Let's add it to the queue for consistency in management.
                                    uploadQueue.value.unshift(queueItem);
                                     // Start processing queue if it wasn't active
                                     if (!isProcessingActive.value) {
                                         startProcessingQueue();
                                     } else if (currentlyProcessingFile.value?.recordingId !== recording.id) {
                                         // If processor is active but on a different file, just ensure polling starts
                                         // Note: startProcessingQueue handles finding the next 'queued'. This item
                                         // might not be 'queued'. We need direct polling.
                                         // Let's rethink: The queue processor should handle finding PENDING/PROCESSING items.
                                         // For simplicity, let's just trigger the queue processor. It will find this item if it's next.
                                         // If something else is truly processing, this won't interrupt.
                                         console.log("Triggering queue processor check due to reloaded incomplete item.")
                                         // Ensure it's marked conceptually 'queued' for the processor to pick up
                                         queueItem.status = 'queued';
                                         startProcessingQueue(); // Let the queue logic handle it
                                     }

                                } else if (queueItem.status !== recording.status && !['completed', 'failed'].includes(queueItem.status)) {
                                    // If queue status differs from DB, update queue status
                                     console.log(`Correcting queue status for ${queueItem.clientId} from ${queueItem.status} to ${recording.status}`);
                                     queueItem.status = recording.status;
                                     // Restart queue processing if needed
                                     if (!isProcessingActive.value) startProcessingQueue();
                                 }
                            }
                         }

                    } catch (error) {
                        console.error('Load Recordings Error:', error);
                        setGlobalError(`Failed to load recordings: ${error.message}`);
                        recordings.value = [];
                    } finally {
                        isLoadingRecordings.value = false;
                    }
                };

                 const selectRecording = (recording) => {
                     selectedRecording.value = recording;
                     // Optional: Check if polling needs to be restarted if user selects an incomplete item
                     // This logic is complex and might be redundant with the loadRecordings check.
                     // Let's rely on loadRecordings and the queue processor for robustness.
                 };

                const editRecording = (recording) => {
                     // Create a deep copy for the modal to prevent modifying original object directly
                    editingRecording.value = JSON.parse(JSON.stringify(recording));
                    showEditModal.value = true;
                };

                const cancelEdit = () => {
                    showEditModal.value = false;
                    editingRecording.value = null;
                };

                 const saveEdit = async () => {
                    // Save using the saveMetadata function which updates the main list & selected item
                     const success = await saveMetadata(editingRecording.value);
                    if (success) {
                        cancelEdit(); // Close modal on success
                     }
                     // Keep modal open on failure, error shown via globalError
                };

                const confirmDelete = (recording) => {
                    recordingToDelete.value = recording;
                    showDeleteModal.value = true;
                };

                const cancelDelete = () => {
                    showDeleteModal.value = false;
                    recordingToDelete.value = null;
                };

                const deleteRecording = async () => {
                    globalError.value = null;
                    if (!recordingToDelete.value) return;
                    const idToDelete = recordingToDelete.value.id;
                    const titleToDelete = recordingToDelete.value.title; // For logging/messaging
                    try {
                        const response = await fetch(`/recording/${idToDelete}`, { method: 'DELETE' });
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Failed to delete recording');

                         // Remove from gallery list
                        recordings.value = recordings.value.filter(r => r.id !== idToDelete);

                        // Find and remove from upload queue
                        const queueIndex = uploadQueue.value.findIndex(item => item.recordingId === idToDelete);
                         if (queueIndex !== -1) {
                            const deletedItem = uploadQueue.value.splice(queueIndex, 1)[0];
                             console.log(`Removed item ${deletedItem.clientId} from queue.`);
                             // If deleting the file currently being processed, stop polling and move to next
                            if (currentlyProcessingFile.value?.clientId === deletedItem.clientId) {
                                console.log(`Deleting currently processing file: ${titleToDelete}. Stopping poll and moving to next.`);
                                clearInterval(pollInterval.value); // Stop polling explicitly
                                pollInterval.value = null;
                                resetCurrentFileProcessingState();
                                isProcessingActive.value = false; // Allow queue to restart
                                await nextTick();
                                startProcessingQueue();
                            }
                        }

                        if (selectedRecording.value?.id === idToDelete) selectedRecording.value = null;
                        cancelDelete();
                        console.log(`Successfully deleted recording ${idToDelete} (${titleToDelete})`);

                    } catch (error) {
                        console.error('Delete Error:', error);
                        setGlobalError(`Failed to delete recording "${titleToDelete}": ${error.message}`);
                        cancelDelete(); // Still close modal on error
                    }
                };

                // --- Lifecycle Hooks ---
                onMounted(() => {
                    loadRecordings();
                });

                // --- Watchers ---
                 watch(uploadQueue, (newQueue, oldQueue) => {
                    if (newQueue.length === 0 && oldQueue.length > 0 && !isProcessingActive.value) {
                        console.log("Upload queue processing finished.");
                        // Optional: Auto-minimize after delay
                         // setTimeout(() => progressPopupMinimized.value = true, 3000);
                     }
                 }, { deep: true });


                return {
                    // State
                    currentView, dragover, recordings, selectedRecording, // currentRecording removed
                    showEditModal, showDeleteModal, editingRecording, recordingToDelete,
                    isLoadingRecordings, globalError, maxFileSizeMB,
                    // Multi-upload State
                    uploadQueue, currentlyProcessingFile, processingProgress, processingMessage,
                    isProcessingActive, progressPopupMinimized,
                    // Computed
                    groupedRecordings, totalInQueue, completedInQueue, queuedFiles, finishedFilesInQueue,
                    // Methods
                    handleDrop, handleFileSelect, /*autoSave removed*/ loadRecordings,
                    selectRecording, editRecording, cancelEdit, saveEdit, confirmDelete,
                    cancelDelete, deleteRecording, switchToUploadView, switchToGalleryView,
                    formatFileSize, setGlobalError, handleDragLeave, formatStatus, getStatusClass,
                 }
            },
            delimiters: ['${', '}'] // Keep Vue delimiters distinct from Flask's Jinja
        }).mount('#app');
    </script>

</body>
</html>
```


## deployment/setup.sh

```bash

#!/bin/bash

# Create directory for the application
sudo mkdir -p /opt/transcription-app
sudo chown $USER:$USER /opt/transcription-app

# Copy application files
cp app.py /opt/transcription-app/
cp -r templates /opt/transcription-app/
cp requirements.txt /opt/transcription-app/
cp reset_db.py /opt/transcription-app/

# Create and activate virtual environment
python3 -m venv /opt/transcription-app/venv
source /opt/transcription-app/venv/bin/activate

# Install requirements
cd /opt/transcription-app
pip install -r requirements.txt

# Create directories for uploads and database with proper permissions
mkdir -p /opt/transcription-app/uploads
mkdir -p /opt/transcription-app/instance
chmod 755 /opt/transcription-app/uploads
chmod 755 /opt/transcription-app/instance

# Initialize the database
python reset_db.py

# Set proper ownership for all files
sudo chown -R $USER:$USER /opt/transcription-app

# Create systemd service file
sudo tee /etc/systemd/system/transcription.service << EOF
[Unit]
Description=Transcription Web Application
After=network.target

[Service]
User=$USER
EnvironmentFile=/opt/transcription-app/.env
WorkingDirectory=/opt/transcription-app
Environment="PATH=/opt/transcription-app/venv/bin"
Environment="PYTHONPATH=/opt/transcription-app"
ExecStart=/opt/transcription-app/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8899 --timeout 600 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl restart transcription
sudo systemctl enable transcription

# Check service status
echo "Checking service status..."
sleep 3
sudo systemctl status transcription

echo "Installation complete! The application should be running on port 8899."
```

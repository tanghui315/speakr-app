# app.py
from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from openai import OpenAI
import json
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import select
import threading # Import threading

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////opt/transcription-app/instance/transcriptions.db' # Make sure path is correct
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 250 * 1024 * 1024  # 250MB max file size
db = SQLAlchemy()
db.init_app(app)

# Ensure upload and instance directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)


# --- Database Models ---
class Recording(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    participants = db.Column(db.String(500))
    notes = db.Column(db.Text)
    transcription = db.Column(db.Text, nullable=True) # Allow null initially
    status = db.Column(db.String(50), default='PENDING') # Add status field: PENDING, PROCESSING, COMPLETED, FAILED
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
            'status': self.status, # Include status
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'file_size': self.file_size
        }

with app.app_context():
    db.create_all()

# --- API client setup ---
# Ensure you have your API key and base URL configured correctly
# For local testing, you might use environment variables or a config file
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY", "cant-be-empty"), # Use env var or default
    base_url=os.environ.get("OPENAI_BASE_URL", "http://192.168.68.85:1611/v1/") # Use env var or default
)

# --- Background Transcription Task ---
def transcribe_audio_task(app_context, recording_id, filepath):
    """Runs the transcription in a background thread."""
    with app_context: # Need app context for db operations in thread
        recording = db.session.get(Recording, recording_id)
        if not recording:
            print(f"Error: Recording {recording_id} not found for transcription.")
            return

        try:
            print(f"Starting transcription for recording {recording_id}...")
            recording.status = 'PROCESSING'
            db.session.commit()

            with open(filepath, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="Systran/faster-distil-whisper-large-v3", # Or your desired model
                    file=audio_file,
                    language="en" # Specify language if known
                )

            recording.transcription = transcript.text
            recording.status = 'COMPLETED'
            print(f"Transcription COMPLETED for recording {recording_id}.")
            db.session.commit()

        except Exception as e:
            print(f"Transcription FAILED for recording {recording_id}: {str(e)}")
            recording.transcription = f"Transcription failed: {str(e)}" # Store error message
            recording.status = 'FAILED'
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
    # This route remains largely the same, just updates metadata
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        recording_id = data.get('id')
        if not recording_id:
            return jsonify({'error': 'No recording ID provided'}), 400

        recording = db.session.get(Recording, recording_id)
        if not recording:
            return jsonify({'error': 'Recording not found'}), 404

        # Update fields if provided
        if 'title' in data:
            recording.title = data['title']
        if 'participants' in data:
            recording.participants = data['participants']
        if 'notes' in data:
            recording.notes = data['notes']
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
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Get file size before saving
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        # Check size limit again (Flask's MAX_CONTENT_LENGTH handles the actual request blocking)
        if file_size > app.config['MAX_CONTENT_LENGTH']:
             raise RequestEntityTooLarge()

        file.save(filepath)
        print(f"File saved to {filepath}")

        # Create initial database entry with PENDING status
        recording = Recording(
            audio_path=filepath,
            title=f"Untitled - {datetime.now().strftime('%Y-%m-%d %H:%M')}", # Simpler default title
            file_size=file_size,
            status='PENDING' # Explicitly set status
        )
        db.session.add(recording)
        db.session.commit()
        print(f"Initial recording record created with ID: {recording.id}")

        # --- Start transcription in background thread ---
        # Pass the app context to the thread
        thread = threading.Thread(
            target=transcribe_audio_task,
            args=(app.app_context(), recording.id, filepath)
        )
        thread.start()
        print(f"Background transcription thread started for recording ID: {recording.id}")

        # Return the initial recording data and ID immediately
        return jsonify(recording.to_dict()), 202 # 202 Accepted indicates processing started

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

# --- NEW: Status Endpoint ---
@app.route('/status/<int:recording_id>', methods=['GET'])
def get_status(recording_id):
    """Endpoint to check the transcription status."""
    try:
        recording = db.session.get(Recording, recording_id)
        if not recording:
            return jsonify({'error': 'Recording not found'}), 404

        # Return the full recording data, including status and transcription (if available)
        return jsonify(recording.to_dict())

    except Exception as e:
        app.logger.error(f"Error fetching status for recording {recording_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/audio/<int:recording_id>')
def get_audio(recording_id):
    try:
        recording = db.session.get(Recording, recording_id)
        if not recording or not recording.audio_path:
            return jsonify({'error': 'Recording or audio file not found'}), 404
        # Ensure the file actually exists before trying to send it
        if not os.path.exists(recording.audio_path):
             return jsonify({'error': 'Audio file missing from server'}), 404
        return send_file(recording.audio_path)
    except Exception as e:
        app.logger.error(f"Error serving audio for recording {recording_id}: {e}")
        return jsonify({'error': str(e)}), 500

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
                print(f"Deleted audio file: {recording.audio_path}")
        except Exception as e:
            # Log error but proceed to delete DB record
            app.logger.error(f"Error deleting audio file {recording.audio_path}: {e}")

        # Delete the database record
        db.session.delete(recording)
        db.session.commit()
        print(f"Deleted recording record ID: {recording_id}")

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting recording {recording_id}: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use waitress or gunicorn in production instead of Flask's dev server
    # Example: waitress-serve --host 0.0.0.0 --port 8899 app:app
    app.run(host='0.0.0.0', port=8899, debug=True) # debug=True reloads, which can interfere with threads. Set False for testing threads properly. Consider waitress for better threading.
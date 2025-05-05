# app.py
import os
import sys
from flask import Flask, render_template, request, jsonify, send_file, Markup
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
import re
import markdown

# Load environment variables from .env file
load_dotenv()

# Helper function to convert markdown to HTML
def md_to_html(text):
    if not text:
        return ""
    # Convert markdown to HTML with extensions for tables, code highlighting, etc.
    html = markdown.markdown(text, extensions=[
        'tables',           # Support for tables
        'fenced_code',      # Support for ```code blocks```
        'codehilite',       # Syntax highlighting for code blocks
        'nl2br',            # Convert newlines to <br> tags
        'sane_lists',       # Better list handling
        'smarty'            # Smart quotes, dashes, etc.
    ])
    return html

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
    meeting_date = db.Column(db.Date, nullable=True) # <-- ADDED: Meeting Date field
    file_size = db.Column(db.Integer)  # Store file size in bytes

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'participants': self.participants,
            'notes': self.notes,
            'notes_html': md_to_html(self.notes) if self.notes else "",
            'transcription': self.transcription,
            'summary': self.summary,
            'summary_html': md_to_html(self.summary) if self.summary else "",
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'meeting_date': self.meeting_date.isoformat() if self.meeting_date else None, # <-- ADDED: Include meeting_date
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
                
                try:
                    response_content = completion.choices[0].message.content
                    app.logger.debug(f"Raw OpenRouter response for {recording_id}: {response_content}")

                    # Use regex to extract JSON content from potential markdown code blocks
                    # This looks for content between markdown code blocks or just takes the whole content
                    json_match = re.search(r'```(?:json)?(.*?)```|(.+)', response_content, re.DOTALL)
                    
                    if json_match:
                        # Use the first group that matched (either between ``` or the whole content)
                        sanitized_response = json_match.group(1) if json_match.group(1) else json_match.group(2)
                        sanitized_response = sanitized_response.strip()
                    else:
                        sanitized_response = response_content.strip()
                        
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

# --- Chat with Transcription ---
@app.route('/chat', methods=['POST'])
def chat_with_transcription():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        recording_id = data.get('recording_id')
        user_message = data.get('message')
        message_history = data.get('message_history', [])
        
        if not recording_id:
            return jsonify({'error': 'No recording ID provided'}), 400
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
            
        # Get the recording
        recording = db.session.get(Recording, recording_id)
        if not recording:
            return jsonify({'error': 'Recording not found'}), 404
            
        # Check if OpenRouter client is available
        if client is None:
            return jsonify({'error': 'Chat service is not available (OpenRouter client not configured)'}), 503
            
        # Prepare the system prompt with the transcription
        system_prompt = f"""You are a professional meeting analyst working with Murtaza Nasir, Assistant Professor at Wichita State University. Analyze the following meeting information and respond to the specific request.

Following are the meeting participants and their roles:
{recording.participants or "No specific participants information provided."}

Following is the meeting transcript:
<<start transcript>>
{recording.transcription or "No transcript available."}
<<end transcript>>

Additional context and notes about the meeting:
{recording.notes or "none"}
"""
        
        # Call the LLM
        try:
            # Prepare messages array with system prompt and conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add message history if provided
            if message_history:
                messages.extend(message_history)
            
            # Add the current user message
            messages.append({"role": "user", "content": user_message})
            
            completion = client.chat.completions.create(
                model=openrouter_model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            response_content = completion.choices[0].message.content
            
            # Convert markdown in the response to HTML
            response_html = md_to_html(response_content)
            
            return jsonify({
                'response': response_content,
                'response_html': response_html,
                'success': True
            })
            
        except Exception as chat_error:
            app.logger.error(f"Error calling OpenRouter API for chat: {str(chat_error)}")
            return jsonify({'error': f'Chat service error: {str(chat_error)}'}), 500
            
    except Exception as e:
        app.logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
        if 'meeting_date' in data:
            try:
                # Attempt to parse date string (e.g., "YYYY-MM-DD")
                date_str = data['meeting_date']
                if date_str:
                    recording.meeting_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                else:
                    recording.meeting_date = None # Allow clearing the date
            except (ValueError, TypeError) as e:
                app.logger.warning(f"Could not parse meeting_date '{data.get('meeting_date')}': {e}")
                # Optionally return an error or just ignore the invalid date
                # return jsonify({'error': f"Invalid date format for meeting_date. Use YYYY-MM-DD."}), 400

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
            status='PENDING', # Explicitly set status
            meeting_date=datetime.utcnow().date() # <-- ADDED: Default meeting_date to today
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

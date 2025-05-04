# Project Files

Generated documentation of all project files.


## reset_db.py

```python

#!/usr/bin/env python3

from app import app, db
import os

def reset_database():
    # Get the database file path
    db_path = os.path.join('instance', 'transcriptions.db')
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database at {db_path}")
        os.remove(db_path)
    
    # Create application context
    with app.app_context():
        print("Creating new database...")
        # Create all tables
        db.create_all()
        print("Database initialization complete!")

if __name__ == "__main__":
    reset_database()
```


## app.py

```python

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

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///transcriptions.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 250 * 1024 * 1024  # 250MB max file size
db = SQLAlchemy()
db.init_app(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class Recording(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    participants = db.Column(db.String(500))
    notes = db.Column(db.Text)
    transcription = db.Column(db.Text)
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'file_size': self.file_size
        }

with app.app_context():
    db.create_all()

# API client setup
client = OpenAI(api_key="cant-be-empty", base_url="http://192.168.68.85:1611/v1/")

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
        return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST'])
def save_metadata():
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
        
        db.session.commit()
        return jsonify({'success': True, 'recording': recording.to_dict()})
    
    except Exception as e:
        db.session.rollback()
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
        
        file.save(filepath)
        
        # Create initial database entry
        recording = Recording(
            audio_path=filepath,
            title=f"Untitled Recording - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            file_size=file_size
        )
        db.session.add(recording)
        db.session.commit()
        
        # Start transcription
        try:
            with open(filepath, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="Systran/faster-distil-whisper-large-v3",
                    file=audio_file,
                    language="en"
                )
            
            recording.transcription = transcript.text
            db.session.commit()
            
            return jsonify(recording.to_dict())
            
        except Exception as e:
            # If transcription fails, we still keep the file but mark the error
            recording.transcription = f"Transcription failed: {str(e)}"
            db.session.commit()
            return jsonify({'error': f'Transcription failed: {str(e)}'}), 500
            
    except RequestEntityTooLarge:
        return jsonify({
            'error': 'File too large',
            'max_size_mb': app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
        }), 413
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/audio/<int:recording_id>')
def get_audio(recording_id):
    try:
        recording = db.session.get(Recording, recording_id)
        if not recording:
            return jsonify({'error': 'Recording not found'}), 404
        return send_file(recording.audio_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/recording/<int:recording_id>', methods=['DELETE'])
def delete_recording(recording_id):
    try:
        recording = db.session.get(Recording, recording_id)
        if not recording:
            return jsonify({'error': 'Recording not found'}), 404
        
        # Delete the audio file
        try:
            if recording.audio_path and os.path.exists(recording.audio_path):
                os.remove(recording.audio_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
        
        # Delete the database record
        db.session.delete(recording)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8899, debug=True)
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
</head>
<body class="bg-gray-100">
    <div id="app" class="container mx-auto px-4 py-8">
        <!-- Navigation -->
        <nav class="flex justify-between mb-8">
            <h1 class="text-2xl font-bold">Audio Transcription</h1>
            <div>
                <button @click="currentView = 'upload'" class="px-4 py-2 mr-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                    New Recording
                </button>
                <button @click="currentView = 'gallery'" class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600">
                    Gallery
                </button>
            </div>
        </nav>

        <!-- Upload View -->
        <div v-if="currentView === 'upload'" 
             @dragover.prevent="dragover = true"
             @dragleave.prevent="dragover = false"
             @drop.prevent="handleDrop"
             :class="{'border-blue-500 bg-blue-50': dragover}"
             class="border-2 border-dashed rounded-lg p-12 text-center transition-all duration-200">
            
            <!-- Loading State -->
            <div v-if="isProcessing" class="space-y-4">
                <div class="animate-spin mx-auto">
                    <i class="fas fa-circle-notch text-4xl text-blue-500"></i>
                </div>
                <h2 class="text-xl mb-2">Processing your audio file...</h2>
                <div class="max-w-md mx-auto">
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div class="bg-blue-500 h-2.5 rounded-full transition-all duration-500"
                             :style="{ width: processingStatus.progress + '%' }"></div>
                    </div>
                    <p class="text-sm text-gray-600 mt-2">${ processingStatus.message }</p>
                </div>
            </div>

            <!-- Upload State -->
            <div v-else>
                <i class="fas fa-cloud-upload-alt text-4xl mb-4 text-blue-500"></i>
                <h2 class="text-xl mb-2">Drag and drop your audio file here</h2>
                <p class="text-gray-500">or</p>
                <input type="file" @change="handleFileSelect" accept="audio/*" class="hidden" ref="fileInput">
                <button @click="$refs.fileInput.click()" class="mt-4 px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                    Select File
                </button>
            </div>
        </div>

        <!-- Input View -->
        <div v-if="currentView === 'input'" class="grid grid-cols-2 gap-8">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-4">Transcription</h3>
                <div class="h-96 overflow-y-auto p-4 bg-gray-50 rounded">
                    <span v-if="currentRecording">${ currentRecording.transcription }</span>
                </div>
            </div>

            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-4">Recording Details</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Title</label>
                        <input v-model="currentRecording.title" 
                               @input="autoSave"
                               class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Participants</label>
                        <input v-model="currentRecording.participants" 
                               @input="autoSave"
                               class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Notes</label>
                        <textarea v-model="currentRecording.notes" 
                                 @input="autoSave"
                                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                 rows="4"></textarea>
                    </div>
                </div>
            </div>
        </div>

        <!-- Gallery View -->
        <div v-if="currentView === 'gallery'" class="grid grid-cols-4 gap-8">
            <!-- Left side: Recording list -->
            <div class="col-span-1 bg-white p-6 rounded-lg shadow">
                <h3 class="text-lg font-semibold mb-4">Recordings</h3>
                <div class="space-y-4">
                    <div v-for="group in groupedRecordings" :key="group.title">
                        <h4 class="font-medium text-gray-700 mb-2">${ group.title }</h4>
                        <ul class="space-y-2">
                            <li v-for="recording in group.items" 
                                :key="recording.id"
                                @click="selectRecording(recording)"
                                class="cursor-pointer p-2 rounded hover:bg-gray-100 flex justify-between items-center"
                                :class="{'bg-blue-50': selectedRecording?.id === recording.id}">
                                <span>${ recording.title }</span>
                                <div class="flex space-x-2">
                                    <button @click.stop="editRecording(recording)" 
                                            class="text-blue-500 hover:text-blue-700">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button @click.stop="confirmDelete(recording)" 
                                            class="text-red-500 hover:text-red-700">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Right side: Selected recording details -->
            <div v-if="selectedRecording" class="col-span-3 bg-white p-6 rounded-lg shadow">
                <div class="flex justify-between items-start mb-4">
                    <h3 class="text-xl font-semibold">${ selectedRecording.title }</h3>
                    <div class="flex space-x-2">
                        <button @click="editRecording(selectedRecording)" 
                                class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600">
                            <i class="fas fa-edit mr-1"></i> Edit
                        </button>
                        <button @click="confirmDelete(selectedRecording)"
                                class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600">
                            <i class="fas fa-trash mr-1"></i> Delete
                        </button>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-8">
                    <div>
                        <h4 class="font-medium mb-2">Transcription</h4>
                        <div class="h-96 overflow-y-auto p-4 bg-gray-50 rounded">
                            ${ selectedRecording.transcription }
                        </div>
                    </div>
                    <div class="space-y-4">
                        <div>
                            <h4 class="font-medium mb-2">Audio</h4>
                            <audio controls class="w-full" :key="selectedRecording.id">
                                <source :src="'/audio/' + selectedRecording.id" type="audio/mpeg">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                        <div>
                            <h4 class="font-medium mb-2">Participants</h4>
                            <p>${ selectedRecording.participants || 'None specified' }</p>
                        </div>
                        <div>
                            <h4 class="font-medium mb-2">Notes</h4>
                            <p class="whitespace-pre-wrap">${ selectedRecording.notes || 'No notes' }</p>
                        </div>
                        <div>
                            <h4 class="font-medium mb-2">Created</h4>
                            <p>${ new Date(selectedRecording.created_at).toLocaleString() }</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Edit Modal -->
        <div v-if="showEditModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div class="bg-white p-6 rounded-lg shadow-lg w-full max-w-lg">
                <h3 class="text-lg font-semibold mb-4">Edit Recording</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Title</label>
                        <input v-model="editingRecording.title" 
                               class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Participants</label>
                        <input v-model="editingRecording.participants" 
                               class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Notes</label>
                        <textarea v-model="editingRecording.notes" 
                                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                 rows="4"></textarea>
                    </div>
                    <div class="flex justify-end space-x-2">
                        <button @click="showEditModal = false" 
                                class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600">
                            Cancel
                        </button>
                        <button @click="saveEdit" 
                                class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Delete Confirmation Modal -->
        <div v-if="showDeleteModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <div class="bg-white p-6 rounded-lg shadow-lg">
                <h3 class="text-lg font-semibold mb-4">Confirm Delete</h3>
                <p>Are you sure you want to delete this recording?</p>
                <p class="text-sm text-gray-500 mb-4">This action cannot be undone.</p>
                <div class="flex justify-end space-x-2">
                    <button @click="showDeleteModal = false" 
                            class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600">
                        Cancel
                    </button>
                    <button @click="deleteRecording" 
                            class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">
                        Delete
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const { createApp } = Vue

        createApp({
            data() {
                return {
                    currentView: 'upload',
                    dragover: false,
                    currentRecording: null,
                    recordings: [],
                    selectedRecording: null,
                    showEditModal: false,
                    showDeleteModal: false,
                    editingRecording: null,
                    recordingToDelete: null,
                    autoSaveTimeout: null,
                    isProcessing: false,
                    processingStatus: {
                        progress: 0,
                        message: ''
                    }
                }
            },
            computed: {
                groupedRecordings() {
                    const now = new Date()
                    const oneWeek = 7 * 24 * 60 * 60 * 1000
                    
                    return [
                        {
                            title: 'This Week',
                            items: this.recordings.filter(r => {
                                const date = new Date(r.created_at)
                                return now - date < oneWeek
                            })
                        },
                        {
                            title: 'Last Week',
                            items: this.recordings.filter(r => {
                                const date = new Date(r.created_at)
                                return now - date >= oneWeek && now - date < oneWeek * 2
                            })
                        },
                        {
                            title: 'Older',
                            items: this.recordings.filter(r => {
                                const date = new Date(r.created_at)
                                return now - date >= oneWeek * 2
                            })
                        }
                    ]
                }
            },
            delimiters: ['${', '}'],  // Changed delimiters to avoid conflicts with Jinja2
            methods: {
                async handleDrop(e) {
                    this.dragover = false
                    const file = e.dataTransfer.files[0]
                    if (file && file.type.startsWith('audio/')) {
                        await this.uploadFile(file)
                    }
                },
                async handleFileSelect(e) {
                    const file = e.target.files[0]
                    if (file) {
                        await this.uploadFile(file)
                    }
                },
                async uploadFile(file) {
                    this.isProcessing = true
                    this.processingStatus = {
                        progress: 0,
                        message: 'Starting upload...'
                    }

                    const formData = new FormData()
                    formData.append('file', file)
                    
                    try {
                        // Upload file
                        this.processingStatus = {
                            progress: 20,
                            message: 'Uploading file...'
                        }
                        
                        const response = await fetch('/upload', {
                            method: 'POST',
                            body: formData
                        })
                        
                        if (!response.ok) {
                            throw new Error('Upload failed')
                        }

                        // Start polling for status
                        const data = await response.json()
                        if (data.task_id) {
                            await this.pollProcessingStatus(data.task_id)
                        } else {
                            // Handle immediate response
                            this.handleProcessingComplete(data)
                        }
                    } catch (error) {
                        alert('Upload failed: ' + error)
                        this.isProcessing = false
                    }
                },

                
                async pollProcessingStatus(taskId) {
                    const pollInterval = setInterval(async () => {
                        try {
                            const response = await fetch(`/status/${taskId}`)
                            const data = await response.json()
                            
                            this.processingStatus = {
                                progress: data.progress,
                                message: data.message
                            }

                            if (data.status === 'completed') {
                                clearInterval(pollInterval)
                                this.handleProcessingComplete(data.result)
                            } else if (data.status === 'failed') {
                                clearInterval(pollInterval)
                                throw new Error(data.error)
                            }
                        } catch (error) {
                            clearInterval(pollInterval)
                            alert('Processing failed: ' + error)
                            this.isProcessing = false
                        }
                    }, 1000)
                },

                handleProcessingComplete(data) {
                    this.currentRecording = {
                        id: data.id,
                        transcription: data.transcription,
                        title: '',
                        participants: '',
                        notes: ''
                    }
                    this.isProcessing = false
                    this.currentView = 'input'
                },

                autoSave() {
                    clearTimeout(this.autoSaveTimeout)
                    this.autoSaveTimeout = setTimeout(() => {
                        this.saveRecording()
                    }, 1000)
                },
                async saveRecording() {
                    try {
                        const response = await fetch('/save', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(this.currentRecording)
                        })
                        const data = await response.json()
                        
                        if (!response.ok) {
                            throw new Error(data.error)
                        }
                    } catch (error) {
                        alert('Save failed: ' + error)
                    }
                },
                async loadRecordings() {
                    try {
                        const response = await fetch('/recordings')
                        const data = await response.json()
                        this.recordings = data
                    } catch (error) {
                        alert('Failed to load recordings: ' + error)
                    }
                },

                editRecording(recording) {
                    this.editingRecording = { ...recording };
                    this.showEditModal = true;
                },

                async saveEdit() {
                    try {
                        const response = await fetch('/save', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(this.editingRecording)
                        });
                        
                        if (!response.ok) {
                            throw new Error('Failed to save changes');
                        }
                        
                        const data = await response.json();
                        
                        // Update the recording in the list
                        const index = this.recordings.findIndex(r => r.id === this.editingRecording.id);
                        if (index !== -1) {
                            this.recordings[index] = data.recording;
                            if (this.selectedRecording?.id === data.recording.id) {
                                this.selectedRecording = data.recording;
                            }
                        }
                        
                        this.showEditModal = false;
                    } catch (error) {
                        alert('Failed to save changes: ' + error);
                    }
                },

                confirmDelete(recording) {
                    this.recordingToDelete = recording;
                    this.showDeleteModal = true;
                },

                async deleteRecording() {
                    try {
                        const response = await fetch(`/recording/${this.recordingToDelete.id}`, {
                            method: 'DELETE'
                        });
                        
                        if (!response.ok) {
                            throw new Error('Failed to delete recording');
                        }
                        
                        // Remove from recordings list
                        this.recordings = this.recordings.filter(r => r.id !== this.recordingToDelete.id);
                        
                        // Clear selected recording if it was deleted
                        if (this.selectedRecording?.id === this.recordingToDelete.id) {
                            this.selectedRecording = null;
                        }
                        
                        this.showDeleteModal = false;
                        this.recordingToDelete = null;
                    } catch (error) {
                        alert('Failed to delete recording: ' + error);
                    }
                },
                
                selectRecording(recording) {
                    this.selectedRecording = recording
                }
            },
            mounted() {
                this.loadRecordings()
            }
        }).mount('#app')
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
WorkingDirectory=/opt/transcription-app
Environment="PATH=/opt/transcription-app/venv/bin"
Environment="PYTHONPATH=/opt/transcription-app"
ExecStart=/opt/transcription-app/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8899 app:app
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

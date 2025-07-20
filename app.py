from flask import Flask, request, jsonify, send_from_directory
import hashlib
import json
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import sqlite3
import openai
import pathlib
from flask_cors import CORS

from dotenv import load_dotenv

# Load environment variables from .env file with override
# This will override any existing environment variables with values from .env
load_dotenv(override=True)

import sys

from database import init_database, get_db_connection, cleanup_old_clipboard_entries, create_uploads_directory

app = Flask(__name__)

# Production-ready CORS configuration
# Allow specific origins in production, all origins in development
if os.environ.get('FLASK_ENV') == 'production':
    # In production, allow specific domains - UPDATE THESE WITH YOUR ACTUAL RENDER URLS
    allowed_origins = [
        'https://clio-frontend.onrender.com',
        'https://clio-frontend-6frc.onrender.com'  # Your actual frontend URL
    ]
    CORS(app, origins=allowed_origins, supports_credentials=False)
else:
    # In development, allow all origins
    CORS(app, origins='*', supports_credentials=False)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize database and directories on startup
init_database()
create_uploads_directory()

# Ensure uploads directory exists with absolute path
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir, exist_ok=True)
    print(f"[INFO] Created uploads directory: {uploads_dir}")

# Add request logging middleware
@app.before_request
def log_request_info():
    print(f"[DEBUG] {request.method} {request.path}")
    print(f"[DEBUG] Origin: {request.headers.get('Origin', 'No origin')}")
    print(f"[DEBUG] User-Agent: {request.headers.get('User-Agent', 'No user-agent')}")
    if request.method == 'OPTIONS':
        print("[DEBUG] Preflight request detected")

# Initialize OpenAI API with better error handling
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("[ERROR] FATAL: No OpenAI API key found in environment variables!")
    print("[ERROR] Please ensure OPENAI_API_KEY is set in your environment or .env file.")
else:
    print(f"[INFO] OpenAI API key loaded successfully. Length: {len(api_key)} characters")
    print(f"[INFO] API key preview: {api_key[:20]}...{api_key[-4:]}")
    openai.api_key = api_key

def generate_file_hash(content):
    """Generate MD5 hash of file content."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def detect_content_type(content):
    """Simple content type detection based on content patterns."""
    content_lower = content.lower().strip()
    
    if content_lower.startswith(('http://', 'https://', 'www.')):
        return 'url'
    elif '@' in content and '.' in content.split('@')[-1]:
        return 'email'
    elif any(keyword in content_lower for keyword in ['def ', 'function', 'class ', 'import ', 'const ', 'var ']):
        return 'code'
    elif content.isdigit() or (content.replace('.', '').replace('-', '').isdigit()):
        return 'number'
    else:
        return 'text'

@app.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint."""
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM versions')
        version_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'version_count': version_count,
            'openai_key_configured': bool(api_key)
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.route('/api/projects', methods=['GET', 'OPTIONS'])
def get_projects():
    """Get list of all unique projects, organized by group."""
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT project_name, group_name FROM versions ORDER BY group_name, project_name')
        
        projects_by_group = {}
        for row in cursor.fetchall():
            group = row['group_name'] if row['group_name'] else 'Uncategorized'
            project = row['project_name']
            if group not in projects_by_group:
                projects_by_group[group] = []
            projects_by_group[group].append(project)
        
        # Format for frontend
        grouped_projects = []
        for group_name, projects in sorted(projects_by_group.items()):
            grouped_projects.append({'group_name': group_name, 'projects': sorted(projects)})

        conn.close()
        
        response = jsonify({
            'success': True,
            'projects': grouped_projects
        })
        
        # Add explicit CORS headers
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        
        return response
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/upload', methods=['POST'])
def upload_version():
    """Save a new version (file upload or text content)."""
    try:
        project_name = request.form.get('project_name', '').strip()
        filename = request.form.get('filename', '').strip()
        comment = request.form.get('comment', '').strip()
        group_name = request.form.get('group_name', '').strip() or None
        
        if not project_name:
            return jsonify({'success': False, 'error': 'Project name is required'}), 400
        
        # Handle file upload
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            filename = secure_filename(file.filename) if filename == '' else secure_filename(filename)
            content = file.read().decode('utf-8', errors='ignore')
        
        # Handle text content
        elif 'content' in request.form:
            content = request.form.get('content', '')
            if not filename:
                filename = f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        else:
            return jsonify({'success': False, 'error': 'No file or content provided'}), 400
        
        if not content.strip():
            return jsonify({'success': False, 'error': 'Content cannot be empty'}), 400
        
        # Generate file hash and timestamp
        file_hash = generate_file_hash(content)
        timestamp = datetime.now().isoformat()
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO versions (project_name, filename, content, comment, timestamp, file_hash, group_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (project_name, filename, content, comment, timestamp, file_hash, group_name))
        
        version_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create project directory and save file
        project_dir = os.path.join('uploads', 'projects', secure_filename(project_name))
        os.makedirs(project_dir, exist_ok=True)
        
        file_path = os.path.join(project_dir, f"{version_id}_{filename}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'version_id': version_id,
            'message': f'Version saved successfully with ID: {version_id}'
        })
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/versions/<project>', methods=['GET'])
def get_versions(project):
    """Get all versions for a specific project."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, comment, timestamp, file_hash 
            FROM versions 
            WHERE project_name = ? 
            ORDER BY timestamp DESC
        ''', (project,))
        
        versions = []
        for row in cursor.fetchall():
            versions.append({
                'id': row['id'],
                'filename': row['filename'],
                'comment': row['comment'],
                'timestamp': row['timestamp'],
                'file_hash': row['file_hash']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'project': project,
            'versions': versions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/version/<int:version_id>/content', methods=['GET'])
def get_version_content(version_id):
    """Get the content of a specific version."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT content, filename FROM versions WHERE id = ?', (version_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'success': False, 'error': 'Version not found'}), 404
        
        return jsonify({
            'success': True,
            'content': row['content'],
            'filename': row['filename']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clipboard', methods=['GET'])
def get_clipboard():
    """Get clipboard entries from the last 24 hours."""
    try:
        # Clean up old entries first
        cleanup_old_clipboard_entries()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, content, timestamp, content_type, source_app 
            FROM clipboard 
            ORDER BY timestamp DESC
        ''')
        
        entries = []
        for row in cursor.fetchall():
            entries.append({
                'id': row['id'],
                'content': row['content'],
                'timestamp': row['timestamp'],
                'content_type': row['content_type'],
                'source_app': row['source_app']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'entries': entries
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clipboard', methods=['POST'])
def save_clipboard():
    """Save a new clipboard entry."""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'success': False, 'error': 'Content is required'}), 400
        
        content = data['content'].strip()
        if not content:
            return jsonify({'success': False, 'error': 'Content cannot be empty'}), 400
        
        # Detect content type
        content_type = detect_content_type(content)
        
        # Get source app if provided
        source_app = data.get('source_app', 'Unknown')
        
        # Generate timestamp
        timestamp = datetime.now().isoformat()
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clipboard (content, timestamp, content_type, source_app)
            VALUES (?, ?, ?, ?)
        ''', (content, timestamp, content_type, source_app))
        
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'entry_id': entry_id,
            'message': 'Clipboard entry saved successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clipboard/<int:entry_id>', methods=['DELETE'])
def delete_clipboard_entry(entry_id):
    """Delete a specific clipboard entry."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clipboard WHERE id = ?', (entry_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Entry not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Entry deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analyze-diff', methods=['POST'])
def analyze_diff():
    print("[DEBUG] /api/analyze-diff called")
    try:
        data = request.get_json()
        if not data:
            print("[DEBUG] No JSON data received")
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
            
        print("[DEBUG] Received data keys:", list(data.keys()))
        old_content = data.get('old_content', '')
        new_content = data.get('new_content', '')
        print("[DEBUG] old_content length:", len(old_content))
        print("[DEBUG] new_content length:", len(new_content))

        if not old_content or not new_content:
            print("[DEBUG] Missing old_content or new_content")
            return jsonify({
                'success': False,
                'error': 'Both old and new content are required'
            }), 400

        # Check content size limits (approximately 150,000 characters to stay under token limits)
        MAX_CONTENT_SIZE = 150000
        
        if len(old_content) > MAX_CONTENT_SIZE or len(new_content) > MAX_CONTENT_SIZE:
            print(f"[DEBUG] Content too large - truncating to {MAX_CONTENT_SIZE} characters")
            
            # Truncate content and add notice
            old_content_truncated = old_content[:MAX_CONTENT_SIZE] + "\n\n[Content truncated due to size limits]"
            new_content_truncated = new_content[:MAX_CONTENT_SIZE] + "\n\n[Content truncated due to size limits]"
            
            analysis = {
                'summary': f"File is very large ({len(new_content):,} characters). Analysis is based on the first {MAX_CONTENT_SIZE:,} characters only.",
                'insights': [
                    f"Original file size: {len(new_content):,} characters",
                    f"Analysis limited to first {MAX_CONTENT_SIZE:,} characters",
                    "For large files, consider comparing specific sections manually"
                ]
            }
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })

        # Get the API key and verify it's correct
        api_key = os.environ.get("OPENAI_API_KEY")
        print(f"[DEBUG] Using OpenAI key: {api_key[:20]}...{api_key[-4:] if len(api_key) > 24 else api_key}")
        print(f"[DEBUG] API key length: {len(api_key)}")
        
        if not api_key or len(api_key) < 50:
            print("[DEBUG] API key is too short or missing")
            return jsonify({
                'success': False,
                'error': 'Invalid API key configuration'
            }), 500

        # Compose a prompt for OpenAI
        prompt = (
            "Summarize the main differences between these two versions of text/code. "
            "Highlight key changes, additions, and removals in a concise way.\n\n"
            f"Old version:\n{old_content}\n\nNew version:\n{new_content}\n\nSummary:"
        )
        print("[DEBUG] Prompt for OpenAI:", prompt[:200], "...")

        print("[DEBUG] Creating OpenAI client...")
        client = openai.OpenAI(api_key=api_key)
        print("[DEBUG] OpenAI client created")
        
        print("[DEBUG] Making OpenAI API call...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Changed to gpt-3.5-turbo for better compatibility
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes diffs between two versions of text or code."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3,
        )
        print("[DEBUG] OpenAI response received")
        summary = response.choices[0].message.content.strip()
        print("[DEBUG] Summary:", summary)

        analysis = {
            'summary': summary,
            'insights': []
        }

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        print(f"[DEBUG] AI analysis error: {e}")
        import traceback
        print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/project/<project_name>', methods=['DELETE'])
def delete_project(project_name):
    """Delete a project and all its versions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all versions for this project
        cursor.execute('DELETE FROM versions WHERE project_name = ?', (project_name,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # Delete project directory if it exists
        project_dir = os.path.join('uploads', 'projects', secure_filename(project_name))
        if os.path.exists(project_dir):
            import shutil
            shutil.rmtree(project_dir)
        
        return jsonify({
            'success': True,
            'message': f'Project "{project_name}" and {deleted_count} versions deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/group/<group_name>', methods=['DELETE'])
def delete_group(group_name):
    """Delete all projects in a group."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all projects in this group
        cursor.execute('SELECT project_name FROM versions WHERE group_name = ?', (group_name,))
        projects = [row['project_name'] for row in cursor.fetchall()]
        
        # Delete all versions for projects in this group
        cursor.execute('DELETE FROM versions WHERE group_name = ?', (group_name,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # Delete project directories
        for project_name in projects:
            project_dir = os.path.join('uploads', 'projects', secure_filename(project_name))
            if os.path.exists(project_dir):
                import shutil
                shutil.rmtree(project_dir)
        
        return jsonify({
            'success': True,
            'message': f'Group "{group_name}" and {deleted_count} versions deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/project/<old_name>', methods=['PUT'])
def rename_project(old_name):
    """Rename a project."""
    try:
        data = request.get_json()
        if not data or 'new_name' not in data:
            return jsonify({'success': False, 'error': 'New name is required'}), 400
        
        new_name = data['new_name'].strip()
        if not new_name:
            return jsonify({'success': False, 'error': 'New name cannot be empty'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update all versions for this project
        cursor.execute('UPDATE versions SET project_name = ? WHERE project_name = ?', (new_name, old_name))
        updated_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # Rename project directory if it exists
        old_dir = os.path.join('uploads', 'projects', secure_filename(old_name))
        new_dir = os.path.join('uploads', 'projects', secure_filename(new_name))
        if os.path.exists(old_dir):
            os.rename(old_dir, new_dir)
        
        return jsonify({
            'success': True,
            'message': f'Project renamed from "{old_name}" to "{new_name}" ({updated_count} versions updated)'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/project/<project_name>/group', methods=['PUT'])
def move_project_to_group(project_name):
    """Move a project to a different group."""
    try:
        data = request.get_json()
        if not data or 'group_name' not in data:
            return jsonify({'success': False, 'error': 'Group name is required'}), 400
        
        group_name = data['group_name'].strip() or None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update all versions for this project
        cursor.execute('UPDATE versions SET group_name = ? WHERE project_name = ?', (group_name, project_name))
        updated_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Project "{project_name}" moved to group "{group_name or "Uncategorized"}" ({updated_count} versions updated)'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """Root endpoint - redirect to frontend or show API info."""
    return jsonify({
        'message': 'Clio Backend API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'projects': '/api/projects',
            'upload': '/api/upload',
            'clipboard': '/api/clipboard',
            'analyze': '/api/analyze-diff'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api')
def api_info():
    """API information endpoint."""
    return jsonify({
        'name': 'Clio Backend API',
        'version': '1.0.0',
        'description': 'Clipboard manager and version control system',
        'endpoints': {
            'health': '/api/health',
            'projects': '/api/projects',
            'upload': '/api/upload',
            'clipboard': '/api/clipboard',
            'analyze': '/api/analyze-diff'
        }
    })

@app.route('/api/test', methods=['GET', 'OPTIONS'])
def test_endpoint():
    """Test endpoint for debugging CORS issues."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'preflight'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    return jsonify({
        'status': 'ok',
        'message': 'CORS test successful',
        'timestamp': datetime.now().isoformat(),
        'origin': request.headers.get('Origin', 'No origin header'),
        'method': request.method
    })

# Folder Management API Endpoints

@app.route('/api/folder-projects', methods=['GET', 'OPTIONS'])
def get_folder_projects():
    """Get list of all folder projects."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name, created_at FROM folder_projects ORDER BY created_at DESC')
        
        projects = []
        for row in cursor.fetchall():
            projects.append({
                'name': row['name'],
                'created_at': row['created_at']
            })
        
        conn.close()
        
        response = jsonify({
            'success': True,
            'projects': projects
        })
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        
        return response
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/folder-projects', methods=['POST'])
def create_folder_project():
    """Create a new folder project."""
    try:
        data = request.json
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
            
        project_name = data.get('name')
        if project_name is None:
            return jsonify({'success': False, 'error': 'Project name is required'}), 400
        project_name = project_name.strip()
        
        if not project_name:
            return jsonify({'success': False, 'error': 'Project name is required'}), 400
        
        timestamp = datetime.now().isoformat()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO folder_projects (name, created_at)
                VALUES (?, ?)
            ''', (project_name, timestamp))
            conn.commit()
            
            response = jsonify({
                'success': True,
                'message': f'Project "{project_name}" created successfully'
            })
            
        except sqlite3.IntegrityError:
            response = jsonify({
                'success': False,
                'error': f'Project "{project_name}" already exists'
            }), 400
        
        conn.close()
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/folder-versions', methods=['POST'])
def get_or_save_folder_versions():
    """Get folder versions for a project or save a new folder version."""
    try:
        print(f"[DEBUG] Request content type: {request.content_type}")
        print(f"[DEBUG] Request data: {request.get_data()}")
        
        data = request.json
        if data is None:
            print("[ERROR] request.json is None")
            return jsonify({
                'success': False, 
                'error': 'No JSON data received. Please ensure Content-Type is application/json'
            }), 400
            
        print(f"[DEBUG] Parsed JSON data: {data}")
        
        # Check if this is a request to get versions (has only project field)
        if 'project' in data and len(data) == 1:
            project_name = data.get('project')
            if project_name is None:
                return jsonify({'success': False, 'error': 'Project name is required'}), 400
            project_name = project_name.strip()
            
            if not project_name:
                return jsonify({'success': False, 'error': 'Project name is required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, project_name, folder_name, comment, file_count, created_at
                FROM folder_versions 
                WHERE project_name = ?
                ORDER BY created_at DESC
            ''', (project_name,))
            
            versions = []
            for row in cursor.fetchall():
                versions.append({
                    'id': row['id'],
                    'project_name': row['project_name'],
                    'folder_name': row['folder_name'],
                    'comment': row['comment'],
                    'file_count': row['file_count'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            
            response = jsonify({
                'success': True,
                'versions': versions
            })
            
        else:
            # This is a request to save a new folder version
            project_name = data.get('project')
            if project_name is None:
                return jsonify({'success': False, 'error': 'Project name is required'}), 400
            project_name = project_name.strip()
            
            folder_name = data.get('folder_name')
            if folder_name is None:
                return jsonify({'success': False, 'error': 'Folder name is required'}), 400
            folder_name = folder_name.strip()
            
            folder_structure = data.get('folder_structure', {})
            
            comment = data.get('comment')
            if comment is not None:
                comment = comment.strip() or None
            
            file_count = data.get('file_count', 0)
            
            if not project_name:
                return jsonify({'success': False, 'error': 'Project name is required'}), 400
            
            if not folder_name:
                return jsonify({'success': False, 'error': 'Folder name is required'}), 400
            
            if not folder_structure:
                return jsonify({'success': False, 'error': 'Folder structure is required'}), 400
            
            timestamp = datetime.now().isoformat()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify project exists
            cursor.execute('SELECT name FROM folder_projects WHERE name = ?', (project_name,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': f'Project "{project_name}" does not exist'}), 400
            
            # Save folder version
            cursor.execute('''
                INSERT INTO folder_versions (project_name, folder_name, folder_structure, file_contents, comment, file_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_name, folder_name, json.dumps(folder_structure), None, comment, file_count, timestamp))
            
            version_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            response = jsonify({
                'success': True,
                'message': 'Folder version saved successfully',
                'version_id': version_id
            })
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/folder-versions/<int:version_id>', methods=['GET'])
def get_folder_version(version_id):
    """Get a specific folder version with full structure."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, project_name, folder_name, folder_structure, comment, file_count, created_at
            FROM folder_versions 
            WHERE id = ?
        ''', (version_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Folder version not found'}), 404
        
        version = {
            'id': row['id'],
            'project_name': row['project_name'],
            'folder_name': row['folder_name'],
            'folder_structure': json.loads(row['folder_structure']),
            'comment': row['comment'],
            'file_count': row['file_count'],
            'created_at': row['created_at']
        }
        
        conn.close()
        
        response = jsonify({
            'success': True,
            'version': version
        })
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/folder-versions/<int:version_id>/download', methods=['GET'])
def download_folder_version(version_id):
    """Download folder version structure as JSON."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT project_name, folder_name, folder_structure, comment, file_count, created_at
            FROM folder_versions 
            WHERE id = ?
        ''', (version_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Folder version not found'}), 404
        
        version_data = {
            'project_name': row['project_name'],
            'folder_name': row['folder_name'],
            'folder_structure': json.loads(row['folder_structure']),
            'comment': row['comment'],
            'file_count': row['file_count'],
            'created_at': row['created_at'],
            'export_timestamp': datetime.now().isoformat()
        }
        
        conn.close()
        
        response = jsonify(version_data)
        response.headers['Content-Disposition'] = f'attachment; filename=folder-version-{version_id}.json'
        response.headers.add('Access-Control-Allow-Origin', '*')
        
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/folder-versions/<int:version_id>/download-zip', methods=['GET'])
def download_folder_version_zip(version_id):
    """Download folder version as ZIP file with actual contents."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT project_name, folder_name, folder_structure, comment, file_count, created_at
            FROM folder_versions 
            WHERE id = ?
        ''', (version_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Folder version not found'}), 404
        
        folder_structure = json.loads(row['folder_structure'])
        folder_name = row['folder_name']
        
        # Check if this version has file contents
        if not has_file_contents(folder_structure):
            conn.close()
            return jsonify({
                'success': False, 
                'error': 'This folder version was saved before file contents were supported. Only structure metadata is available.'
            }), 400
        
        conn.close()
        
        # Return the folder structure so frontend can create ZIP
        response = jsonify({
            'success': True,
            'folder_structure': folder_structure,
            'folder_name': folder_name
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

def has_file_contents(structure):
    """Check if folder structure contains actual file contents."""
    if structure.get('type') == 'file':
        return 'content' in structure
    elif structure.get('type') == 'directory' and 'children' in structure:
        return any(has_file_contents(child) for child in structure['children'])
    return False

@app.route('/api/folder-projects/<old_name>', methods=['PUT'])
def rename_folder_project(old_name):
    """Rename a folder project."""
    try:
        data = request.json
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
            
        new_name = data.get('new_name')
        if new_name is None:
            return jsonify({'success': False, 'error': 'New name is required'}), 400
        new_name = new_name.strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'New name cannot be empty'}), 400
        
        if new_name == old_name:
            return jsonify({'success': False, 'error': 'New name must be different from current name'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if old project exists
        cursor.execute('SELECT name FROM folder_projects WHERE name = ?', (old_name,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': f'Project "{old_name}" not found'}), 404
        
        # Check if new name already exists
        cursor.execute('SELECT name FROM folder_projects WHERE name = ?', (new_name,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': f'Project "{new_name}" already exists'}), 400
        
        # Update project name in folder_projects table
        cursor.execute('UPDATE folder_projects SET name = ? WHERE name = ?', (new_name, old_name))
        
        # Update project name in folder_versions table
        cursor.execute('UPDATE folder_versions SET project_name = ? WHERE project_name = ?', (new_name, old_name))
        
        conn.commit()
        conn.close()
        
        response = jsonify({
            'success': True,
            'message': f'Project renamed from "{old_name}" to "{new_name}"'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/folder-projects/<project_name>', methods=['DELETE'])
def delete_folder_project(project_name):
    """Delete a folder project and all its versions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if project exists
        cursor.execute('SELECT name FROM folder_projects WHERE name = ?', (project_name,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': f'Project "{project_name}" not found'}), 404
        
        # Delete all folder versions for this project
        cursor.execute('DELETE FROM folder_versions WHERE project_name = ?', (project_name,))
        deleted_versions = cursor.rowcount
        
        # Delete the project itself
        cursor.execute('DELETE FROM folder_projects WHERE name = ?', (project_name,))
        
        conn.commit()
        conn.close()
        
        response = jsonify({
            'success': True,
            'message': f'Project "{project_name}" and {deleted_versions} versions deleted successfully'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
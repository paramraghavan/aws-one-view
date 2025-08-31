# Basic upload page

create a python flask app. with html5 the user drags and drop files from desktop into the drop zone on the UI page, and
says submit.
On submit it invokes a script which does custom stuff. For now assume this script does prints the filename, file size
and path. Some of these files are large and the script is a synchronous call, show a hour glass or wait on the UI for
all the files to get procesed. As each file is sent to the script it is picked up by the script. processed and
completed, write this log on the UI screen and also log to a file identify the client info - ip address, domain name,
hostname log as well. The script uses a config yaml file, allow user to view, update this config yaml file from UI

# FlaskSockerIO

Great questions! Let me explain the role of Flask-SocketIO and eventlet in this application:

## 🔌 **Flask-SocketIO: Real-time Communication**

Flask-SocketIO enables **bidirectional, real-time communication** between the server and client. Here's why we need it:

### **Without SocketIO (Traditional Flask):**

```python
# User uploads files → Server processes → User sees nothing until all done
# No progress updates, no real-time feedback
# User just sees a spinning wheel with no information
```

### **With SocketIO (Our App):**

```python
# User uploads files → Server processes each file → 
# Server sends live updates → Client updates UI in real-time
# "Processing file1.txt..." → "✓ Completed file1.txt" → "Processing file2.txt..."
```

## 📍 **Where We Use SocketIO in Our Code:**

### **1. Server Side (app.py):**

```python
from flask_socketio import SocketIO, emit

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")


# Send real-time updates during processing
def process_file(filepath, filename, client_info, config):
    # Send "processing started" update
    socketio.emit('file_progress', {
        'filename': filename,
        'status': 'processing',
        'message': f"Processing {filename}..."
    })

    # ... do actual processing ...

    # Send "completed" update
    socketio.emit('file_progress', {
        'filename': filename,
        'status': 'completed',
        'message': f"✓ Completed {filename}"
    })
```

### **2. Client Side (index.html):**

```javascript
// Connect to SocketIO
const socket = io();

// Listen for real-time updates
socket.on('file_progress', (data) => {
    // Update UI immediately when server sends progress
    addLogEntry(data.status, data.message, data.filename);
    updateFileStatus(data.filename, data.status);
});
```

## ⚡ **Eventlet: Async Server Backend**

Eventlet is a **high-performance async networking library** that Flask-SocketIO uses under the hood.

### **Why Eventlet:**

1. **Handles Multiple Connections:** Can manage thousands of simultaneous WebSocket connections
2. **Non-blocking I/O:** Server doesn't freeze when processing files
3. **Better Performance:** More efficient than standard WSGI servers for real-time apps

### **Where Eventlet is Used:**

```python
# In app.py - the final line
socketio.run(app, debug=True, host='0.0.0.0', port=5000)
# ↑ This automatically uses eventlet if available
```

Flask-SocketIO automatically detects and uses eventlet when available. If eventlet isn't installed, it falls back to
other backends (threading, gevent).

## 🔄 **The Complete Flow:**

```
1. User drops files → Frontend JavaScript
2. Files uploaded via POST → Flask endpoint
3. Flask starts background processing → Python thread
4. Each file processed → process_file() function
5. Progress updates sent → socketio.emit()
6. Updates received → JavaScript socket.on()
7. UI updated instantly → Real-time feedback
```

## 💡 **Alternative Without SocketIO:**

If you removed Flask-SocketIO, you'd need to:

1. **Polling Approach:**

```javascript
// Check progress every 2 seconds (inefficient)
setInterval(async () => {
    const response = await fetch('/check_progress');
    const progress = await response.json();
    updateUI(progress);
}, 2000);
```

2. **No Real-time Updates:**

```python
# User uploads → Long wait → All results at once
# No progress indication, poor user experience
```

## 🎯 **Benefits in Our App:**

- **Instant Feedback:** Users see exactly which file is being processed
- **Better UX:** No mysterious waiting periods
- **Error Handling:** Immediate notification if a file fails
- **Scalability:** Can handle multiple users uploading simultaneously
- **Professional Feel:** Modern apps expect real-time updates

## 📦 **Installation Note:**

```bash
pip install Flask-SocketIO  # Automatically includes python-socketio
pip install eventlet       # Optional but recommended for better performance
```

**Bottom Line:** Flask-SocketIO transforms this from a basic file upload into a modern, real-time application that
provides immediate feedback to users - essential for processing large files where users need to know the system is
working!
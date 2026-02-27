# Data Ingest Runner

A minimal Flask web application that:
- Detects available environments from `.properties` files
- Prompts for password (cached per session)
- Accepts multiple input files
- Runs a callback function with password and files
- Streams all output in real-time to the browser

## Features

✅ **Minimal & Simple**: Single Flask file (`app.py`)
✅ **Auto-Detect Environments**: Scans `config/` folder for `*_*.properties` files
✅ **Password Caching**: Password cached per environment for session
✅ **Multi-File Support**: Select multiple files, processes them with one password
✅ **Real-Time Output**: All print statements visible on the app screen
✅ **Process Control**: Stop/restart execution anytime
✅ **Session Persistent**: Default environment saved across sessions

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add environment config files (if not present)
# Files like: config/uat_app.properties, config/dev_app.properties

# 3. Run the app
python run.py
```

Visit `http://localhost:5123`

## Project Structure

```
generic_flask_app/
├── app.py                       # Single Flask app file
├── templates/
│   └── index.html              # Simple UI form
├── static/
│   ├── css/style.css           # Styling
│   └── js/app.js               # Frontend + SocketIO
├── config/                     # Environment properties
│   ├── uat_app.properties
│   ├── dev_app.properties
│   └── prod_app.properties
├── run.py                       # Entry point
├── requirements.txt
└── .env
```

## How It Works

### 1. Environment Detection
App automatically scans `config/` folder for files matching pattern `*_*.properties`:
- `uat_app.properties` → shows as "UAT" in dropdown
- `dev_app.properties` → shows as "DEV" in dropdown
- `prod_app.properties` → shows as "PROD" in dropdown

### 2. User Workflow
1. **Select environment** from dropdown
2. **Enter password** (only asked once per environment per session)
3. **Select files** to process (multi-select)
4. **Click Ingest** button
5. **Watch output** in real-time as callback runs
6. **Stop/Clear** as needed

### 3. Callback Function
Your callback function receives password and files:

```python
def callback_myjob(password: str, files: list, execution_id: str):
    """
    Args:
        password: User-provided password
        files: List of selected file paths
        execution_id: Execution ID (ignore if not needed)
    """
    print(f"Processing {len(files)} files")
    for file_path in files:
        print(f"Processing: {file_path}")
        # Your logic here
        # All print statements appear on the app screen
```

## Configuration

### Add Environment Properties
Create `.properties` files in the `config/` folder:

**config/uat_app.properties:**
```properties
database.host=uat-db.example.com
database.port=5432
api.endpoint=https://uat-api.example.com
```

**config/dev_app.properties:**
```properties
database.host=localhost
database.port=5432
api.endpoint=http://localhost:8000
```

### Update Callback Function
Edit the `callback_myjob()` function in `app.py` to add your logic:

```python
def callback_myjob(password: str, files: list, execution_id: str):
    print(f"Password length: {len(password)}")

    for idx, file_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] Processing: {file_path}")

        # TODO: Replace with your actual library call
        # result = your_library.process(file_path, password)
        # print(result)
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/environments` | List available environments |
| GET | `/api/get-password/<env>` | Check if password cached |
| POST | `/api/ingest` | Start ingest job |
| POST | `/api/stop/<execution_id>` | Stop running job |

## Browser Limitation: File Paths

⚠️ **Note**: Browsers cannot pass full file paths to the backend for security reasons. You'll receive only filenames.

If you need full paths, modify the callback to prepend a base directory:

```python
def callback_myjob(password: str, files: list, execution_id: str):
    # If files = ['file1.csv', 'file2.csv']
    base_dir = "/Users/data/ingest"
    for file in files:
        full_path = os.path.join(base_dir, file)
        # Process full_path
```

## Password Lifecycle

- ✅ **Session Start**: User enters password for selected environment
- ✅ **Multi-File Run**: Same password used for all files (asked only once)
- ✅ **Session Persistence**: Password cached in Flask session for environment
- ❌ **Environment Change**: Password cleared if user selects different environment
- ❌ **App Restart**: Password cleared (not persisted to disk)

## Output Capture

All `print()` statements in `callback_myjob()` appear on the app screen in real-time:

```python
print("Starting processing...")       # Appears immediately
for file in files:
    print(f"Processing: {file}")       # Each line appears as printed
    # Your code
print("✓ Completed")                   # Final message
```

## Customization

### Change Default Port
In `run.py`:
```python
socketio.run(app, port=8000)  # Changed from 5123
```

### Modify UI
Edit `templates/index.html` and `static/css/style.css`

### Add More Fields
In `index.html`, add form fields. In `app.py` `/api/ingest`, receive them:
```python
data = request.get_json()
custom_field = data.get('custom_field', '')
```

## Troubleshooting

**Environments not showing?**
- Create `.properties` files in `config/` folder
- Naming must be: `<env>_<anything>.properties` (e.g., `uat_app.properties`)
- Restart Flask app

**Output not appearing?**
- Check browser console (F12) for JavaScript errors
- Verify SocketIO is connected (look for "Connected to server" in console)

**Password not caching?**
- Flask sessions require SECRET_KEY (already set in `.env`)
- Ensure cookies are enabled in browser

**Files showing only filenames?**
- This is browser security limitation
- Prepend base directory in callback function

## Dependencies

- **Flask 2.3.3** - Web framework
- **Flask-SocketIO 5.3.4** - Real-time communication
- **python-dotenv 1.0.0** - Environment variables
- **eventlet 0.33.3** - Async I/O

See `requirements.txt`

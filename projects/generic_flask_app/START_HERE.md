# ✅ Flask Script Runner - Simple Polling Approach

Your Flask app is **complete and ready to use**!

## 🎯 How It Works (Ultra Simple)

```
1. User clicks "Ingest"
   ↓
2. Server starts your script in background thread
   ↓
3. Script prints output: print("message here")
   ↓
4. All print() output goes to a buffer
   ↓
5. Browser asks server every 1 second: "What's new?"
   ↓
6. Server sends all new output since last poll
   ↓
7. Browser displays it immediately
```

**That's it!** No Socket.IO, no execution IDs, no queues - just a simple buffer and polling.

## 🚀 5-Minute Setup

### Step 1: Install
```bash
pip install -r requirements.txt
```

### Step 2: Run
```bash
./launcher.sh
```

### Step 3: Customize
Edit `app.py` - find `callback_myjob()` function and replace it with your code:

```python
def callback_myjob(password: str, files: list):
    """Your custom logic here"""

    print(f"Processing {len(files)} files")

    for file_path in files:
        print(f"Processing: {file_path}")

        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  File size: {size} bytes")
        else:
            print(f"  ✗ File not found")

    print("✓ Done!")
```

That's it! Your `print()` statements automatically appear in the browser.

## 📝 Key Patterns

### Simple Output
```python
print("This appears in browser immediately")
print(f"File: {file_path}")
print()  # Empty line for spacing
```

### Process Files
```python
for idx, file_path in enumerate(files, 1):
    print(f"[{idx}/{len(files)}] Processing: {file_path}")
    # Your logic here
```

### Call External Script
```python
from job_runner import run_python_script

exit_code = run_python_script(
    "./scripts/my_job.py",
    args=["--input", file_path],
    password=password
)
print(f"Script exited with code: {exit_code}")
```

### Handle Password
```python
# In external scripts:
import os
password = os.getenv('JOB_PASSWORD')

# In your Python:
print(f"Password: {'*' * len(password)}")  # Masked
```

## 🧪 Test It Now

Just run it:
```bash
./launcher.sh
```

Select files and click "Ingest" - you'll see test output stream to the browser.

## 📂 File Structure

```
app.py                 ← Edit callback_myjob() here
run.py                 ← python run.py
launcher.sh            ← ./launcher.sh
job_runner.py          ← Helper for running scripts
requirements.txt       ← pip install -r

config/
  ├─ dev_app.properties
  ├─ uat_app.properties
  └─ prod_app.properties

scripts/
  └─ example_job.py    ← Your scripts here

static/
  ├─ css/style.css
  └─ js/app.js         ← Browser polls every 1 second

templates/
  └─ index.html
```

## ✨ Features

✅ All stdout/stderr visible in browser in real-time
✅ Simple buffer approach (no Socket.IO)
✅ Browser polls every 1 second
✅ Multiple file processing
✅ Password masking
✅ Stop button
✅ Environment detection
✅ External script support
✅ Error handling

## 📚 Documentation

- **This file** - Quick start
- **IMPLEMENTATION_GUIDE.md** - Step-by-step examples
- **ARCHITECTURE.md** - Technical details

## 🚀 You're Ready!

```bash
pip install -r requirements.txt
./launcher.sh
```

Edit `callback_myjob()` in `app.py` with your code. Users will see all output in real-time.

---

**Status**: ✅ Complete & Ready
**Approach**: Simple buffer + polling
**Polling interval**: 1 second
**No external dependencies**: Just Flask

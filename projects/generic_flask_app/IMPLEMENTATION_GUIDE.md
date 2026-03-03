# Implementation Guide: Simple Polling Approach

## Overview

Your Flask app uses a **simple polling mechanism** for real-time output:

1. **Backend**: All output goes to a shared buffer
2. **Browser**: Polls `/api/stream_event` every 1 second
3. **Display**: Shows new content since last poll

**No Socket.IO, no SSE, no execution IDs - just simple polling!**

## Architecture

```
App starts
    ↓
User clicks "Ingest"
    ↓
/api/ingest creates thread and returns
    ↓
Browser starts polling /api/stream_event every 1 second
    ↓
Thread runs: callback_myjob(password, files)
    └─ print() → global buffer
    ↓
Browser polling loop:
    fetch(/api/stream_event)
    ↓ Returns: {output: [...], is_running: true/false}
    ↓
Display new lines
    ↓
When is_running=false, stop polling
```

## How Output Works

### Global Buffer
```python
# In app.py
output_buffer = []  # Global list
buffer_lock = threading.Lock()  # Thread-safe access

def add_output(text: str):
    """Add to buffer (thread-safe)"""
    with buffer_lock:
        output_buffer.append(text)
```

### Capture
```python
class BufferCapture:
    def write(self, text: str):
        # Write to terminal
        self.original_stdout.write(text)
        # Write to buffer
        add_output(text.rstrip())
```

### Polling
```python
# Browser JavaScript
setInterval(async () => {
    const response = await fetch('/api/stream_event');
    const data = response.json();

    // data.output is the full buffer
    // data.is_running is true/false

    // Display new lines since last poll
    for (let i = lastOutputCount; i < data.output.length; i++) {
        displayLine(data.output[i]);
    }
    lastOutputCount = data.output.length;

    // If done, stop polling
    if (!data.is_running) {
        clearInterval(pollInterval);
    }
}, 1000);  // Every 1 second
```

## Complete Example

### Your Custom Job (callback_myjob in app.py)

```python
def callback_myjob(password: str, files: list):
    """
    Process files with password.
    All print() statements appear in browser.
    """
    print(f"Starting job")
    print(f"Files: {len(files)}")
    print(f"Password: {'*' * len(password)}")
    print()

    success = 0
    failed = 0

    for idx, file_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {file_path}")

        try:
            # Check file exists
            if not os.path.exists(file_path):
                print(f"  ✗ File not found")
                failed += 1
                continue

            # Process it
            size = os.path.getsize(file_path)
            print(f"  Size: {size} bytes")

            # Call external script
            from job_runner import run_python_script
            exit_code = run_python_script(
                "./scripts/ingest.py",
                args=["--input", file_path],
                password=password
            )

            if exit_code == 0:
                print(f"  ✓ Success")
                success += 1
            else:
                print(f"  ✗ Failed (code {exit_code})")
                failed += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

        print()

    # Summary
    print("=" * 60)
    print(f"Results: {success} succeeded, {failed} failed")
    print("=" * 60)
```

### External Script (scripts/ingest.py)

```python
#!/usr/bin/env python
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()

    file_path = args.input
    password = os.getenv('JOB_PASSWORD')

    print(f"Processing: {file_path}")
    print(f"Password length: {len(password)}")

    try:
        # Your processing logic
        with open(file_path, 'r') as f:
            lines = f.readlines()

        print(f"✓ Read {len(lines)} lines")
        print(f"✓ Processing complete")
        return 0

    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

## API Endpoints

### POST /api/ingest
Start job execution

**Request:**
```json
{
    "password": "mypassword",
    "files": ["/path/to/file1", "/path/to/file2"],
    "environment": "dev"
}
```

**Response:**
```json
{
    "success": true
}
```

Server starts background thread running `callback_myjob()`

### GET /api/stream_event
Get current output buffer (browser polls this)

**Response:**
```json
{
    "output": [
        "=== Job Started ===",
        "Password: ****",
        "Files: 2",
        "[1/2] /path/to/file1",
        "  File size: 1234 bytes",
        "[2/2] /path/to/file2",
        "  ✗ File not found!"
    ],
    "is_running": false
}
```

Browser only displays new lines since last poll (tracked by `lastOutputCount`).

### POST /api/stop
Stop execution

**Response:**
```json
{"success": true}
```

Adds ">>> Execution stopped by user" to buffer.

## Code Flow

### 1. User Clicks Ingest (JavaScript)
```javascript
// app.js: startIngest()
const response = await fetch('/api/ingest', {
    method: 'POST',
    body: JSON.stringify({password, files, environment})
});

// Start polling
isRunning = true;
startPolling();  // Sets up interval
```

### 2. Server Receives Request (Python)
```python
# app.py: ingest()
clear_output()  # Clear old output
thread = threading.Thread(
    target=run_job,
    args=(password, files),
    daemon=True
)
thread.start()
return jsonify({'success': True})
```

### 3. Job Runs in Thread (Python)
```python
# app.py: run_job()
capture = BufferCapture()  # Redirect stdout
sys.stdout = capture

callback_myjob(password, files)  # Your code

sys.stdout = old_stdout  # Restore
is_running = False  # Signal completion
```

### 4. Browser Polls (JavaScript)
```javascript
// app.js: startPolling()
setInterval(async () => {
    const response = await fetch('/api/stream_event');
    const data = await response.json();

    // Display new lines
    for (let i = lastOutputCount; i < data.output.length; i++) {
        addOutputLine(data.output[i]);
    }
    lastOutputCount = data.output.length;

    // Stop when done
    if (!data.is_running) {
        clearInterval(pollInterval);
        isRunning = false;
    }
}, 1000);  // Every 1 second
```

## Testing

### Test 1: Basic Output
```python
def callback_myjob(password: str, files: list):
    print("Test 1")
    print("Test 2")
    print("Test 3")
```

**Expected**: All 3 lines appear in browser within 1 second.

### Test 2: With Files
```python
def callback_myjob(password: str, files: list):
    for i, file in enumerate(files, 1):
        print(f"File {i}: {file}")
```

**Expected**: Each file listed.

### Test 3: External Script
```python
def callback_myjob(password: str, files: list):
    from job_runner import run_python_script

    run_python_script(
        "./scripts/example_job.py",
        args=["--input", files[0]],
        password=password
    )
```

**Expected**: All output from script appears.

### Test 4: Exception
```python
def callback_myjob(password: str, files: list):
    print("About to fail...")
    raise ValueError("Test error")
```

**Expected**: Error and traceback appear in browser.

## Polling Characteristics

### Advantages
- ✅ Ultra simple
- ✅ No connection state to manage
- ✅ Works with any frontend framework
- ✅ Survives network glitches
- ✅ Easy to debug

### Latency
- Polling interval: 1 second
- Max latency: ~1 second (until next poll)
- Normal: <200ms from print to display

### Performance
- Throughput: Unlimited
- CPU: Minimal (1 poll/second)
- Network: Minimal (~1KB per poll)

## Customization

### Change Polling Interval
In `static/js/app.js`, find `startPolling()`:
```javascript
pollInterval = setInterval(async () => {
    // ...
}, 1000);  // Change this: 500 = faster, 2000 = slower
```

### Limit Buffer Size
In `app.py`, after line with `add_output()`:
```python
def add_output(text: str):
    global output_buffer
    with buffer_lock:
        output_buffer.append(text)
        # Keep only last 1000 lines
        if len(output_buffer) > 1000:
            output_buffer = output_buffer[-1000:]
```

### Add Filtering
```python
class BufferCapture:
    def write(self, text: str):
        self.original_stdout.write(text)

        # Only capture lines with "ERROR" or "✓"
        if 'ERROR' in text or '✓' in text:
            add_output(text.rstrip())
```

## Troubleshooting

### Output not appearing
1. Check that `print()` is being called
2. Check browser console for errors
3. Check Flask logs
4. Try refreshing page

### Slow output
- Normal: ~1 second latency (polling interval)
- If slower: Check network or Flask logs

### Multiple jobs interfere
- Current design: Only one job at a time
- All output goes to same buffer
- To support multiple: Would need separate buffers per job

### Stop button doesn't work
- The stop flag is set, but callback must finish naturally
- Add delays/checks to make it responsive:
```python
import time
for item in long_list:
    time.sleep(0.1)  # Allows stop signal to work
    process(item)
```

## Performance Notes

| Metric | Value |
|--------|-------|
| Polling interval | 1 second |
| Max latency | ~1 second |
| Throughput | Unlimited |
| Memory/buffer | ~10KB per 1000 lines |
| Network/poll | ~1-5KB |
| CPU overhead | Minimal |

## Next Steps

1. Edit `callback_myjob()` in `app.py`
2. Test with `./launcher.sh`
3. Create scripts in `scripts/` folder
4. Share `launcher.sh` with users

---

**Approach**: Simple polling
**Framework**: Flask
**Complexity**: Minimal
**Dependencies**: 3

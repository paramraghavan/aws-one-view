# Troubleshooting Dashboard Access Issues

If the web dashboard isn't showing at port 5000, follow these steps:

## Step 1: Verify the Application is Running

Check the console output when you start the app. You should see:

```
🚀 Snowflake Database Sync Dashboard Starting...
📊 Dashboard URL: http://localhost:5000
📊 Dashboard URL: http://127.0.0.1:5000
📊 Network URL: http://0.0.0.0:5000
```

## Step 2: Test Different URLs

Try these URLs in your browser:

1. **http://localhost:5000/test** - Simple test page
2. **http://127.0.0.1:5000/test** - Alternative localhost
3. **http://localhost:5000/health** - Health check API
4. **http://localhost:5000/** - Main dashboard

## Step 3: Check Port Availability

Run these commands to check if port 5000 is in use:

### Windows:

```cmd
netstat -an | findstr :5000
```

### Linux/Mac:

```bash
netstat -tuln | grep :5000
# or
lsof -i :5000
```

## Step 4: Check for Port Conflicts

If port 5000 is busy, modify the app to use a different port:

```python
# In app.py, change the port number:
app.run(
    debug=False,
    host='0.0.0.0',
    port=5001,  # Use different port
    use_reloader=False,
    threaded=True
)
```

## Step 5: Check Firewall/Security Software

- **Windows**: Check Windows Defender Firewall
- **Mac**: Check System Preferences > Security & Privacy > Firewall
- **Linux**: Check iptables or ufw rules
- **Antivirus**: Some antivirus software blocks local web servers

## Step 6: Verify Templates Directory

Make sure you have this directory structure:

```
your-app-directory/
├── app.py
├── config.yaml
├── templates/
│   └── index.html
└── requirements.txt
```

If the `templates/` directory or `index.html` is missing, the app will show an error page but should still work
at `/test`.

## Step 7: Check Console for Errors

Look for error messages in the console output such as:

- `Address already in use`
- `Permission denied`
- `Template not found`
- `Configuration error`

## Step 8: Try Alternative Start Methods

### Method 1: Direct Flask Run

```bash
export FLASK_APP=app.py
flask run --host=0.0.0.0 --port=5000
```

### Method 2: Python Module

```bash
python -m flask --app app run --host=0.0.0.0 --port=5000
```

### Method 3: Different Port

```bash
python app.py
# Then try http://localhost:5001 if you changed the port
```

## Step 9: Minimal Test

Create a simple test file (`test_flask.py`) to verify Flask works:

```python
from flask import Flask

app = Flask(__name__)


@app.route('/')
def hello():
    return '<h1>Flask is working!</h1><p>Port 5000 is accessible.</p>'


if __name__ == '__main__':
    print("Starting test Flask app on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
```

Run: `python test_flask.py`

## Step 10: Check Network Configuration

If running on a remote server or VM:

1. **Check if the server allows external connections on port 5000**
2. **Update security groups/firewall rules**
3. **Use the server's external IP address instead of localhost**

## Common Solutions:

### Issue: "Address already in use"

**Solution**: Another application is using port 5000

```bash
# Kill the process using port 5000
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F

# Linux/Mac:
sudo lsof -t -i tcp:5000 | xargs kill -9
```

### Issue: Template not found

**Solution**: Create the templates directory and copy index.html

```bash
mkdir templates
# Copy the index.html file to templates/index.html
```

### Issue: Permission denied

**Solution**: Run with different port or as administrator

```bash
# Try port above 1024
python app.py  # and change port to 8000 in code
```

### Issue: Browser shows "This site can't be reached"

**Solution**:

1. Check if app is actually running (look for console output)
2. Try 127.0.0.1 instead of localhost
3. Check browser proxy settings
4. Try different browser or incognito mode

## Debug Mode

Enable debug mode temporarily to see detailed error messages:

```python
# In app.py, temporarily change:
app.run(
    debug=True,  # Enable debug mode
    host='0.0.0.0',
    port=5000,
    use_reloader=False,
    threaded=True
)
```


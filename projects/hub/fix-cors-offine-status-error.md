The issue you're experiencing is likely due to how CORS affects your Flask app's behavior when handling requests from the same server versus different servers. Here are a few solutions to fix this:The issue you're experiencing is common when CORS is added to Flask apps. Here's what's happening and how to fix it:

## Root Cause:
When you add CORS to Flask, it can interfere with same-server requests because:
1. **Preflight requests** - CORS may trigger OPTIONS requests first
2. **Header requirements** - Missing or incorrect headers can cause failures
3. **Origin restrictions** - Same-server requests might be blocked by CORS policies

## Solutions:

### 1. **Immediate Fix - Use the Enhanced Status Check**
The code above provides multiple fallback methods:
- Tries direct HTTP with proper headers
- Falls back to socket connection testing
- Attempts localhost URL variations
- Handles local vs remote URLs differently

### 2. **Add Dedicated Health Endpoints**
Add these to your Flask apps:
```python
@app.route('/health', methods=['GET'])
def health_check():
    return {'status': 'healthy'}, 200

@app.route('/status', methods=['GET']) 
def status_check():
    return {'status': 'online'}, 200
```

### 3. **Fix CORS Configuration**
Make sure your CORS is configured to allow health checks:
```python
from flask_cors import CORS

CORS(app, resources={
    r"/health": {"origins": "*", "methods": ["GET"]},
    r"/status": {"origins": "*", "methods": ["GET"]}
})
```

### 4. **Quick Test**
Replace your current function with:
```python
def check_app_status(url):
    try:
        headers = {'User-Agent': 'Internal-Status-Check'}
        response = requests.get(url, timeout=5, headers=headers)
        return 'online' if response.status_code == 200 else 'offline'
    except:
        # Fallback: try socket connection for local URLs
        if 'localhost' in url or '127.0.0.1' in url:
            try:
                import socket
                from urllib.parse import urlparse
                parsed = urlparse(url)
                port = parsed.port or 5000
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(3)
                    result = sock.connect_ex(('localhost', port))
                    return 'online' if result == 0 else 'offline'
            except:
                pass
        return 'offline'
```


import requests
from urllib.parse import urlparse
import socket


def check_app_status(url):
    """Check if a Flask app is running with CORS considerations"""
    try:
        # Parse the URL to determine if it's local or remote
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)

        # Check if this is a local URL
        is_local = is_local_url(host)

        if is_local:
            # For local URLs, try multiple approaches
            return check_local_app_status(url, host, port)
        else:
            # For remote URLs, use standard HTTP request
            return check_remote_app_status(url)

    except Exception as e:
        print(f"Error checking app status for {url}: {e}")
        return 'offline'


def is_local_url(host):
    """Determine if a URL is pointing to localhost/same server"""
    if not host:
        return True

    local_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']

    # Check if it's an explicit local host
    if host.lower() in local_hosts:
        return True

    # Check if it's the same as current server's hostname/IP
    try:
        current_ip = socket.gethostbyname(socket.gethostname())
        target_ip = socket.gethostbyname(host)
        return current_ip == target_ip
    except:
        return False


def check_local_app_status(url, host, port):
    """Check status for local apps with multiple fallback methods"""

    # Method 1: Try direct HTTP request with headers that bypass CORS issues
    try:
        headers = {
            'User-Agent': 'Internal-Status-Check',
            'Accept': 'text/html,application/json,*/*',
            'Cache-Control': 'no-cache'
        }
        response = requests.get(url, timeout=5, headers=headers)
        if response.status_code == 200:
            return 'online'
    except requests.exceptions.RequestException:
        pass

    # Method 2: Try a simple socket connection to check if port is open
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            if result == 0:
                # Port is open, but let's try HTTP again with different approach
                try:
                    # Try with session to handle cookies/redirects better
                    session = requests.Session()
                    session.headers.update({
                        'Origin': f"http://{host}:{port}",
                        'Referer': f"http://{host}:{port}"
                    })
                    response = session.get(url, timeout=3)
                    return 'online' if response.status_code == 200 else 'partial'
                except:
                    return 'partial'  # Port open but HTTP not responding properly
    except:
        pass

    # Method 3: Try different URL variations
    try:
        # Try with explicit localhost
        local_url = url.replace(host, 'localhost')
        response = requests.get(local_url, timeout=3)
        return 'online' if response.status_code == 200 else 'offline'
    except:
        pass

    return 'offline'


def check_remote_app_status(url):
    """Check status for remote apps"""
    try:
        headers = {
            'User-Agent': 'Status-Check-Bot/1.0',
            'Accept': '*/*'
        }
        response = requests.get(url, timeout=10, headers=headers)
        return 'online' if response.status_code == 200 else 'offline'
    except requests.exceptions.RequestException:
        return 'offline'


# Alternative simpler approach - Create a dedicated health check endpoint
def create_health_check_endpoint(app):
    """Add a dedicated health check endpoint that bypasses CORS"""

    @app.route('/health', methods=['GET'])
    def health_check():
        """Simple health check endpoint"""
        return {'status': 'healthy', 'timestamp': int(time.time())}, 200

    @app.route('/status', methods=['GET'])
    def status_check():
        """More detailed status endpoint"""
        return {
            'status': 'online',
            'service': 'flask-app',
            'version': '1.0.0',
            'timestamp': int(time.time())
        }, 200


# Flask app configuration example with proper CORS setup
def configure_flask_app_with_cors():
    """Example of how to properly configure Flask with CORS"""
    from flask import Flask
    from flask_cors import CORS
    import time

    app = Flask(__name__)

    # Configure CORS properly
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Configure this to your specific domains in production
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        },
        r"/health": {
            "origins": "*",
            "methods": ["GET"]
        },
        r"/status": {
            "origins": "*",
            "methods": ["GET"]
        }
    })

    # Add health check endpoints
    create_health_check_endpoint(app)

    return app


# Usage example
def monitor_multiple_apps():
    """Example of monitoring multiple apps"""
    apps_to_monitor = [
        'http://localhost:5000/health',  # Local app
        'http://127.0.0.1:8080/status',  # Another local app
        'http://your-server.com:5000/health',  # Remote app
        'https://api.example.com/status'  # Remote HTTPS app
    ]

    results = {}
    for app_url in apps_to_monitor:
        status = check_app_status(app_url)
        results[app_url] = status
        print(f"{app_url}: {status}")

    return results


# Enhanced status check with retry logic
def check_app_status_with_retry(url, max_retries=3, delay=1):
    """Check app status with retry logic"""
    import time

    for attempt in range(max_retries):
        status = check_app_status(url)
        if status == 'online':
            return status

        if attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 2  # Exponential backoff

    return 'offline'


if __name__ == "__main__":
    # Test the monitoring
    monitor_multiple_apps()
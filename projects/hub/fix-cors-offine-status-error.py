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

    try:
        # Get current server's IP addresses
        current_hostname = socket.gethostname()
        current_fqdn = socket.getfqdn()

        # Get all possible IPs for current server
        current_ips = set()
        try:
            current_ips.add(socket.gethostbyname(current_hostname))
            current_ips.add(socket.gethostbyname(current_fqdn))
            # Also get all network interfaces
            import netifaces
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        current_ips.add(addr['addr'])
        except ImportError:
            # netifaces not available, use basic approach
            current_ips.add(socket.gethostbyname(current_hostname))
        except:
            pass

        # Check if target host resolves to any of our IPs
        try:
            target_ip = socket.gethostbyname(host)
            if target_ip in current_ips:
                return True
        except:
            pass

        # Check if hostname matches
        if host.lower() in [current_hostname.lower(), current_fqdn.lower()]:
            return True

    except Exception as e:
        print(f"Error determining if {host} is local: {e}")

    return False


def check_local_app_status(url, host, port):
    """Check status for local/same-server apps with multiple fallback methods"""

    # Method 1: Try direct HTTP request with headers that bypass CORS issues
    try:
        headers = {
            'User-Agent': 'Internal-Status-Check',
            'Accept': 'text/html,application/json,*/*',
            'Cache-Control': 'no-cache',
            'Connection': 'close'  # Avoid connection pooling issues
        }
        response = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
        if response.status_code == 200:
            return 'online'
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed for {url}: {e}")

    # Method 2: Socket connection test (works for any same-server app regardless of CORS)
    print(f"Trying socket connection to {host}:{port}")
    try:
        # Try to resolve host first
        resolved_ip = socket.gethostbyname(host)
        print(f"Resolved {host} to {resolved_ip}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            result = sock.connect_ex((resolved_ip, port))
            if result == 0:
                print(f"Socket connection successful to {host}:{port}")
                # Port is open, try HTTP again with different approaches

                # Try with the resolved IP
                try:
                    ip_url = url.replace(host, resolved_ip)
                    response = requests.get(ip_url, timeout=3, headers={'Host': host})
                    if response.status_code == 200:
                        return 'online'
                except:
                    pass

                # Try with session and different headers
                try:
                    session = requests.Session()
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Internal Status Check)',
                        'Accept': '*/*'
                    })
                    response = session.get(url, timeout=3)
                    if response.status_code == 200:
                        return 'online'
                except:
                    pass

                return 'partial'  # Port open but HTTP not responding properly
            else:
                print(f"Socket connection failed to {host}:{port} with error code {result}")
    except Exception as e:
        print(f"Socket connection error: {e}")

    # Method 3: Try localhost variations for same-server apps
    if host not in ['localhost', '127.0.0.1']:
        try:
            print("Trying localhost fallback")
            local_url = url.replace(host, 'localhost')
            response = requests.get(local_url, timeout=3)
            if response.status_code == 200:
                return 'online'
        except Exception as e:
            print(f"Localhost fallback failed: {e}")

        try:
            print("Trying 127.0.0.1 fallback")
            local_url = url.replace(host, '127.0.0.1')
            response = requests.get(local_url, timeout=3)
            if response.status_code == 200:
                return 'online'
        except Exception as e:
            print(f"127.0.0.1 fallback failed: {e}")

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


# Quick and simple version for immediate use
def quick_check_app_status(url):
    """Simplified version that handles CORS issues for same-server apps"""
    try:
        # First try normal HTTP request
        headers = {'User-Agent': 'Internal-Status-Check'}
        response = requests.get(url, timeout=5, headers=headers)
        return 'online' if response.status_code == 200 else 'offline'
    except:
        # Fallback: try socket connection for same-server URLs
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)

            # Check if this might be same server
            is_same_server = (
                    host in ['localhost', '127.0.0.1', '0.0.0.0'] or
                    host == socket.gethostname() or
                    host == socket.getfqdn()
            )

            if is_same_server or True:  # Try socket fallback for any failed HTTP request
                print(f"Trying socket fallback for {host}:{port}")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(3)
                    try:
                        resolved_ip = socket.gethostbyname(host)
                        result = sock.connect_ex((resolved_ip, port))
                        return 'online' if result == 0 else 'offline'
                    except:
                        # If hostname resolution fails, try localhost
                        result = sock.connect_ex(('localhost', port))
                        return 'online' if result == 0 else 'offline'
        except:
            pass

        return 'offline'


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


# Usage example
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
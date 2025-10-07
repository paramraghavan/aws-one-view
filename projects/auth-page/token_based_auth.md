# Flask Token-Based Authentication with Auth Servers

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding Token-Based Authentication](#understanding-token-based-authentication)
3. [OAuth 2.0 and OpenID Connect](#oauth-20-and-openid-connect)
4. [JWT Tokens Explained](#jwt-tokens-explained)
5. [Implementation Options](#implementation-options)
6. [Auth0 Implementation](#auth0-implementation)
7. [Azure AD Implementation](#azure-ad-implementation)
8. [Google OAuth Implementation](#google-oauth-implementation)
9. [Custom JWT Implementation](#custom-jwt-implementation)
10. [Security Best Practices](#security-best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

Token-based authentication is a modern approach to securing web applications and APIs. Instead of maintaining session
state on the server, tokens carry all necessary authentication information, making applications more scalable and
suitable for distributed systems.

### Why Use Tokens Instead of Sessions?

| Feature       | Session-Based                    | Token-Based                     |
|---------------|----------------------------------|---------------------------------|
| State         | Stateful (server stores session) | Stateless (token contains info) |
| Scalability   | Requires sticky sessions         | Works across multiple servers   |
| Mobile Apps   | Difficult                        | Native support                  |
| APIs          | Limited                          | Excellent                       |
| Cross-domain  | Requires CORS setup              | Works seamlessly                |
| Microservices | Challenging                      | Ideal                           |

---

## Understanding Token-Based Authentication

### The Authentication Flow

```
┌─────────┐                ┌──────────────┐                ┌─────────────┐
│         │   1. Login     │              │   2. Validate  │             │
│  User   │──────────────> │ Auth Server  │──────────────> │  Database   │
│         │                │  (Auth0/     │                │             │
└─────────┘                │  Azure/etc)  │                └─────────────┘
     │                     └──────────────┘                       │
     │                            │                               │
     │     3. Return Tokens       │         4. Credentials OK     │
     │<───────────────────────────┤<──────────────────────────────┘
     │                            │
     │                            │
     │   5. Request with Token    │
     │──────────────────────────> │
     │                            │
     │                     ┌──────▼─────┐
     │   6. Protected      │            │
     │      Resource       │   Flask    │
     │<────────────────────│    App     │
                           │            │
                           └────────────┘
```

### Key Components

1. **Access Token**: Short-lived token (15-60 minutes) used to access protected resources
2. **Refresh Token**: Long-lived token (days/weeks) used to get new access tokens
3. **ID Token**: Contains user identity information (OpenID Connect)
4. **Token Validation**: Verifying token signature and claims

---

## OAuth 2.0 and OpenID Connect

### OAuth 2.0

OAuth 2.0 is an **authorization** framework that allows applications to obtain limited access to user accounts.

**Grant Types:**

- Authorization Code (most secure, for web apps)
- Implicit (deprecated, previously for SPAs)
- Client Credentials (machine-to-machine)
- Resource Owner Password (use sparingly)

### OpenID Connect (OIDC)

OIDC is an **authentication** layer built on top of OAuth 2.0. It adds:

- ID tokens (JWT format)
- UserInfo endpoint
- Standard claims (name, email, etc.)

**Why Use OIDC?**

- Standardized authentication
- Built-in token validation
- User profile information
- Single Sign-On (SSO) support

---

## JWT Tokens Explained

### What is JWT?

JSON Web Token (JWT) is a compact, URL-safe token format containing three parts:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

[Header].[Payload].[Signature]
```

### JWT Structure

#### 1. Header

```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "key-id-123"
}
```

#### 2. Payload (Claims)

```json
{
  "sub": "user-id-123",
  "name": "John Doe",
  "email": "john@example.com",
  "roles": [
    "admin",
    "user"
  ],
  "iat": 1516239022,
  "exp": 1516242622,
  "iss": "https://your-auth-server.com"
}
```

**Standard Claims:**

- `sub` - Subject (user identifier)
- `iat` - Issued at (timestamp)
- `exp` - Expiration time
- `iss` - Issuer
- `aud` - Audience

#### 3. Signature

```
HMACSHA256(
  base64UrlEncode(header) + "." +
  base64UrlEncode(payload),
  secret
)
```

### Token Validation Steps

1. **Verify signature** - Ensure token hasn't been tampered with
2. **Check expiration** - Ensure token is still valid
3. **Validate issuer** - Confirm token came from trusted source
4. **Verify audience** - Ensure token is for your application
5. **Check custom claims** - Validate any application-specific claims

---

## Implementation Options

### Comparison of Auth Providers

| Provider    | Best For                     | Complexity | Cost                |
|-------------|------------------------------|------------|---------------------|
| Auth0       | Modern apps, quick setup     | Low        | Free tier available |
| Azure AD    | Enterprise, Office 365       | Medium     | Included with M365  |
| Google      | Google Workspace             | Low        | Free                |
| Okta        | Enterprise SSO               | Medium     | Paid                |
| AWS Cognito | AWS ecosystem                | Medium     | Pay per user        |
| Custom JWT  | Full control, specific needs | High       | Free (DIY)          |

---

## Auth0 Implementation

### Setup Steps

#### 1. Install Dependencies

```bash
pip install authlib requests flask-cors pyjwt cryptography
```

#### 2. Create Auth0 Application

1. Go to [Auth0 Dashboard](https://manage.auth0.com)
2. Create new Application (Regular Web Application)
3. Note: Domain, Client ID, Client Secret
4. Set Allowed Callback URLs: `http://localhost:5000/callback`
5. Set Allowed Logout URLs: `http://localhost:5000`

#### 3. Flask Implementation

```python
from flask import Flask, redirect, request, session, jsonify
from authlib.integrations.flask_client import OAuth
from functools import wraps
import jwt
from urllib.request import urlopen
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Auth0 Configuration
AUTH0_DOMAIN = 'your-tenant.auth0.com'
AUTH0_CLIENT_ID = 'your-client-id'
AUTH0_CLIENT_SECRET = 'your-client-secret'
AUTH0_CALLBACK_URL = 'http://localhost:5000/callback'
AUTH0_AUDIENCE = 'your-api-identifier'

# Initialize OAuth
oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=f'https://{AUTH0_DOMAIN}',
    access_token_url=f'https://{AUTH0_DOMAIN}/oauth/token',
    authorize_url=f'https://{AUTH0_DOMAIN}/authorize',
    client_kwargs={'scope': 'openid profile email'},
    server_metadata_url=f'https://{AUTH0_DOMAIN}/.well-known/openid-configuration'
)


def verify_token(token):
    """Verify JWT token from Auth0"""
    try:
        # Get Auth0 public keys
        jsonurl = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
        jwks = json.loads(jsonurl.read())

        # Get key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}

        for key in jwks['keys']:
            if key['kid'] == unverified_header['kid']:
                rsa_key = {
                    'kty': key['kty'],
                    'kid': key['kid'],
                    'use': key['use'],
                    'n': key['n'],
                    'e': key['e']
                }

        if rsa_key:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=['RS256'],
                audience=AUTH0_AUDIENCE,
                issuer=f'https://{AUTH0_DOMAIN}/'
            )
            return payload

        raise Exception('Unable to find appropriate key')

    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.JWTClaimsError:
        raise Exception('Invalid claims')
    except Exception as e:
        raise Exception(f'Unable to parse token: {str(e)}')


def requires_auth(f):
    """Decorator to require authentication"""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        parts = auth_header.split()
        if parts[0].lower() != 'bearer' or len(parts) != 2:
            return jsonify({'error': 'Invalid authorization header'}), 401

        token = parts[1]

        try:
            payload = verify_token(token)
            request.user = payload
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401

    return decorated


def requires_scope(required_scope):
    """Decorator to check permissions/scopes"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token_scopes = request.user.get('scope', '').split()
            if required_scope not in token_scopes:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Web Routes (Session-based)
@app.route('/login')
def login():
    """Redirect to Auth0 login page"""
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL)


@app.route('/callback')
def callback():
    """Handle Auth0 callback"""
    try:
        token = auth0.authorize_access_token()
        session['access_token'] = token['access_token']
        session['id_token'] = token['id_token']

        user_info = auth0.get('userinfo').json()
        session['user'] = user_info

        return redirect('/dashboard')
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(
        f'https://{AUTH0_DOMAIN}/v2/logout?'
        f'client_id={AUTH0_CLIENT_ID}&'
        f'returnTo=http://localhost:5000/'
    )


@app.route('/dashboard')
def dashboard():
    """Protected web page"""
    if 'user' not in session:
        return redirect('/login')
    return jsonify(user=session['user'])


# API Routes (Token-based)
@app.route('/api/protected')
@requires_auth
def api_protected():
    """Protected API endpoint"""
    return jsonify({
        'message': 'This is a protected endpoint',
        'user': request.user
    })


@app.route('/api/admin')
@requires_auth
@requires_scope('admin:access')
def api_admin():
    """Admin-only endpoint"""
    return jsonify({
        'message': 'Admin access granted',
        'user': request.user
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

#### 4. Frontend Integration

**HTML Login Button:**

```html
<a href="/login" class="btn btn-primary">Login with Auth0</a>
```

**JavaScript API Call:**

```javascript
const accessToken = localStorage.getItem('access_token');

fetch('/api/protected', {
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    }
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

---

## Azure AD Implementation

### Setup Steps

#### 1. Register Application in Azure

1. Go to [Azure Portal](https://portal.azure.com)
2. Azure Active Directory → App registrations → New registration
3. Set Redirect URI: `http://localhost:5000/callback`
4. Create client secret in Certificates & secrets
5. Note: Application (client) ID, Directory (tenant) ID, Client secret

#### 2. Install Dependencies

```bash
pip install msal requests pyjwt
```

#### 3. Flask Implementation

```python
from flask import Flask, redirect, request, session, jsonify
from msal import ConfidentialClientApplication
import requests
from functools import wraps
import jwt
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Azure AD Configuration
AZURE_CLIENT_ID = 'your-client-id'
AZURE_CLIENT_SECRET = 'your-client-secret'
AZURE_TENANT_ID = 'your-tenant-id'
AZURE_REDIRECT_URI = 'http://localhost:5000/callback'
AZURE_AUTHORITY = f'https://login.microsoftonline.com/{AZURE_TENANT_ID}'
AZURE_SCOPE = ['User.Read']

# Create MSAL app
msal_app = ConfidentialClientApplication(
    AZURE_CLIENT_ID,
    authority=AZURE_AUTHORITY,
    client_credential=AZURE_CLIENT_SECRET
)


def validate_azure_token(token):
    """Validate Azure AD token"""
    try:
        # Get Azure AD public keys
        jwks_uri = f'{AZURE_AUTHORITY}/discovery/v2.0/keys'
        jwks = requests.get(jwks_uri).json()

        unverified_header = jwt.get_unverified_header(token)

        # Find the right key
        rsa_key = None
        for key in jwks['keys']:
            if key['kid'] == unverified_header['kid']:
                rsa_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break

        if not rsa_key:
            raise Exception('Public key not found')

        # Decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=['RS256'],
            audience=AZURE_CLIENT_ID,
            issuer=f'{AZURE_AUTHORITY}/v2.0'
        )

        return payload

    except Exception as e:
        raise Exception(f'Token validation failed: {str(e)}')


def requires_azure_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]

        try:
            payload = validate_azure_token(token)
            request.user = payload
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401

    return decorated


@app.route('/login')
def login():
    """Initiate Azure AD login"""
    auth_url = msal_app.get_authorization_request_url(
        AZURE_SCOPE,
        redirect_uri=AZURE_REDIRECT_URI
    )
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Handle Azure AD callback"""
    code = request.args.get('code')

    if not code:
        return jsonify({'error': 'No authorization code'}), 400

    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=AZURE_SCOPE,
        redirect_uri=AZURE_REDIRECT_URI
    )

    if 'error' in result:
        return jsonify(result), 400

    session['access_token'] = result['access_token']
    session['id_token'] = result.get('id_token')

    # Get user info from Microsoft Graph
    headers = {'Authorization': f'Bearer {result["access_token"]}'}
    user_info = requests.get(
        'https://graph.microsoft.com/v1.0/me',
        headers=headers
    ).json()

    session['user'] = user_info

    return redirect('/dashboard')


@app.route('/api/protected')
@requires_azure_auth
def protected():
    return jsonify({
        'message': 'Protected resource',
        'user': request.user
    })
```

---

## Google OAuth Implementation

### Setup Steps

#### 1. Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. Add authorized redirect URI: `http://localhost:5000/callback`
5. Download credentials JSON

#### 2. Install Dependencies

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2
```

#### 3. Flask Implementation

```python
from flask import Flask, redirect, request, session, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Google OAuth Configuration
GOOGLE_CLIENT_ID = 'your-client-id.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'your-client-secret'
GOOGLE_REDIRECT_URI = 'http://localhost:5000/callback'

# Disable HTTPS check for local development only
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# OAuth 2.0 flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI]
        }
    },
    scopes=['openid', 'email', 'profile']
)
flow.redirect_uri = GOOGLE_REDIRECT_URI


def verify_google_token(token):
    """Verify Google ID token"""
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer')

        return idinfo

    except Exception as e:
        raise Exception(f'Token verification failed: {str(e)}')


def requires_google_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]

        try:
            user_info = verify_google_token(token)
            request.user = user_info
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401

    return decorated


@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)


@app.route('/callback')
def callback():
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    session['access_token'] = credentials.token
    session['id_token'] = credentials.id_token

    user_info = verify_google_token(credentials.id_token)
    session['user'] = user_info

    return redirect('/dashboard')


@app.route('/api/protected')
@requires_google_auth
def protected():
    return jsonify({
        'message': 'Protected resource',
        'user': request.user
    })
```

---

## Custom JWT Implementation

### When to Use Custom JWT

- Full control over token structure
- Internal microservices
- No external dependencies
- Specific security requirements

### Implementation

```python
from flask import Flask, request, jsonify
from functools import wraps
import jwt
from datetime import datetime, timedelta

app = Flask(__name__)

# JWT Configuration
JWT_SECRET = 'your-jwt-secret-key-change-this'
JWT_ALGORITHM = 'HS256'
JWT_ISSUER = 'your-app-name'


def create_token(user_id, email, roles=None):
    """Create JWT token"""
    payload = {
        'sub': user_id,
        'email': email,
        'roles': roles or [],
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iss': JWT_ISSUER
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError as e:
        raise Exception(f'Invalid token: {str(e)}')


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing authorization header'}), 401

        token = auth_header.split(' ')[1]

        try:
            payload = verify_jwt_token(token)
            request.user = payload
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401

    return decorated


def requires_role(required_role):
    """Check if user has required role"""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_roles = request.user.get('roles', [])
            if required_role not in user_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


@app.route('/auth/login', methods=['POST'])
def login():
    """Authenticate and generate token"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Validate credentials (replace with your logic)
    # This is just an example - use proper authentication!
    if username == 'admin' and password == 'password':
        token = create_token(
            user_id='user-123',
            email='admin@example.com',
            roles=['admin', 'user']
        )

        return jsonify({
            'access_token': token,
            'token_type': 'Bearer',
            'expires_in': 3600
        })

    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/profile')
@requires_auth
def profile():
    return jsonify({
        'user_id': request.user['sub'],
        'email': request.user['email'],
        'roles': request.user['roles']
    })


@app.route('/api/admin')
@requires_auth
@requires_role('admin')
def admin():
    return jsonify({'message': 'Admin access granted'})
```

---

## Security Best Practices

### 1. Token Storage

**❌ DON'T:**

- Store tokens in localStorage (vulnerable to XSS)
- Include tokens in URL parameters
- Log tokens to console or logs

**✅ DO:**

- Use httpOnly cookies for web apps
- Use secure storage for mobile apps
- Store tokens in memory for SPAs (with refresh strategy)

### 2. Token Validation

Always validate:

- Signature (token hasn't been tampered with)
- Expiration time
- Issuer (iss claim)
- Audience (aud claim)
- Not Before time (nbf claim, if present)

### 3. HTTPS Only

```python
# Force HTTPS in production
@app.before_request
def force_https():
    if not request.is_secure and not app.debug:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```

### 4. Short Token Lifetimes

- Access tokens: 15-60 minutes
- Refresh tokens: 7-30 days
- ID tokens: Same as access tokens

### 5. Implement Token Refresh

```python
@app.route('/auth/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refresh_token')

    # Verify refresh token
    try:
        payload = verify_refresh_token(refresh_token)

        # Issue new access token
        new_token = create_token(
            user_id=payload['sub'],
            email=payload['email'],
            roles=payload['roles']
        )

        return jsonify({
            'access_token': new_token,
            'token_type': 'Bearer',
            'expires_in': 3600
        })
    except:
        return jsonify({'error': 'Invalid refresh token'}), 401
```

### 6. Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


@app.route('/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # Login logic
    pass
```

### 7. Environment Variables

```python
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.environ.get('JWT_SECRET')
AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
```

Create `.env` file:

```
JWT_SECRET=your-super-secret-key
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
```

### 8. Logging and Monitoring

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@requires_auth
def protected_endpoint():
    logging.info(f"User {request.user['sub']} accessed protected resource")
    # Endpoint logic
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Token Validation Fails

**Problem:** `Invalid signature` or `Token verification failed`

**Solutions:**

- Verify JWT_SECRET matches between token creation and validation
- Check token hasn't expired
- Ensure using correct algorithm (RS256 vs HS256)
- Verify issuer and audience claims

```python
# Debug token contents
import jwt

decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded)
```

#### 2. CORS Errors

**Problem:** Browser blocks API requests

**Solution:**

```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

#### 3. Token Expired Too Quickly

**Problem:** Users constantly need to re-login

**Solution:** Implement refresh tokens

```python
# Longer expiration for refresh tokens
refresh_payload = {
    'sub': user_id,
    'type': 'refresh',
    'exp': datetime.utcnow() + timedelta(days=7)
}
refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
```

#### 4. Authorization Header Not Sent

**Problem:** `No authorization header` error

**Solution:**

```javascript
// Ensure Authorization header is included
fetch('/api/protected', {
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    }
})
```

#### 5. OAuth Redirect Mismatch

**Problem:** `redirect_uri_mismatch` error

**Solution:**

- Ensure redirect URI in code matches provider settings exactly
- Include protocol (http:// or https://)
- Check for trailing slashes
- Add all possible redirect URIs to provider

#### 6. Public Key Not Found

**Problem:** Can't verify RS256 tokens

**Solution:**

```python
import requests


# Fetch JWKS with error handling
def get_jwks():
    try:
        response = requests.get(
            f'https://{AUTH0_DOMAIN}/.well-known/jwks.json',
            timeout=5
        )
        return response.json()
    except Exception as e:
        logging.error(f"Failed to fetch JWKS: {e}")
        raise
```

---

## Complete Example: Production-Ready App

```python
from flask import Flask, request, jsonify
from functools import wraps
import jwt
import os
from datetime import datetime, timedelta
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

# CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-this-secret')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id, email, roles=None):
    """Create access token"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        'sub': user_id,
        'email': email,
        'roles': roles or [],
        'type': 'access',
        'exp': expire,
        'iat': datetime.utcnow(),
        'iss': 'your-app'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id):
    """Create refresh token"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'sub': user_id,
        'type': 'refresh',
        'exp': expire,
        'iat': datetime.utcnow(),
        'iss': 'your-app'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token, token_type='access'):
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer='your-app'
        )

        if payload.get('type') != token_type:
            raise jwt.InvalidTokenError('Invalid token type')

        return payload

    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError as e:
        raise Exception(f'Invalid token: {str(e)}')


def requires_auth(f):
    """Require valid access token"""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning(f"Missing auth header from {request.remote_addr}")
            return jsonify({'error': 'Missing authorization header'}), 401

        token = auth_header.split(' ')[1]

        try:
            payload = verify_token(token, 'access')
            request.user = payload
            logger.info(f"User {payload['sub']} accessed {request.path}")
            return f(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Invalid token from {request.remote_addr}: {e}")
            return jsonify({'error': str(e)}), 401

    return decorated


def requires_role(role):
    """Require specific role"""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_roles = request.user.get('roles', [])
            if role not in user_roles:
                logger.warning(
                    f"User {request.user['sub']} attempted unauthorized access to {request.path}"
                )
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


# Routes
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Authenticate and issue tokens"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    # TODO: Validate against your user database
    # This is just an example
    if username == 'admin' and password == 'password':
        user_id = 'user-123'
        email = 'admin@example.com'
        roles = ['admin', 'user']

        access_token = create_access_token(user_id, email, roles)
        refresh_token = create_refresh_token(user_id)

        logger.info(f"Successful login for user: {username}")

        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60
        })

    logger.warning(f"Failed login attempt for user: {username}")
    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/auth/refresh', methods=['POST'])
def refresh():
    """Refresh access token"""
    refresh_token = request.json.get('refresh_token')

    if not refresh_token:
        return jsonify({'error': 'Missing refresh token'}), 400

    try:
        payload = verify_token(refresh_token, 'refresh')
        user_id = payload['sub']

        # TODO: Fetch user data from database
        email = 'admin@example.com'
        roles = ['admin', 'user']

        new_access_token = create_access_token(user_id, email, roles)

        logger.info(f"Token refreshed for user: {user_id}")

        return jsonify({
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60
        })
    except Exception as e:
        logger.warning(f"Invalid refresh token: {e}")
        return jsonify({'error': str(e)}), 401


@app.route('/api/profile')
@requires_auth
def profile():
    """Get user profile"""
    return jsonify({
        'user_id': request.user['sub'],
        'email': request.user['email'],
        'roles': request.user['roles']
    })


@app.route('/api/admin')
@requires_auth
@requires_role('admin')
def admin():
    """Admin-only endpoint"""
    return jsonify({'message': 'Admin access granted'})


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    logger.warning(f"Rate limit exceeded from {request.remote_addr}")
    return jsonify({'error': 'Rate limit exceeded'}), 429


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
```

---

## Additional Resources

### Documentation

- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [JWT.io](https://jwt.io/) - JWT debugger
- [Flask Documentation](https://flask.palletsprojects.com/)

### Libraries

- [Authlib](https://docs.authlib.org/) - OAuth/OIDC library
- [PyJWT](https://pyjwt.readthedocs.io/) - JWT implementation
- [Flask-Login](https://flask-login.readthedocs.io/) - Session management
- [Flask-CORS](https://flask-cors.readthedocs.io/) - CORS handling

### Security Tools

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Security Headers](https://securityheaders.com/) - Test security headers
- [SSL Labs](https://www.ssllabs.com/ssltest/) - Test SSL/TLS configuration

---

## Conclusion

Token-based authentication provides a modern, scalable approach to securing Flask applications. By using established
providers like Auth0, Azure AD, or Google, you can implement enterprise-grade authentication quickly. For custom
requirements, implementing your own JWT system gives you complete control.

**Key Takeaways:**

- Use OAuth 2.0 and OpenID Connect for standardized authentication
- Always validate tokens thoroughly (signature, expiration, issuer, audience)
- Implement HTTPS in production
- Use short-lived access tokens with refresh token rotation
- Follow security best practices and regularly update dependencies
- Monitor and log authentication events for security auditing
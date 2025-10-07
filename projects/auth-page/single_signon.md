# Flask Single Sign-On (SSO) Implementation Guide

## Table of Contents
1. [What is Single Sign-On (SSO)?](#what-is-single-sign-on-sso)
2. [SSO Protocols](#sso-protocols)
3. [SSO Architecture](#sso-architecture)
4. [OAuth/OIDC SSO Implementation](#oauthoidc-sso-implementation)
5. [SAML SSO Implementation](#saml-sso-implementation)
6. [Enterprise SSO Solutions](#enterprise-sso-solutions)
7. [Multi-App SSO Setup](#multi-app-sso-setup)
8. [Session Management](#session-management)
9. [Security Considerations](#security-considerations)
10. [Troubleshooting](#troubleshooting)

---

## What is Single Sign-On (SSO)?

Single Sign-On (SSO) allows users to authenticate once and gain access to multiple applications without re-entering credentials.

### Benefits

**For Users:**
- ✅ One set of credentials for multiple apps
- ✅ Fewer passwords to remember
- ✅ Seamless experience across applications
- ✅ Faster access to resources

**For Organizations:**
- ✅ Centralized user management
- ✅ Enhanced security (MFA in one place)
- ✅ Reduced help desk tickets (password resets)
- ✅ Better compliance and auditing
- ✅ Easier onboarding/offboarding

### SSO Flow

```
┌──────────┐         ┌──────────────┐         ┌──────────────┐
│          │         │              │         │              │
│  User    │────1───>│   App A      │         │   App B      │
│          │  Login  │  (Flask)     │         │  (Flask)     │
└──────────┘         └──────┬───────┘         └──────┬───────┘
                            │                        │
                        2   │                    5   │
                  Redirect  │                 Already │
                   to SSO   │                 Auth'd  │
                            │                        │
                            ▼                        ▼
                     ┌──────────────┐         ┌──────────────┐
                     │              │         │              │
                     │  SSO/IdP     │◄───4────│   Session    │
                     │  (Auth0/     │  Check  │   Store      │
                     │   Okta/AD)   │         │  (Redis)     │
                     │              │         │              │
                     └──────┬───────┘         └──────────────┘
                            │
                        3   │
                    Return  │
                     Token  │
                            │
                     ┌──────▼───────┐
                     │              │
                     │   User       │
                     │   Logged In  │
                     │              │
                     └──────────────┘
```

**Steps:**
1. User tries to access App A
2. App A redirects to SSO provider
3. User authenticates, SSO returns token
4. User accesses App B
5. App B checks session, user already authenticated

---

## SSO Protocols

### 1. OAuth 2.0 / OpenID Connect (OIDC)

**Best for:** Modern web/mobile apps, APIs, consumer apps

**Characteristics:**
- RESTful/JSON-based
- Works well with APIs
- Mobile-friendly
- Industry standard for modern apps

**Token Types:**
- Access Token - API access
- ID Token - User identity
- Refresh Token - Get new tokens

### 2. SAML 2.0

**Best for:** Enterprise applications, legacy systems

**Characteristics:**
- XML-based
- Enterprise standard
- Works with Active Directory
- More complex but feature-rich

**Components:**
- Service Provider (SP) - Your Flask app
- Identity Provider (IdP) - SSO server
- SAML Assertions - XML tokens

### Comparison

| Feature | OIDC/OAuth | SAML |
|---------|------------|------|
| Format | JSON | XML |
| Complexity | Simple | Complex |
| Mobile Support | Excellent | Limited |
| API Support | Native | Workarounds needed |
| Enterprise Adoption | Growing | Established |
| Use Case | Modern apps | Enterprise legacy |

---

## SSO Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    SSO Ecosystem                            │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│  │  App A   │    │  App B   │    │  App C   │            │
│  │ (Flask)  │    │ (Flask)  │    │ (Flask)  │            │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘            │
│       │               │               │                    │
│       │               │               │                    │
│       └───────────────┴───────────────┘                    │
│                       │                                     │
│                       ▼                                     │
│            ┌──────────────────────┐                        │
│            │   Identity Provider  │                        │
│            │   (Auth0/Okta/AD)   │                        │
│            └──────────┬───────────┘                        │
│                       │                                     │
│                       ▼                                     │
│            ┌──────────────────────┐                        │
│            │   User Directory     │                        │
│            │   (LDAP/AD/Database) │                        │
│            └──────────────────────┘                        │
│                                                             │
│            ┌──────────────────────┐                        │
│            │   Session Store      │                        │
│            │   (Redis/Database)   │                        │
│            └──────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Identity Provider (IdP)** - Authenticates users
2. **Service Provider (SP)** - Your Flask apps
3. **Session Store** - Shared session storage
4. **User Directory** - User database (LDAP, AD, DB)

---

## OAuth/OIDC SSO Implementation

### Option 1: Auth0 SSO

#### Setup

```bash
pip install authlib requests flask-session redis
```

#### Flask App Configuration

```python
from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
from flask_session import Session
import redis
from functools import wraps
from datetime import timedelta
import os

app = Flask(__name__)

# Configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    SESSION_TYPE='redis',
    SESSION_PERMANENT=True,
    SESSION_USE_SIGNER=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_REDIS=redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
)

# Initialize Flask-Session for shared sessions across apps
Session(app)

# Auth0 SSO Configuration
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL')

# Initialize OAuth
oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=f'https://{AUTH0_DOMAIN}',
    access_token_url=f'https://{AUTH0_DOMAIN}/oauth/token',
    authorize_url=f'https://{AUTH0_DOMAIN}/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url=f'https://{AUTH0_DOMAIN}/.well-known/openid-configuration'
)

def requires_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    """Home page"""
    return jsonify({
        'app': 'Application A',
        'authenticated': 'user' in session,
        'user': session.get('user')
    })

@app.route('/login')
def login():
    """Initiate SSO login"""
    # Store the page user was trying to access
    next_url = request.args.get('next', url_for('index'))
    session['next_url'] = next_url
    
    return auth0.authorize_redirect(
        redirect_uri=AUTH0_CALLBACK_URL,
        audience=f'https://{AUTH0_DOMAIN}/userinfo'
    )

@app.route('/callback')
def callback():
    """Handle SSO callback"""
    try:
        # Get tokens from Auth0
        token = auth0.authorize_access_token()
        
        # Get user info
        resp = auth0.get('userinfo')
        userinfo = resp.json()
        
        # Store user info in session (shared across apps)
        session['user'] = {
            'id': userinfo['sub'],
            'name': userinfo.get('name'),
            'email': userinfo.get('email'),
            'picture': userinfo.get('picture')
        }
        session['access_token'] = token['access_token']
        session['id_token'] = token['id_token']
        
        # Mark session as SSO
        session['sso_enabled'] = True
        session['sso_provider'] = 'auth0'
        
        # Redirect to originally requested page
        next_url = session.pop('next_url', url_for('index'))
        return redirect(next_url)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/logout')
def logout():
    """SSO logout - clears session and logs out from Auth0"""
    session.clear()
    
    # Logout from Auth0 (SSO logout)
    return redirect(
        f'https://{AUTH0_DOMAIN}/v2/logout?'
        f'client_id={AUTH0_CLIENT_ID}&'
        f'returnTo={url_for("index", _external=True)}'
    )

@app.route('/protected')
@requires_auth
def protected():
    """Protected resource"""
    return jsonify({
        'message': 'This is a protected resource',
        'user': session['user']
    })

@app.route('/profile')
@requires_auth
def profile():
    """User profile"""
    return jsonify(session['user'])

# Health check for load balancer
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Multiple Flask Apps with Shared SSO

**App A (Port 5000):**
```python
# app_a.py
from flask import Flask, session, jsonify
from flask_session import Session
import redis
from datetime import timedelta

app = Flask(__name__)
app.config.update(
    SECRET_KEY='same-secret-for-all-apps',  # MUST BE SAME
    SESSION_TYPE='redis',
    SESSION_REDIS=redis.from_url('redis://localhost:6379'),
    SESSION_KEY_PREFIX='sso:',  # Same prefix for all apps
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)

Session(app)

@app.route('/')
def index():
    if 'user' in session:
        return jsonify({
            'app': 'Application A',
            'user': session['user'],
            'message': 'Already logged in via SSO!'
        })
    return jsonify({
        'app': 'Application A',
        'message': 'Not logged in',
        'login_url': 'http://localhost:5000/login'
    })

if __name__ == '__main__':
    app.run(port=5000)
```

**App B (Port 5001):**
```python
# app_b.py
from flask import Flask, session, jsonify
from flask_session import Session
import redis
from datetime import timedelta

app = Flask(__name__)
app.config.update(
    SECRET_KEY='same-secret-for-all-apps',  # MUST BE SAME
    SESSION_TYPE='redis',
    SESSION_REDIS=redis.from_url('redis://localhost:6379'),
    SESSION_KEY_PREFIX='sso:',  # Same prefix for all apps
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)

Session(app)

@app.route('/')
def index():
    if 'user' in session:
        return jsonify({
            'app': 'Application B',
            'user': session['user'],
            'message': 'SSO worked! No login needed!'
        })
    return jsonify({
        'app': 'Application B',
        'message': 'Not logged in',
        'login_url': 'http://localhost:5000/login'
    })

if __name__ == '__main__':
    app.run(port=5001)
```

**Key Points for Shared SSO:**
- ✅ Same SECRET_KEY across all apps
- ✅ Same Redis server
- ✅ Same SESSION_KEY_PREFIX
- ✅ Same Auth0 tenant/application

---

## SAML SSO Implementation

### When to Use SAML

Use SAML when:
- Integrating with enterprise IdPs (Okta, Azure AD, OneLogin)
- Corporate IT requires SAML
- Working with legacy enterprise systems
- Need advanced features (attribute mapping, encryption)

### Setup

```bash
pip install python3-saml
```

### SAML Configuration

**settings.json:**
```json
{
    "strict": true,
    "debug": true,
    "sp": {
        "entityId": "https://your-app.com/saml/metadata",
        "assertionConsumerService": {
            "url": "https://your-app.com/saml/acs",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        },
        "singleLogoutService": {
            "url": "https://your-app.com/saml/sls",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        "x509cert": "",
        "privateKey": ""
    },
    "idp": {
        "entityId": "https://idp.example.com/saml/metadata",
        "singleSignOnService": {
            "url": "https://idp.example.com/saml/sso",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "singleLogoutService": {
            "url": "https://idp.example.com/saml/slo",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "x509cert": "MIIDdzCCAl+gAwIBAgIEb..."
    },
    "security": {
        "nameIdEncrypted": false,
        "authnRequestsSigned": false,
        "logoutRequestSigned": false,
        "logoutResponseSigned": false,
        "signMetadata": false,
        "wantMessagesSigned": false,
        "wantAssertionsSigned": true,
        "wantNameIdEncrypted": false,
        "wantAssertionsEncrypted": false,
        "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
    }
}
```

### Flask SAML Implementation

```python
from flask import Flask, request, redirect, session, jsonify, url_for
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

def init_saml_auth(req):
    """Initialize SAML auth"""
    auth = OneLogin_Saml2_Auth(req, custom_base_path='saml')
    return auth

def prepare_flask_request(request):
    """Prepare Flask request for SAML"""
    url_data = {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.host,
        'server_port': request.environ.get('SERVER_PORT'),
        'script_name': request.path,
        'get_data': request.args.copy(),
        'post_data': request.form.copy()
    }
    return url_data

def requires_saml_auth(f):
    """Decorator to require SAML authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'samlUserdata' not in session:
            return redirect(url_for('saml_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    """Home page"""
    if 'samlUserdata' in session:
        return jsonify({
            'authenticated': True,
            'user': session['samlUserdata'],
            'attributes': session.get('samlNameId')
        })
    return jsonify({
        'authenticated': False,
        'login_url': url_for('saml_login')
    })

@app.route('/saml/login')
def saml_login():
    """Initiate SAML SSO"""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    # Redirect to IdP for authentication
    return redirect(auth.login())

@app.route('/saml/acs', methods=['POST'])
def saml_acs():
    """Assertion Consumer Service - handles SAML response"""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    # Process SAML response
    auth.process_response()
    errors = auth.get_errors()
    
    if len(errors) == 0:
        # Store user data in session
        session['samlUserdata'] = auth.get_attributes()
        session['samlNameId'] = auth.get_nameid()
        session['samlSessionIndex'] = auth.get_session_index()
        
        # Redirect to originally requested URL
        self_url = OneLogin_Saml2_Utils.get_self_url(req)
        if 'RelayState' in request.form and self_url != request.form['RelayState']:
            return redirect(auth.redirect_to(request.form['RelayState']))
        
        return redirect(url_for('index'))
    else:
        return jsonify({
            'errors': errors,
            'error_reason': auth.get_last_error_reason()
        }), 400

@app.route('/saml/metadata')
def saml_metadata():
    """SAML metadata endpoint"""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    
    if len(errors) == 0:
        return metadata, 200, {
            'Content-Type': 'text/xml'
        }
    else:
        return jsonify({'errors': errors}), 500

@app.route('/saml/sls')
def saml_sls():
    """Single Logout Service"""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    url = auth.process_slo(delete_session_cb=lambda: session.clear())
    errors = auth.get_errors()
    
    if len(errors) == 0:
        if url is not None:
            return redirect(url)
        else:
            return redirect(url_for('index'))
    else:
        return jsonify({'errors': errors}), 400

@app.route('/logout')
@requires_saml_auth
def logout():
    """Initiate SAML logout"""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    name_id = session.get('samlNameId')
    session_index = session.get('samlSessionIndex')
    
    return redirect(auth.logout(
        name_id=name_id,
        session_index=session_index
    ))

@app.route('/protected')
@requires_saml_auth
def protected():
    """Protected resource"""
    return jsonify({
        'message': 'Protected resource',
        'user': session['samlUserdata']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

---

## Enterprise SSO Solutions

### Azure AD (Microsoft)

Azure AD is the most common enterprise SSO solution.

#### Setup Azure AD SSO

```python
from flask import Flask, redirect, session, request, jsonify
from msal import ConfidentialClientApplication
import requests
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Azure AD Configuration
AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')
AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID')
AZURE_AUTHORITY = f'https://login.microsoftonline.com/{AZURE_TENANT_ID}'
AZURE_REDIRECT_URI = os.environ.get('AZURE_REDIRECT_URI')
AZURE_SCOPE = ['User.Read']

# MSAL app
msal_app = ConfidentialClientApplication(
    AZURE_CLIENT_ID,
    authority=AZURE_AUTHORITY,
    client_credential=AZURE_CLIENT_SECRET
)

def requires_azure_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/login')
def login():
    """Initiate Azure AD SSO"""
    # Check if user already has active session
    accounts = msal_app.get_accounts()
    
    if accounts:
        # Silent token acquisition
        result = msal_app.acquire_token_silent(AZURE_SCOPE, account=accounts[0])
        if result:
            session['user'] = result.get('id_token_claims')
            return redirect('/dashboard')
    
    # Redirect to Azure AD
    auth_url = msal_app.get_authorization_request_url(
        AZURE_SCOPE,
        redirect_uri=AZURE_REDIRECT_URI,
        prompt='select_account'  # Force account selection
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Azure AD callback"""
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
    
    # Store user info
    session['user'] = result.get('id_token_claims')
    session['access_token'] = result['access_token']
    
    # Get additional user info from Microsoft Graph
    graph_result = requests.get(
        'https://graph.microsoft.com/v1.0/me',
        headers={'Authorization': f'Bearer {result["access_token"]}'}
    ).json()
    
    session['user']['graph'] = graph_result
    
    return redirect('/dashboard')

@app.route('/dashboard')
@requires_azure_auth
def dashboard():
    """Dashboard - requires authentication"""
    return jsonify({
        'user': session['user'],
        'message': 'Logged in via Azure AD SSO'
    })

@app.route('/logout')
def logout():
    """Azure AD logout"""
    session.clear()
    
    # Azure AD logout URL
    logout_url = (
        f'{AZURE_AUTHORITY}/oauth2/v2.0/logout?'
        f'post_logout_redirect_uri={AZURE_REDIRECT_URI}'
    )
    return redirect(logout_url)
```

### Okta SSO

```python
from flask import Flask, redirect, session, request, jsonify
from okta_jwt_verifier import JWTVerifier
import requests
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Okta Configuration
OKTA_DOMAIN = os.environ.get('OKTA_DOMAIN')  # e.g., 'dev-12345.okta.com'
OKTA_CLIENT_ID = os.environ.get('OKTA_CLIENT_ID')
OKTA_CLIENT_SECRET = os.environ.get('OKTA_CLIENT_SECRET')
OKTA_REDIRECT_URI = os.environ.get('OKTA_REDIRECT_URI')
OKTA_ISSUER = f'https://{OKTA_DOMAIN}/oauth2/default'

# JWT Verifier
jwt_verifier = JWTVerifier(
    issuer=OKTA_ISSUER,
    client_id=OKTA_CLIENT_ID,
    audience='api://default'
)

def requires_okta_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/login')
def login():
    """Initiate Okta SSO"""
    authorization_url = (
        f'{OKTA_ISSUER}/v1/authorize?'
        f'client_id={OKTA_CLIENT_ID}&'
        f'response_type=code&'
        f'scope=openid profile email&'
        f'redirect_uri={OKTA_REDIRECT_URI}&'
        f'state=random_state_string'
    )
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    """Okta callback"""
    code = request.args.get('code')
    
    # Exchange code for tokens
    token_url = f'{OKTA_ISSUER}/v1/token'
    response = requests.post(token_url, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': OKTA_REDIRECT_URI,
        'client_id': OKTA_CLIENT_ID,
        'client_secret': OKTA_CLIENT_SECRET
    })
    
    token_data = response.json()
    
    if 'error' in token_data:
        return jsonify(token_data), 400
    
    # Verify ID token
    try:
        verified_token = jwt_verifier.verify_access_token(token_data['access_token'])
        
        # Get user info
        userinfo_url = f'{OKTA_ISSUER}/v1/userinfo'
        userinfo = requests.get(
            userinfo_url,
            headers={'Authorization': f'Bearer {token_data["access_token"]}'}
        ).json()
        
        session['user'] = userinfo
        session['access_token'] = token_data['access_token']
        
        return redirect('/dashboard')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/dashboard')
@requires_okta_auth
def dashboard():
    return jsonify({
        'user': session['user'],
        'message': 'Logged in via Okta SSO'
    })

@app.route('/logout')
def logout():
    """Okta logout"""
    session.clear()
    
    logout_url = (
        f'https://{OKTA_DOMAIN}/oauth2/v1/logout?'
        f'id_token_hint={session.get("id_token")}&'
        f'post_logout_redirect_uri={OKTA_REDIRECT_URI}'
    )
    return redirect(logout_url)
```

---

## Multi-App SSO Setup

### Architecture for Multiple Apps

```python
# shared_sso.py - Shared SSO module for all apps
from flask_session import Session
import redis
from datetime import timedelta
import os

class SSOConfig:
    """Shared SSO configuration"""
    SECRET_KEY = os.environ.get('SSO_SECRET_KEY')
    SESSION_TYPE = 'redis'
    SESSION_REDIS = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    SESSION_KEY_PREFIX = 'sso:'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_NAME = 'sso_session'
    SESSION_COOKIE_DOMAIN = '.yourdomain.com'  # Shared across subdomains
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_SAMESITE = 'Lax'

def init_sso(app):
    """Initialize SSO for Flask app"""
    app.config.from_object(SSOConfig)
    Session(app)
    return app
```

### App 1: Authentication Hub

```python
# auth_app.py - Handles all authentication
from flask import Flask, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from shared_sso import init_sso

app = Flask(__name__)
app = init_sso(app)

# OAuth setup (Auth0, Azure AD, etc.)
oauth = OAuth(app)
# ... configure oauth provider ...

@app.route('/login')
def login():
    """Central login endpoint"""
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for('callback', _external=True)
    )

@app.route('/callback')
def callback():
    """Handle SSO callback"""
    token = oauth.auth0.authorize_access_token()
    user_info = oauth.auth0.get('userinfo').json()
    
    # Store in shared session
    session['user'] = user_info
    session['sso_authenticated'] = True
    
    # Redirect to originally requested app
    return_to = session.get('return_to', 'https://app1.yourdomain.com')
    return redirect(return_to)

@app.route('/logout')
def logout():
    """Central logout - clears shared session"""
    session.clear()
    # Redirect to IdP logout
    return redirect('https://idp.example.com/logout')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### App 2: Business Application

```python
# business_app.py - Uses SSO
from flask import Flask, session, redirect, jsonify
from shared_sso import init_sso
from functools import wraps

app = Flask(__name__)
app = init_sso(app)

def requires_sso(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('sso_authenticated'):
            # Store current URL to return after login
            session['return_to'] = request.url
            return redirect('https://auth.yourdomain.com/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_sso
def index():
    return jsonify({
        'app': 'Business Application',
        'user': session['user'],
        'message': 'Accessed via SSO!'
    })

@app.route('/api/data')
@requires_sso
def api_data():
    return jsonify({
        'data': 'Protected business data',
        'user_id': session['user']['sub']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

### App 3: Admin Portal

```python
# admin_app.py - Uses SSO with role check
from flask import Flask, session, redirect, jsonify
from shared_sso import init_sso
from functools import wraps

app = Flask(__name__)
app = init_sso(app)

def requires_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('sso_authenticated'):
            session['return_to'] = request.url
            return redirect('https://auth.yourdomain.com/login')
        
        # Check admin role
        user_roles = session.get('user', {}).get('roles', [])
        if 'admin' not in user_roles:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_admin
def admin_dashboard():
    return jsonify({
        'app': 'Admin Portal',
        'user': session['user'],
        'message': 'Admin access granted via SSO'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
```

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  auth_app:
    build: ./auth_app
    ports:
      - "5000:5000"
    environment:
      - SSO_SECRET_KEY=your-shared-secret
      - REDIS_URL=redis://redis:6379
      - AUTH0_DOMAIN=your-tenant.auth0.com
      - AUTH0_CLIENT_ID=your-client-id
      - AUTH0_CLIENT_SECRET=your-client-secret
    depends_on:
      - redis

  business_app:
    build: ./business_app
    ports:
      - "5001:5001"
    environment:
      - SSO_SECRET_KEY=your-shared-secret
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  admin_app:
    build: ./admin_app
    ports:
      - "5002:5002"
    environment:
      - SSO_SECRET_KEY=your-shared-secret
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis_data:
```

---

## Session Management

### Distributed Session Storage

#### Redis Session Store

```python
from flask import Flask, session
from flask_session import Session
import redis
from datetime import timedelta

app = Flask(__name__)

# Redis configuration
app.config.update(
    SESSION_TYPE='redis',
    SESSION_REDIS=redis.StrictRedis(
        host='localhost',
        port=6379,
        db=0,
        password='your-redis-password'
    ),
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_USE_SIGNER=True,
    SESSION_KEY_PREFIX='sso:'
)

Session(app)

@app.route('/set-session')
def set_session():
    session['user'] = {'id': 123, 'name': 'John'}
    return 'Session set'

@app.route('/get-session')
def get_session():
    return session.get('user', {})
```

#### Database Session Store

```python
from flask import Flask
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.update(
    SESSION_TYPE='sqlalchemy',
    SQLALCHEMY_DATABASE_URI='postgresql://user:pass@localhost/sessions',
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)

db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db

Session(app)
```

### Session Synchronization

```python
# session_sync.py
import redis
import json
from datetime import datetime

class SessionSync:
    """Synchronize sessions across multiple apps"""
    
    def __init__(self, redis_url='redis://localhost:6379'):
        self.redis_client = redis.from_url(redis_url)
        self.session_prefix = 'sso:session:'
    
    def create_session(self, session_id, user_data, expires_in=3600):
        """Create or update session"""
        key = f'{self.session_prefix}{session_id}'
        data = {
            'user': user_data,
            'created_at': datetime.utcnow().isoformat(),
            'last_accessed': datetime.utcnow().isoformat()
        }
        self.redis_client.setex(
            key,
            expires_in,
            json.dumps(data)
        )
    
    def get_session(self, session_id):
        """Retrieve session"""
        key = f'{self.session_prefix}{session_id}'
        data = self.redis_client.get(key)
        
        if data:
            session_data = json.loads(data)
            # Update last accessed time
            session_data['last_accessed'] = datetime.utcnow().isoformat()
            self.redis_client.setex(
                key,
                3600,
                json.dumps(session_data)
            )
            return session_data
        return None
    
    def delete_session(self, session_id):
        """Delete session (logout)"""
        key = f'{self.session_prefix}{session_id}'
        self.redis_client.delete(key)
    
    def extend_session(self, session_id, extends_by=3600):
        """Extend session expiration"""
        key = f'{self.session_prefix}{session_id}'
        self.redis_client.expire(key, extends_by)

# Usage
sync = SessionSync()

# Create session
sync.create_session('user-123', {
    'id': 123,
    'email': 'user@example.com',
    'roles': ['user']
})

# Get session
user_data = sync.get_session('user-123')

# Logout
sync.delete_session('user-123')
```

---

## Security Considerations

### 1. Token Security

```python
# Secure token storage
from cryptography.fernet import Fernet

class SecureTokenStorage:
    def __init__(self, encryption_key):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_token(self, token):
        """Encrypt token before storing"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        """Decrypt token when retrieving"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()

# Usage
key = Fernet.generate_key()
storage = SecureTokenStorage(key)

# Encrypt before storing in session
encrypted = storage.encrypt_token(access_token)
session['encrypted_token'] = encrypted

# Decrypt when using
token = storage.decrypt_token(session['encrypted_token'])
```

### 2. CSRF Protection

```python
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

# Exempt SSO endpoints from CSRF
@app.route('/saml/acs', methods=['POST'])
@csrf.exempt
def saml_acs():
    # Handle SAML response
    pass
```

### 3. Session Fixation Prevention

```python
from flask import session
import os

@app.route('/callback')
def callback():
    # Regenerate session ID after successful login
    old_session = dict(session)
    session.clear()
    
    # Generate new session ID
    session.sid = os.urandom(24).hex()
    
    # Restore user data with new session
    session.update(old_session)
    session['user'] = user_data
    
    return redirect('/dashboard')
```

### 4. Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/login')
@limiter.limit("10 per minute")
def login():
    # Prevent brute force attacks
    pass
```

### 5. Audit Logging

```python
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    filename='sso_audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_sso_event(event_type, user_id, details):
    """Log SSO events for auditing"""
    logging.info(f"SSO_EVENT: {event_type} | User: {user_id} | Details: {details}")

# Usage
@app.route('/callback')
def callback():
    # ... authentication logic ...
    
    log_sso_event(
        'LOGIN_SUCCESS',
        user_data['id'],
        {'ip': request.remote_addr, 'timestamp': datetime.utcnow()}
    )
    
    return redirect('/dashboard')
```

---

## Troubleshooting

### Common SSO Issues

#### 1. Sessions Not Shared Across Apps

**Problem:** User logs in to App A but still needs to login to App B

**Solutions:**
- ✅ Verify all apps use same SECRET_KEY
- ✅ Check Redis is accessible from all apps
- ✅ Ensure SESSION_KEY_PREFIX is identical
- ✅ Verify SESSION_COOKIE_DOMAIN covers all apps
- ✅ Check cookies are sent (same domain or subdomain)

```python
# Debug session
@app.route('/debug-session')
def debug_session():
    return jsonify({
        'session_data': dict(session),
        'session_id': session.sid if hasattr(session, 'sid') else 'N/A',
        'cookie_domain': app.config.get('SESSION_COOKIE_DOMAIN'),
        'secret_key_set': bool(app.secret_key)
    })
```

#### 2. SAML Signature Verification Fails

**Problem:** SAML assertion rejected

**Solutions:**
- Verify IdP certificate is correct
- Check clock synchronization (NTP)
- Ensure HTTPS is used
- Validate metadata URLs

```python
# Debug SAML
from onelogin.saml2.utils import OneLogin_Saml2_Utils

@app.route('/debug-saml')
def debug_saml():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    
    return jsonify({
        'sp_entity_id': settings.get_sp_entity_id(),
        'idp_entity_id': settings.get_idp_entity_id(),
        'sp_acs_url': settings.get_sp_assertion_consumer_service_url(),
        'errors': settings.validate_metadata(settings.get_sp_metadata())
    })
```

#### 3. Token Expired Too Quickly

**Problem:** Users constantly re-authenticating

**Solutions:**
- Implement token refresh
- Extend session lifetime
- Use refresh tokens

```python
from datetime import datetime, timedelta

def refresh_token_if_needed():
    """Automatically refresh token before expiration"""
    if 'token_expires_at' in session:
        expires_at = datetime.fromisoformat(session['token_expires_at'])
        
        # Refresh if expires in less than 5 minutes
        if datetime.utcnow() + timedelta(minutes=5) > expires_at:
            # Call IdP to refresh token
            new_token = oauth.auth0.fetch_access_token()
            session['access_token'] = new_token['access_token']
            session['token_expires_at'] = (
                datetime.utcnow() + timedelta(seconds=new_token['expires_in'])
            ).isoformat()
```

#### 4. Redirect URI Mismatch

**Problem:** OAuth callback fails

**Solutions:**
- Exact match required (including protocol, port, path)
- Add all possible URIs to IdP config
- Check for trailing slashes

```python
# Dynamic redirect URI based on environment
import os

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    REDIRECT_URI = 'https://app.example.com/callback'
elif ENVIRONMENT == 'staging':
    REDIRECT_URI = 'https://staging.example.com/callback'
else:
    REDIRECT_URI = 'http://localhost:5000/callback'
```

#### 5. CORS Errors in Browser

**Problem:** Browser blocks SSO requests

**Solution:**
```python
from flask_cors import CORS

# Allow specific origins
CORS(app, resources={
    r"/saml/*": {
        "origins": ["https://idp.example.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})
```

---

## Complete SSO Solution Example

```python
# complete_sso_app.py
from flask import Flask, request, redirect, session, jsonify, url_for
from authlib.integrations.flask_client import OAuth
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import logging
from datetime import timedelta
from functools import wraps
import os

# Initialize Flask
app = Flask(__name__)

# Configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    SESSION_TYPE='redis',
    SESSION_REDIS=redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379')),
    SESSION_KEY_PREFIX='sso:',
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_COOKIE_NAME='sso_session',
    SESSION_COOKIE_DOMAIN=os.environ.get('COOKIE_DOMAIN', 'localhost'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Initialize extensions
Session(app)
limiter = Limiter(app=app, key_func=get_remote_address)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sso.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# OAuth setup
oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=os.environ.get('AUTH0_CLIENT_ID'),
    client_secret=os.environ.get('AUTH0_CLIENT_SECRET'),
    api_base_url=f'https://{os.environ.get("AUTH0_DOMAIN")}',
    access_token_url=f'https://{os.environ.get("AUTH0_DOMAIN")}/oauth/token',
    authorize_url=f'https://{os.environ.get("AUTH0_DOMAIN")}/authorize',
    client_kwargs={'scope': 'openid profile email'},
)

# Decorators
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            logger.warning(f"Unauthorized access attempt to {request.path}")
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def requires_role(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            
            user_roles = session['user'].get('roles', [])
            if role not in user_roles:
                logger.warning(f"User {session['user']['id']} lacks role {role}")
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

# Routes
@app.route('/')
def index():
    if 'user' in session:
        return jsonify({
            'authenticated': True,
            'user': session['user'],
            'sso_provider': session.get('sso_provider')
        })
    return jsonify({
        'authenticated': False,
        'login_url': url_for('login')
    })

@app.route('/login')
@limiter.limit("10 per minute")
def login():
    logger.info(f"Login initiated from {request.remote_addr}")
    return auth0.authorize_redirect(
        redirect_uri=url_for('callback', _external=True)
    )

@app.route('/callback')
def callback():
    try:
        token = auth0.authorize_access_token()
        resp = auth0.get('userinfo')
        userinfo = resp.json()
        
        session['user'] = {
            'id': userinfo['sub'],
            'name': userinfo.get('name'),
            'email': userinfo.get('email'),
            'roles': userinfo.get('roles', ['user'])
        }
        session['access_token'] = token['access_token']
        session['sso_provider'] = 'auth0'
        
        logger.info(f"Successful SSO login for user {userinfo['email']}")
        
        next_url = session.pop('next_url', url_for('index'))
        return redirect(next_url)
        
    except Exception as e:
        logger.error(f"SSO callback error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/logout')
def logout():
    user_id = session.get('user', {}).get('id', 'unknown')
    session.clear()
    logger.info(f"User {user_id} logged out")
    
    return redirect(
        f'https://{os.environ.get("AUTH0_DOMAIN")}/v2/logout?'
        f'client_id={os.environ.get("AUTH0_CLIENT_ID")}&'
        f'returnTo={url_for("index", _external=True)}'
    )

@app.route('/protected')
@requires_auth
def protected():
    return jsonify({
        'message': 'Protected resource',
        'user': session['user']
    })

@app.route('/admin')
@requires_auth
@requires_role('admin')
def admin():
    return jsonify({
        'message': 'Admin resource',
        'user': session['user']
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## Conclusion

Single Sign-On significantly improves user experience and security by:
- Reducing password fatigue
- Centralizing authentication
- Enabling enterprise integration
- Simplifying user management

**Key Takeaways:**
- Choose OAuth/OIDC for modern apps, SAML for enterprise
- Use shared session storage (Redis) for multi-app SSO
- Implement proper session management and security
- Always use HTTPS in production
- Log and monitor SSO events for security
- Test SSO flow thoroughly before production


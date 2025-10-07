# app.py - Simple & Secure Flask Login
from flask import Flask, render_template_string, request, redirect, url_for, session
from functools import wraps
from datetime import timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30 min timeout

# Simple user database (replace with your database/LDAP)
USERS = {
    'admin': 'admin123',
    'user': 'user123'
}

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

# Refresh session on every request (extends timeout)
@app.before_request
def make_session_permanent():
    session.permanent = True

# BASE TEMPLATE - Used by all pages
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: #f5f5f5;
        }
        nav { 
            background: #333; 
            color: white; 
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        nav a { 
            color: white; 
            text-decoration: none; 
            margin-right: 1rem;
        }
        nav a:hover { text-decoration: underline; }
        .container { 
            max-width: 800px; 
            margin: 2rem auto; 
            padding: 2rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            font-size: 1rem;
        }
        .btn-primary { background: #007bff; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn:hover { opacity: 0.9; }
        .alert { 
            padding: 1rem; 
            margin-bottom: 1rem; 
            border-radius: 4px;
        }
        .alert-error { background: #f8d7da; color: #721c24; }
        .alert-success { background: #d4edda; color: #155724; }
        .user-info { color: #ddd; }
    </style>
</head>
<body>
    <nav>
        <div>
            <a href="{{ url_for('home') }}">Home</a>
            {% if 'username' in session %}
                <a href="{{ url_for('dashboard') }}">Dashboard</a>
                <a href="{{ url_for('profile') }}">Profile</a>
            {% endif %}
        </div>
        <div>
            {% if 'username' in session %}
                <span class="user-info">👤 {{ session['username'] }}</span>
                <a href="{{ url_for('logout') }}" class="btn btn-danger">Logout</a>
            {% else %}
                <a href="{{ url_for('login') }}" class="btn btn-primary">Login</a>
            {% endif %}
        </div>
    </nav>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="container">
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}
    
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

# HOME PAGE (public)
HOME_PAGE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1>Welcome! 👋</h1>
    {% if 'username' in session %}
        <p>You are logged in as <strong>{{ session['username'] }}</strong></p>
        <p><a href="{{ url_for('dashboard') }}">Go to Dashboard →</a></p>
    {% else %}
        <p>Please <a href="{{ url_for('login') }}">login</a> to access protected pages.</p>
        <p><small>Demo: admin/admin123 or user/user123</small></p>
    {% endif %}
''')

# LOGIN PAGE
LOGIN_PAGE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1>Login</h1>
    <form method="POST">
        <div class="form-group">
            <label>Username</label>
            <input type="text" name="username" required autofocus>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="btn btn-primary">Login</button>
    </form>
    <p style="margin-top: 1rem;"><small>Demo: admin/admin123 or user/user123</small></p>
''')

# DASHBOARD PAGE (protected)
DASHBOARD_PAGE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1>Dashboard 📊</h1>
    <p>Welcome, <strong>{{ session['username'] }}</strong>!</p>
    <div style="margin-top: 2rem; padding: 1rem; background: #e8f5e9; border-radius: 4px;">
        <p>✅ This is a protected page</p>
        <p>🔒 Session expires after 30 minutes of inactivity</p>
        <p>♻️ Timeout resets on every page visit</p>
    </div>
''')

# PROFILE PAGE (protected)
PROFILE_PAGE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1>Profile 👤</h1>
    <p><strong>Username:</strong> {{ session['username'] }}</p>
    <p><strong>Status:</strong> Logged in</p>
    <div style="margin-top: 2rem; padding: 1rem; background: #fff3e0; border-radius: 4px;">
        <p>This is another protected page. Only logged-in users can see this.</p>
    </div>
''')

# ROUTES
@app.route('/')
def home():
    return render_template_string(HOME_PAGE, title='Home')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Validate credentials
        if username in USERS and USERS[username] == password:
            session['username'] = username
            session.permanent = True
            
            # Redirect to page they were trying to access
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            from flask import flash
            flash('Invalid username or password', 'error')
    
    return render_template_string(LOGIN_PAGE, title='Login')

@app.route('/logout')
def logout():
    session.clear()
    from flask import flash
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string(DASHBOARD_PAGE, title='Dashboard')

@app.route('/profile')
@login_required
def profile():
    return render_template_string(PROFILE_PAGE, title='Profile')

if __name__ == '__main__':
    app.run(debug=False, port=5000)
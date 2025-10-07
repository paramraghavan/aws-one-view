'''python
# requirements.txt
flask==2.3.3
flask-login==0.6.2
python-ldap==3.4.3

# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required,  current_user
import ldap
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# LDAP configuration
LDAP_SERVER = 'ldap://your.domain.com'  # Replace with your AD server
LDAP_BASE_DN = 'DC=domain,DC=com'       # Replace with your base DN

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    return User(username)

def authenticate_ldap(username, password):
    try:
        # Initialize LDAP connection
        ldap_client = ldap.initialize(LDAP_SERVER)
        ldap_client.set_option(ldap.OPT_REFERRALS, 0)
        
        # Bind with user credentials
        user_dn = f'CN={username},{LDAP_BASE_DN}'
        ldap_client.simple_bind_s(user_dn, password)
        
        return True
    except ldap.INVALID_CREDENTIALS:
        return False
    except ldap.SERVER_DOWN:
        flash('LDAP server is unavailable')
        return False
    finally:
        ldap_client.unbind()

def audit_log(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logging.info(f"Access to {f.__name__} by {current_user.id if current_user.is_authenticated else 'anonymous'}")
        return f(*args, **kwargs)
    return decorated_function


# For global audit logging across all endpoints:
@app.before_request
def log_request():
    if current_user.is_authenticated:
        logging.info(f"User {current_user.id} requested {request.endpoint}")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if authenticate_ldap(username, password):
            user = User(username)
            login_user(user)
            return redirect(url_for('protected'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/protected')
@login_required
@audit_log
def protected():
    return render_template('protected.html')

if __name__ == '__main__':
    app.run(debug=True)
'''

'''html
# templates/login.html
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        .login-container {
            width: 300px;
            margin: 100px auto;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 8px;
            margin-top: 5px;
        }
        .flash-messages {
            color: red;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>Login</h2>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <div class="flash-messages">
                    {{ messages[0] }}
                </div>
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label>Username:</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Password:</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>

# templates/protected.html
<!DOCTYPE html>
<html>
<head>
    <title>Protected Page</title>
</head>
<body>
    <h1>Welcome {{ current_user.id }}!</h1>
    <p>This is a protected page.</p>
    <a href="{{ url_for('logout') }}">Logout</a>
</body>
</html>
'''
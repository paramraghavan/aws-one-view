from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps  # ← MISSING IMPORT
import ldap
import logging
from datetime import timedelta
import os

app = Flask(__name__)

# Security Configuration
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))  # Use environment variable
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Auto-logout after 30 min
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookie over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# LDAP configuration
LDAP_SERVER = 'ldap://your.domain.com'
LDAP_BASE_DN = 'DC=domain,DC=com'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audit.log'),
        logging.StreamHandler()
    ]
)

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
    """Authenticate user against LDAP/Active Directory"""
    ldap_client = None
    try:
        # Initialize LDAP connection
        ldap_client = ldap.initialize(LDAP_SERVER)
        ldap_client.set_option(ldap.OPT_REFERRALS, 0)
        ldap_client.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)  # 10 second timeout

        # Bind with user credentials
        # Note: Adjust the DN format based on your AD structure
        user_dn = f'CN={username},{LDAP_BASE_DN}'
        ldap_client.simple_bind_s(user_dn, password)

        logging.info(f"Successful LDAP authentication for user: {username}")
        return True

    except ldap.INVALID_CREDENTIALS:
        logging.warning(f"Failed login attempt for user: {username} - Invalid credentials")
        return False
    except ldap.SERVER_DOWN:
        logging.error(f"LDAP server unavailable for user: {username}")
        flash('Authentication service is unavailable. Please try again later.')
        return False
    except ldap.LDAPError as e:
        logging.error(f"LDAP error for user {username}: {str(e)}")
        flash('Authentication error occurred.')
        return False
    except Exception as e:
        logging.error(f"Unexpected error during authentication for {username}: {str(e)}")
        return False
    finally:
        if ldap_client:
            try:
                ldap_client.unbind_s()
            except:
                pass


def audit_log(f):
    """Decorator for audit logging"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            logging.info(
                f"User '{current_user.id}' accessed endpoint '{f.__name__}' "
                f"from IP {request.remote_addr}"
            )
        else:
            logging.warning(f"Anonymous access attempt to {f.__name__}")
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def before_request():
    """Handle session management and audit logging"""
    if current_user.is_authenticated:
        # Make session permanent and refresh timeout on activity
        session.permanent = True
        session.modified = True

        # Audit log every request
        logging.info(
            f"User '{current_user.id}' requested '{request.endpoint}' "
            f"[{request.method}] from {request.remote_addr}"
        )


# Force HTTPS in production
@app.before_request
def force_https():
    if not app.debug and not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('protected'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Basic input validation
        if not username or not password:
            flash('Username and password are required')
            logging.warning(f"Login attempt with missing credentials from {request.remote_addr}")
            return render_template('login.html')

        # Log login attempt (NEVER log the password)
        logging.info(f"Login attempt for user: {username} from {request.remote_addr}")

        if authenticate_ldap(username, password):
            user = User(username)
            login_user(user, remember=False)
            session.permanent = True

            logging.info(f"Successful login for user: {username}")

            # Redirect to originally requested page or default to protected
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('protected'))
        else:
            flash('Invalid username or password')
            logging.warning(f"Failed login for user: {username}")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    username = current_user.id
    logout_user()
    session.clear()
    logging.info(f"User {username} logged out")
    flash('You have been logged out')
    return redirect(url_for('login'))


@app.route('/protected')
@login_required
@audit_log
def protected():
    return render_template('protected.html', username=current_user.id)


@app.route('/api/check-session')
@login_required
def check_session():
    """API endpoint to check if session is still active"""
    return {'status': 'active', 'user': current_user.id}, 200


if __name__ == '__main__':
    # NEVER use debug=True in production!
    app.run(debug=False, host='0.0.0.0', port=5000)
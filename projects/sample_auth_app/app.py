from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from datetime import timedelta
import ldap
import logging
import info

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Session configuration for 15-minute timeout
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# LDAP configuration
LDAP_SERVER = 'ldap://your.domain.com'  # Replace with your AD server
LDAP_BASE_DN = 'DC=domain,DC=com'  # Replace with your base DN

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'  # Protect against session hijacking


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
    except Exception as e:
        logging.error(f"LDAP error: {str(e)}")
        return False
    finally:
        try:
            ldap_client.unbind()
        except:
            pass


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


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('protected'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('protected'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if authenticate_ldap(username, password):
            user = User(username)
            login_user(user, remember=False)
            session.permanent = True  # Enable session timeout

            # Redirect to next page if specified, otherwise to protected
            next_page = request.args.get('next')
            return redirect(next_page or url_for('protected'))
        else:
            flash('Invalid username or password')

    return render_template('login.html', entitlement=info.entitlement)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Clear session data
    flash('You have been logged out successfully')
    return redirect(url_for('login'))


@app.route('/protected')
@login_required
@audit_log
def protected():
    return render_template('protected.html', username=current_user.id, about=info.about)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)
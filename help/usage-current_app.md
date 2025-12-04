## Using `current_app` with Config in Root Folder

Here's a practical example with a project structure:

### Project Structure

```
my_project/
├── config.py          # Config in root folder
├── app.py             # Main Flask app
└── services/
    └── email.py       # A separate module that needs config
```

---

### 1. Config File (root folder)

```python
# config.py
class Config:
    APP_NAME = 'My Shop'
    SECRET_KEY = 'super-secret-123'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
```

---

### 2. Main App

```python
# app.py
from flask import Flask
from config import Config

app = Flask(__name__)
app.config.from_object(Config)  # Load config from root folder

# Import routes after app is created
from services.email import send_welcome_email


@app.route('/')
def index():
    send_welcome_email('user@example.com')
    return 'Email sent!'


if __name__ == '__main__':
    app.run(debug=True)
```

---

### 3. Separate Module Using `current_app`

```python
# services/email.py
from flask import current_app


def send_welcome_email(user_email):
    # Access config values using current_app
    server = current_app.config['MAIL_SERVER']
    port = current_app.config['MAIL_PORT']
    app_name = current_app.config['APP_NAME']

    print(f'Connecting to {server}:{port}')
    print(f'Sending welcome email from {app_name} to {user_email}')

    # Your actual email logic here...
```

---

### Why This Works

```
Request comes in
       ↓
Flask sets up "current_app" → points to your app
       ↓
email.py calls current_app.config → gets Config values
```

---

### The Problem Without `current_app`

```python
# ❌ BAD - causes circular import!
# services/email.py
from app import app  # This imports app.py, which imports email.py... loop!


def send_welcome_email(user_email):
    server = app.config['MAIL_SERVER']
```

```python
# ✅ GOOD - no circular import
# services/email.py
from flask import current_app  # Just imports from Flask, not your app


def send_welcome_email(user_email):
    server = current_app.config['MAIL_SERVER']
```

---

### Quick Summary

| Without `current_app`         | With `current_app`         |
|-------------------------------|----------------------------|
| Need to import `app` directly | No direct import needed    |
| Risk of circular imports      | Safe from circular imports |
| Tightly coupled code          | Loosely coupled, cleaner   |

`current_app` simply says: "Give me whatever Flask app is currently handling this request" — so your helper modules
don't need to know about `app.py` directly.
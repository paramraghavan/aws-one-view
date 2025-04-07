# Multiple web apps on a single port (7000).

**Features**

* Main App: A landing page that links to all sub-applications
* App 1: A simple content-based app with basic pages
* App 2: A dashboard application with mock metrics
* App 3: An API-focused application with a JSON endpoint and frontend integration

```python
# Project Structure:
# multi_flask_app/
# ├── app.py              # Main application entry point
# ├── config.py           # Configuration settings
# ├── requirements.txt    # Dependencies
# ├── static/             # Shared static files
# │   ├── css/
# │   ├── js/
# │   └── img/
# └── apps/               # Individual applications
#     ├── app1/           # First application
#     │   ├── __init__.py
#     │   ├── routes.py
#     │   ├── models.py
#     │   └── templates/
#     │       └── app1/
#     ├── app2/           # Second application
#     │   ├── __init__.py
#     │   ├── routes.py
#     │   ├── models.py
#     │   └── templates/
#     │       └── app2/
#     └── app3/           # Third application
#         ├── __init__.py
#         ├── routes.py
#         ├── models.py
#         └── templates/
#             └── app3/
```

 ## Access the application via:
* Main app: http://localhost:7000/
* App 1: http://localhost:7000/app1/
* App 2: http://localhost:7000/app2/
* App 3: http://localhost:7000/app3/
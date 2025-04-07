from flask import Blueprint

# Create the blueprint
app1 = Blueprint('app1', __name__, template_folder='templates', url_prefix='/app1')

# Import routes after creating the blueprint to avoid circular imports
# Define a function to initialize routes
def init_app():
    from apps.app1 import routes
    return app1
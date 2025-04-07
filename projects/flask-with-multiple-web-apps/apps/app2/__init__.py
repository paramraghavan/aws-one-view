from flask import Blueprint

# Create the blueprint
app2 = Blueprint('app2', __name__, template_folder='templates', url_prefix='/app2')

# Define a function to initialize routes
def init_app():
    from apps.app2 import routes
    return app2
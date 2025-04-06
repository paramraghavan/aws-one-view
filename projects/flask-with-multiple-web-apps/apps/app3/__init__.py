from flask import Blueprint

# Create the blueprint
app3 = Blueprint('app3', __name__, template_folder='templates', url_prefix='/app3')

# Define a function to initialize routes
def init_app():
    from apps.app3 import routes
    return app3
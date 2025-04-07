from flask import Flask, render_template

from config import Config
# Import init_app functions instead of blueprints directly
from apps.app1 import init_app as init_app1
from apps.app2 import init_app as init_app2
from apps.app3 import init_app as init_app3

app = Flask(__name__)
app.config.from_object(Config)

# Register all blueprints by calling their init_app functions
app.register_blueprint(init_app1())
app.register_blueprint(init_app2())
app.register_blueprint(init_app3())

# Root route
@app.route('/')
def index():
    return render_template('index.html', title='Multi-App Flask Demo')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7071, debug=True)
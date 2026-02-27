#!/usr/bin/env python
"""
Run the Data Ingest Flask Application
"""
if __name__ == '__main__':
    from app import app, socketio
    import os

    socketio.run(
        app,
        host='0.0.0.0',
        port=5123,
        debug=os.getenv('FLASK_ENV') == 'development'
    )

#!/usr/bin/env python
"""
Run the Data Ingest Flask Application
Configured for PyCharm debugging with threading instead of eventlet
"""
if __name__ == '__main__':
    import os
    import sys

    # Set debug mode
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'

    from app import app, socketio

    print("\n" + "="*60)
    print("Starting Flask App with Socket.IO")
    print("="*60)
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")
    print(f"FLASK_DEBUG: {os.getenv('FLASK_DEBUG')}")
    print(f"Running on: http://0.0.0.0:5123")
    print("="*60 + "\n")

    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5123,
            debug=True,
            use_reloader=False,         # Disable auto-reload (interferes with debugging)
            async_mode='threading',     # Use threading instead of eventlet for better debug support
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        print(f"\n[ERROR] Failed to start app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

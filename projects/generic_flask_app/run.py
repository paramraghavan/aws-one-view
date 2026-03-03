#!/usr/bin/env python
"""
Run the Data Ingest Flask Application
Simple polling approach: Browser polls /api/stream_event every second
"""
if __name__ == '__main__':
    import os
    import sys

    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'

    from app import app

    print("\n" + "="*60)
    print("Starting Flask App (Simple Polling)")
    print("="*60)
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")
    print(f"FLASK_DEBUG: {os.getenv('FLASK_DEBUG')}")
    print(f"Running on: http://localhost:5123")
    print("Output method: Browser polls /api/stream_event every 1 second")
    print("="*60 + "\n")

    try:
        app.run(
            host='0.0.0.0',
            port=5123,
            debug=True,
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        print(f"\n[ERROR] Failed to start app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

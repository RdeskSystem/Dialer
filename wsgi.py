#!/usr/bin/env python
import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from src.main import app, socketio

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
else:
    # For WSGI servers
    application = app


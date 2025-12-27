#!/usr/bin/env python3
"""
FastCGI dispatcher for DreamHost shared hosting.
This script should be placed in your web-accessible directory and made executable.
"""

import sys
import os

# Set the path to your application directory
# Adjust this to match your actual directory structure
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# Set environment variables for image and cache directories
# IMPORTANT: Change these paths to match your server setup
os.environ['IMAGE_ROOT'] = os.path.join(os.path.expanduser('~'), 'images')
os.environ['CACHE_ROOT'] = os.path.join(APP_DIR, 'cache')

# Import and run the application with error handling
try:
    from app import application
    from flup.server.fcgi import WSGIServer
except ImportError as e:
    # Write error to stderr so it appears in Apache error logs
    sys.stderr.write("ERROR: Failed to import required modules.\n")
    sys.stderr.write("Import error: {0}\n".format(str(e)))
    sys.stderr.write("Make sure dependencies are installed: pip install -r requirements.txt\n")
    sys.stderr.write("Python path: {0}\n".format(sys.path))
    sys.stderr.write("Python version: {0}\n".format(sys.version))
    sys.exit(1)
except Exception as e:
    # Catch any other initialization errors
    sys.stderr.write("ERROR: Unexpected error during initialization.\n")
    sys.stderr.write("Error: {0}\n".format(str(e)))
    sys.exit(1)

if __name__ == '__main__':
    try:
        WSGIServer(application).run()
    except Exception as e:
        # Write error to stderr so it appears in Apache error logs
        sys.stderr.write("ERROR: Failed to start FastCGI server.\n")
        sys.stderr.write("Error: {0}\n".format(str(e)))
        sys.exit(1)

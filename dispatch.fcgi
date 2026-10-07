#!/usr/bin/env python3
"""
FastCGI dispatcher for DreamHost shared hosting.
This script should be placed in your web-accessible directory and made executable.
"""

import sys
import os
import traceback

# Re-exec under the bundled virtualenv (created by the deploy workflow) if present,
# so the shebang doesn't need hand-editing and survives redeploys.
_VENV_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'bin', 'python3')
if os.path.exists(_VENV_PY) and os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(_VENV_PY))):
    os.execv(_VENV_PY, [_VENV_PY] + sys.argv)

def log_error(message):
    """Write error message to stderr and flush immediately."""
    print(message, file=sys.stderr)
    sys.stderr.flush()

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
    # Write detailed error to stderr with flush for Apache error logs
    log_error("=" * 70)
    log_error("SIMPLE-ALBUM FASTCGI ERROR: Failed to import required modules")
    log_error("=" * 70)
    log_error("Import error: {0}".format(str(e)))
    log_error("")
    log_error("Python version: {0}".format(sys.version))
    log_error("Python executable: {0}".format(sys.executable))
    log_error("Python path: {0}".format(sys.path))
    log_error("")
    log_error("SOLUTION: Make sure dependencies are installed:")
    log_error("  pip install -r requirements.txt")
    log_error("")
    log_error("Full traceback:")
    log_error(traceback.format_exc())
    log_error("=" * 70)
    sys.exit(1)
except Exception as e:
    # Catch any other initialization errors
    log_error("=" * 70)
    log_error("SIMPLE-ALBUM FASTCGI ERROR: Unexpected initialization error")
    log_error("=" * 70)
    log_error("Error: {0}".format(str(e)))
    log_error("Python version: {0}".format(sys.version))
    log_error("")
    log_error("Full traceback:")
    log_error(traceback.format_exc())
    log_error("=" * 70)
    sys.exit(1)

if __name__ == '__main__':
    try:
        WSGIServer(application).run()
    except Exception as e:
        # Write error to stderr with flush for Apache error logs
        log_error("=" * 70)
        log_error("SIMPLE-ALBUM FASTCGI ERROR: Failed to start server")
        log_error("=" * 70)
        log_error("Error: {0}".format(str(e)))
        log_error("")
        log_error("Full traceback:")
        log_error(traceback.format_exc())
        log_error("=" * 70)
        sys.exit(1)

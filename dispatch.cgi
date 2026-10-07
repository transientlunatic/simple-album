#!/usr/bin/env python3
"""
CGI dispatcher for DreamHost shared hosting.
This script should be placed in your web-accessible directory and made executable.

Note: This is a standard CGI implementation that works around flup's Python 3 
compatibility issues. If FastCGI is available, use dispatch.fcgi instead for 
better performance.
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

# Import the application with error handling
try:
    from app import application
except ImportError as e:
    # Write detailed error to stderr with flush for Apache error logs
    log_error("=" * 70)
    log_error("SIMPLE-ALBUM CGI ERROR: Failed to import required modules")
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
    log_error("SIMPLE-ALBUM CGI ERROR: Unexpected initialization error")
    log_error("=" * 70)
    log_error("Error: {0}".format(str(e)))
    log_error("Python version: {0}".format(sys.version))
    log_error("")
    log_error("Full traceback:")
    log_error(traceback.format_exc())
    log_error("=" * 70)
    sys.exit(1)


def run_cgi():
    """Run the WSGI application as a CGI script."""
    # Build the WSGI environ dictionary from CGI environment
    environ = dict(os.environ.items())
    
    # Apache sets SCRIPT_NAME to the dispatcher (e.g. /dispatch.cgi) and PATH_INFO to
    # the rewritten remainder; the app routes on PATH_INFO, so expose the real script
    # name and keep PATH_INFO as given.
    environ.setdefault('PATH_INFO', '/')

    # Add WSGI-specific variables
    environ['wsgi.input'] = sys.stdin.buffer
    environ['wsgi.errors'] = sys.stderr
    environ['wsgi.version'] = (1, 0)
    environ['wsgi.multithread'] = False
    environ['wsgi.multiprocess'] = True
    environ['wsgi.run_once'] = True
    
    # Determine URL scheme
    if environ.get('HTTPS', 'off').lower() in ('on', '1', 'yes', 'true'):
        environ['wsgi.url_scheme'] = 'https'
    else:
        environ['wsgi.url_scheme'] = 'http'
    
    # Track headers
    headers_set = []
    headers_sent = []
    
    def send_headers():
        """Emit the CGI status line and headers (once)."""
        status, response_headers = headers_set
        out = sys.stdout.buffer
        out.write(b'Status: ' + status.encode('latin-1') + b'\r\n')
        for header_name, header_value in response_headers:
            out.write(header_name.encode('latin-1') + b': ' +
                      header_value.encode('latin-1') + b'\r\n')
        out.write(b'\r\n')
        headers_sent.append(True)

    def write(data):
        """Write response data to stdout."""
        if not headers_set:
            raise AssertionError("write() before start_response()")
        if not headers_sent:
            send_headers()
        if isinstance(data, str):
            data = data.encode('utf-8')
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    def start_response(status, response_headers, exc_info=None):
        """WSGI start_response callable."""
        if exc_info:
            try:
                if headers_sent:
                    # Re-raise original exception if headers already sent
                    raise exc_info[1].with_traceback(exc_info[2])
            finally:
                exc_info = None  # Avoid circular reference
        elif headers_set:
            raise AssertionError("Headers already set!")
        
        headers_set[:] = [status, response_headers]
        return write
    
    # Run the application
    try:
        result = application(environ, start_response)
        try:
            for data in result:
                if data:  # Don't send headers until body appears
                    write(data)
            if not headers_sent and headers_set:
                send_headers()  # Body was empty
                sys.stdout.buffer.flush()
        finally:
            if hasattr(result, 'close'):
                result.close()
    except Exception as e:
        log_error("=" * 70)
        log_error("SIMPLE-ALBUM CGI ERROR: Failed to run application")
        log_error("=" * 70)
        log_error("Error: {0}".format(str(e)))
        log_error("")
        log_error("Full traceback:")
        log_error(traceback.format_exc())
        log_error("=" * 70)
        if not headers_sent:
            # Return a proper 500 rather than "End of script output before headers"
            sys.stdout.buffer.write(b'Status: 500 Internal Server Error\r\n'
                                    b'Content-Type: text/plain\r\n\r\n'
                                    b'Internal Server Error\n')
            sys.stdout.buffer.flush()
        sys.exit(1)


if __name__ == '__main__':
    run_cgi()

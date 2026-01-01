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
    
    # Add WSGI-specific variables
    environ['wsgi.input'] = sys.stdin.buffer if hasattr(sys.stdin, 'buffer') else sys.stdin
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
    
    def write(data):
        """Write response data to stdout."""
        if not headers_set:
            raise AssertionError("write() before start_response()")
        
        if not headers_sent:
            # Send headers before first data write
            status, response_headers = headers_sent[:] = headers_set
            # Use stdout.buffer for binary data in Python 3
            output = sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout
            output.write(b'Status: ' + status.encode('latin-1') + b'\r\n')
            for header_name, header_value in response_headers:
                output.write(header_name.encode('latin-1') + b': ' + 
                           header_value.encode('latin-1') + b'\r\n')
            output.write(b'\r\n')
            output.flush()
        
        # Write data - ensure it's bytes
        output = sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout
        if isinstance(data, str):
            data = data.encode('utf-8')
        output.write(data)
        output.flush()
    
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
            if not headers_sent:
                write(b'')  # Send headers if body was empty
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
        sys.exit(1)


if __name__ == '__main__':
    run_cgi()

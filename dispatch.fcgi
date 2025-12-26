#!/usr/bin/env python
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

# Import and run the application
from app import application
from flup.server.fcgi import WSGIServer

if __name__ == '__main__':
    WSGIServer(application).run()

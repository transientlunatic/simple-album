#!/usr/bin/env python3
"""
Example usage of the image server for local testing/development.
"""

import os
import sys
from pathlib import Path

# Set up paths
BASE_DIR = Path(__file__).parent
os.environ['IMAGE_ROOT'] = str(BASE_DIR / 'example_images')
os.environ['CACHE_ROOT'] = str(BASE_DIR / 'cache')

# Import and run
from app import application
from flup.server.fcgi import WSGIServer

if __name__ == '__main__':
    print("="*60)
    print("Simple Album - Image Server")
    print("="*60)
    print(f"Image directory: {os.environ['IMAGE_ROOT']}")
    print(f"Cache directory: {os.environ['CACHE_ROOT']}")
    print()
    print("Place your images in the 'example_images' directory")
    print("Then access them via: http://localhost:8000/path/to/image.jpg?w=800")
    print()
    print("Starting server...")
    print("="*60)
    
    try:
        WSGIServer(application, bindAddress=('localhost', 8000)).run()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        sys.exit(0)

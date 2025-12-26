#!/usr/bin/env python3
"""
Simple Album - FastCGI Image Server
Serves resized versions of images stored in a directory structure.
Resized versions are cached to avoid regeneration.
"""

import os
import sys
import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, unquote
from io import BytesIO

try:
    from PIL import Image
    from flup.server.fcgi import WSGIServer
except ImportError as e:
    raise ImportError(
        f"Missing required library for Simple Album. Please install dependencies: {e}. "
        "Run: pip install -r requirements.txt"
    ) from e


class ImageServer:
    """Handles image serving with resizing and caching."""
    
    def __init__(self, image_root, cache_root):
        """
        Initialize the image server.
        
        Args:
            image_root: Path to the directory containing original images
            cache_root: Path to the directory for cached resized images
        """
        self.image_root = Path(image_root).resolve()
        self.cache_root = Path(cache_root).resolve()
        
        # Create cache directory if it doesn't exist
        self.cache_root.mkdir(parents=True, exist_ok=True)
        
        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    
    def _is_safe_path(self, requested_path):
        """
        Check if the requested path is within the image root directory.
        Prevents directory traversal attacks.
        
        Args:
            requested_path: The path to check
            
        Returns:
            bool: True if safe, False otherwise
        """
        try:
            resolved = (self.image_root / requested_path).resolve()
        except (ValueError, RuntimeError):
            return False

        # Safely ensure the resolved path is within image_root
        # Use Path.is_relative_to when available (Python 3.9+)
        if hasattr(resolved, "is_relative_to"):
            return resolved.is_relative_to(self.image_root)

        # Fallback for Python 3.6–3.8: use an os.path.sep-aware prefix check
        resolved_str = str(resolved)
        root_str = str(self.image_root)
        return resolved_str == root_str or resolved_str.startswith(root_str + os.path.sep)
    
    def _get_cache_path(self, image_path, width, height, quality):
        """
        Generate a cache path for a resized image.
        
        Args:
            image_path: Path to the original image
            width: Target width
            height: Target height
            quality: JPEG quality
            
        Returns:
            Path: Cache file path
        """
        # Create a hash of the parameters for the cache filename
        # Using SHA-256 for better security practices
        cache_key = f"{str(image_path.resolve())}_{width}_{height}_{quality}".encode('utf-8')
        cache_hash = hashlib.sha256(cache_key).hexdigest()[:32]  # Use first 32 chars
        
        # Preserve the file extension
        ext = image_path.suffix.lower()
        cache_filename = f"{cache_hash}{ext}"
        
        return self.cache_root / cache_filename
    
    def _resize_image(self, image_path, width=None, height=None, quality=85):
        """
        Resize an image while maintaining aspect ratio.
        
        Args:
            image_path: Path to the original image
            width: Target width (optional)
            height: Target height (optional)
            quality: JPEG quality (1-100)
            
        Returns:
            BytesIO: Resized image data
        """
        with Image.open(image_path) as img:
            original_width, original_height = img.size
            
            # If no dimensions specified, return original
            if width is None and height is None:
                output = BytesIO()
                # Only apply quality to JPEG images
                if img.format == 'JPEG':
                    img.save(output, format=img.format, quality=quality)
                else:
                    img.save(output, format=img.format or 'PNG')
                output.seek(0)
                return output
            
            # Calculate new dimensions maintaining aspect ratio
            if width and height:
                # Both specified - fit within box (thumbnail maintains aspect ratio)
                # Make a copy since thumbnail modifies in-place
                img = img.copy()
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
            elif width:
                # Only width specified
                aspect_ratio = original_height / original_width
                new_height = int(width * aspect_ratio)
                img = img.resize((width, new_height), Image.Resampling.LANCZOS)
            else:
                # Only height specified
                aspect_ratio = original_width / original_height
                new_width = int(height * aspect_ratio)
                img = img.resize((new_width, height), Image.Resampling.LANCZOS)
            
            # Save to BytesIO
            output = BytesIO()
            
            # Determine if this is a JPEG based on file extension
            is_jpeg = image_path.suffix.lower() in {'.jpg', '.jpeg'}
            
            if is_jpeg:
                # Ensure image is in a JPEG-compatible mode
                if img.mode in ('RGBA', 'LA', 'PA'):
                    # Convert to RGBA (if needed) then composite onto white background
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    # Use alpha channel as mask (index 3 after RGBA conversion)
                    background.paste(img, mask=img.split()[3])
                    img_to_save = background
                elif img.mode not in ('RGB', 'L'):
                    # Convert unsupported modes (e.g., P, CMYK, etc.) to RGB
                    img_to_save = img.convert('RGB')
                else:
                    # Already JPEG-compatible (RGB or L)
                    img_to_save = img
                
                # JPEG format - apply quality
                img_to_save.save(output, format='JPEG', quality=quality)
            else:
                # Other formats - don't use quality parameter
                # Determine format from original image or use PNG as default
                save_format = img.format if img.format else 'PNG'
                img.save(output, format=save_format)
            
            output.seek(0)
            return output
    
    def serve_image(self, path, width=None, height=None, quality=85):
        """
        Serve an image, resizing if necessary and using cache if available.
        
        Args:
            path: Requested image path
            width: Target width (optional)
            height: Target height (optional)
            quality: JPEG quality (1-100)
            
        Returns:
            tuple: (status, content_type, image_data) or (status, content_type, error_message)
        """
        # Decode and normalize path
        path = unquote(path).lstrip('/')
        
        # Security check
        if not self._is_safe_path(path):
            return (403, 'text/plain', b'Forbidden: Invalid path')
        
        image_path = self.image_root / path
        
        # Check if file exists
        if not image_path.is_file():
            return (404, 'text/plain', b'Not Found: Image does not exist')
        
        # Check if file is an image
        if image_path.suffix.lower() not in self.supported_formats:
            return (400, 'text/plain', b'Bad Request: Unsupported file type')
        
        # Determine content type
        content_type = mimetypes.guess_type(str(image_path))[0] or 'image/jpeg'
        
        # If no resizing needed, serve original
        if width is None and height is None:
            try:
                with open(image_path, 'rb') as f:
                    return (200, content_type, f.read())
            except IOError:
                return (500, 'text/plain', b'Internal Server Error: Cannot read image')
        
        # Check cache
        cache_path = self._get_cache_path(image_path, width, height, quality)
        
        if cache_path.exists():
            # Check if cache is newer than original
            if cache_path.stat().st_mtime >= image_path.stat().st_mtime:
                try:
                    with open(cache_path, 'rb') as f:
                        return (200, content_type, f.read())
                except IOError:
                    pass  # Fall through to regenerate
        
        # Resize and cache
        try:
            resized_data = self._resize_image(image_path, width, height, quality)
            image_bytes = resized_data.read()
            
            # Save to cache
            try:
                with open(cache_path, 'wb') as f:
                    f.write(image_bytes)
            except IOError:
                pass  # Cache write failed, but we can still serve the image
            
            return (200, content_type, image_bytes)
        except Exception as e:
            return (500, 'text/plain', f'Internal Server Error: {str(e)}'.encode('utf-8'))


def application(environ, start_response):
    """
    WSGI application entry point.
    
    Args:
        environ: WSGI environment dict
        start_response: WSGI start_response callable
        
    Returns:
        list: Response body
    """
    # Get configuration from environment or use defaults
    image_root = os.environ.get('IMAGE_ROOT', '/home/username/images')
    cache_root = os.environ.get('CACHE_ROOT', '/home/username/simple-album/cache')
    
    # Initialize server
    server = ImageServer(image_root, cache_root)
    
    # Get request path
    path = environ.get('PATH_INFO', '/')
    
    # Parse query parameters
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    
    # Extract resize parameters
    width = None
    height = None
    quality = 85
    
    if 'w' in params:
        try:
            width = int(params['w'][0])
            width = max(1, min(width, 4000))  # Limit to reasonable range
        except (ValueError, IndexError):
            pass
    
    if 'h' in params:
        try:
            height = int(params['h'][0])
            height = max(1, min(height, 4000))  # Limit to reasonable range
        except (ValueError, IndexError):
            pass
    
    if 'q' in params:
        try:
            quality = int(params['q'][0])
            quality = max(1, min(quality, 100))  # Limit to valid range
        except (ValueError, IndexError):
            pass
    
    # Serve the image
    status_code, content_type, data = server.serve_image(path, width, height, quality)
    
    # Set response status
    status_messages = {
        200: 'OK',
        400: 'Bad Request',
        403: 'Forbidden',
        404: 'Not Found',
        500: 'Internal Server Error'
    }
    status = f'{status_code} {status_messages.get(status_code, "Error")}'
    
    # Set response headers
    response_headers = [
        ('Content-Type', content_type),
        ('Content-Length', str(len(data))),
    ]
    
    # Add caching headers for successful responses
    if status_code == 200:
        response_headers.extend([
            ('Cache-Control', 'public, max-age=31536000'),  # 1 year

        ])
    
    start_response(status, response_headers)
    return [data]


if __name__ == '__main__':
    # Check if configuration is provided
    if 'IMAGE_ROOT' not in os.environ:
        print("Warning: IMAGE_ROOT environment variable not set. Using default.")
        print("Set IMAGE_ROOT to the directory containing your images.")
        print("Set CACHE_ROOT to the directory for cached resized images.")
        print()
    
    # Start FastCGI server
    try:
        WSGIServer(application).run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

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
import configparser
from pathlib import Path
from urllib.parse import parse_qs, unquote
from io import BytesIO

try:
    from PIL import Image
    from flup.server.fcgi import WSGIServer
except ImportError as e:
    raise ImportError(
        "Missing required library for Simple Album. Please install dependencies with "
        "'pip install -r requirements.txt'. Original error: {0}".format(e)
    ) from e


class ImageServer:
    """Handles image serving with resizing and caching."""
    
    def __init__(self, image_root, cache_root, max_width=4000, max_height=4000, 
                 default_quality=85, max_file_size_mb=50):
        """
        Initialize the image server.
        
        Args:
            image_root: Path to the directory containing original images
            cache_root: Path to the directory for cached resized images
            max_width: Maximum allowed width in pixels
            max_height: Maximum allowed height in pixels
            default_quality: Default JPEG quality (1-100)
            max_file_size_mb: Maximum file size in MB to serve (prevents memory issues)
        """
        self.image_root = Path(image_root).resolve()
        self.cache_root = Path(cache_root).resolve()
        self.max_width = max_width
        self.max_height = max_height
        self.default_quality = default_quality
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
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
                # Check for zero dimensions to prevent division by zero
                if original_width == 0:
                    raise ValueError("Image has invalid width (0 pixels)")
                aspect_ratio = original_height / original_width
                new_height = int(width * aspect_ratio)
                img = img.resize((width, new_height), Image.Resampling.LANCZOS)
            else:
                # Only height specified
                # Check for zero dimensions to prevent division by zero
                if original_height == 0:
                    raise ValueError("Image has invalid height (0 pixels)")
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
        
        # Check file size to prevent memory issues
        try:
            file_size = image_path.stat().st_size
            if file_size > self.max_file_size_bytes:
                return (413, 'text/plain', b'Request Entity Too Large: Image file too large')
        except OSError:
            return (500, 'text/plain', b'Internal Server Error: Cannot access file')
        
        # Check if file is an image
        if image_path.suffix.lower() not in self.supported_formats:
            return (400, 'text/plain', b'Bad Request: Unsupported file type')
        
        # Determine content type
        content_type = mimetypes.guess_type(str(image_path))[0] or 'image/jpeg'
        
        # Check if we need to process the image (resize or quality adjustment)
        # If no dimensions specified but quality is provided for JPEG, we might still want to apply quality
        needs_processing = width is not None or height is not None
        is_jpeg = image_path.suffix.lower() in {'.jpg', '.jpeg'}
        
        # If quality parameter is provided for JPEG and differs from default, treat as needing processing
        if is_jpeg and quality != self.default_quality and not needs_processing:
            needs_processing = True
        
        # If no processing needed, serve original
        if not needs_processing:
            try:
                with open(image_path, 'rb') as f:
                    return (200, content_type, f.read())
            except IOError:
                return (500, 'text/plain', b'Internal Server Error: Cannot read file')
        
        # Check cache
        cache_path = self._get_cache_path(image_path, width, height, quality)
        
        if cache_path.exists():
            # Check if cache is newer than original
            if cache_path.stat().st_mtime >= image_path.stat().st_mtime:
                try:
                    with open(cache_path, 'rb') as f:
                        return (200, content_type, f.read())
                except IOError:
                    # Cache read failed, fall through to regenerate
                    pass
        
        # Resize and cache
        try:
            resized_data = self._resize_image(image_path, width, height, quality)
            image_bytes = resized_data.read()
            
            # Save to cache
            try:
                with open(cache_path, 'wb') as f:
                    f.write(image_bytes)
            except IOError:
                # Cache write failed, but we can still serve the image
                pass
            
            return (200, content_type, image_bytes)
        except Exception:
            # Don't expose internal error details to users
            return (500, 'text/plain', b'Internal Server Error: Unable to process image')


def load_config():
    """
    Load configuration from config.ini file or environment variables.
    Environment variables take precedence over config file.
    
    Returns:
        dict: Configuration dictionary
    """
    config = {
        'image_root': '/home/username/images',
        'cache_root': '/home/username/simple-album/cache',
        'default_quality': 85,
        'max_width': 4000,
        'max_height': 4000,
        'max_file_size_mb': 50,
        'cache_max_age': 604800,  # 1 week in seconds
    }
    
    # Try to load from config.ini file
    config_path = Path(__file__).parent / 'config.ini'
    if config_path.exists():
        parser = configparser.ConfigParser()
        try:
            parser.read(config_path)
            
            if parser.has_section('server'):
                if parser.has_option('server', 'image_root'):
                    config['image_root'] = parser.get('server', 'image_root')
                if parser.has_option('server', 'cache_root'):
                    config['cache_root'] = parser.get('server', 'cache_root')
            
            if parser.has_section('resize'):
                if parser.has_option('resize', 'default_quality'):
                    config['default_quality'] = parser.getint('resize', 'default_quality')
                if parser.has_option('resize', 'max_width'):
                    config['max_width'] = parser.getint('resize', 'max_width')
                if parser.has_option('resize', 'max_height'):
                    config['max_height'] = parser.getint('resize', 'max_height')
                if parser.has_option('resize', 'max_file_size_mb'):
                    config['max_file_size_mb'] = parser.getint('resize', 'max_file_size_mb')
            
            if parser.has_section('cache'):
                if parser.has_option('cache', 'max_age'):
                    config['cache_max_age'] = parser.getint('cache', 'max_age')
        except (configparser.Error, ValueError):
            # If config file is malformed, just use defaults
            pass
    
    # Environment variables override config file
    if 'IMAGE_ROOT' in os.environ:
        config['image_root'] = os.environ['IMAGE_ROOT']
    if 'CACHE_ROOT' in os.environ:
        config['cache_root'] = os.environ['CACHE_ROOT']
    if 'DEFAULT_QUALITY' in os.environ:
        try:
            config['default_quality'] = int(os.environ['DEFAULT_QUALITY'])
        except ValueError:
            pass
    if 'MAX_WIDTH' in os.environ:
        try:
            config['max_width'] = int(os.environ['MAX_WIDTH'])
        except ValueError:
            pass
    if 'MAX_HEIGHT' in os.environ:
        try:
            config['max_height'] = int(os.environ['MAX_HEIGHT'])
        except ValueError:
            pass
    if 'MAX_FILE_SIZE_MB' in os.environ:
        try:
            config['max_file_size_mb'] = int(os.environ['MAX_FILE_SIZE_MB'])
        except ValueError:
            pass
    if 'CACHE_MAX_AGE' in os.environ:
        try:
            config['cache_max_age'] = int(os.environ['CACHE_MAX_AGE'])
        except ValueError:
            pass
    
    return config


def get_server():
    """
    Get or create the server instance.
    This is called lazily to avoid errors during import.
    """
    global _server, _config
    if _server is None:
        _config = load_config()
        _server = ImageServer(
            _config['image_root'],
            _config['cache_root'],
            max_width=_config['max_width'],
            max_height=_config['max_height'],
            default_quality=_config['default_quality'],
            max_file_size_mb=_config['max_file_size_mb']
        )
    return _server, _config


# Module-level variables (initialized lazily)
_config = None
_server = None


def application(environ, start_response):
    """
    WSGI application entry point.
    
    Args:
        environ: WSGI environment dict
        start_response: WSGI start_response callable
        
    Returns:
        list: Response body
    """
    # Get the server instance (initialized lazily on first request)
    server, config = get_server()
    
    # Get request path
    path = environ.get('PATH_INFO', '/')
    
    # Parse query parameters
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)
    
    # Extract resize parameters
    width = None
    height = None
    quality = config['default_quality']
    
    if 'w' in params:
        try:
            width = int(params['w'][0])
            width = max(1, min(width, config['max_width']))  # Limit to configured range
        except (ValueError, IndexError):
            # Invalid parameter, ignore
            pass
    
    if 'h' in params:
        try:
            height = int(params['h'][0])
            height = max(1, min(height, config['max_height']))  # Limit to configured range
        except (ValueError, IndexError):
            # Invalid parameter, ignore
            pass
    
    if 'q' in params:
        try:
            quality = int(params['q'][0])
            quality = max(1, min(quality, 100))  # Limit to valid range
        except (ValueError, IndexError):
            # Invalid parameter, use default
            pass
    
    # Serve the image
    status_code, content_type, data = server.serve_image(path, width, height, quality)
    
    # Set response status
    status_messages = {
        200: 'OK',
        400: 'Bad Request',
        403: 'Forbidden',
        404: 'Not Found',
        413: 'Request Entity Too Large',
        500: 'Internal Server Error'
    }
    status = '{0} {1}'.format(status_code, status_messages.get(status_code, 'Error'))
    
    # Set response headers
    response_headers = [
        ('Content-Type', content_type),
        ('Content-Length', str(len(data))),
    ]
    
    # Add caching headers for successful responses
    if status_code == 200:
        response_headers.extend([
            ('Cache-Control', 'public, max-age={0}'.format(config['cache_max_age'])),
        ])
    
    start_response(status, response_headers)
    return [data]
    
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

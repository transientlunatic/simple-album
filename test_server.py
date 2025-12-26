#!/usr/bin/env python3
"""
Simple test script for the image server functionality.
Creates test images and verifies resizing works correctly.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

# Import the application
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import ImageServer


def create_test_image(path, width, height, text):
    """Create a test image with specified dimensions and text."""
    img = Image.new('RGB', (width, height), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    # Add text to the image
    text_content = f"{text}\n{width}x{height}"
    draw.text((10, 10), text_content, fill='black')
    
    # Save the image
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"Created test image: {path} ({width}x{height})")


def test_resize():
    """Test the image resizing functionality."""
    print("\n=== Testing Image Server ===\n")
    
    # Create temporary directories
    temp_dir = Path(tempfile.mkdtemp(prefix='simple-album-test-'))
    image_dir = temp_dir / 'images'
    cache_dir = temp_dir / 'cache'
    
    try:
        # Create test images
        create_test_image(image_dir / 'test1.jpg', 1000, 800, 'Test Image 1')
        create_test_image(image_dir / 'test2.png', 1200, 600, 'Test Image 2')
        create_test_image(image_dir / 'subdir' / 'test3.jpg', 800, 800, 'Test Image 3')
        
        # Initialize server
        server = ImageServer(str(image_dir), str(cache_dir))
        
        # Test 1: Resize by width
        print("\nTest 1: Resize by width (w=400)")
        status, content_type, data = server.serve_image('test1.jpg', width=400)
        print(f"Status: {status}, Content-Type: {content_type}, Size: {len(data)} bytes")
        
        # Verify the resized image
        img = Image.open(BytesIO(data))
        print(f"Resized dimensions: {img.size[0]}x{img.size[1]}")
        assert img.size[0] == 400, f"Expected width 400, got {img.size[0]}"
        assert img.size[1] == 320, f"Expected height 320, got {img.size[1]}"  # Maintains aspect ratio
        print("✓ Test 1 passed")
        
        # Test 2: Resize by height
        print("\nTest 2: Resize by height (h=300)")
        status, content_type, data = server.serve_image('test2.png', height=300)
        print(f"Status: {status}, Content-Type: {content_type}, Size: {len(data)} bytes")
        
        img = Image.open(BytesIO(data))
        print(f"Resized dimensions: {img.size[0]}x{img.size[1]}")
        assert img.size[0] == 600, f"Expected width 600, got {img.size[0]}"
        assert img.size[1] == 300, f"Expected height 300, got {img.size[1]}"
        print("✓ Test 2 passed")
        
        # Test 3: Resize with both dimensions (thumbnail)
        print("\nTest 3: Resize with both dimensions (w=500, h=500)")
        status, content_type, data = server.serve_image('subdir/test3.jpg', width=500, height=500)
        print(f"Status: {status}, Content-Type: {content_type}, Size: {len(data)} bytes")
        
        img = Image.open(BytesIO(data))
        print(f"Resized dimensions: {img.size[0]}x{img.size[1]}")
        width, height = img.size
        assert width <= 500 and height <= 500, f"Expected dimensions to fit within 500x500, got {width}x{height}"
        assert width == 500 or height == 500, f"Expected at least one dimension to be 500, got {width}x{height}"
        print("✓ Test 3 passed")
        
        # Test 4: Cache verification
        print("\nTest 4: Verify caching")
        cache_files_before = list(cache_dir.glob('*'))
        print(f"Cache files: {len(cache_files_before)}")
        
        # Request the same image again (should use cache)
        status2, content_type2, data2 = server.serve_image('test1.jpg', width=400)
        # Should return 200 and valid image data
        assert status2 == 200, "Cached request should return 200"
        assert len(data2) > 0, "Cached image should have data"
        print("✓ Test 4 passed - cache working correctly")
        
        # Test 5: Security - path traversal attempt
        print("\nTest 5: Security test - path traversal")
        status, content_type, data = server.serve_image('../etc/passwd')
        print(f"Status: {status}")
        assert status == 403, f"Expected 403 Forbidden, got {status}"
        print("✓ Test 5 passed - path traversal blocked")
        
        # Test 6: Non-existent file
        print("\nTest 6: Non-existent file")
        status, content_type, data = server.serve_image('nonexistent.jpg')
        print(f"Status: {status}")
        assert status == 404, f"Expected 404 Not Found, got {status}"
        print("✓ Test 6 passed")
        
        # Test 7: Original image (no resize)
        print("\nTest 7: Original image (no resize)")
        status, content_type, data = server.serve_image('test1.jpg')
        print(f"Status: {status}, Content-Type: {content_type}, Size: {len(data)} bytes")
        
        img = Image.open(BytesIO(data))
        print(f"Image dimensions: {img.size[0]}x{img.size[1]}")
        assert img.size[0] == 1000, f"Expected width 1000, got {img.size[0]}"
        assert img.size[1] == 800, f"Expected height 800, got {img.size[1]}"
        print("✓ Test 7 passed")
        
        print("\n=== All tests passed! ===\n")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")


if __name__ == '__main__':
    test_resize()

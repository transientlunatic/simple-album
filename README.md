# simple-album

A lightweight FastCGI-based image server for serving resized images to static site generators like Hugo, Jekyll, or Gatsby. Designed to run on DreamHost shared hosting environments and keep image files out of git repositories.

## Features

- **On-demand image resizing**: Resize images to any dimension via URL parameters
- **Intelligent caching**: Resized images are cached to avoid regeneration
- **FastCGI support**: Optimized for shared hosting environments like DreamHost
- **Secure**: Path traversal protection prevents unauthorized file access
- **Multiple formats**: Supports JPG, PNG, GIF, WebP, and BMP
- **Hugo/Jekyll friendly**: Images are accessible via predictable URLs for static site generators

## Requirements

- Python 3.6+
- Pillow (image processing)
- flup6 (FastCGI support)

## Installation

### On DreamHost Shared Hosting

1. **SSH into your DreamHost server**

2. **Create a directory for the application**:
   ```bash
   cd ~/yourdomain.com
   mkdir simple-album
   cd simple-album
   ```

3. **Clone this repository**:
   ```bash
   git clone https://github.com/transientlunatic/simple-album.git .
   ```

4. **Install dependencies** (using a virtual environment is recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Configure your image directories**:
   
   **Option A: Using config.ini file (recommended)**
   ```bash
   cp config.ini.example config.ini
   nano config.ini  # Edit paths to match your setup
   ```
   
   **Option B: Using dispatch.fcgi**
   Edit `dispatch.fcgi` and update these lines:
   ```python
   os.environ['IMAGE_ROOT'] = '/home/username/images'  # Your original images
   os.environ['CACHE_ROOT'] = '/home/username/simple-album/cache'  # Cache directory
   ```
   
   Note: Environment variables in `dispatch.fcgi` override settings in `config.ini`.

6. **Make the dispatcher executable**:
   ```bash
   chmod +x dispatch.fcgi
   ```

7. **Create the cache directory**:
   ```bash
   mkdir cache
   ```

8. **Update .htaccess** if needed:
   The included `.htaccess` should work out of the box, but verify the path to `dispatch.fcgi` matches your setup.

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/transientlunatic/simple-album.git
   cd simple-album
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the application**:
   
   **Option A: Using config.ini file (recommended)**
   ```bash
   cp config.ini.example config.ini
   nano config.ini  # Edit paths and settings
   ```
   
   **Option B: Using environment variables**
   ```bash
   export IMAGE_ROOT=/path/to/your/images
   export CACHE_ROOT=/path/to/cache
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

## Configuration

The application can be configured using either a `config.ini` file or environment variables. Environment variables take precedence over the config file.

### Config File (config.ini)

Copy `config.ini.example` to `config.ini` and adjust the settings:

```ini
[server]
image_root = /home/username/images
cache_root = /home/username/simple-album/cache

[resize]
default_quality = 85
max_width = 4000
max_height = 4000
max_file_size_mb = 50

[cache]
max_age = 604800  # 1 week in seconds
```

### Environment Variables

Alternatively, set these environment variables:

- `IMAGE_ROOT`: Directory containing original images
- `CACHE_ROOT`: Directory for cached resized images
- `DEFAULT_QUALITY`: Default JPEG quality (1-100, default: 85)
- `MAX_WIDTH`: Maximum allowed width (default: 4000)
- `MAX_HEIGHT`: Maximum allowed height (default: 4000)
- `MAX_FILE_SIZE_MB`: Maximum file size in MB (default: 50)
- `CACHE_MAX_AGE`: Cache duration in seconds (default: 604800 = 1 week)

## Usage

### URL Format

Access images using the following URL pattern:

```
https://yourdomain.com/path/to/image.jpg?w=800&h=600&q=85
```

### Parameters

- `w`: Width in pixels (optional)
- `h`: Height in pixels (optional)
- `q`: JPEG quality 1-100 (optional, default: 85)

### Examples

**Resize to specific width (maintains aspect ratio)**:
```
https://yourdomain.com/photos/vacation.jpg?w=800
```

**Resize to specific height (maintains aspect ratio)**:
```
https://yourdomain.com/photos/vacation.jpg?h=600
```

**Resize to fit within dimensions (maintains aspect ratio)**:
```
https://yourdomain.com/photos/vacation.jpg?w=800&h=600
```

**Resize with custom quality**:
```
https://yourdomain.com/photos/vacation.jpg?w=800&q=90
```

**Original image (no resizing)**:
```
https://yourdomain.com/photos/vacation.jpg
```

## Directory Structure

```
simple-album/
├── app.py              # Main application logic
├── dispatch.fcgi       # FastCGI dispatcher for DreamHost
├── .htaccess           # Apache configuration
├── requirements.txt    # Python dependencies
├── config.ini.example  # Example configuration
└── cache/             # Resized images cache (auto-created)

~/images/              # Your original images (configured in dispatch.fcgi)
├── photos/
│   ├── vacation.jpg
│   └── family.png
└── screenshots/
    └── app.png
```

## Integration with Hugo

In your Hugo templates, reference images like this:

```html
<img src="https://images.yourdomain.com/photos/vacation.jpg?w=800" 
     alt="Vacation photo">
```

Or create a shortcode in `layouts/shortcodes/img.html`:

```html
{{- $src := .Get "src" -}}
{{- $width := .Get "width" | default "800" -}}
{{- $alt := .Get "alt" | default "" -}}
<img src="https://images.yourdomain.com/{{ $src }}?w={{ $width }}" alt="{{ $alt }}">
```

Usage in content:

```markdown
{{< img src="photos/vacation.jpg" width="800" alt="Vacation photo" >}}
```

## Security

- **Path traversal protection**: The server validates all paths to prevent access to files outside the image root directory
- **File type validation**: Only image files with supported extensions are served
- **Dimension limits**: Width and height are capped at 4000 pixels to prevent resource abuse
- **Quality limits**: JPEG quality is limited to the range 1-100

## Performance

- **Caching**: Resized images are cached on first request
- **Cache invalidation**: Cached images are automatically regenerated if the original image is modified
- **HTTP caching headers**: Proper cache-control headers are sent for browser caching

## Troubleshooting

### Images not loading

1. Check file permissions:
   ```bash
   chmod 755 dispatch.fcgi
   chmod 755 app.py
   ```

2. Verify paths in `dispatch.fcgi` are correct

3. Check error logs:
   ```bash
   tail -f ~/logs/yourdomain.com/http/error.log
   ```

### 500 Internal Server Error

1. Ensure Python dependencies are installed in the correct Python environment
2. Check that the Python shebang in `dispatch.fcgi` points to the correct Python binary
3. Verify the virtual environment path if using one

### Images not resizing

1. Ensure Pillow is installed: `pip list | grep -i pillow`
2. Check cache directory permissions: `chmod 755 cache`
3. Verify the original image exists and is readable

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

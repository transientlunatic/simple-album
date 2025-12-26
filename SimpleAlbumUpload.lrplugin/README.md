# Simple Album Upload Plugin for Adobe Lightroom

This Lightroom plugin allows you to export images directly from Adobe Lightroom to your Simple Album server.

## Features

- Direct export from Lightroom to Simple Album server
- Secure API key authentication
- Customizable upload path on server
- Support for JPEG and PNG formats
- Progress tracking during upload

## Installation

1. **Locate the plugin folder**:
   - The plugin is located in the `SimpleAlbumUpload.lrplugin` directory

2. **Install in Lightroom**:
   - In Adobe Lightroom, go to `File > Plug-in Manager...`
   - Click the `Add` button
   - Navigate to and select the `SimpleAlbumUpload.lrplugin` folder
   - Click `Done`

3. **Verify installation**:
   - The plugin should now appear in the Plug-in Manager as "Simple Album Upload"

## Configuration

Before using the plugin, you need to configure your Simple Album server to accept uploads:

### Server Setup

1. **Edit your config.ini file**:
   ```ini
   [upload]
   enabled = true
   api_key = YOUR_API_KEY_HERE
   ```

2. **Generate a secure API key**:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Save the API key** - you'll need it when exporting from Lightroom

### Environment Variables (Alternative)

You can also configure uploads using environment variables:
```bash
export UPLOAD_ENABLED=true
export UPLOAD_API_KEY=your_api_key_here
```

## Usage

1. **Select photos** in Lightroom that you want to upload

2. **Export photos**:
   - Go to `File > Export...`
   - In the Export dialog, under "Export To:", select `Simple Album Server`

3. **Configure export settings**:
   - **Server URL**: Enter your Simple Album server URL (e.g., `https://images.yourdomain.com`)
   - **API Key**: Enter the API key configured on your server
   - **Upload Path**: Enter the destination path (relative to server's image_root)
     - Example: `lightroom/` will upload to `<image_root>/lightroom/`
     - Use `/` to upload to the root directory

4. **Configure image settings** (Lightroom standard export settings):
   - Format: JPEG or PNG
   - Quality: Adjust as needed
   - Color Space: sRGB or Adobe RGB
   - Image Sizing: Resize if desired

5. **Click Export** to upload your images

## Upload Path Examples

- `lightroom/` - Upload to `/lightroom/photo.jpg`
- `photos/2024/` - Upload to `/photos/2024/photo.jpg`
- `/` or empty - Upload to root `/photo.jpg`

## Troubleshooting

### Upload Failed: Invalid or missing API key

- Verify the API key in your Lightroom export settings matches the key in your server's config.ini
- Ensure upload is enabled on the server (`enabled = true` in config.ini)

### Upload Failed: Upload functionality is disabled

- Enable uploads in your server's config.ini:
  ```ini
  [upload]
  enabled = true
  ```

### Upload Failed: No response from server

- Check that your Server URL is correct
- Verify the server is running and accessible
- Check firewall settings

### Upload Failed: Forbidden: Invalid path

- Check that your Upload Path doesn't contain invalid characters
- Avoid using `..` in the path (path traversal is blocked for security)

## Security Notes

- The API key is transmitted in the URL query parameter. For production use, consider using HTTPS to encrypt the connection.
- API keys should be kept secret and not shared
- The server validates paths to prevent directory traversal attacks
- Only image files are accepted

## API Reference

The plugin uses the Simple Album server's upload API:

**Endpoint**: `POST /<path>?api_key=<key>`

**Request**:
- Method: POST
- Body: Raw image data
- Query Parameters:
  - `api_key`: Your server API key

**Response**:
- Success (201): `{"success": true, "message": "Image uploaded successfully", "path": "..."}`
- Error (4xx/5xx): `{"error": "Error message"}`

## Version

Version 1.0.0

## License

MIT License - see main repository LICENSE file for details

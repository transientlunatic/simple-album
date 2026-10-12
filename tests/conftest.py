import os
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import app as app_module  # noqa: E402


def make_image_bytes(width, height, fmt='JPEG', color='lightblue'):
    buf = BytesIO()
    Image.new('RGB', (width, height), color=color).save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def dirs(tmp_path):
    images = tmp_path / 'images'
    cache = tmp_path / 'cache'
    images.mkdir()
    (images / 'test1.jpg').write_bytes(make_image_bytes(1000, 800))
    (images / 'test2.png').write_bytes(make_image_bytes(1200, 600, 'PNG'))
    (images / 'subdir').mkdir()
    (images / 'subdir' / 'test3.jpg').write_bytes(make_image_bytes(800, 800))
    return images, cache


@pytest.fixture
def server(dirs):
    images, cache = dirs
    return app_module.ImageServer(str(images), str(cache))


@pytest.fixture
def upload_server(dirs):
    images, cache = dirs
    return app_module.ImageServer(
        str(images), str(cache), upload_enabled=True, upload_api_key='secret-key')


@pytest.fixture
def wsgi(dirs, monkeypatch):
    """Call the WSGI application against temp directories."""
    images, cache = dirs
    monkeypatch.setenv('IMAGE_ROOT', str(images))
    monkeypatch.setenv('CACHE_ROOT', str(cache))
    monkeypatch.setenv('UPLOAD_ENABLED', 'true')
    monkeypatch.setenv('UPLOAD_API_KEY', 'secret-key')
    monkeypatch.setattr(app_module, '_server', None)
    monkeypatch.setattr(app_module, '_config', None)

    def call(path, method='GET', query='', body=b'', headers=None):
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'QUERY_STRING': query,
            'CONTENT_LENGTH': str(len(body)),
            'wsgi.input': BytesIO(body),
        }
        environ.update(headers or {})
        captured = {}

        def start_response(status, response_headers, exc_info=None):
            captured['status'] = status
            captured['headers'] = dict(response_headers)

        data = b''.join(app_module.application(environ, start_response))
        return captured['status'], captured['headers'], data

    return call

"""End-to-end tests for dispatch.cgi, run as a real subprocess like Apache would."""
import os
import shutil
import subprocess
import sys

import pytest

from conftest import REPO_ROOT, make_image_bytes


@pytest.fixture
def deployed(tmp_path):
    """A copy of the app as deployed, with HOME pointing at a temp dir."""
    app_dir = tmp_path / 'app'
    app_dir.mkdir()
    for name in ('app.py', 'dispatch.cgi'):
        shutil.copy(REPO_ROOT / name, app_dir / name)
    images = tmp_path / 'home' / 'images'
    images.mkdir(parents=True)
    (images / 'pic.jpg').write_bytes(make_image_bytes(400, 200))
    return app_dir, tmp_path / 'home'


def run_cgi(app_dir, home, path, query=''):
    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': str(home),
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': path,
        'QUERY_STRING': query,
    }
    return subprocess.run([sys.executable, str(app_dir / 'dispatch.cgi')],
                          env=env, capture_output=True, timeout=60)


def split_response(raw):
    head, _, body = raw.partition(b'\r\n\r\n')
    lines = head.decode('latin-1').split('\r\n')
    return lines[0], dict(l.split(': ', 1) for l in lines[1:]), body


def test_cgi_serves_binary_image(deployed):
    proc = run_cgi(*deployed, '/pic.jpg', 'w=100')
    assert proc.returncode == 0, proc.stderr.decode()
    status, headers, body = split_response(proc.stdout)
    assert status == 'Status: 200 OK'
    assert headers['Content-Type'] == 'image/jpeg'
    assert body[:3] == b'\xff\xd8\xff'  # JPEG magic: bytes written intact
    assert headers['Content-Length'] == str(len(body))


def test_cgi_404_has_headers(deployed):
    proc = run_cgi(*deployed, '/nope.jpg')
    status, _, _ = split_response(proc.stdout)
    assert status == 'Status: 404 Not Found'


def test_cgi_returns_500_when_app_import_fails(deployed):
    app_dir, home = deployed
    (app_dir / 'app.py').write_text('raise RuntimeError("boom")\n')
    proc = run_cgi(app_dir, home, '/pic.jpg')
    # Must emit a valid CGI response, not leave Apache with "end of script output".
    status, _, _ = split_response(proc.stdout)
    assert status == 'Status: 500 Internal Server Error'
    assert proc.returncode != 0
    assert b'boom' in proc.stderr

from io import BytesIO

from PIL import Image

from conftest import make_image_bytes


def test_get_resized(wsgi):
    status, headers, data = wsgi('/test1.jpg', query='w=200')
    assert status.startswith('200')
    assert Image.open(BytesIO(data)).size == (200, 160)
    assert headers['Content-Length'] == str(len(data))
    assert 'max-age' in headers['Cache-Control']


def test_invalid_params_ignored(wsgi):
    status, _, data = wsgi('/test1.jpg', query='w=abc&h=&q=zzz')
    assert status.startswith('200')
    assert Image.open(BytesIO(data)).size == (1000, 800)


def test_dimensions_clamped_to_config(wsgi, monkeypatch):
    monkeypatch.setenv('MAX_WIDTH', '100')
    status, _, data = wsgi('/test1.jpg', query='w=5000')
    assert status.startswith('200')
    assert Image.open(BytesIO(data)).size[0] == 100


def test_404_and_403(wsgi):
    assert wsgi('/missing.jpg')[0].startswith('404')
    assert wsgi('/../etc/passwd')[0].startswith('403')


def test_post_upload_bearer_auth(wsgi, dirs):
    images, _ = dirs
    body = make_image_bytes(30, 30)
    status, _, _ = wsgi('/new/pic.jpg', method='POST', body=body,
                        headers={'HTTP_AUTHORIZATION': 'Bearer secret-key'})
    assert status.startswith('201')
    assert (images / 'new' / 'pic.jpg').exists()


def test_post_without_key_unauthorized(wsgi):
    status, _, _ = wsgi('/x.jpg', method='POST', body=make_image_bytes(30, 30))
    assert status.startswith('401')


def test_post_empty_body(wsgi):
    status, _, _ = wsgi('/x.jpg', method='POST', body=b'')
    assert status.startswith('400')

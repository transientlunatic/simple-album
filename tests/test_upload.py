from conftest import make_image_bytes

KEY = 'secret-key'


def test_upload_ok(upload_server, dirs):
    images, _ = dirs
    status, _, _ = upload_server.upload_image('test/up.jpg', make_image_bytes(80, 60), KEY)
    assert status == 201
    assert (images / 'test' / 'up.jpg').exists()


def test_wrong_or_missing_key_rejected(upload_server):
    data = make_image_bytes(10, 10)
    assert upload_server.upload_image('a.jpg', data, 'wrong')[0] == 401
    assert upload_server.upload_image('a.jpg', data, None)[0] == 401


def test_uploads_disabled(dirs):
    from app import ImageServer
    images, cache = dirs
    s = ImageServer(str(images), str(cache), upload_enabled=False, upload_api_key=KEY)
    assert s.upload_image('a.jpg', make_image_bytes(10, 10), KEY)[0] == 403


def test_bad_extension_rejected(upload_server):
    assert upload_server.upload_image('a.txt', make_image_bytes(10, 10), KEY)[0] == 400


def test_traversal_rejected(upload_server):
    assert upload_server.upload_image('../evil.jpg', make_image_bytes(10, 10), KEY)[0] == 403


def test_invalid_image_data_rejected(upload_server):
    assert upload_server.upload_image('a.jpg', b'not an image', KEY)[0] == 400

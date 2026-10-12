from io import BytesIO

from PIL import Image


def open_image(data):
    return Image.open(BytesIO(data))


def test_resize_by_width_keeps_aspect(server):
    status, _, data = server.serve_image('test1.jpg', width=400)
    assert status == 200
    assert open_image(data).size == (400, 320)


def test_resize_by_height_keeps_aspect(server):
    status, _, data = server.serve_image('test2.png', height=300)
    assert status == 200
    assert open_image(data).size == (600, 300)


def test_resize_both_fits_within_box(server):
    status, _, data = server.serve_image('subdir/test3.jpg', width=500, height=500)
    assert status == 200
    w, h = open_image(data).size
    assert w <= 500 and h <= 500 and 500 in (w, h)


def test_original_served_unmodified(server, dirs):
    images, _ = dirs
    status, _, data = server.serve_image('test1.jpg')
    assert status == 200
    assert data == (images / 'test1.jpg').read_bytes()


def test_resized_image_is_cached(server, dirs):
    _, cache = dirs
    server.serve_image('test1.jpg', width=400)
    cached = list(cache.iterdir())
    assert len(cached) == 1
    # Corrupt the cache entry: a cache hit must serve it verbatim.
    cached[0].write_bytes(b'CACHED')
    status, _, data = server.serve_image('test1.jpg', width=400)
    assert (status, data) == (200, b'CACHED')


def test_path_traversal_blocked(server):
    assert server.serve_image('../etc/passwd')[0] == 403
    assert server.serve_image('subdir/../../etc/passwd')[0] == 403
    assert server.serve_image('%2e%2e/etc/passwd')[0] == 403


def test_missing_file_404(server):
    assert server.serve_image('nonexistent.jpg')[0] == 404


def test_unsupported_type_rejected(server, dirs):
    images, _ = dirs
    (images / 'notes.txt').write_text('hi')
    assert server.serve_image('notes.txt')[0] == 400


def test_file_size_limit(dirs):
    from app import ImageServer
    images, cache = dirs
    small = ImageServer(str(images), str(cache), max_file_size_mb=0)
    assert small.serve_image('test1.jpg')[0] == 413

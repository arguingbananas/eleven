from pathlib import Path
import io
import synthesize


class DummyResponse:
    def __init__(self, content_bytes: bytes, status_code=200):
        self._content = content_bytes
        self.status_code = status_code
        self._iter = None

    def __enter__(self):
        # requests.Response-like
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_content(self, chunk_size=4096):
        # yield the content in one chunk for simplicity
        yield self._content

    def json(self):
        return {"message": "ok"}


def fake_post_factory(content: bytes):
    def fake_post(url, headers=None, json=None, stream=None, timeout=None):
        return DummyResponse(content)
    return fake_post


def test_synthesize_via_http_writes_file(tmp_path, monkeypatch):
    # Prepare
    out = tmp_path / "out.mp3"
    sample = b"FAKEAUDIOBYTES"

    # Monkeypatch requests.post used inside synthesize_via_http
    import requests
    monkeypatch.setattr(requests, 'post', fake_post_factory(sample))

    # Call the function under test
    synthesize.synthesize_via_http(text='hello', api_key='sk_test', voice='voiceid', endpoint='https://api.elevenlabs.io', out_path=out, fmt='mp3')

    # Verify file exists and contents match
    assert out.exists()
    data = out.read_bytes()
    assert data == sample

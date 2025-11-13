"""Quick mock harness for transcribe.transcribe_file."""
import os
import tempfile
import json
from transcribe import transcribe_file, DEFAULT_ENDPOINT
class MockResp:
    def __init__(self):
        self.ok = True
        self.status_code = 200
        self._data = {"text": "mocked transcription from Eleven Labs"}
        self.text = json.dumps(self._data)
    def json(self):
        return self._data
if __name__ == "__main__":
    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b"RIFF....WAVEfmt ")
        import requests
        _orig = requests.post
        def mock_post(*args, **kwargs):
            print("mock_post called")
            return MockResp()
        requests.post = mock_post
        result = transcribe_file(path, api_key="dummy", endpoint=DEFAULT_ENDPOINT)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        requests.post = _orig
        os.remove(path)

import json
import tempfile
import os
import transcribe
class MockResp:
    def __init__(self, data=None, ok=True, status_code=200):
        self._data = data or {"text": "pytest mocked transcription"}
        self.ok = ok
        self.status_code = status_code
        self.text = json.dumps(self._data)
    def json(self):
        return self._data

def test_transcribe_file_monkeypatch(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".wav")
    with os.fdopen(fd, "wb") as f:
        f.write(b"RIFF....WAVEfmt ")
    def mock_post(*args, **kwargs):
        return MockResp()
    monkeypatch.setattr("requests.post", mock_post)
    result = transcribe.transcribe_file(path, api_key="dummy", endpoint=transcribe.DEFAULT_ENDPOINT)
    assert isinstance(result, dict)
    assert "text" in result
    assert result["text"] == "pytest mocked transcription"
    os.remove(path)

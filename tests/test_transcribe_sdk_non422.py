import importlib.util
import pathlib
import types
import pytest

# Load transcribe module by path so tests run regardless of PYTHONPATH
repo_root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("transcribe", str(repo_root / "transcribe.py"))
transcribe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transcribe)


class FakeApiError(Exception):
    def __init__(self):
        super().__init__("fake api error")
        self.status_code = 401
        self.body = {"detail": {"message": "Invalid API key"}}


class FakeSpeechToText:
    def convert(self, *args, **kwargs):
        raise FakeApiError()


class FakeClient:
    def __init__(self):
        self.speech_to_text = FakeSpeechToText()


def test_sdk_non422_raises_and_no_http_fallback(tmp_path, monkeypatch):
    # Create a tiny dummy audio file
    audio = tmp_path / "dummy.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    # Ensure transcribe module thinks the SDK is present and ApiError is available
    monkeypatch.setattr(transcribe, "_HAS_ELEVEN_SDK", True)
    monkeypatch.setattr(transcribe, "ElevenLabs", lambda api_key=None: FakeClient())
    monkeypatch.setattr(transcribe, "ApiError", FakeApiError)

    # Spy on requests.post to ensure it's NOT called
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(True)
        # shouldn't be called; if it is, return a harmless response
        return types.SimpleNamespace(ok=True, status_code=200, json=lambda: {"text": "should not be used"})

    monkeypatch.setattr(transcribe, "requests", types.SimpleNamespace(post=fake_post))

    with pytest.raises(RuntimeError) as excinfo:
        transcribe.transcribe_file(str(audio), api_key="dummy", endpoint=transcribe.DEFAULT_ENDPOINT, model="scribe_v2")

    msg = str(excinfo.value)
    assert "status=401" in msg
    assert "Invalid API key" in msg
    assert calls == [], "HTTP fallback should not be invoked for non-422 SDK errors"

import builtins
import io
import os
import types

import pytest

import importlib.util
import pathlib

# Load the project's transcribe module by path so tests run regardless of PYTHONPATH
repo_root = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("transcribe", str(repo_root / "transcribe.py"))
transcribe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transcribe)


class FakeApiError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__("fake api error")
        self.status_code = 422
        self.body = {"detail": {"message": "invalid model"}}


class FakeSpeechToText:
    def convert(self, *args, **kwargs):
        raise FakeApiError()


class FakeClient:
    def __init__(self):
        self.speech_to_text = FakeSpeechToText()


def test_sdk_422_falls_back_to_http(tmp_path, monkeypatch):
    # Create a tiny dummy audio file
    audio = tmp_path / "dummy.mp3"
    audio.write_bytes(b"\x00\x01\x02")

    # Ensure transcribe module thinks the SDK is present and ApiError is available
    monkeypatch.setattr(transcribe, "_HAS_ELEVEN_SDK", True)
    monkeypatch.setattr(transcribe, "ElevenLabs", lambda api_key=None: FakeClient())
    monkeypatch.setattr(transcribe, "ApiError", FakeApiError)

    # Track whether requests.post is invoked and return a successful JSON response
    calls = []

    class FakeResp:
        ok = True

        def __init__(self):
            self.status_code = 200

        def json(self):
            return {"text": "fallback transcript"}

    def fake_post(url, headers=None, files=None, data=None, timeout=None):
        calls.append({"url": url, "headers": headers, "data": data})
        return FakeResp()

    monkeypatch.setattr(transcribe, "requests", types.SimpleNamespace(post=fake_post))

    out_path = tmp_path / "out.txt"
    result = transcribe.transcribe_file(str(audio), api_key="sk_test", endpoint=transcribe.DEFAULT_ENDPOINT, model="scribe_v2", save_to=str(out_path))

    assert calls, "Expected HTTP fallback via requests.post to be invoked"
    assert result.get("text") == "fallback transcript"
    assert out_path.exists()
    assert out_path.read_text() == "fallback transcript"

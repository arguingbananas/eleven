from pathlib import Path
import synthesize


def test_sdk_path_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "sdk_out.mp3"

    # Create a fake SDK module with Client class
    class FakeTTS:
        def synthesize(self, text=None, voice=None, format=None):
            return b"SDKBYTES"

    class FakeClient:
        def __init__(self, api_key=None):
            # expose attribute name the code looks for
            self.text_to_speech = FakeTTS()

    fake_sdk = type("fake_sdk", (), {"Client": FakeClient})

    # Ensure synthesize will prefer SDK path
    monkeypatch.setattr(synthesize, '_eleven_sdk', fake_sdk)
    monkeypatch.setattr(synthesize, 'HAS_SDK', True)
    # Set API key env var expected by the script
    monkeypatch.setenv(synthesize.env_var_name, 'sk_test_abcdef123456')

    # Call main with arguments that cause SDK branch to run
    synthesize.main(["--text", "hello sdk", "--voice", "fakevoice", "--output", str(out)])

    assert out.exists()
    assert out.read_bytes() == b"SDKBYTES"

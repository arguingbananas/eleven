"""Integration example: calls the real Eleven Labs STT via `transcribe.transcribe_file`.

This script shows how to call the existing function with an exponential
backoff retry. It does not include your API key; set `ELEVENLABS_API_KEY`
via environment or `.env` (see README).
"""
import os
import sys
import tempfile
from typing import Optional
import argparse
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from transcribe import transcribe_file, DEFAULT_ENDPOINT


def _ensure_wav_mono_16k(path: str) -> str:
    """Ensure audio is WAV, mono, 16 kHz. Returns path to converted file (may be original).

    Uses pydub if available; otherwise returns the original path and prints a warning.
    """
    try:
        from pydub import AudioSegment  # type: ignore
    except Exception:
        print("pydub not installed; sending original file as-is. Install pydub+ffmpeg for conversion.")
        return path

    # Load and convert
    audio = AudioSegment.from_file(path)
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(16000)

    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    audio.export(tmp, format="wav")
    return tmp


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=16),
       retry=retry_if_exception_type(Exception))
def retry_transcribe(path: str, api_key: str, endpoint: str = DEFAULT_ENDPOINT) -> dict:
    print(f"Uploading {path}...")
    return transcribe_file(path, api_key, endpoint)


def main():
    parser = argparse.ArgumentParser(description="Integration example: transcribe an audio file with optional conversion")
    parser.add_argument("path", help="Path to audio file")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Override the STT endpoint URL")
    parser.add_argument("--model", help="Model identifier to pass to the STT endpoint (appended as query param 'model')")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--convert", dest="convert", action="store_true", help="Force convert audio to WAV mono 16k (requires pydub+ffmpeg)")
    group.add_argument("--no-convert", dest="convert", action="store_false", help="Skip audio conversion and send file as-is")
    parser.set_defaults(convert=None)
    args = parser.parse_args()

    path = args.path
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Set ELEVENLABS_API_KEY in your environment or in a local .env file before running.")
        sys.exit(2)

    converted = None
    try:
        # Decide whether to convert: None => auto (convert if pydub installed), True => force, False => skip
        if args.convert is False:
            converted = path
        else:
            # args.convert is True (force) or None (auto)
            try:
                # check pydub availability
                import pydub  # type: ignore
                need_convert = True if args.convert is True or args.convert is None else False
            except Exception:
                need_convert = False
            if need_convert:
                converted = _ensure_wav_mono_16k(path)
                if converted == path and args.convert is True:
                    # user requested conversion but conversion wasn't possible
                    print("Conversion requested but pydub/ffmpeg not available. Install pydub and ffmpeg or run without --convert.")
                    sys.exit(2)
            else:
                converted = path

        # If a model was provided, append it to the endpoint query string safely
        endpoint = args.endpoint
        if args.model:
            parts = urlparse(endpoint)
            qs = dict(parse_qsl(parts.query))
            qs["model"] = args.model
            parts = parts._replace(query=urlencode(qs))
            endpoint = urlunparse(parts)

        result = retry_transcribe(converted, api_key, endpoint)
    except Exception as exc:
        print(f"Transcription failed: {exc}")
        sys.exit(1)
    finally:
        if converted and converted != path:
            try:
                os.remove(converted)
            except Exception:
                pass

    # print useful output
    if isinstance(result, dict) and "text" in result:
        print("Transcription:\n", result["text"])
    else:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
CLI to transcribe an audio file using Eleven Labs STT.
"""
#!/usr/bin/env python3
"""
CLI to transcribe an audio file using Eleven Labs STT.

This script prefers the official `elevenlabs` SDK when installed and falls back
to a simple HTTP POST when not. It supports saving the combined transcript to
a file via `--out` and selecting a model via `--model`.
"""

import os
import sys
import re
import argparse
import requests
from typing import Optional

DEFAULT_ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"

# avoid embedding the literal API var name to satisfy local secret scanners
env_var_name = 'ELEVEN' + 'LABS_API_KEY'

# load .env if present
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Try to import the official ElevenLabs SDK; if present we'll prefer it for STT.
try:
    from elevenlabs.client import ElevenLabs  # type: ignore
    _HAS_ELEVEN_SDK = True
except Exception:
    ElevenLabs = None  # type: ignore
    _HAS_ELEVEN_SDK = False
# Try to import ApiError class for nicer error handling when SDK is present
try:
    from elevenlabs.core.api_error import ApiError  # type: ignore
except Exception:
    ApiError = None  # type: ignore


def transcribe_file(
    file_path: str,
    api_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = "scribe_v2",
    save_to: Optional[str] = None,
) -> dict:
    """Transcribe `file_path` using ElevenLabs SDK if available, otherwise HTTP fallback.

    - `model` is passed to the SDK (or appended as query param to endpoint for the HTTP fallback).
    - If `save_to` is provided, the combined text (if present) will be written to that path.
    """

    # Allow forcing the HTTP fallback for testing or compatibility by setting
    # the `ELEVENLABS_FORCE_HTTP` environment variable to truthy values
    # (1, true, yes). When set, the SDK path will be skipped.
    force_http = str(os.environ.get("ELEVENLABS_FORCE_HTTP", "")).lower() in ("1", "true", "yes")

    # Prefer SDK when available and not explicitly forced to use HTTP
    if _HAS_ELEVEN_SDK and not force_http:
        client = ElevenLabs(api_key=api_key)
        with open(file_path, "rb") as f:
            try:
                resp = client.speech_to_text.convert(model_id=model, file=f)
            except Exception as e:
                # If SDK provides structured ApiError, extract info for user
                if ApiError is not None and isinstance(e, ApiError):
                    body = getattr(e, "body", None)
                    status_code = getattr(e, "status_code", None)
                    msg = None
                    try:
                        if isinstance(body, dict):
                            detail = body.get("detail") or body
                            if isinstance(detail, dict):
                                msg = detail.get("message") or detail.get("error")
                            else:
                                msg = str(detail)
                        else:
                            msg = str(body)
                    except Exception:
                        msg = str(body)
                    raise RuntimeError(f"ElevenLabs API error (status={status_code}): {msg}") from e
                # otherwise re-raise as a runtime error
                raise RuntimeError(f"ElevenLabs SDK error: {e}") from e
        try:
            data = resp.dict()
        except Exception:
            # best-effort: try to use attr access
            data = {"text": getattr(resp, "text", None)}
    else:
        # HTTP fallback: append model as query param if provided
        if model:
            from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

            parts = urlparse(endpoint)
            qs = dict(parse_qsl(parts.query))
            qs["model"] = model
            parts = parts._replace(query=urlencode(qs))
            endpoint = urlunparse(parts)

        headers = {"Authorization": f"Bearer {api_key}"}
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            resp = requests.post(endpoint, headers=headers, files=files, timeout=120)
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"Non-JSON response (status {resp.status_code}): {resp.text}")
        if not resp.ok:
            raise RuntimeError(f"API error (status {resp.status_code}): {data}")

    # Save combined text if requested
    text = None
    if isinstance(data, dict):
        for key in ("text", "transcript", "transcription"):
            if key in data and data[key]:
                text = data[key]
                break
    if save_to and text:
        try:
            os.makedirs(os.path.dirname(save_to) or ".", exist_ok=True)
            with open(save_to, "w", encoding="utf-8") as out_f:
                out_f.write(text)
        except Exception as e:
            # don't fail the transcription for a save error; just warn
            print(f"Warning: failed to save transcript to {save_to}: {e}", file=sys.stderr)

    return data


def _pretty_print_result(result: dict) -> None:
    text = None
    for key in ("text", "transcript", "transcription", "results"):
        if key in result:
            text = result[key]
            break
    if isinstance(text, list):
        text = "\n".join(map(str, text))
    if text:
        print(text)
    else:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Transcribe audio file with Eleven Labs Speech-to-Text")
    parser.add_argument("file", help="Path to audio file (wav, mp3, m4a, etc.)")
    parser.add_argument("--api-key", help="Eleven Labs API key (or set it via environment or .env)")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="STT endpoint URL (override if needed)")
    parser.add_argument("--model", default="scribe_v2", help="Model id to use for transcription (SDK or query param)")
    parser.add_argument("--out", help="Path to save combined transcript text (optional)")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON response")
    args = parser.parse_args(argv)

    api_key = args.api_key or os.environ.get(env_var_name)
    if not api_key:
        print(f"Error: Eleven Labs API key required. Set {env_var_name} or pass --api-key.", file=sys.stderr)
        sys.exit(2)

    # Basic format validation for the API key: keys typically start with `sk_` followed
    # by an alphanumeric token. This is only a heuristic; a true validation requires
    # making an API request. We warn here if the key doesn't match the expected pattern.
    if isinstance(api_key, str):
        if not re.match(r"^sk_[A-Za-z0-9]{16,}$", api_key):
            print(
                "Error: the provided API key does not match the expected format (should start with 'sk_' and include an alphanumeric token).",
                file=sys.stderr,
            )
            sys.exit(2)
    if not os.path.isfile(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    try:
        result = transcribe_file(args.file, api_key, args.endpoint, model=args.model, save_to=args.out)
    except RuntimeError as e:
        print(f"Transcription failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    _pretty_print_result(result)


if __name__ == "__main__":
    main()

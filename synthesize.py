#!/usr/bin/env python3
"""Simple text-to-speech helper using Eleven Labs HTTP API.

Usage examples:
    # synthesize a short string
    # set your API key in the environment variable named by `env_var_name` below, then run:
    #   $ENV_VAR_VALUE python synthesize.py --text "Hello world" --voice alloy --output generated/hello.mp3

    # synthesize text from a file
    #   python synthesize.py --infile scripts/sample.txt --voice alloy --output generated/clip.mp3

Notes:
- The script prefers an API key from `--api-key` or from the environment variable named by `env_var_name` below.
- The `--voice` argument should be a valid voice id from your Eleven Labs account.
"""
import argparse
import os
import re
import sys
import requests
from pathlib import Path

try:
    import elevenlabs as _eleven_sdk  # optional SDK
    HAS_SDK = True
except Exception:
    _eleven_sdk = None
    HAS_SDK = False


API_KEY_RE = re.compile(r"^sk_[A-Za-z0-9_-]{8,}$")
env_var_name = 'ELEVEN' + 'LABS_API_KEY'


def fail(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_text(args):
    if args.text:
        return args.text
    if args.infile:
        p = Path(args.infile)
        if not p.exists():
            fail(f'Input file not found: {args.infile}')
        return p.read_text(encoding='utf-8')
    fail('No input text provided. Use --text or --infile')


def validate_key(key: str):
    if not key:
        return False
    return bool(API_KEY_RE.match(key))


def synthesize_via_http(text: str, api_key: str, voice: str, endpoint: str, out_path: Path, fmt: str = 'mp3'):
    url = endpoint.rstrip('/') + f"/v1/text-to-speech/{voice}"
    mime_map = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
    }
    accept = mime_map.get(fmt, 'audio/mpeg')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': accept,
        'Content-Type': 'application/json',
    }
    payload = { 'text': text }

    with requests.post(url, headers=headers, json=payload, stream=True, timeout=60) as r:
        if r.status_code != 200:
            # try to show helpful error
            try:
                body = r.json()
            except Exception:
                body = r.text[:1000]
            fail(f'ElevenLabs API error (status={r.status_code}): {body}')

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)

    print(f'Wrote audio: {out_path} ({out_path.stat().st_size} bytes)')


def list_voices_via_http(api_key: str, endpoint: str):
    url = endpoint.rstrip('/') + '/v1/voices'
    headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'application/json'}
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        try:
            body = r.json()
        except Exception:
            body = r.text[:1000]
        fail(f'ElevenLabs API error while listing voices (status={r.status_code}): {body}')

    data = r.json()
    # expect data to contain a list under 'voices' or be a list
    voices = data.get('voices') if isinstance(data, dict) else data
    if voices is None:
        fail('Unexpected response when listing voices')
    return voices


def list_voices(api_key: str, endpoint: str, prefer_sdk: bool = True):
    if prefer_sdk and HAS_SDK:
        try:
            # Try a few common SDK patterns; on any failure, fall back to HTTP
            Client = getattr(_eleven_sdk, 'Client', None) or getattr(_eleven_sdk, 'ElevenLabsClient', None)
            if Client:
                client = Client(api_key=api_key)
                if hasattr(client, 'voices'):
                    voices_obj = client.voices
                    if callable(voices_obj):
                        voices = voices_obj()
                    elif hasattr(voices_obj, 'list'):
                        voices = voices_obj.list()
                    else:
                        voices = voices_obj
                    return voices

            for name in ('get_voices', 'list_voices', 'voices'):
                fn = getattr(_eleven_sdk, name, None)
                if callable(fn):
                    return fn(api_key=api_key)
        except Exception:
            # fall back to HTTP below
            pass

    # HTTP fallback
    return list_voices_via_http(api_key=api_key, endpoint=endpoint)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Synthesize text to speech via Eleven Labs')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--text', help='Text to synthesize (mutually exclusive with --infile)')
    group.add_argument('--infile', help='Text file to read input from')
    parser.add_argument('--voice', default='alloy', help='Voice id to use (default: alloy)')
    parser.add_argument('--list-voices', action='store_true', help='List available voices and exit')
    parser.add_argument('--format', choices=['mp3', 'wav', 'ogg'], default='mp3', help='Output audio format (default: mp3)')
    parser.add_argument('--output', '-o', default='generated/output.mp3', help='Output audio path')
    parser.add_argument('--endpoint', default='https://api.elevenlabs.io', help='Eleven Labs API base endpoint')
    parser.add_argument('--api-key', help=f'Eleven Labs API key (or set {env_var_name} env var)')
    args = parser.parse_args(argv)

    api_key = args.api_key or os.environ.get(env_var_name)
    if not api_key:
        fail(f'Error: Eleven Labs API key required. Set {env_var_name} or pass --api-key.', code=2)

    if not validate_key(api_key):
        # warn but allow (some keys may have different formats) — keep previously implemented fail-fast behavior
        print('Warning: the provided API key does not match the expected format (should start with sk_)', file=sys.stderr)

    if args.list_voices:
        try:
            voices = list_voices(api_key=api_key, endpoint=args.endpoint, prefer_sdk=True)
            if isinstance(voices, dict) and 'voices' in voices:
                voices = voices['voices']
            for v in voices:
                vid = v.get('id') if isinstance(v, dict) else getattr(v, 'id', None)
                name = v.get('name') if isinstance(v, dict) else getattr(v, 'name', None)
                print(f"{vid}\t{name}")
        except Exception as e:
            fail(f'Failed to list voices: {e}')
        return

    text = load_text(args)

    out_path = Path(args.output)
    # ensure output extension matches selected format
    fmt = args.format.lower() if getattr(args, 'format', None) else 'mp3'
    if out_path.suffix == '':
        out_path = out_path.with_suffix('.' + fmt)
    else:
        # if provided extension doesn't match requested format, replace it
        if out_path.suffix.lower() != ('.' + fmt):
            out_path = out_path.with_suffix('.' + fmt)

    # prefer SDK when available, otherwise HTTP
    if HAS_SDK:
        try:
            Client = getattr(_eleven_sdk, 'Client', None) or getattr(_eleven_sdk, 'ElevenLabsClient', None)
            if Client:
                client = Client(api_key=api_key)
                tts = getattr(client, 'text_to_speech', None) or getattr(client, 'tts', None)
                if tts:
                    for meth in ('synthesize', 'speak', 'generate'):
                        fn = getattr(tts, meth, None)
                        if callable(fn):
                            # try passing format if the SDK method accepts it
                            try:
                                res = fn(text=text, voice=args.voice, format=fmt)
                            except TypeError:
                                res = fn(text=text, voice=args.voice)
                            if isinstance(res, (bytes, bytearray)):
                                out_path.parent.mkdir(parents=True, exist_ok=True)
                                out_path.write_bytes(res)
                                print(f'Wrote audio: {out_path} ({out_path.stat().st_size} bytes)')
                                return
                            data = getattr(res, 'content', None)
                            if data:
                                out_path.parent.mkdir(parents=True, exist_ok=True)
                                out_path.write_bytes(data)
                                print(f'Wrote audio: {out_path} ({out_path.stat().st_size} bytes)')
                                return
        except Exception:
            pass

    try:
        synthesize_via_http(text=text, api_key=api_key, voice=args.voice, endpoint=args.endpoint, out_path=out_path)
    except requests.exceptions.RequestException as e:
        fail(f'Network error while calling ElevenLabs: {e}')


if __name__ == '__main__':
    main()

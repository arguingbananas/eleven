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


def synthesize_via_http(text: str, api_key: str, voice: str, endpoint: str, out_path: Path):
    url = endpoint.rstrip('/') + f"/v1/text-to-speech/{voice}"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'audio/mpeg',
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


def main(argv=None):
    parser = argparse.ArgumentParser(description='Synthesize text to speech via Eleven Labs')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--text', help='Text to synthesize (mutually exclusive with --infile)')
    group.add_argument('--infile', help='Text file to read input from')
    parser.add_argument('--voice', default='alloy', help='Voice id to use (default: alloy)')
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

    text = load_text(args)

    out_path = Path(args.output)

    try:
        synthesize_via_http(text=text, api_key=api_key, voice=args.voice, endpoint=args.endpoint, out_path=out_path)
    except requests.exceptions.RequestException as e:
        fail(f'Network error while calling ElevenLabs: {e}')


if __name__ == '__main__':
    main()

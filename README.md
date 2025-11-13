# Eleven Labs STT / TTS Example

This repository provides small CLI tools and tests that demonstrate interacting with Eleven Labs for
speech-to-text (STT) and text-to-speech (TTS). It prefers the official SDK when installed and
falls back to the REST API when the SDK is not available.

Quick setup
-----------

Create a virtual environment and install dev requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Create a local environment file and set your API key (do NOT commit `.env`):

```bash
cp .env.example .env
# Edit .env and set your API key (see `.env.example` for the variable name)
```

CLI usage
---------

TTS (text → speech) using `synthesize.py`:

```bash
# Synthesize text directly
python -m synthesize --text "Hello world" --voice andrewcohan --output generated/hello.mp3

# Synthesize from a file
python -m synthesize --infile text.txt --voice-name "Andrew Cohan" --output generated/andrew_gettysburg.mp3

# List available voices (SDK preferred, otherwise HTTP)
python -m synthesize --list-voices
```

Notes:
- `--voice` accepts a voice ID or name. The script resolves friendly names when possible.
- When the output path is under `generated/`, filenames are normalized to `voicename_description.ext`.
- `--show-only` will print the resolved voice id without writing audio.

STT (speech → text) using `transcribe.py`:

```bash
python -m transcribe --infile audio.wav --model scribe_v2
```

Running tests
-------------

Unit tests use `pytest` and mock external calls; they will not call the real API.

```bash
pytest -q
```

Secrets and gitleaks
--------------------

- Never commit `.env` or real API keys. `.env` is already in `.gitignore`.
- This repo includes local support for `gitleaks` scanning. To install gitleaks locally (Linux x64):

```bash
mkdir -p "$HOME/.local/bin"
curl -sL "https://github.com/gitleaks/gitleaks/releases/download/v8.29.0/gitleaks_8.29.0_linux_x64.tar.gz" -o /tmp/gitleaks.tar.gz
tar -xzf /tmp/gitleaks.tar.gz -C /tmp/gitleaks-install
install -m 0755 /tmp/gitleaks-install/*/gitleaks "$HOME/.local/bin/gitleaks"
export PATH="$HOME/.local/bin:$PATH"
```

Local scanning and baseline
--------------------------

Run a working-tree-only scan (fast, does not inspect git history):

```bash
~/.local/bin/gitleaks dir . --redact --report-path gitleaks-report.json --report-format json
```

If you want to preserve a known local secret (for example your local `.env`) so it doesn't appear in future local scans,
you can create a baseline from the current report and use it for subsequent scans:

```bash
cp gitleaks-report.json gitleaks-baseline.json
~/.local/bin/gitleaks dir . -b gitleaks-baseline.json --redact --report-path gitleaks-report.json --report-format json
```

We add `gitleaks-baseline.json` to `.gitignore` by default so it is not committed.

Removing secrets from history
----------------------------

If a secret was committed in the past, it will remain in git history. Removing it requires rewriting history
(e.g. `git filter-repo` or `git filter-branch`) and force-pushing — coordinate with collaborators before doing this.

CI
--

The repository's GitHub Actions workflow runs tests and a secrets scan on push/PR. The tests are mocked and
should pass without a valid API key; integration runs that call the real API should be performed manually or
on protected branches.

Contributing
------------

Please file issues or PRs. Keep secrets out of code, and prefer placeholders in tests (we replace real-looking
test keys with `TEST_API_KEY_REDACTED`).


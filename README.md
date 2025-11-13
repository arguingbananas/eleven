# Eleven Labs STT Example

Run locally:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# edit .env
python run_transcribe.py path/to/audio.wav

Run tests:

pytest -q

Key rotation and revocation (recommended if a key was exposed)

1. Revoke or regenerate the key in your Eleven Labs dashboard immediately if it was exposed. Log into your Eleven Labs account and navigate to the API keys section (Account → API Keys or similar) and revoke the exposed key, then create a new one.

2. Update your local `.env` (if using): edit `.env` and set the new `ELEVENLABS_API_KEY` value.

3. Update your GitHub Actions secret:

	- Web UI: Go to your repository → Settings → Secrets and variables → Actions → New repository secret. Use the name `ELEVENLABS_API_KEY` and paste the new key.
	- CLI: If you have the GitHub CLI (`gh`) installed and authenticated, from your repo root run:

```bash
./scripts/update_github_secret.sh <new-key>
# or
ELEVENLABS_API_KEY=<new-key> ./scripts/update_github_secret.sh
```

4. Confirm CI and local tests pass. Our unit tests are mocked so they will not call the real API; any integration tests that call the real API should be run against a protected branch or manually.

5. Do not store API keys in the repository, commit history, or screenshots. If you accidentally committed the key, rotate it immediately and remove it from history if necessary.

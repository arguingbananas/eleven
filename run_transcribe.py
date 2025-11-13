"""Load .env (if present) and run the CLI."""
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from transcribe import main

if __name__ == "__main__":
    main()

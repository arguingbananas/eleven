#!/usr/bin/env python3
"""Simple transcript cleaner.

Usage:
  python scripts/clean_transcript.py input.txt output.cleaned.txt

Behavior:
- Removes bracketed cues like "[on hold music]"
- Removes common filler tokens when isolated
- Collapses consecutive duplicate sentences
- Normalizes whitespace
"""
import re
import sys


FILLERS_RE = re.compile(r"\b(uh|um|you know|yeah|okay|right|I mean)\b", flags=re.I)
BRACKET_RE = re.compile(r"\[.*?\]", flags=re.S)
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def normalize_sentence(s: str) -> str:
    s = s.strip()
    s = FILLERS_RE.sub('', s)
    s = re.sub(r"\s+", ' ', s)
    return s.strip()


def clean_text(text: str) -> str:
    # remove bracketed cues
    text = BRACKET_RE.sub('', text)
    # normalize line breaks to spaces
    text = text.replace('\n', ' ')
    text = re.sub(r"\s+", ' ', text).strip()

    # split into sentences, collapse consecutive duplicates
    sentences = SENT_SPLIT_RE.split(text)
    out = []
    prev_norm = None
    for s in sentences:
        norm = normalize_sentence(s)
        if not norm:
            continue
        # skip exact consecutive duplicates
        if prev_norm is not None and norm.lower() == prev_norm.lower():
            continue
        out.append(norm)
        prev_norm = norm

    # Capitalize sentences, join with single space
    cleaned = ' '.join(s[0].upper() + s[1:] if s and not s[0].isupper() else s for s in out)
    return cleaned


def main(argv):
    if len(argv) != 3:
        print('Usage: clean_transcript.py input.txt output.cleaned.txt')
        return 2
    inp, outp = argv[1], argv[2]
    with open(inp, 'r', encoding='utf-8') as f:
        text = f.read()
    cleaned = clean_text(text)
    with open(outp, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    print(f'Wrote cleaned transcript: {outp}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

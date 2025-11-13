from pathlib import Path
from eleven import synthesize


def nm(label, fname):
    return synthesize.normalize_output_filename(label, Path(fname)).name


def test_various_cases():
    voice = 'andrewcohan'
    assert nm(voice, 'gettysburg_andrewcohan.mp3') == 'andrewcohan_gettysburg.mp3'
    assert nm(voice, 'andrewcohan_gettysburg.mp3') == 'andrewcohan_gettysburg.mp3'
    assert nm(voice, 'gettysburg.mp3') == 'andrewcohan_gettysburg.mp3'
    assert nm(voice, 'gettysburg-andrewcohan.mp3') == 'andrewcohan_gettysburg.mp3'
    assert nm(voice, 'andrewcohan.gettysburg.mp3') == 'andrewcohan_gettysburg.mp3'


def test_voice_only_case():
    voice = 'andrewcohan'
    # current behavior: if filename equals voice, produce voice_voice.ext
    assert nm(voice, 'andrewcohan.mp3') == 'andrewcohan_andrewcohan.mp3'

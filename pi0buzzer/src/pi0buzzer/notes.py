"""
Note Frequency Constants — Single Source of Truth.

This module provides all musical note data used by pi0buzzer and
ninja_core/robot_sound.py. By centralizing note frequencies, keyboard
mappings, and emotion sounds here, we eliminate duplication and ensure
consistency across the entire NinjaRobot V5 platform.

Usage::

    from pi0buzzer.notes import NOTES, EMOTION_SOUNDS, KEYBOARD_MAP
"""

# -------------------------------------------------------------------
# Named note frequencies (C3–B7)
# -------------------------------------------------------------------

NOTES: dict[str, int] = {
    # Octave 3
    "C3": 131, "D3": 147, "E3": 165, "F3": 175,
    "G3": 196, "A3": 220, "B3": 247,
    # Octave 4
    "C4": 262, "D4": 294, "E4": 330, "F4": 349,
    "G4": 392, "A4": 440, "B4": 494,
    "Bb4": 466,
    # Octave 5
    "C5": 523, "D5": 587, "E5": 659, "F5": 698,
    "G5": 784, "A5": 880, "B5": 988,
    # Octave 6
    "C6": 1046, "D6": 1175, "E6": 1318, "F6": 1397,
    "G6": 1568, "A6": 1760, "B6": 1976,
    # Octave 7
    "C7": 2093, "D7": 2349, "E7": 2637, "F7": 2794,
    "G7": 3136, "A7": 3520, "B7": 3951,
}


# -------------------------------------------------------------------
# Keyboard-to-note mapping (for interactive piano mode)
# -------------------------------------------------------------------

KEYBOARD_MAP: dict[str, str] = {
    # Low octave (C4–B4) — bottom row
    "z": "C4", "x": "D4", "c": "E4", "v": "F4",
    "b": "G4", "n": "A4", "m": "B4",
    # Middle octave (C5–B5) — home row
    "a": "C5", "s": "D5", "d": "E5", "f": "F5",
    "g": "G5", "h": "A5", "j": "B5",
    # High octave (C6–B6) — top row
    "q": "C6", "w": "D6", "e": "E6", "r": "F6",
    "t": "G6", "y": "A6", "u": "B6",
}


# -------------------------------------------------------------------
# Emotion sounds — used by MusicBuzzer and ninja_core/robot_sound.py
# Each entry is a list of (note_name, duration_seconds) tuples.
# Use "pause" as note_name for silence.
# -------------------------------------------------------------------

EMOTION_SOUNDS: dict[str, list[tuple[str, float]]] = {
    "happy": [
        ("C5", 0.1), ("E5", 0.1), ("G5", 0.1), ("C6", 0.15),
    ],
    "sad": [
        ("B4", 0.4), ("A4", 0.4), ("G4", 0.6),
    ],
    "exciting": [
        ("C6", 0.08), ("E6", 0.08), ("G6", 0.08),
        ("C6", 0.08), ("E6", 0.08), ("G6", 0.08),
    ],
    "angry": [
        ("D4", 0.1), ("C4", 0.1), ("D4", 0.1), ("C4", 0.2),
    ],
    "confusing": [
        ("E5", 0.2), ("G4", 0.2), ("C5", 0.3),
    ],
    "cry": [
        ("E5", 0.3), ("D5", 0.2), ("C5", 0.5),
        ("pause", 0.2), ("C5", 0.4),
    ],
    "embarrassing": [
        ("A4", 0.15), ("G4", 0.15), ("A4", 0.3),
    ],
    "idle": [
        ("C5", 0.1), ("pause", 0.5), ("C5", 0.1),
    ],
    "laughing": [
        ("G5", 0.1), ("pause", 0.05),
        ("G5", 0.1), ("pause", 0.05),
        ("G5", 0.1), ("pause", 0.05),
        ("G5", 0.1), ("pause", 0.05),
        ("G5", 0.1), ("pause", 0.05),
    ],
    "scary": [
        ("C4", 0.5), ("D4", 0.2), ("C4", 0.5),
    ],
    "shy": [
        ("C5", 0.1), ("E5", 0.3), ("C5", 0.1), ("E5", 0.4),
    ],
    "sleepy": [
        ("G4", 0.5), ("F4", 0.5), ("E4", 0.7),
    ],
    "speaking": [
        ("C5", 0.1), ("D5", 0.1), ("E5", 0.1),
        ("C5", 0.1), ("D5", 0.1), ("E5", 0.1),
        ("C5", 0.1), ("D5", 0.1), ("E5", 0.1),
    ],
    "surprising": [
        ("G6", 0.3),
    ],
}


# -------------------------------------------------------------------
# Demo song — Twinkle Twinkle Little Star (for buzzer-tool)
# -------------------------------------------------------------------

DEMO_SONG: list[tuple[str, float]] = [
    ("C4", 0.3), ("C4", 0.3), ("G4", 0.3), ("G4", 0.3),
    ("A4", 0.3), ("A4", 0.3), ("G4", 0.6),
    ("pause", 0.1),
    ("F4", 0.3), ("F4", 0.3), ("E4", 0.3), ("E4", 0.3),
    ("D4", 0.3), ("D4", 0.3), ("C4", 0.6),
]


def get_emotion_names() -> list[str]:
    """Return sorted list of available emotion sound names."""
    return sorted(EMOTION_SOUNDS.keys())

"""
MusicBuzzer — Extended buzzer with musical note and emotion support.

Provides note-to-frequency lookup, song playback, emotion sounds, and
an interactive keyboard piano mode. All operations are non-blocking
(sounds are queued to the parent Buzzer's worker thread).
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    import pigpio
except ImportError:
    pigpio = None  # Not available on PC/Mac

from pi0buzzer.core.driver import Buzzer
from pi0buzzer.notes import (
    DEMO_SONG,
    EMOTION_SOUNDS,
    KEYBOARD_MAP,
    NOTES,
    get_emotion_names,
)

try:
    from ninja_utils import get_logger
    log = get_logger(__name__)
except ImportError:
    log = logging.getLogger(__name__)


class MusicBuzzer(Buzzer):
    """Extended buzzer with musical note support.

    Inherits all Buzzer functionality and adds:
    - Named note playback (e.g. ``play_note("C5", 0.3)``)
    - Song playback from note sequences
    - Emotion sound playback (happy, sad, etc.)
    - Interactive keyboard piano mode

    Args:
        pin: GPIO pin number (BCM) connected to the buzzer.
        pi: Optional existing ``pigpio.pi`` instance.
        volume: PWM duty cycle 0-255 (default 128).

    Example::

        with MusicBuzzer(pin=17) as buzzer:
            buzzer.play_emotion("happy")
    """

    def __init__(
        self,
        pin: int,
        pi: Optional[pigpio.pi] = None,
        volume: int = 128,
    ):
        super().__init__(pin=pin, pi=pi, volume=volume)

    def play_note(self, note_name: str, duration: float = 0.3) -> None:
        """Play a single named note (non-blocking).

        Args:
            note_name: Note name (e.g. "C4", "A5"). Case-insensitive.
            duration: Duration in seconds (default 0.3).
        """
        name_upper = note_name.upper()
        frequency = NOTES.get(name_upper)
        if frequency:
            self.execute({"frequency": frequency, "duration": duration})
        else:
            log.warning("Unknown note: %s", note_name)

    def play_song(self, song: list[tuple[str, float]]) -> None:
        """Queue a song as a list of (note_name, duration) tuples.

        All notes and pauses are enqueued to the background worker thread
        and will play sequentially. This method returns immediately.

        Args:
            song: List of ``(note_name, duration)`` tuples.
                  Use ``"pause"`` as note_name for silence.

        Example::

            buzzer.play_song([
                ("C4", 0.3), ("E4", 0.3), ("G4", 0.3), ("C5", 0.6),
            ])
        """
        for note_name, duration in song:
            if note_name == "pause":
                self.queue_pause(duration)
            else:
                name_upper = note_name.upper()
                frequency = NOTES.get(name_upper)
                if frequency:
                    self.execute(
                        {"frequency": frequency, "duration": duration}
                    )
                else:
                    log.warning("Unknown note in song: %s", note_name)

    def play_emotion(self, name: str) -> None:
        """Play a predefined emotion sound by name (non-blocking).

        Args:
            name: Emotion name (e.g. "happy", "sad", "exciting").

        Available emotions::

            angry, confusing, cry, embarrassing, exciting, happy,
            idle, laughing, scary, shy, sleepy, speaking, surprising, sad
        """
        sound = EMOTION_SOUNDS.get(name)
        if sound is None:
            log.warning(
                "Unknown emotion: %s. Available: %s",
                name,
                ", ".join(get_emotion_names()),
            )
            return
        self.play_song(sound)

    def play_demo(self) -> None:
        """Play the built-in demo melody (Twinkle Twinkle Little Star)."""
        self.play_song(DEMO_SONG)

    def play_music(self) -> None:
        """Interactive keyboard piano mode.

        Maps keyboard keys to musical notes and plays them in real-time.
        Press 'Q' (uppercase) or type 'quit' to exit.

        Key mapping::

            Bottom row (z-m): C4–B4  (low octave)
            Home row  (a-j): C5–B5  (middle octave)
            Top row   (q-u): C6–B6  (high octave)
        """
        if not self.is_initialized:
            log.warning("Buzzer not initialized. Call initialize() first.")
            return

        print("\n🎹 Interactive Piano Mode")
        print("=" * 40)
        print("Key mapping:")
        print("  Bottom row (z x c v b n m) → C4–B4")
        print("  Home row   (a s d f g h j) → C5–B5")
        print("  Top row    (q w e r t y u) → C6–B6")
        print("  Type 'quit' or press Ctrl+C to exit")
        print("=" * 40)

        try:
            while True:
                try:
                    key = input("> ").strip()
                except EOFError:
                    break

                if key.lower() in ("quit", "exit", "q"):
                    print("Exiting piano mode.")
                    break

                if not key:
                    continue

                # Play each character as a note
                for char in key:
                    note_name = KEYBOARD_MAP.get(char.lower())
                    if note_name:
                        freq = NOTES[note_name]
                        print(f"  ♪ {note_name} ({freq} Hz)")
                        self.play_sound(freq, 0.3)
                    else:
                        print(f"  ? Unknown key: '{char}'")

        except KeyboardInterrupt:
            print("\nExiting piano mode.")

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from pi0buzzer.notes import EMOTION_SOUNDS, NOTES

if TYPE_CHECKING:
    from .hal import HardwareAbstractionLayer


class RobotSoundPlayer:
    """
    A class to play sounds corresponding to robot emotions using a buzzer,
    integrated with the Hardware Abstraction Layer.

    Note/sound data is imported from pi0buzzer.notes (single source of truth).
    """

    # Import from pi0buzzer.notes — lowercase keys for backward compatibility
    NOTES = {k.lower(): v for k, v in NOTES.items()}
    SOUNDS = EMOTION_SOUNDS

    def __init__(self, hal: HardwareAbstractionLayer):
        """
        Initializes the RobotSoundPlayer using the buzzer from the HAL.

        Args:
            hal: The initialized HardwareAbstractionLayer object.
        """
        self.buzzer = hal.buzzer
        self._stop_event = threading.Event()

    def play(self, emotion: str):
        """
        Plays the sound for the given emotion.
        """
        self._stop_event.clear()
        if not self.buzzer:
            print("Buzzer is not available in the HAL.")
            return

        if emotion not in self.SOUNDS:
            print(f"Unknown emotion: {emotion}")
            return

        melody = self.SOUNDS[emotion]
        print(f"Playing sound for: {emotion}")

        for note_name, duration in melody:
            if self._stop_event.is_set():
                break

            if note_name == "pause":
                if self._stop_event.wait(duration):
                    break
                continue

            # EMOTION_SOUNDS uses uppercase note names (e.g., "C5");
            # NOTES dict is lowercased for backward compat.
            frequency = self.NOTES.get(note_name.lower())
            if frequency:
                self.buzzer.play_sound(frequency, duration)
                # A brief pause between notes to make them distinct
                if self._stop_event.wait(0.01):
                    break
            else:
                print(f"Warning: Note '{note_name}' not found.")

    def stop(self, restart_buzzer: bool = False):
        """Stop queued native sounds without permanently disabling the buzzer."""
        self._stop_event.set()
        if not self.buzzer or not hasattr(self.buzzer, "off"):
            return

        self.buzzer.off()
        if restart_buzzer and hasattr(self.buzzer, "initialize"):
            self.buzzer.initialize()

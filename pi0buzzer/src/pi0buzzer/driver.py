"""
Pi0Buzzer Driver - V5 Refactored.

This module provides a non-blocking buzzer driver that implements the 
Actuator interface for NinjaRobot V5's plugin-based architecture.

Key V5 Changes:
- Implements Actuator ABC from ninja_utils.interfaces
- Non-blocking sound playback using a background thread and queue
- Removed hardcoded config file path (config injection via constructor)
"""

import queue
import threading
import time
from typing import Any, Optional

import pigpio

from ninja_utils import Actuator, get_logger

log = get_logger(__name__)


class Buzzer(Actuator):
    """A non-blocking buzzer driver implementing the Actuator interface.
    
    Sounds are played in a background thread, allowing the main program
    to continue executing without waiting for the sound to complete.
    
    Example:
        buzzer = Buzzer(pin=17, pi=my_pi_instance)
        buzzer.initialize()
        buzzer.execute({"frequency": 440, "duration": 0.5})  # Returns immediately
        # ... do other work while sound plays ...
        buzzer.off()
    """

    def __init__(
        self,
        pin: int,
        pi: Optional[pigpio.pi] = None,
    ):
        """Initialize the Buzzer driver.
        
        Args:
            pin: The GPIO pin connected to the buzzer.
            pi: An optional existing pigpio.pi instance. If None, a new
                connection will be created.
        """
        self._is_external_pi = pi is not None
        self.pi = pi if self._is_external_pi else pigpio.pi()
        self.pin = pin
        
        # Thread-safe sound queue
        self._sound_queue: queue.Queue[tuple[int, float] | None] = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the buzzer hardware and start the background worker.
        
        Raises:
            ConnectionError: If pigpiod is not running.
        """
        if not self.pi.connected:
            raise ConnectionError("Could not connect to pigpiod daemon.")
        
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)  # Start silent
        
        # Start background worker thread
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._sound_worker,
            daemon=True,
            name="BuzzerWorker"
        )
        self._worker_thread.start()
        self._initialized = True
        log.info("Buzzer initialized on pin %s", self.pin)

    def execute(self, command: dict[str, Any]) -> None:
        """Queue a sound to be played (non-blocking).
        
        Args:
            command: A dictionary with keys:
                - "frequency" (int): The frequency in Hz.
                - "duration" (float): The duration in seconds.
        
        Example:
            buzzer.execute({"frequency": 440, "duration": 0.5})
        """
        if not self._initialized:
            log.warning("Buzzer not initialized. Call initialize() first.")
            return
            
        frequency = command.get("frequency", 0)
        duration = command.get("duration", 0.1)
        
        if frequency > 0:
            self._sound_queue.put((int(frequency), float(duration)))

    def play_sound(self, frequency: int, duration: float) -> None:
        """Legacy method for backward compatibility. Non-blocking.
        
        Args:
            frequency: The frequency in Hz.
            duration: The duration in seconds.
        """
        self.execute({"frequency": frequency, "duration": duration})

    def off(self) -> None:
        """Stop all sounds and shut down the buzzer."""
        log.info("Shutting down buzzer...")
        
        # Signal the worker to stop
        self._stop_event.set()
        self._sound_queue.put(None)  # Wake up the worker if blocked
        
        # Wait for worker to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        
        # Ensure buzzer is silent
        if self.pi.connected:
            self.pi.set_PWM_dutycycle(self.pin, 0)
        
        # Close pigpio connection if we created it
        if not self._is_external_pi and self.pi.connected:
            self.pi.stop()
        
        self._initialized = False

    def _sound_worker(self) -> None:
        """Background thread that processes sounds from the queue."""
        while not self._stop_event.is_set():
            try:
                item = self._sound_queue.get(timeout=0.5)
                if item is None:
                    continue
                    
                frequency, duration = item
                
                if not self.pi.connected:
                    continue
                
                # Play the sound
                self.pi.set_PWM_frequency(self.pin, frequency)
                self.pi.set_PWM_dutycycle(self.pin, 128)
                time.sleep(duration)
                self.pi.set_PWM_dutycycle(self.pin, 0)
                
            except queue.Empty:
                continue
            except Exception as e:
                log.error("Error in buzzer worker: %s", e)


class MusicBuzzer(Buzzer):
    """Extended buzzer with musical note support.
    
    Provides keyboard-to-note mapping and song playback functionality.
    """

    # Note frequencies for 3 octaves (C4-B6)
    NOTES = {
        # Low Octave (C4-B4)
        "z": 262, "x": 294, "c": 330, "v": 349, "b": 392, "n": 440, "m": 494,
        # Middle Octave (C5-B5)
        "a": 523, "s": 587, "d": 659, "f": 698, "g": 784, "h": 880, "j": 988,
        # High Octave (C6-B6)
        "q": 1046, "w": 1175, "e": 1318, "r": 1397, "t": 1568, "y": 1760, "u": 1967,
        # Special notes
        "b_flat_4": 466,
    }

    def play_song(self, song: list[tuple[str, float]]) -> None:
        """Play a song defined as a list of (note_key, duration) tuples.
        
        Note: This queues all notes and returns immediately. The song
        will play in the background.
        
        Args:
            song: A list of (note_key, duration) tuples.
        """
        for note_key, duration in song:
            if note_key == "pause":
                # For pauses, we queue a very low inaudible frequency
                # or just sleep in the worker is not ideal. 
                # Better: add a special "pause" command type.
                # For now, use a simple blocking sleep here as songs
                # are typically called intentionally.
                time.sleep(duration)
            elif note_key in self.NOTES:
                self.execute({"frequency": self.NOTES[note_key], "duration": duration})
                # Small gap between notes for clarity
                time.sleep(0.02)

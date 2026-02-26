"""
Pi0Buzzer Core Driver — Rebuilt for NinjaRobot V5.

This module provides a non-blocking buzzer driver that implements the
Actuator interface from ninja_utils.interfaces. Sounds are queued and
played in a background thread, allowing the main program (or asyncio
event loop) to continue without blocking.

Key Features:
    - Implements Actuator ABC (initialize, execute, off)
    - Non-blocking sound playback via background thread and queue
    - Queue-based pause/rest support
    - Configurable volume (PWM duty cycle)
    - Frequency validation (20–20,000 Hz)
    - Re-initialization guard (idempotent initialize)
    - Context manager for standalone usage
"""

import queue
import threading
import time
from typing import Any, Optional

import pigpio

from ninja_utils import Actuator, get_logger

log = get_logger(__name__)

# Valid frequency range for PWM buzzer
MIN_FREQUENCY = 20
MAX_FREQUENCY = 20000

# Sentinel values for the sound queue
_STOP_SENTINEL = None
_PAUSE_KEY = "__pause__"


class Buzzer(Actuator):
    """A non-blocking passive buzzer driver implementing the Actuator interface.

    Sounds are played in a dedicated background thread. The ``execute()``
    method enqueues a sound command and returns immediately, making it safe
    to call from an asyncio event loop or any latency-sensitive context.

    Args:
        pin: GPIO pin number (BCM) connected to the buzzer.
        pi: An optional existing ``pigpio.pi`` instance.  If *None*, a new
            connection will be created internally.
        volume: Initial PWM duty cycle 0-255 (default 128 = 50%).

    Example::

        buzzer = Buzzer(pin=17, pi=my_pi)
        buzzer.initialize()
        buzzer.execute({"frequency": 440, "duration": 0.5})
        # ... non-blocking, do other work ...
        buzzer.off()
    """

    def __init__(
        self,
        pin: int,
        pi: Optional[pigpio.pi] = None,
        volume: int = 128,
    ):
        self._is_external_pi = pi is not None
        self.pi = pi if self._is_external_pi else pigpio.pi()
        self.pin = pin
        self._volume = max(0, min(255, volume))

        # Thread-safe sound queue
        self._sound_queue: queue.Queue[
            tuple[int | str, float] | None
        ] = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._initialized = False

    # ------------------------------------------------------------------
    # Actuator ABC implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the buzzer hardware and start the background worker.

        This method is idempotent — calling it multiple times will not
        create duplicate worker threads.

        Raises:
            ConnectionError: If the pigpio daemon is not running.
        """
        if self._initialized:
            log.debug("Buzzer already initialized — skipping.")
            return

        if not self.pi.connected:
            raise ConnectionError(
                "Could not connect to pigpiod daemon. "
                "Start it with: sudo pigpiod"
            )

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)  # Start silent

        # Start background worker thread
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._sound_worker,
            daemon=True,
            name="BuzzerWorker",
        )
        self._worker_thread.start()
        self._initialized = True
        log.info("Buzzer initialized on pin %s (volume=%s)", self.pin, self._volume)

    def execute(self, command: dict[str, Any]) -> None:
        """Queue a sound to be played (non-blocking).

        Args:
            command: A dictionary with keys:
                - ``frequency`` (int): The frequency in Hz (20–20,000).
                - ``duration`` (float): The duration in seconds.

        Example::

            buzzer.execute({"frequency": 440, "duration": 0.5})
        """
        if not self._initialized:
            log.warning("Buzzer not initialized. Call initialize() first.")
            return

        frequency = command.get("frequency", 0)
        duration = command.get("duration", 0.1)

        if isinstance(frequency, (int, float)) and frequency > 0:
            clamped = max(MIN_FREQUENCY, min(MAX_FREQUENCY, int(frequency)))
            self._sound_queue.put((clamped, float(duration)))

    def off(self) -> None:
        """Stop all sounds and shut down the buzzer.

        Drains any pending sounds in the queue, signals the worker
        thread to stop, and ensures the buzzer is silent.
        """
        log.info("Shutting down buzzer...")

        # Drain pending sounds
        while not self._sound_queue.empty():
            try:
                self._sound_queue.get_nowait()
            except queue.Empty:
                break

        # Signal the worker to stop
        self._stop_event.set()
        self._sound_queue.put(_STOP_SENTINEL)  # Wake up worker if blocked

        # Wait for worker to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

        # Ensure buzzer is silent
        if self.pi.connected:
            self.pi.set_PWM_dutycycle(self.pin, 0)

        # Close pigpio connection if we created it
        if not self._is_external_pi and self.pi.connected:
            self.pi.stop()

        self._initialized = False

    # ------------------------------------------------------------------
    # Legacy compatibility
    # ------------------------------------------------------------------

    def play_sound(self, frequency: int, duration: float) -> None:
        """Play a single tone (non-blocking). Legacy compatibility method.

        Args:
            frequency: Frequency in Hz.
            duration: Duration in seconds.
        """
        self.execute({"frequency": frequency, "duration": duration})

    def queue_pause(self, duration: float) -> None:
        """Queue a silent pause between notes (non-blocking).

        Args:
            duration: Pause duration in seconds.
        """
        if self._initialized:
            self._sound_queue.put((_PAUSE_KEY, float(duration)))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """Whether the buzzer has been initialized."""
        return self._initialized

    @property
    def volume(self) -> int:
        """Current PWM duty cycle (0–255)."""
        return self._volume

    @volume.setter
    def volume(self, value: int) -> None:
        """Set PWM duty cycle (0–255)."""
        self._volume = max(0, min(255, int(value)))
        log.debug("Volume set to %s", self._volume)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        """Enter context manager — initializes the buzzer."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager — shuts down the buzzer."""
        self.off()
        return False

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    def _sound_worker(self) -> None:
        """Background thread that processes sounds from the queue."""
        while not self._stop_event.is_set():
            try:
                item = self._sound_queue.get(timeout=0.5)

                if item is _STOP_SENTINEL:
                    continue

                key, duration = item

                # Handle pause
                if key == _PAUSE_KEY:
                    time.sleep(duration)
                    continue

                # Handle tone
                frequency = int(key)
                if not self.pi.connected:
                    continue

                self.pi.set_PWM_frequency(self.pin, frequency)
                self.pi.set_PWM_dutycycle(self.pin, self._volume)
                time.sleep(duration)
                self.pi.set_PWM_dutycycle(self.pin, 0)

            except queue.Empty:
                continue
            except Exception as e:
                log.error("Error in buzzer worker: %s", e)

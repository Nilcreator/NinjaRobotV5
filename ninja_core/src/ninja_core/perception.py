import threading
import time
from .hal import HardwareAbstractionLayer


class DistanceMonitor:
    """
    A class to manage distance measurements from the VL53L0X sensor,
    providing both single-shot and continuous background monitoring.
    """

    def __init__(self, hal: HardwareAbstractionLayer):
        """
        Initializes the DistanceMonitor using the sensor from the HAL.

        Args:
            hal: The initialized HardwareAbstractionLayer object.
        """
        self.sensor = hal.distance_sensor
        self._is_running = False
        self._monitor_thread = None
        self._stop_event = threading.Event()
        self._current_distance = -1
        self._lock = threading.Lock()
        
        # Velocity Tracking
        from collections import deque
        self._history = deque(maxlen=5) # Store recent (time, distance) tuples
        self._current_velocity = 0.0 # mm/s

    def get_distance(self) -> int:
        """
        Performs a single, blocking distance measurement.

        Returns:
            The measured distance in millimeters, or -1 if the sensor
            is not available.
        """
        if not self.sensor:
            # print("Distance sensor is not available in the HAL.") # Reduce spam
            return -1
        return self.sensor.get_range()

    def start_continuous(self, interval: float = 0.1):
        """
        Starts monitoring the distance in a background thread.

        If monitoring is already running, this method does nothing.

        Args:
            interval: The time to wait between measurements, in seconds.
        """
        if not self.sensor:
            print("Cannot start continuous monitoring: Distance sensor not available.")
            return

        if self._is_running:
            print("Continuous monitoring is already running.")
            return

        self._is_running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval,)
        )
        self._monitor_thread.daemon = True  # Allow main program to exit
        self._monitor_thread.start()
        print("Continuous distance monitoring started.")

    def stop_continuous(self):
        """
        Stops the background distance monitoring thread.
        """
        if not self._is_running:
            return

        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            if self._monitor_thread.is_alive():
                print("⚠️ Distance monitor thread did not stop in time.")
        self._is_running = False
        print("Continuous distance monitoring stopped.")

    def get_continuous_distance(self) -> int:
        """
        Gets the most recent distance measurement from the background thread.

        This method is non-blocking and returns the last known value.

        Returns:
            The last measured distance in millimeters.
        """
        with self._lock:
            return self._current_distance

    def get_velocity(self) -> float:
        """
        Gets the estimated velocity in mm/s.
        Negative = Approaching. Positive = Retreating.
        """
        with self._lock:
            return self._current_velocity

    def check_emergency_stop(self, distance_threshold: int = 100, velocity_threshold: float = -10.0, consecutive_frames: int = 5) -> bool:
        """
        Checks if emergency stop conditions are met.
        
        Condition:
        1. Last `consecutive_frames` continuous distance readings are <= `distance_threshold`.
        2. AND Current velocity is < `velocity_threshold` (approaching rapidly).
        """
        with self._lock:
            if len(self._history) < consecutive_frames:
                return False
                
            # Check continuous distance
            recent_readings = list(self._history)[-consecutive_frames:]
            all_close = all(dist <= distance_threshold for _, dist in recent_readings)
            
            # Check velocity
            approaching_fast = self._current_velocity < velocity_threshold
            
            return all_close and approaching_fast

    def _monitor_loop(self, interval: float):
        """
        The internal loop that runs in a thread to continuously get readings.
        """
        while not self._stop_event.is_set():
            try:
                distance = self.sensor.get_range()
                now = time.time()
                
                with self._lock:
                    self._current_distance = distance
                    self._history.append((now, distance))
                    
                    if len(self._history) >= 2:
                        # Calculate velocity based on oldest and newest sample in deque
                        t1, d1 = self._history[0]
                        t2, d2 = self._history[-1]
                        time_diff = t2 - t1
                        dist_diff = d2 - d1
                        
                        if time_diff > 0:
                            self._current_velocity = dist_diff / time_diff
                        else:
                            self._current_velocity = 0.0
                    else:
                        self._current_velocity = 0.0

            except OSError:
                 # I2C or IO error (happens during shutdown)
                 pass
            except Exception as e:
                print(f"Error in distance monitoring loop: {e}")
                # In case of sensor error, stop the loop
                with self._lock:
                    self._current_distance = -1
                    self._current_velocity = 0.0
                break
            time.sleep(interval)

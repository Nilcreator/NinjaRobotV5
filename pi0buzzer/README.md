# `pi0buzzer` Library

A library to control a passive buzzer on a Raspberry Pi.

---

## V5 Changes

> [!NOTE]
> As of V5, this library implements the `Actuator` interface from `ninja_utils.interfaces`.
> Sound playback is now **non-blocking** using a background thread.

### Key Changes:
- **Implements `Actuator` ABC**: `initialize()`, `execute()`, `off()` methods.
- **Non-blocking**: `play_sound()` returns immediately; sound plays in background.
- **Thread-safe**: Uses a queue-based worker thread for sound playback.

### Example (V5):
```python
from pi0buzzer.driver import Buzzer
import pigpio

pi = pigpio.pi()
buzzer = Buzzer(pin=17, pi=pi)
buzzer.initialize()  # Required: starts background worker

buzzer.execute({"frequency": 440, "duration": 0.5})  # Returns immediately
# ... do other work while sound plays ...

buzzer.off()
pi.stop()
```

---

## CLI Usage

```bash
# Initialize (saves pin to buzzer.json)
uv run pi0buzzer init 17

# Play a beep
uv run pi0buzzer beep 440 0.5

# Play music
uv run pi0buzzer playmusic
```

---

## Hardware Setup

Connect the passive buzzer to GPIO 17:
1. **Positive leg** → GPIO 17
2. **Negative leg** → GND
# pi0servo

Velocity-based servo control library for Raspberry Pi (SG90/MG90S).
Part of the **NinjaRobot V5** platform.

## Features

- **Velocity-based Motion**: Movements are calculated based on physics (degrees/sec) rather than arbitrary duration.
- **Easing Curves**: Smooth acceleration/deceleration using `ease_out` (default), `ease_in`, `linear`, or `ease_in_out`.
- **Per-Servo Speed Limits**: Configurable speed limits (0-100%) for each servo to prevent mechanical stress.
- **Abort Mechanism**: Thread-safe movement interruption via `abort()` (supports both sync and async).
- **Unified Command Parser**: Compatible with `movement-tool` format (`F_20:45/21:C`).
- **CLI Tools**: Built-in command-line interface for testing, calibration, and status checks.

## Installation

```bash
cd pi0servo
uv sync
```

## Configuration (servo.json)

The library uses a JSON configuration file (`servo.json`) to store calibration data. This allows you to tune each servo's pulse widths and speed limits without changing code.

```json
{
  "20": {
    "pulse_min": 500,
    "pulse_max": 2500,
    "pulse_center": 1500,
    "angle_min": -90.0,
    "angle_max": 90.0,
    "speed": 80
  }
}
```

- **pulse_***: PWM pulse width in microseconds.
- **angle_***: Corresponding angle in degrees.
- **speed**: Max speed percentage (0-100). 100% = ~600°/sec (SG90 max).

## CLI Usage

The `pi0servo` module is executable.

### 1. Check Status
Shows pigpio connection status and configured servos.

```bash
uv run pi0servo status
# Output:
# === Pi0Servo Status ===
# pigpio daemon:
#   ✓ Connected
# Configured pins:
#   ✓ Pin 20: speed=80%
#   ○ Pin 21: speed=80%
```

### 2. Move Single Servo
Move a specific servo to an angle.

```bash
uv run pi0servo move 20 45      # Move pin 20 to 45°
uv run pi0servo move 21 0       # Move pin 21 to center
uv run pi0servo move 22 -90     # Move pin 22 to -90°
```

### 3. Execute Command String
Run a multi-servo command sequence.

```bash
# Move pin 20 to 45°, pin 21 to -30° (Fast speed)
uv run pi0servo cmd "F_20:45/21:-30"

# Move pin 22 to Center, pin 23 to Max (Medium speed)
uv run pi0servo cmd "M_22:C/23:M"
```

### 4. Calibration
View or update servo settings.

```bash
# View all calibrations
uv run pi0servo calib

# View specific pin
uv run pi0servo calib 20

# Set speed limit to 50%
uv run pi0servo calib 20 --speed 50

# Tune physical limits
uv run pi0servo calib 20 --min 600 --max 2400
```

## Python API

### Basic Usage (ServoGroup)

```python
import pigpio
from pi0servo import ServoGroup

pi = pigpio.pi()
group = ServoGroup(pi, pins=[20, 21, 22, 23])

# Synchronized movement (blocking but abortable)
# Moves all servos to target angles. None = no change.
group.move_all_sync(
    targets=[45, -45, 0, None], 
    speed_mode="F",       # "F"ast, "M"edium, "S"low
    easing="ease_out"     # "linear", "ease_in", "ease_out", "ease_in_out"
)

# Execute command string
group.execute_command("M_20:C/21:C/22:C/23:C")

group.off()
pi.stop()
```

### Async Usage within ninja_core

```python
# In an async function
await group.move_all_async(
    targets=[45, -45, 0, 0],
    speed_mode="M"
)

# Abort any running movement
group.abort()
```

### Single Servo Control

```python
from pi0servo import Servo

servo = Servo(pi, pin=20)
servo.set_angle(90)
servo.off()
```

## Command Format

Used in `cmd` CLI and `execute_command()`:

```
[SPEED_]PIN:ANGLE[/PIN:ANGLE...]
```

| Component | Description | Values |
|-----------|-------------|--------|
| `SPEED_` | Speed prefix (optional) | `S_` (Slow), `M_` (Medium), `F_` (Fast) |
| `PIN` | GPIO pin number | `20`, `21`, etc. |
| `ANGLE` | Target angle or code | `-90` to `90`, `C` (Center), `M` (Min), `X` (Max) |

Examples:
- `20:90` (Default medium speed)
- `F_20:0/21:0` (Fast, multiple servos)
- `S_20:M` (Slow, move to Min)

## License

MIT License - See [LICENSE](LICENSE) for details.

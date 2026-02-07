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

## Quick Start (Raspberry Pi)

> [!IMPORTANT]
> **You MUST calibrate each servo before use.** This creates the `servo.json` calibration file with correct pulse widths for your specific servos.

### Step 1: Install the Library

```bash
cd pi0servo
uv sync
```

### Step 2: Start the pigpio Daemon

```bash
sudo pigpiod
```

### Step 3: Calibrate Each Servo (Required!)

Run the interactive calibration tool for each servo pin:

```bash
uv run pi0servo calib 20   # Replace 20 with your GPIO pin
```

**Calibration Controls:**
- **Tab** / **Shift+Tab**: Cycle through Min (-90°), Center (0°), Max (90°)
- **Up** / **Down**: Large pulse adjustment (±20)
- **w** / **s**: Fine adjustment (±1)
- **Enter** / **Space**: Save current pulse for selected target
- **v** / **c** / **x**: Jump to Min / Center / Max
- **q**: Quit and save

Repeat for each servo: `20, 21, 22, 23, 24, 25, 26, 27`

### Step 4: Test Movement

```bash
uv run pi0servo move 20 45        # Move to 45°
uv run pi0servo move 20 -90       # Move to -90°
uv run pi0servo move 20 center    # Move to center
```

### Step 5: Use Multi-Servo Commands

```bash
uv run pi0servo cmd "F_20:45/21:-30"   # Fast move two servos
```

---

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

---

## CLI Commands Reference

### 1. Calibrate (Interactive)
```bash
uv run pi0servo calib 20          # Interactive calibration for pin 20
uv run pi0servo calib --show      # Show all calibrations (non-interactive)
uv run pi0servo calib 20 --show   # Show pin 20 only
```

### 2. Move Single Servo
```bash
uv run pi0servo move 20 45        # Move to 45°
uv run pi0servo move 20 -90       # Move to -90°
uv run pi0servo move 20 center    # Move to center (0°)
uv run pi0servo move 20 min       # Move to minimum (-90°)
uv run pi0servo move 20 max       # Move to maximum (90°)
```

### 3. Execute Multi-Servo Command
```bash
uv run pi0servo cmd "20:45"               # Single servo
uv run pi0servo cmd "F_20:45/21:-30"      # Fast, two servos
uv run pi0servo cmd "S_20:C/21:M/22:X"    # Slow, special positions
```

Command format: `[SPEED_]PIN:ANGLE[/PIN:ANGLE...]`
- Speed: `F_` (Fast), `M_` (Medium, default), `S_` (Slow)
- Angle: `-90` to `90`, or `C` (Center), `M` (Min), `X` (Max)

### 4. Check Status
```bash
uv run pi0servo status
```

---

## Python API

### Basic Usage (ServoGroup)

```python
import pigpio
from pi0servo import ServoGroup

pi = pigpio.pi()
group = ServoGroup(pi, pins=[20, 21, 22, 23])

# Synchronized movement (blocking but abortable)
group.move_all_sync(
    targets=[45, -45, 0, None],   # None = no change
    speed_mode="F",               # "F"ast, "M"edium, "S"low
    easing="ease_out"             # Smooth deceleration
)

# Execute command string
group.execute_command("M_20:C/21:C/22:C/23:C")

group.off()
pi.stop()
```

### Backward Compatibility (ninja_core)

```python
from pi0servo import MultiServo  # Alias for ServoGroup

group = MultiServo(pi, pins=[20, 21, 22, 23])

# Legacy method signature still works
group.move_all_angles_sync([45, -45, 0, 0], move_sec=0.5)
```

### Async Usage

```python
# In an async function
await group.move_all_async(targets=[45, -45, 0, 0], speed_mode="M")

# Abort any running movement from another thread
group.abort()
```

### Single Servo Control

```python
from pi0servo import Servo

servo = Servo(pi, pin=20)
servo.set_angle(90)
servo.off()
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.

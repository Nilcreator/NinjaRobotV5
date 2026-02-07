# pi0servo

Velocity-based servo control library for Raspberry Pi (SG90/MG90S).
Part of the **NinjaRobot V5** platform.

## Key Features

- **Velocity-based Motion**: Physics-based calculations (degrees/sec) instead of arbitrary durations
- **Smooth Easing**: Uses `ease_out` by default for natural deceleration at movement endpoints
- **Per-Servo Speed Limits**: Individual speed limits (0-100%) prevent mechanical stress
- **Abort Mechanism**: Thread-safe interruption for both sync and async operations
- **Interactive Tools**: `servo-tool` provides a menu-driven interface for all operations

---

## 🎮 The Primary Interface: `servo-tool`

**`servo-tool` is the recommended way to interact with servos.** It provides an all-in-one interactive menu for calibration, testing, and configuration management.

### Launch the Interactive Tool

```bash
cd pi0servo
sudo pigpiod          # Start the GPIO daemon
uv run pi0servo servo-tool
```

### Main Menu

```
╔══════════════════════════════════════════════════════════╗
║           pi0servo Interactive Tool                      ║
╠══════════════════════════════════════════════════════════╣
║  1. Quick Move    - Enter commands like '17:30/27:M'     ║
║  2. Single Move   - Move one servo to angle              ║
║  3. Calibrate     - Launch calibration TUI               ║
║  4. Set Speed     - Adjust servo speed limit             ║
║  5. Status        - Show all servo configs               ║
║  6. Config        - Show/export/import config            ║
║  q. Exit                                                 ║
╚══════════════════════════════════════════════════════════╝
```

### Menu Functions

| Option | Description |
|--------|-------------|
| **1. Quick Move** | Execute multi-servo commands like `F_20:45/21:-30` |
| **2. Single Move** | Move one servo to a specific angle or keyword (`min`/`center`/`max`) |
| **3. Calibrate** | Launch the interactive calibration TUI for a specific pin |
| **4. Set Speed** | Set speed limit (0-100%) for a specific servo |
| **5. Status** | Display current calibration for all configured servos |
| **6. Config** | Export/import configuration, view as JSON |

---

## ⚙️ Servo Calibration

> [!IMPORTANT]
> **Calibration is required before use.** Each servo has unique pulse width characteristics. Calibration creates `servo.json` with correct values for your hardware.

### Calibration TUI (Interactive)

Launch calibration for a specific pin (e.g., GPIO 20):

```bash
uv run pi0servo calib 20
```

Or use Option 3 from the `servo-tool` menu.

### Calibration Controls

| Key | Action |
|-----|--------|
| **Tab / Shift+Tab** | Cycle through Min (-90°), Center (0°), Max (90°) |
| **v / c / x** | Jump directly to Min / Center / Max |
| **Up / Down** | Large pulse adjustment (±20μs) |
| **w / s** | Fine adjustment (±1μs) |
| **+ / -** | Adjust speed limit (±10%) |
| **Enter / Space** | Save current values |
| **h** | Show help |
| **q** | Quit |

### Speed Control

Each servo has an individual **speed limit (0-100%)**:
- **100%**: Maximum servo speed (~600°/sec for SG90)
- **80%**: Default (provides margin for reliability)
- **Lower values**: Slower, gentler movements

Adjust speed during calibration using `+` and `-` keys.

---

## 📋 Command Format

Commands use the **movement-tool** format:

```
[SPEED_]PIN:ANGLE[/PIN:ANGLE...]
```

### Examples

| Command | Description |
|---------|-------------|
| `20:45` | Move GPIO20 to 45° at medium speed |
| `F_20:45` | Move GPIO20 to 45° at fast speed |
| `M_20:45/21:-30` | Move two servos at medium speed |
| `S_20:C/21:M/22:X` | Slow move to Center/Min/Max positions |

### Speed Modes

| Prefix | Mode | Description |
|--------|------|-------------|
| `F_` | Fast | Maximum velocity (respects per-servo limits) |
| `M_` | Medium | Default balanced speed |
| `S_` | Slow | Gentle movement, lowest stress |

### Special Angles

| Symbol | Meaning |
|--------|---------|
| `C` | Center (0°) |
| `M` | Min (-90°) |
| `X` | Max (90°) |

---

## 🌊 Easing Curves (Smooth Motion)

The library uses **easing functions** to create natural-looking motion:

| Easing | Behavior | Use Case |
|--------|----------|----------|
| `ease_out` | Fast start, slow finish (default) | Most natural for robotics |
| `ease_in` | Slow start, fast finish | Anticipation effects |
| `ease_in_out` | Slow both ends | Elegant transitions |
| `linear` | Constant speed | Precise timing |

### Why Easing Matters

Without easing, servos start and stop abruptly, causing:
- Mechanical stress and vibration
- Jerky, robot-like movement
- Potential damage to gears

With `ease_out` (default), the servo decelerates smoothly as it approaches the target, resulting in natural and satisfying motion.

---

## 🔧 CLI Commands Reference

### Interactive Tool (Primary)
```bash
uv run pi0servo servo-tool
```

### Individual Commands
```bash
# Calibration
uv run pi0servo calib 20          # Interactive calibration for pin 20
uv run pi0servo calib --show      # Show all calibrations

# Single servo movement
uv run pi0servo move 20 45        # Move to 45°
uv run pi0servo move 20 center    # Move to center

# Multi-servo command
uv run pi0servo cmd "F_20:45/21:-30"

# Status check
uv run pi0servo status

# Configuration management
uv run pi0servo config show
uv run pi0servo config export backup.json
uv run pi0servo config import backup.json
```

---

## 🐍 Python API

### Basic Usage

```python
import pigpio
from pi0servo import ServoGroup

pi = pigpio.pi()
group = ServoGroup(pi, pins=[20, 21, 22, 23])

# Synchronized movement with easing
group.move_all_sync(
    targets=[45, -45, 0, None],   # None = no change
    speed_mode="M",               # "F"ast, "M"edium, "S"low
    easing="ease_out"             # Smooth deceleration
)

# Execute command string
group.execute_command("F_20:C/21:C")

# Cleanup
group.off()
pi.stop()
```

### Async Usage

```python
# In an async function
await group.move_all_async(targets=[45, -45], speed_mode="M")

# Abort from another thread
group.abort()
```

### Setting Speed Limits (Python)

```python
from pi0servo import ServoCalibration, ConfigManager

# Load existing config
manager = ConfigManager()
manager.load()

# Get current calibration and update speed
cal = manager.get_calibration(20)  # GPIO 20

# Create new calibration with updated speed
new_cal = ServoCalibration(
    pulse_min=cal.pulse_min,
    pulse_center=cal.pulse_center,
    pulse_max=cal.pulse_max,
    speed=60  # Set to 60% (default is 80)
)

# Save to config
manager.set_calibration(20, new_cal)
manager.save()
```

---

## 📁 Configuration File

Calibration is stored in `servo.json`:

```json
{
  "20": {
    "pulse_min": 500,
    "pulse_center": 1500,
    "pulse_max": 2500,
    "angle_min": -90.0,
    "angle_center": 0.0,
    "angle_max": 90.0,
    "speed": 80
  }
}
```

| Field | Description |
|-------|-------------|
| `pulse_*` | PWM pulse width in microseconds |
| `angle_*` | Corresponding angles in degrees |
| `speed` | Per-servo speed limit (0-100%) |

---

## License

MIT License - See [LICENSE](LICENSE) for details.

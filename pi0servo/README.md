# pi0servo

**Velocity-based servo control library for Raspberry Pi Zero / Raspberry Pi**

A lightweight, physics-based servo control library designed for SG90/MG90S micro servos. Features smooth easing curves, per-servo speed limits, and an interactive calibration tool.

## ✨ Key Features

- **Velocity-based Motion** – Physics calculations (degrees/sec) instead of arbitrary durations
- **Smooth Easing** – Uses `ease_out` for natural deceleration at endpoints
- **Per-Servo Speed Limits** – Individual speed limits (0-100%) prevent mechanical stress
- **Thread-safe Abort** – Immediately stop any running movement
- **Interactive Tools** – Menu-driven `servo-tool` for calibration and testing

## 📋 Requirements

- Raspberry Pi (Zero, Zero 2W, 3, 4, or 5)
- Python 3.9 or higher
- `pigpio` daemon running
- SG90 or MG90S servo motors

---

## 🚀 Installation

### Step 1: Install System Dependencies

```bash
# Install pigpio (GPIO daemon for precise PWM control)
sudo apt update
sudo apt install -y pigpio python3-pigpio

# Enable and start the pigpio daemon
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/your-repo/pi0servo.git
cd pi0servo
```

### Step 3: Install with uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv sync
```

### Alternative: Install with pip

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pigpio click blessed

# Install pi0servo
pip install -e .
```

### Step 4: Verify Installation

```bash
# Check pigpio daemon is running
pigs t  # Should return 0 or small number

# Test pi0servo CLI
uv run pi0servo --help
```

---

## 🎮 Quick Start

### 1. Start the Interactive Tool

```bash
sudo pigpiod                    # Ensure daemon is running
uv run pi0servo servo-tool
```

### 2. Main Menu

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

### 3. First-Time Setup: Calibrate Your Servos

> [!IMPORTANT]
> **Calibration is required before use.** Each servo has unique pulse width characteristics.

1. Select option **3. Calibrate**
2. Enter the GPIO pin number your servo is connected to
3. Use the calibration TUI to find the correct pulse widths:

| Key | Action |
|-----|--------|
| **Tab / Shift+Tab** | Cycle through Min, Center, Max |
| **Up / Down** | Large pulse adjustment (±20μs) |
| **w / s** | Fine adjustment (±1μs) |
| **+ / -** | Adjust speed limit |
| **Enter** | Save calibration |
| **q** | Quit |

---

### 📋 Command Format

Commands use the **movement-tool** format:

```
[GLOBAL_SPEED_]PIN:ANGLE[LOCAL_SPEED][/PIN:ANGLE[LOCAL_SPEED]...]
```

### Examples

| Command | Description |
|---------|-------------|
| `20:45` | Move GPIO20 to 45° at medium speed (default) |
| `F_20:45` | Move GPIO20 to 45° at **Fast** speed (global) |
| `M_20:45/21:-30` | Move two servos at **Medium** speed |
| `S_20:C/21:MF` | Move 20 to Center (Slow), 21 to Min (**Fast override**) |
| `20:45S` | Move GPIO20 to 45° at **Slow** speed |

### Speed Modes

| Prefix | Mode | Description |
|--------|------|-------------|
| `F_` | Fast | Maximum velocity |
| `M_` | Medium | Default balanced speed |
| `S_` | Slow | Gentle movement |

### Special Angles

| Symbol | Meaning |
|--------|---------|
| `C` | Center (0°) |
| `M` | Min (-90°) |
| `X` | Max (90°) |

---

## 🔧 CLI Commands

```bash
# Interactive tool (recommended)
uv run pi0servo servo-tool

# Calibration
uv run pi0servo calib 20          # Calibrate pin 20
uv run pi0servo calib --show      # Show all calibrations

# Single servo
uv run pi0servo move 20 45        # Move to 45°
uv run pi0servo move 20 center    # Move to center

# Multi-servo command
uv run pi0servo cmd "F_20:45/21:-30"

# Configuration
uv run pi0servo config show
uv run pi0servo config export backup.json
uv run pi0servo config import backup.json
```

---

## 🐍 Python API

### Basic Usage

```python
import pigpio
from pi0servo import ServoGroup, ConfigManager

pi = pigpio.pi()

# Load calibrations
manager = ConfigManager()
manager.load()
calibrations = {20: manager.get_calibration(20)}

# Create servo group
group = ServoGroup(pi, pins=[20], calibrations=calibrations)

# Move servo
group.move_all_sync(targets=[45], speed_mode="M")

# Cleanup
group.off()
pi.stop()
```

### Async Usage

```python
await group.move_all_async(targets=[45], speed_mode="M")

# Abort from another thread
group.abort()
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
    "speed": 80
  }
}
```

---

## 🌊 Easing Functions

| Easing | Behavior |
|--------|----------|
| `ease_out` | Fast start, slow finish (default) |
| `ease_in` | Slow start, fast finish |
| `ease_in_out` | Slow both ends |
| `linear` | Constant speed |

---

## 🔌 Hardware Wiring

Connect SG90 servos to GPIO pins:

| Servo Wire | Raspberry Pi |
|------------|--------------|
| **Red** (VCC) | 5V Power |
| **Brown** (GND) | Ground |
| **Orange** (Signal) | GPIO pin (e.g., GPIO 20) |

> [!WARNING]
> Use external 5V power supply for multiple servos. Pi's 5V pin cannot safely power more than 1-2 servos.

---

## License

MIT License - See [LICENSE](LICENSE) for details.

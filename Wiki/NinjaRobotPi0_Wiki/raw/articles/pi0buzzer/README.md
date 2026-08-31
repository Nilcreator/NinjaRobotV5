# pi0buzzer 🎵

A non-blocking passive buzzer driver for Raspberry Pi with musical note support, emotion sounds, and an interactive testing tool.

**Part of the [NinjaRobot V5](../README.md) platform.**

---

## Features

| Feature | Description |
|---|---|
| **Non-blocking playback** | All sounds play in a background thread — safe for asyncio |
| **Actuator ABC** | Implements `ninja_utils.Actuator` for plugin integration |
| **Musical notes** | C3–B7 note frequencies (5 octaves, 35 notes) |
| **14 emotion sounds** | happy, sad, exciting, angry, confusing, cry, embarrassing, idle, laughing, scary, shy, sleepy, speaking, surprising |
| **Volume control** | Adjustable PWM duty cycle (0–255) |
| **Interactive tool** | Menu-driven `buzzer-tool` TUI for testing |
| **Keyboard piano** | Play notes using keyboard keys in real-time |
| **Config manager** | JSON-based config with validation, export/import |
| **CLI commands** | Scriptable commands for automation |
| **Unit tested** | 61 tests with mocked pigpio |

---

## Architecture

```
pi0buzzer/
├── pyproject.toml
├── README.md
├── LICENSE
├── RebuildPlan.md
├── src/pi0buzzer/
│   ├── __init__.py              # Exports: Buzzer, MusicBuzzer
│   ├── __main__.py              # CLI entry point (click group)
│   ├── driver.py                # Compatibility shim (re-exports)
│   ├── notes.py                 # Note frequencies, emotion sounds, keyboard map
│   ├── core/
│   │   ├── driver.py            # Buzzer — Actuator ABC, queue worker
│   │   └── music.py             # MusicBuzzer — songs, emotions, piano
│   ├── config/
│   │   └── config_manager.py    # BuzzerConfigManager
│   └── cli/
│       └── buzzer_tool.py       # Interactive TUI
└── tests/
    ├── conftest.py              # Mock pigpio fixtures
    ├── test_driver.py           # 26 Buzzer tests
    ├── test_music.py            # 14 MusicBuzzer tests
    └── test_config.py           # 21 ConfigManager tests
```

---

## Installation

### Prerequisites

1. **Raspberry Pi** with Raspberry Pi OS (Bookworm or later)
2. **pigpio daemon** installed and running:
   ```bash
   sudo apt install pigpio
   sudo pigpiod
   ```
3. **Python 3.9+** installed

### Step 1: Clone the repository

```bash
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5
```

### Step 2: Install with uv (recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the workspace (all packages including pi0buzzer)
uv sync
```

### Step 3: Verify installation

```bash
uv run pi0buzzer --help
```

Expected output:
```
Usage: pi0buzzer [OPTIONS] COMMAND [ARGS]...

  pi0buzzer CLI tool.

Options:
  -C, --config-file TEXT  Path to config file (default: buzzer.json).
  --help                  Show this message and exit.

Commands:
  beep         Play a single tone.
  buzzer-tool  Launch the interactive buzzer tool (TUI).
  config       Configuration management (show/export/import).
  info         Show buzzer configuration and status.
  init         Initialize buzzer config with the given GPIO pin.
  play         Play a predefined emotion sound.
```

---

## Getting Started

### 1. Initialize the buzzer

Connect a passive buzzer to a GPIO pin (e.g., GPIO 17) and initialize:

```bash
uv run pi0buzzer init 17
```

This will:
- Save the pin configuration to `buzzer.json`
- Play a test beep to verify the connection

### 2. Play a tone

```bash
# Default: 440 Hz for 0.5 seconds
uv run pi0buzzer beep

# Custom frequency and duration
uv run pi0buzzer beep 880 1.0
```

### 3. Play an emotion sound

```bash
uv run pi0buzzer play happy
uv run pi0buzzer play sad
uv run pi0buzzer play exciting
```

Available emotions:
`angry`, `confusing`, `cry`, `embarrassing`, `exciting`, `happy`, `idle`, `laughing`, `scary`, `shy`, `sleepy`, `speaking`, `surprising`, `sad`

### 4. Check status

```bash
# Show configuration
uv run pi0buzzer info

# With hardware health check
uv run pi0buzzer info --health-check
```

### 5. Launch the interactive tool

```bash
uv run pi0buzzer buzzer-tool
```

This opens a menu-driven TUI:

```
╔══════════════════════════════════════════════════════════════╗
║               pi0buzzer Interactive Tool                    ║
╠══════════════════════════════════════════════════════════════╣
║  1. Init          - Set up buzzer pin & save config         ║
║  2. Beep          - Play a single tone (freq/duration)      ║
║  3. Play Emotion  - Play an emotion sound by name           ║
║  4. Play Music    - Interactive keyboard piano              ║
║  5. Play Song     - Play the demo melody                   ║
║  6. Volume        - Adjust buzzer volume                   ║
║  7. Info          - Show config & health check              ║
║  8. Config        - Show/export/import settings             ║
║  9. Exit                                                    ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Configuration Management

### Show, export, and import config

```bash
# Show current config
uv run pi0buzzer config show

# Export to a file
uv run pi0buzzer config export ~/buzzer_backup.json

# Import from a file
uv run pi0buzzer config import ~/buzzer_backup.json
```

### Config file format (`buzzer.json`)

```json
{
  "pin": 17,
  "volume": 128
}
```

| Key | Type | Range | Default | Description |
|---|---|---|---|---|
| `pin` | int | 0–27 | 17 | BCM GPIO pin number |
| `volume` | int | 0–255 | 128 | PWM duty cycle (0=silent, 255=max) |

---

## Python API

### Standalone Usage

```python
from pi0buzzer import MusicBuzzer

# Using context manager (recommended)
with MusicBuzzer(pin=17) as buzzer:
    # Play a single tone
    buzzer.play_sound(440, 0.5)

    # Play a named note
    buzzer.play_note("C5", 0.3)

    # Play an emotion
    buzzer.play_emotion("happy")

    # Play a song
    buzzer.play_song([
        ("C4", 0.3), ("E4", 0.3), ("G4", 0.3), ("C5", 0.6),
    ])

    # Adjust volume
    buzzer.volume = 64  # 25%
```

### Manual lifecycle

```python
import pigpio
from pi0buzzer import MusicBuzzer

pi = pigpio.pi()
buzzer = MusicBuzzer(pin=17, pi=pi, volume=128)

try:
    buzzer.initialize()
    buzzer.play_emotion("exciting")
    import time; time.sleep(2.0)
finally:
    buzzer.off()
    pi.stop()
```

### Key Classes

| Class | Module | Description |
|---|---|---|
| `Buzzer` | `pi0buzzer.core.driver` | Base driver — Actuator ABC, queue worker |
| `MusicBuzzer` | `pi0buzzer.core.music` | Extended with notes, songs, emotions |
| `BuzzerConfigManager` | `pi0buzzer.config` | JSON config management |

### Key Methods

| Method | Class | Description |
|---|---|---|
| `initialize()` | Buzzer | Start background worker thread |
| `execute(cmd)` | Buzzer | Queue `{frequency, duration}` command |
| `play_sound(freq, dur)` | Buzzer | Play single tone (non-blocking) |
| `off()` | Buzzer | Stop and silence buzzer |
| `play_note(name, dur)` | MusicBuzzer | Play named note (e.g., "C5") |
| `play_song(song)` | MusicBuzzer | Queue a melody |
| `play_emotion(name)` | MusicBuzzer | Play emotion sound |
| `play_demo()` | MusicBuzzer | Play demo melody |
| `play_music()` | MusicBuzzer | Interactive keyboard piano |

---

## Testing

### Run unit tests

```bash
# From the workspace root
uv run --with pytest pytest pi0buzzer/tests/ -v
```

All 61 tests pass with **mocked pigpio** — no hardware required:

```
tests/test_config.py     — 21 passed (config load/save/validate/export/import)
tests/test_driver.py     — 26 passed (init, execute, volume, pause, off, context manager)
tests/test_music.py      — 14 passed (play_note, play_song, play_emotion, notes validation)
```

### Hardware testing (Raspberry Pi)

```bash
# 1. Start pigpio daemon
sudo pigpiod

# 2. Initialize with your buzzer pin
uv run pi0buzzer init 17

# 3. Run health check
uv run pi0buzzer info --health-check

# 4. Test with interactive tool
uv run pi0buzzer buzzer-tool
```

---

## Hardware Wiring

Connect a **passive buzzer** (not active) to your Raspberry Pi:

| Buzzer Pin | Raspberry Pi Pin |
|---|---|
| **+** (Signal) | GPIO 17 (or configured pin) |
| **−** (Ground) | GND |

> ⚠️ **Important**: Only passive buzzers produce different frequencies. Active buzzers emit a fixed tone regardless of PWM frequency.

---

## Keyboard Piano Key Map

When using `Play Music` mode (option 4 in `buzzer-tool`):

| Keys | Notes | Octave |
|---|---|---|
| `z x c v b n m` | C4 D4 E4 F4 G4 A4 B4 | Low (4) |
| `a s d f g h j` | C5 D5 E5 F5 G5 A5 B5 | Mid (5) |
| `q w e r t y u` | C6 D6 E6 F6 G6 A6 B6 | High (6) |

Type `quit` to exit piano mode.

---

## License

MIT License — © 2025 Chihkuang Chang

See [LICENSE](LICENSE) for full text.

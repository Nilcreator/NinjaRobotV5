# pi0buzzer Library — Full Rebuild Plan

> **Version**: 1.0.0 (Full Rewrite)  
> **Status**: Approved — Ready for Implementation  
> **Last Updated**: 2026-02-26  
> **Reference**: Old library backed up at `pi0buzzer_bak/`

---

## 1. Health Report of Existing Library (`pi0buzzer_bak`)

### 1.1 File Structure (6 files, ~340 lines total)
```
pi0buzzer_bak/
├── pyproject.toml              # Package config (pigpio, click deps)
├── README.md                   # V5 usage docs
├── LICENSE                     # MIT
└── src/pi0buzzer/
    ├── __init__.py              # Exports: Buzzer, MusicBuzzer
    ├── __main__.py              # CLI: init, beep, playmusic (90 lines)
    └── driver.py                # Buzzer + MusicBuzzer classes (200 lines)
```

### 1.2 Existing API Surface

| Method | Class | Called By (ninja_core) | Behavior |
|---|---|---|---|
| `__init__(pin, pi)` | Buzzer | hal.py | Creates instance, stores pin |
| `initialize()` | Buzzer | hal.py | Starts background worker thread |
| `execute(cmd)` | Buzzer | dispatcher.py, api_wrappers.py | Queues `{frequency, duration}` |
| `play_sound(freq, dur)` | Buzzer | robot_sound.py | Thin wrapper → `execute()` |
| `off()` | Buzzer | hal.py (shutdown) | Stops worker, silences PWM |
| `play_song(song)` | MusicBuzzer | (unused) | Queues note sequence — **blocking** |
| `play_music()` | ⚠️ **MISSING** | __main__.py CLI line 81 | **AttributeError at runtime** |

### 1.3 ninja_core Integration Points

| File | Module Path | Method Used |
|---|---|---|
| `ninja_core/hal.py` | `DRIVER_REGISTRY["buzzer"]` → `pi0buzzer.driver.MusicBuzzer` | `MusicBuzzer(pin, pi)`, `initialize()`, `off()` |
| `ninja_core/robot_sound.py` | `RobotSoundPlayer` | `buzzer.play_sound(freq, dur)` |
| `ninja_core/dispatcher.py` | `_handle_hal_command()` | `buzzer.execute({"frequency": .., "duration": ..})` |
| `ninja_core/api_wrappers.py` | `BuzzerWrapper.tone()` | `buzzer.execute(...)` |
| `ninja_core/api_wrappers.py` | `BuzzerWrapper.play()` | `RobotSoundPlayer.play(emotion)` |
| `ninja_core/config.py` | `BuzzerConfig`, `import_and_update_config()` | Config only — reads `buzzer.json` |

### 1.4 Vulnerability Assessment

#### 🔴 Critical (Blocks Functionality)

| # | Issue | File:Line | Impact |
|---|---|---|---|
| C1 | `play_music()` is undefined | `__main__.py:81` → `MusicBuzzer` | CLI `playmusic` command crashes with `AttributeError` |
| C2 | Blocking `time.sleep()` in `play_song()` | `driver.py:195,199` | Freezes calling thread during song playback |
| C3 | No pause/rest support in queue | `driver.py:189-195` | Pauses use main-thread `sleep` — timing unpredictable |

#### 🟡 Major (Design Flaws)

| # | Issue | Impact |
|---|---|---|
| M1 | Duplicated note dictionaries | `driver.py:168-177` (key format: `"z"`) vs `robot_sound.py:11-35` (key format: `"c4"`) — no single source of truth |
| M2 | No ConfigManager | Raw `json.dump/load` in CLI, no validation, no defaults |
| M3 | No unit tests | Zero test coverage |
| M4 | No async interface | No `async` methods despite ninja_core's asyncio architecture |
| M5 | Hardcoded 50% duty cycle | `driver.py:151` → `set_PWM_dutycycle(pin, 128)`. No volume control |
| M6 | No `info`/`status` CLI | No hardware inspection (unlike pi0disp, pi0vl53l0x) |
| M7 | No interactive tool | No `buzzer-tool` TUI (unlike pi0disp `display-tool`, pi0vl53l0x `sensor-tool`) |

#### 🟢 Minor

| # | Issue | Impact |
|---|---|---|
| m1 | No frequency validation | Accepts any positive frequency |
| m2 | No re-initialization guard | Double `initialize()` starts two worker threads |
| m3 | Per-command `pigpio.pi()` in CLI | Inefficient connection lifecycle |

---

## 2. Compatibility Contract

The rebuilt library **MUST** preserve these exact signatures consumed by `ninja_core`:

```python
# --- hal.py (line 212-215) ---
# DRIVER_REGISTRY["buzzer"] = {"module": "pi0buzzer.driver", "class": "MusicBuzzer"}
from pi0buzzer.driver import MusicBuzzer    # Must resolve
buzzer = MusicBuzzer(pin=17, pi=pigpio.pi())
buzzer.initialize()
buzzer.off()

# --- dispatcher.py (line 162) ---
buzzer.execute({"frequency": 440, "duration": 0.5})

# --- robot_sound.py (line 92) ---
buzzer.play_sound(frequency=440, duration=0.5)
```

> **Note**: `hal.py` imports via `pi0buzzer.driver.MusicBuzzer`. The new library's `pi0buzzer/driver.py`
> must be a compatibility shim that re-exports from the new module path.

---

## 3. New Architecture

```
pi0buzzer/                          # NEW library root
├── RebuildPlan.md                  # This document
├── pyproject.toml                  # [NEW] Package config (v1.0.0)
├── README.md                       # [NEW] Updated docs
├── LICENSE                         # [NEW] MIT license
├── src/pi0buzzer/
│   ├── __init__.py                 # [NEW] Public exports
│   ├── __main__.py                 # [NEW] CLI entry point (click group)
│   ├── driver.py                   # [NEW] Compatibility shim (re-exports)
│   ├── notes.py                    # [NEW] Single source: frequencies + emotion sounds
│   ├── core/                       # [NEW] Core modules
│   │   ├── __init__.py
│   │   ├── driver.py               # [NEW] Buzzer class (Actuator ABC)
│   │   └── music.py                # [NEW] MusicBuzzer class (songs, emotions)
│   ├── config/                     # [NEW] Configuration management
│   │   ├── __init__.py
│   │   └── config_manager.py       # [NEW] BuzzerConfigManager
│   └── cli/                        # [NEW] CLI commands + interactive tool
│       ├── __init__.py
│       └── buzzer_tool.py          # [NEW] Interactive TUI
└── tests/                          # [NEW] Unit tests
    ├── __init__.py
    ├── conftest.py                 # [NEW] Mock pigpio fixtures
    ├── test_driver.py              # [NEW] Buzzer tests
    ├── test_music.py               # [NEW] MusicBuzzer tests
    └── test_config.py              # [NEW] ConfigManager tests
```

---

## 4. Module Specifications

### 4.1 `notes.py` — Note Frequency Constants

Single source of truth for all note data. Eliminates M1 (duplication).

```python
# Named note frequencies (C3–B7)
NOTES = {
    "C4": 262, "D4": 294, "E4": 330, "F4": 349,
    "G4": 392, "A4": 440, "B4": 494,
    "C5": 523, "D5": 587, "E5": 659, "F5": 698,
    "G5": 784, "A5": 880, "B5": 988,
    "C6": 1046, "D6": 1175, "E6": 1318, "F6": 1397,
    "G6": 1568, "A6": 1760, "B6": 1976,
    # ... extended range C3–B7
}

# Interactive keyboard-to-note mapping
KEYBOARD_MAP = {
    "z": "C4", "x": "D4", "c": "E4", "v": "F4",
    "b": "G4", "n": "A4", "m": "B4",
    "a": "C5", "s": "D5", "d": "E5", "f": "F5",
    "g": "G5", "h": "A5", "j": "B5",
    "q": "C6", "w": "D6", "e": "E6", "r": "F6",
    "t": "G6", "y": "A6", "u": "B6",
}

# Emotion sounds — used by both pi0buzzer and ninja_core/robot_sound.py
EMOTION_SOUNDS = {
    "happy":        [("C5", 0.1), ("E5", 0.1), ("G5", 0.1), ("C6", 0.15)],
    "sad":          [("B4", 0.4), ("A4", 0.4), ("G4", 0.6)],
    "exciting":     [("C6", 0.08), ("E6", 0.08), ("G6", 0.08)] * 2,
    "angry":        [("D4", 0.1), ("C4", 0.1), ("D4", 0.1), ("C4", 0.2)],
    "confusing":    [("E5", 0.2), ("G4", 0.2), ("C5", 0.3)],
    "cry":          [("E5", 0.3), ("D5", 0.2), ("C5", 0.5), ("pause", 0.2), ("C5", 0.4)],
    "embarrassing": [("A4", 0.15), ("G4", 0.15), ("A4", 0.3)],
    "idle":         [("C5", 0.1), ("pause", 0.5), ("C5", 0.1)],
    "laughing":     [("G5", 0.1), ("pause", 0.05)] * 5,
    "scary":        [("C4", 0.5), ("D4", 0.2), ("C4", 0.5)],
    "shy":          [("C5", 0.1), ("E5", 0.3), ("C5", 0.1), ("E5", 0.4)],
    "sleepy":       [("G4", 0.5), ("F4", 0.5), ("E4", 0.7)],
    "speaking":     [("C5", 0.1), ("D5", 0.1), ("E5", 0.1)] * 3,
    "surprising":   [("G6", 0.3)],
}
```

### 4.2 `core/driver.py` — Buzzer Class

Implements `Actuator` ABC. Fixes C2, C3, M5, m1, m2.

```python
class Buzzer(Actuator):
    def __init__(self, pin: int, pi: Optional[pigpio.pi] = None): ...
    def initialize(self) -> None: ...       # Starts worker, sets pin mode
    def execute(self, command: dict) -> None: ...  # Queues {frequency, duration}
    def play_sound(self, frequency: int, duration: float) -> None: ...  # Legacy compat
    def off(self) -> None: ...               # Drains queue, stops worker
    
    # New properties/methods:
    @property
    def is_initialized(self) -> bool: ...
    @property
    def volume(self) -> int: ...             # PWM duty cycle (0–255)
    @volume.setter
    def volume(self, value: int) -> None: ...
    def __enter__(self): ...                 # Context manager for standalone
    def __exit__(self, *args): ...
```

Key improvements:
- **Re-init guard**: `initialize()` is idempotent (no duplicate workers)
- **Volume control**: Configurable PWM duty cycle via `volume` property
- **Frequency validation**: Clamps to 20–20,000 Hz range
- **Queue-based pauses**: `("__pause__", duration)` handled in worker thread
- **Queue drain**: `off()` clears pending sounds before stopping

### 4.3 `core/music.py` — MusicBuzzer Class

Extends Buzzer with musical capabilities. Fixes C1.

```python
class MusicBuzzer(Buzzer):
    def play_song(self, song: list[tuple[str, float]]) -> None: ...
    def play_emotion(self, name: str) -> None: ...
    def play_music(self) -> None: ...        # Interactive keyboard piano (FIXES C1)
```

### 4.4 `config/config_manager.py` — BuzzerConfigManager

Fixes M2. Follows `pi0disp` and `pi0servo` patterns.

```python
DEFAULT_CONFIG = {"pin": 17, "volume": 128}

class BuzzerConfigManager:
    def __init__(self, config_path: str = "buzzer.json"): ...
    def load(self) -> dict: ...
    def save(self) -> None: ...
    def get_pin(self) -> int: ...
    def set_pin(self, pin: int) -> None: ...
    def get_volume(self) -> int: ...
    def set_volume(self, volume: int) -> None: ...
    def export_config(self, path: str) -> None: ...
    def import_config(self, path: str) -> None: ...
```

### 4.5 `driver.py` (root) — Compatibility Shim

Ensures `from pi0buzzer.driver import MusicBuzzer` still works for `hal.py`.

```python
"""Compatibility shim — re-exports from new module path."""
from pi0buzzer.core.driver import Buzzer
from pi0buzzer.core.music import MusicBuzzer

__all__ = ["Buzzer", "MusicBuzzer"]
```

### 4.6 `cli/buzzer_tool.py` — Interactive TUI

Fixes M7. Menu-driven interactive tool matching `display_tool.py` and `sensor_tool.py` patterns.

```
╔══════════════════════════════════════════════════════════════╗
║               pi0buzzer Interactive Tool                    ║
╠══════════════════════════════════════════════════════════════╣
║  1. Init          - Set up buzzer pin & save config         ║
║  2. Beep          - Play a single tone (freq/duration)      ║
║  3. Play Emotion  - Play an emotion sound by name           ║
║  4. Play Music    - Interactive keyboard piano              ║
║  5. Play Song     - Play a built-in demo melody             ║
║  6. Volume        - Adjust PWM duty cycle (volume)          ║
║  7. Info          - Show config & health check              ║
║  8. Config        - Show/export/import settings             ║
║  9. Exit                                                    ║
╚══════════════════════════════════════════════════════════════╝
```

### 4.7 `__main__.py` — CLI Commands

Individual scripting commands + `buzzer-tool` entry point.

| Command | Description |
|---|---|
| `pi0buzzer init <pin>` | Initialize buzzer, save `buzzer.json` |
| `pi0buzzer beep [freq] [dur]` | Play a tone |
| `pi0buzzer play <emotion>` | Play named emotion sound |
| `pi0buzzer info [--health-check]` | Show config, optionally verify hardware |
| `pi0buzzer config show\|export\|import` | Configuration management |
| `pi0buzzer buzzer-tool` | Launch interactive TUI |

---

## 5. Phased Implementation

### Phase 1: Scaffold
- [ ] Create directory structure (`core/`, `config/`, `cli/`, `tests/`)
- [ ] Create `pyproject.toml` (v1.0.0, deps: pigpio, click; dev: ruff, pytest)
- [ ] Create `LICENSE` (MIT)
- [ ] Create all `__init__.py` files
- [ ] **Lint**: `uv run ruff check pi0buzzer/`

### Phase 2: Core Driver (`core/driver.py`)
- [ ] Implement `Buzzer(Actuator)` with queue-based worker
- [ ] Add volume control, frequency validation, re-init guard
- [ ] Add queue-based pause support (`__pause__` sentinel)
- [ ] Add context manager (`__enter__`/`__exit__`)
- [ ] **Lint**: `uv run ruff check pi0buzzer/src/pi0buzzer/core/driver.py`

### Phase 3: Notes & Music Engine (`notes.py` + `core/music.py`)
- [ ] Create `notes.py` with `NOTES`, `KEYBOARD_MAP`, `EMOTION_SOUNDS`
- [ ] Implement `MusicBuzzer(Buzzer)` with `play_song()`, `play_emotion()`, `play_music()`
- [ ] Create `driver.py` compatibility shim (root-level re-export)
- [ ] **Lint**: `uv run ruff check pi0buzzer/src/pi0buzzer/`

### Phase 4: Config Manager (`config/config_manager.py`)
- [ ] Implement `BuzzerConfigManager` (load, save, validate, export, import)
- [ ] **Lint**: `uv run ruff check pi0buzzer/src/pi0buzzer/config/`

### Phase 5: CLI & Buzzer Tool
- [ ] Implement `__main__.py` CLI commands (init, beep, play, info, config)
- [ ] Implement `cli/buzzer_tool.py` interactive TUI (9-option menu)
- [ ] **Lint**: `uv run ruff check pi0buzzer/src/pi0buzzer/__main__.py pi0buzzer/src/pi0buzzer/cli/`

### Phase 6: Unit Tests
- [ ] Create `tests/conftest.py` (mock pigpio fixtures)
- [ ] Create `tests/test_driver.py` (Buzzer class tests)
- [ ] Create `tests/test_music.py` (MusicBuzzer tests)
- [ ] Create `tests/test_config.py` (ConfigManager tests)
- [ ] **Test**: `uv run pytest pi0buzzer/tests/ -v`
- [ ] **Lint**: `uv run ruff check pi0buzzer/tests/`

### Phase 7: ninja_core Integration
- [ ] Refactor `ninja_core/robot_sound.py` → import `NOTES` and `EMOTION_SOUNDS` from `pi0buzzer.notes`
- [ ] Verify `hal.py` loads new library via compatibility shim
- [ ] **Lint**: `uv run ruff check ninja_core/src/ninja_core/robot_sound.py`

### Phase 8: Documentation
- [ ] Write `README.md` (architecture, CLI, standalone/integration usage)
- [ ] Update `DevelopmentLog.md`
- [ ] Update `ProjectUpgradePlan.md` milestone status

---

## 6. Verification Plan

### Automated
```bash
uv run ruff check pi0buzzer/        # Lint all files
uv run pytest pi0buzzer/tests/ -v   # Run unit tests
uv run ruff check ninja_core/src/ninja_core/robot_sound.py  # Integration lint
```

### Manual (Raspberry Pi)
```bash
# Interactive tool
uv run pi0buzzer buzzer-tool

# Individual CLI commands
uv run pi0buzzer init 17
uv run pi0buzzer beep 440 0.5
uv run pi0buzzer play happy
uv run pi0buzzer info --health-check

# ninja_core integration
uv run ninja_core server    # Verify buzzer sounds in web interface
```

# pi0servo Step-by-Step Rebuild Plan

> **Goal:** Build a new `pi0servo` library from scratch with quality gates at each phase.

> [!IMPORTANT]
> The old library is preserved in `pi0servo_bak/` for reference. This plan assumes a **clean `pi0servo/` folder**.

---

## Overview

| Phase | Name | Deliverables | Validation Gate |
|-------|------|--------------|-----------------|
| 0 | Project Scaffold | `pyproject.toml`, src structure, tests/ | `uv sync` passes |
| 1 | Motion Module | `motion/easing.py`, `motion/calculator.py` | Unit tests pass |
| 2 | Command Parser | `parser/command.py` | Unit tests pass |
| 3 | Core Classes | `core/servo.py`, `core/multi_servos.py` | Unit tests + lint pass |
| 4 | Config Manager | `config/config_manager.py` | Unit tests pass |
| 5 | CLI Commands | `cli/*.py`, `__main__.py` | CLI smoke tests pass |
| 6 | Integration | Export API, compatibility aliases | Integration tests pass (Pi) |

---

## Phase 0: Project Scaffold (Day 0)

### 0.1 Create Directory Structure

```bash
cd /path/to/NinjaRobotV5/pi0servo

# Create source tree
mkdir -p src/pi0servo/{motion,parser,core,config,cli}
mkdir -p tests

# Create empty __init__.py files
touch src/pi0servo/__init__.py
touch src/pi0servo/motion/__init__.py
touch src/pi0servo/parser/__init__.py
touch src/pi0servo/core/__init__.py
touch src/pi0servo/config/__init__.py
touch src/pi0servo/cli/__init__.py
touch tests/__init__.py
```

### 0.2 Create `pyproject.toml`

```toml
[project]
name = "pi0servo"
version = "1.0.0"
description = "Servo control library for Raspberry Pi with velocity-based motion."
authors = [
    {name = "NinjaRobot Team", email = "contact@ninjarobot.example"},
]
dependencies = [
    "pigpio",
    "click",
    "blessed",
    "ninja_utils",
]
requires-python = ">=3.9"
readme = "README.md"
license = {file = "LICENSE"}

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
]

[project.scripts]
pi0servo = "pi0servo.__main__:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

### 0.3 Create Minimal `__init__.py`

```python
# src/pi0servo/__init__.py
"""pi0servo - Velocity-based servo control for Raspberry Pi."""

__version__ = "1.0.0"
```

### 0.4 Create Minimal `__main__.py`

```python
# src/pi0servo/__main__.py
"""CLI entry point for pi0servo."""

import click

@click.group()
def cli():
    """pi0servo CLI - Servo control for Raspberry Pi."""
    pass

if __name__ == "__main__":
    cli()
```

### 0.5 Create `tests/conftest.py` (Mock pigpio)

```python
# tests/conftest.py
"""Pytest fixtures for mocking pigpio on PC/Mac."""

import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def mock_pigpio(monkeypatch):
    """Mock pigpio for all tests - no hardware required."""
    mock_pi = MagicMock()
    mock_pi.connected = True
    mock_pi.get_servo_pulsewidth.return_value = 1500
    mock_pi.set_servo_pulsewidth.return_value = None
    
    monkeypatch.setattr("pigpio.pi", lambda: mock_pi)
    return mock_pi
```

### ✅ Phase 0 Validation Gate

```bash
cd pi0servo

# 1. Create virtual environment
uv venv
source .venv/bin/activate

# 2. Install dependencies
uv sync

# 3. Verify import
uv run python -c "import pi0servo; print(pi0servo.__version__)"
# Expected: 1.0.0

# 4. Verify CLI
uv run pi0servo --help
# Expected: Shows help message

# 5. Run empty test suite
uv run pytest tests/ -v
# Expected: 0 tests collected (OK at this point)
```

**Gate Criteria:** All 5 commands execute without errors.

---

## Phase 1: Motion Module (Day 1)

### 1.1 Create `motion/easing.py`

```python
# src/pi0servo/motion/easing.py
"""Easing functions for smooth servo movement."""

def linear(t: float) -> float:
    """Linear interpolation (no easing)."""
    return t

def ease_out(t: float) -> float:
    """Quadratic ease-out (DEFAULT). Start fast, end slow."""
    return t * (2 - t)

def ease_in(t: float) -> float:
    """Quadratic ease-in. Start slow, end fast."""
    return t * t

def ease_in_out(t: float) -> float:
    """Quadratic ease-in-out. Smooth acceleration and deceleration."""
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2

EASING_FUNCTIONS = {
    "linear": linear,
    "ease_out": ease_out,
    "ease_in": ease_in,
    "ease_in_out": ease_in_out,
}
```

### 1.2 Create `motion/calculator.py`

```python
# src/pi0servo/motion/calculator.py
"""Velocity and duration calculations for servo movement."""

PHYSICAL_MAX_VELOCITY = 600.0  # °/sec (SG90 spec: 0.10s/60°)

FMS_MULTIPLIERS = {
    "F": 1.0,   # Fast = 100% of speed limit
    "M": 0.75,  # Medium = 75% of speed limit
    "S": 0.5,   # Slow = 50% of speed limit
}

def calculate_duration(distance: float, speed_limit: int, speed_mode: str) -> float:
    """Calculate movement duration from distance and velocity.
    
    Args:
        distance: Angle difference in degrees (always positive)
        speed_limit: Per-servo speed limit (0-100)
        speed_mode: "F", "M", or "S"
    
    Returns:
        Duration in seconds
    """
    fms_mult = FMS_MULTIPLIERS.get(speed_mode, 0.75)
    velocity = PHYSICAL_MAX_VELOCITY * (speed_limit / 100) * fms_mult
    return abs(distance) / velocity if velocity > 0 else 0
```

### 1.3 Update `motion/__init__.py`

```python
# src/pi0servo/motion/__init__.py
from .easing import ease_out, ease_in, ease_in_out, linear, EASING_FUNCTIONS
from .calculator import calculate_duration, PHYSICAL_MAX_VELOCITY, FMS_MULTIPLIERS

__all__ = [
    "ease_out", "ease_in", "ease_in_out", "linear", "EASING_FUNCTIONS",
    "calculate_duration", "PHYSICAL_MAX_VELOCITY", "FMS_MULTIPLIERS",
]
```

### 1.4 Create `tests/test_motion.py`

```python
# tests/test_motion.py
"""Unit tests for motion module."""

import pytest
from pi0servo.motion import ease_out, ease_in, ease_in_out, linear, calculate_duration

class TestEasingFunctions:
    def test_linear_midpoint(self):
        assert linear(0.5) == 0.5
    
    def test_ease_out_midpoint(self):
        assert ease_out(0.5) == 0.75  # Faster at start
    
    def test_ease_in_midpoint(self):
        assert ease_in(0.5) == 0.25  # Slower at start
    
    def test_boundaries(self):
        for fn in [linear, ease_out, ease_in, ease_in_out]:
            assert fn(0.0) == 0.0
            assert fn(1.0) == 1.0

class TestCalculateDuration:
    def test_fast_mode(self):
        # 90° at 100% speed limit, Fast mode
        # velocity = 600 * 1.0 * 1.0 = 600 °/sec
        # duration = 90 / 600 = 0.15 sec
        assert calculate_duration(90, 100, "F") == 0.15
    
    def test_medium_mode(self):
        # 90° at 80% speed limit, Medium mode
        # velocity = 600 * 0.8 * 0.75 = 360 °/sec
        # duration = 90 / 360 = 0.25 sec
        assert calculate_duration(90, 80, "M") == 0.25
    
    def test_slow_mode(self):
        # 45° at 100% speed limit, Slow mode
        # velocity = 600 * 1.0 * 0.5 = 300 °/sec
        # duration = 45 / 300 = 0.15 sec
        assert calculate_duration(45, 100, "S") == 0.15
    
    def test_zero_speed_returns_zero(self):
        assert calculate_duration(90, 0, "F") == 0
```

### ✅ Phase 1 Validation Gate

```bash
cd pi0servo
source .venv/bin/activate

# 1. Lint
uv run ruff check src/pi0servo/motion/
# Expected: No errors

# 2. Unit tests
uv run pytest tests/test_motion.py -v
# Expected: 8 passed

# 3. Quick import test
uv run python -c "from pi0servo.motion import ease_out, calculate_duration; print(ease_out(0.5), calculate_duration(90, 80, 'F'))"
# Expected: 0.75 0.1875
```

**Gate Criteria:** Lint clean, all tests pass.

---

## Phase 2: Command Parser (Day 1-2)

### 2.1 Create `parser/command.py`

```python
# src/pi0servo/parser/command.py
"""Parser for movement-tool command format."""

def parse_command(command_str: str) -> tuple[str, dict[int, int]]:
    """Parse movement-tool format command string.
    
    Format: [SPEED_]PIN:ANGLE[/PIN:ANGLE...]
    
    Args:
        command_str: e.g., "F_20:45/21:M" or "17:30"
    
    Returns:
        Tuple of (speed_mode, {pin: angle})
    
    Raises:
        ValueError: If command format is invalid
    """
    speed_mode = "M"  # Default Medium
    
    # Check for speed prefix
    if command_str.startswith(("S_", "M_", "F_")):
        speed_mode = command_str[0]
        command_str = command_str[2:]
    
    movements = {}
    parts = command_str.split("/")
    
    for part in parts:
        if ":" not in part:
            raise ValueError(f"Invalid format: '{part}'. Expected PIN:ANGLE")
        
        pin_str, angle_str = part.split(":", 1)
        pin = int(pin_str)
        
        # Parse angle (X=90, M=-90, C=0, or number)
        angle_upper = angle_str.upper()
        if angle_upper == "X":
            angle = 90
        elif angle_upper == "M":
            angle = -90
        elif angle_upper == "C":
            angle = 0
        else:
            angle = int(angle_str)
            if not -90 <= angle <= 90:
                raise ValueError(f"Angle must be -90 to 90, got {angle}")
        
        movements[pin] = angle
    
    return speed_mode, movements
```

### 2.2 Update `parser/__init__.py`

```python
# src/pi0servo/parser/__init__.py
from .command import parse_command

__all__ = ["parse_command"]
```

### 2.3 Create `tests/test_parser.py`

```python
# tests/test_parser.py
"""Unit tests for command parser."""

import pytest
from pi0servo.parser import parse_command

class TestParseCommand:
    def test_simple_command(self):
        speed, movements = parse_command("20:45")
        assert speed == "M"  # Default
        assert movements == {20: 45}
    
    def test_multiple_servos(self):
        speed, movements = parse_command("20:45/21:30/22:-15")
        assert speed == "M"
        assert movements == {20: 45, 21: 30, 22: -15}
    
    def test_fast_prefix(self):
        speed, movements = parse_command("F_20:45")
        assert speed == "F"
        assert movements == {20: 45}
    
    def test_slow_prefix(self):
        speed, movements = parse_command("S_17:0")
        assert speed == "S"
        assert movements == {17: 0}
    
    def test_angle_shortcuts(self):
        speed, movements = parse_command("20:X/21:M/22:C")
        assert movements == {20: 90, 21: -90, 22: 0}
    
    def test_invalid_format_no_colon(self):
        with pytest.raises(ValueError, match="Invalid format"):
            parse_command("2045")
    
    def test_invalid_angle_out_of_range(self):
        with pytest.raises(ValueError, match="Angle must be"):
            parse_command("20:100")
```

### ✅ Phase 2 Validation Gate

```bash
cd pi0servo
source .venv/bin/activate

# 1. Lint
uv run ruff check src/pi0servo/parser/
# Expected: No errors

# 2. Unit tests
uv run pytest tests/test_parser.py -v
# Expected: 7 passed

# 3. All tests so far
uv run pytest tests/ -v
# Expected: 15 passed
```

**Gate Criteria:** Lint clean, all tests pass.

---

## Phase 3: Core Classes (Day 2-3)

### 3.1 Reference Implementation

> **Reference:** See `pi0servo_bak/src/pi0servo/core/` for existing patterns.

Key files to reference:
- `piservo.py` - Low-level PWM control
- `calibrable_servo.py` - Calibration data handling
- `multi_servo.py` - Multi-servo coordination

### 3.2 Create `core/servo.py`

```python
# src/pi0servo/core/servo.py
"""Single servo control with calibration support."""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pigpio

from pi0servo.motion import ease_out, calculate_duration

logger = logging.getLogger(__name__)

class Servo:
    """Single servo controller with velocity-based movement."""
    
    DEFAULT_MIN_PW = 500
    DEFAULT_CENTER_PW = 1500
    DEFAULT_MAX_PW = 2500
    DEFAULT_SPEED = 80
    
    def __init__(
        self,
        pi: "pigpio.pi",
        pin: int,
        min_pw: int = DEFAULT_MIN_PW,
        center_pw: int = DEFAULT_CENTER_PW,
        max_pw: int = DEFAULT_MAX_PW,
        speed: int = DEFAULT_SPEED,
    ):
        self._pi = pi
        self._pin = pin
        self._min_pw = min_pw
        self._center_pw = center_pw
        self._max_pw = max_pw
        self._speed = speed
        self._current_angle = 0.0
    
    @property
    def pin(self) -> int:
        return self._pin
    
    @property
    def current_angle(self) -> float:
        return self._current_angle
    
    def angle_to_pulsewidth(self, angle: float) -> int:
        """Convert angle (-90 to 90) to pulsewidth."""
        if angle < 0:
            pw = self._center_pw + (self._min_pw - self._center_pw) * (angle / -90)
        else:
            pw = self._center_pw + (self._max_pw - self._center_pw) * (angle / 90)
        return int(pw)
    
    def set_angle(self, angle: float) -> None:
        """Set servo to angle immediately (no interpolation)."""
        pw = self.angle_to_pulsewidth(angle)
        self._pi.set_servo_pulsewidth(self._pin, pw)
        self._current_angle = angle
    
    def off(self) -> None:
        """Turn off servo (stop PWM signal)."""
        self._pi.set_servo_pulsewidth(self._pin, 0)
```

### 3.3 Create `core/multi_servos.py`

See `ProjectUpgradePlan.md` section 4.4 for the full API specification.

Key features:
- `move_all_sync()` with `threading.Event` for abort
- `move_to_async()` for native async support
- Legacy `move_all_angles_sync()` wrapper

### 3.4 Create `tests/test_core.py`

```python
# tests/test_core.py
"""Unit tests for core servo classes."""

import pytest
from pi0servo.core.servo import Servo

class TestServo:
    def test_angle_to_pulsewidth_center(self, mock_pigpio):
        servo = Servo(mock_pigpio, 20)
        assert servo.angle_to_pulsewidth(0) == 1500
    
    def test_angle_to_pulsewidth_max(self, mock_pigpio):
        servo = Servo(mock_pigpio, 20)
        assert servo.angle_to_pulsewidth(90) == 2500
    
    def test_angle_to_pulsewidth_min(self, mock_pigpio):
        servo = Servo(mock_pigpio, 20)
        assert servo.angle_to_pulsewidth(-90) == 500
    
    def test_set_angle_calls_pi(self, mock_pigpio):
        servo = Servo(mock_pigpio, 20)
        servo.set_angle(45)
        mock_pigpio.set_servo_pulsewidth.assert_called_once_with(20, 2000)
        assert servo.current_angle == 45
```

### ✅ Phase 3 Validation Gate

```bash
cd pi0servo
source .venv/bin/activate

# 1. Lint
uv run ruff check src/pi0servo/core/
# Expected: No errors

# 2. Unit tests
uv run pytest tests/test_core.py -v
# Expected: 4+ passed

# 3. All tests
uv run pytest tests/ -v --cov=pi0servo
# Expected: 19+ passed, coverage report generated
```

**Gate Criteria:** Lint clean, all tests pass, coverage > 70%.

---

## Phase 4: Config Manager (Day 3)

### 4.1 Reference Implementation

> **Reference:** See `pi0servo_bak/src/pi0servo/utils/servo_config_manager.py`

Key improvements:
- Use library-relative paths (not CWD)
- Add `speed` field to schema
- Add `export()` and `import_from()` methods

### 4.2 Create `config/config_manager.py`

(Implementation following schema in ProjectUpgradePlan.md section 4.2)

### ✅ Phase 4 Validation Gate

```bash
cd pi0servo
source .venv/bin/activate

# 1. Lint
uv run ruff check src/pi0servo/config/
# Expected: No errors

# 2. Unit tests
uv run pytest tests/test_config.py -v
# Expected: All passed

# 3. Integration test with temp file
uv run python -c "
from pi0servo.config import ConfigManager
import tempfile
import json

with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
    f.write(b'{}')
    path = f.name

cm = ConfigManager(path)
cm.save_pin(20, {'min': 500, 'center': 1500, 'max': 2500, 'speed': 80})
data = cm.get_pin(20)
assert data['speed'] == 80
print('Config manager OK')
"
```

**Gate Criteria:** Lint clean, all tests pass, integration test OK.

---

## Phase 5: CLI Commands (Day 4)

### 5.1 Reference Implementation

> **Reference:** See `pi0servo_bak/src/pi0servo/command/` for existing CLI patterns.

### 5.2 Create CLI Commands

| File | Command | Purpose |
|------|---------|---------|
| `cli/servo_tool.py` | `servo-tool` | Interactive menu |
| `cli/cmd.py` | `cmd` | Execute command string |
| `cli/move.py` | `move` | Move single servo |
| `cli/calib.py` | `calib` | Calibration wizard |
| `cli/status.py` | `status` | Show servo states |

### ✅ Phase 5 Validation Gate

```bash
cd pi0servo
source .venv/bin/activate

# 1. Lint
uv run ruff check src/pi0servo/cli/
# Expected: No errors

# 2. CLI help tests
uv run pi0servo --help
uv run pi0servo cmd --help
uv run pi0servo move --help
uv run pi0servo calib --help
uv run pi0servo status --help
# Expected: All show help messages

# 3. Full test suite
uv run pytest tests/ -v
# Expected: All passed
```

**Gate Criteria:** Lint clean, CLI help works, all tests pass.

---

## Phase 6: Integration (Day 5)

### 6.1 Update Exports

```python
# src/pi0servo/__init__.py
"""pi0servo - Velocity-based servo control for Raspberry Pi."""

from .core.servo import Servo
from .core.multi_servos import ServoGroup
from .parser.command import parse_command

# Backward compatibility alias
MultiServo = ServoGroup

__version__ = "1.0.0"
__all__ = ["Servo", "ServoGroup", "MultiServo", "parse_command", "__version__"]
```

### 6.2 Raspberry Pi Hardware Validation

```bash
# On Raspberry Pi Zero 2W
sudo pigpiod
cd /home/pi/NinjaRobotV5/pi0servo
source .venv/bin/activate
uv sync

# Test CLI
uv run pi0servo status
uv run pi0servo move 20 45 -s F
uv run pi0servo cmd "F_20:45/21:M"

# Test ninja_core integration
cd ../ninja_core
uv run ninja_core movement-tool
```

### ✅ Phase 6 Final Validation

| Test | Expected Result |
|------|-----------------|
| `uv run pi0servo status` | Shows all servo angles |
| `uv run pi0servo move 20 45` | Servo 20 moves to 45° |
| `uv run pi0servo cmd "F_20:0/21:0"` | Both servos center |
| `uv run ninja_core movement-tool` | Record/play movements work |

**Gate Criteria:** All hardware tests pass on Raspberry Pi.

---

## Abort Mechanism Design

### Threading-based Abort

```python
import threading

class ServoGroup:
    def __init__(self, ...):
        self._abort_event = threading.Event()
    
    def abort(self):
        """Signal all ongoing movements to stop immediately."""
        self._abort_event.set()
    
    def move_all_sync(self, angles, speed_mode="M") -> bool:
        """Synchronized movement with abort support."""
        self._abort_event.clear()
        
        for step in range(step_count):
            if self._abort_event.is_set():
                return False  # Aborted
            # ... interpolation ...
        
        return True  # Completed
```

### Async Abort

```python
import asyncio

class ServoGroup:
    async def move_to_async(self, angles, speed_mode="M") -> bool:
        """Native async movement with abort support."""
        self._async_abort = asyncio.Event()
        
        for step in range(step_count):
            if self._async_abort.is_set():
                return False
            await asyncio.sleep(step_interval)
        
        return True
```

---

## Development Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: DEVELOPMENT (PC/Mac)                    │
├─────────────────────────────────────────────────────────────────────┤
│  • Write all code on PC/Mac                                         │
│  • Run linting: uv run ruff check src/                              │
│  • Run unit tests with mocked pigpio                                │
│  • No hardware required                                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STAGE 2: VALIDATION (Raspberry Pi Zero 2W)             │
├─────────────────────────────────────────────────────────────────────┤
│  • Deploy code to Pi via git pull or scp                            │
│  • Run hardware integration tests                                   │
│  • Test CLI commands with physical servos                           │
│  • Verify ninja_core integration                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

**Document maintained by:** Development Team  
**Last updated:** 2026-02-07

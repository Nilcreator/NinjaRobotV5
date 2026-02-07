# pi0servo Step-by-Step Rebuild Plan

> **Goal:** Enable any developer to implement this plan with zero friction.

---

## 1. Development Workflow (Two-Stage Approach)

> **IMPORTANT:** All development is performed on PC/Mac, NOT on the Raspberry Pi.

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

**Why This Approach?**
1. **Faster iteration** - No need to wait for Pi boot/deploy cycles
2. **Better tooling** - Full IDE support on PC/Mac
3. **Avoid hardware damage** - Untested code doesn't touch servos
4. **CI/CD compatible** - Unit tests run in GitHub Actions

---

## 2. Stage 1: Development Environment (PC/Mac)

### Prerequisites (PC/Mac)

```bash
# 1. Ensure uv is installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone/navigate to project
cd NinjaRobotV5/pi0servo

# 3. Create and activate virtual environment (REQUIRED)
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 4. Install dependencies within venv
uv sync

# 5. Verify setup
uv run python -c "import pi0servo; print('OK')"
```

> [!IMPORTANT]
> **Always activate the virtual environment first** before running any `uv` commands.
> This keeps dependencies isolated and avoids polluting your system Python.

### Mocking pigpio for Development

Create `tests/conftest.py` for unit testing without hardware:

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def mock_pigpio(monkeypatch):
    """Mock pigpio for all tests - no hardware required."""
    mock_pi = MagicMock()
    mock_pi.connected = True
    mock_pi.get_servo_pulsewidth.return_value = 1500
    
    mock_module = MagicMock()
    mock_module.pi.return_value = mock_pi
    
    monkeypatch.setattr("pigpio.pi", lambda: mock_pi)
    return mock_pi
```

### Development Commands (PC/Mac Only)

```bash
# Lint code
uv run ruff check src/

# Run unit tests (mocked, no hardware)
uv run pytest tests/ -v

# Format code
uv run ruff format src/

# Type check (optional)
uv run mypy src/
```

---

## 3. Stage 2: Validation Environment (Raspberry Pi)

### Prerequisites (Raspberry Pi Zero 2W)

```bash
# 1. Start pigpio daemon
sudo pigpiod

# 2. Navigate to project
cd /home/pi/NinjaRobotV5/pi0servo

# 3. Sync latest code from development machine
git pull  # or use scp/rsync

# 4. Activate virtual environment (REQUIRED)
source .venv/bin/activate

# 5. Install/update dependencies within venv
uv sync
```

> [!IMPORTANT]
> **Always activate the virtual environment** (`source .venv/bin/activate`) before running any commands on the Raspberry Pi.

### Validation Commands (Raspberry Pi Only)

```bash
# Verify CLI works
uv run pi0servo --help

# Test interactive tool with physical servos
uv run pi0servo servo-tool

# Test single servo movement
uv run pi0servo move 20 45

# Test command format
uv run pi0servo cmd "F_20:45/21:M"

# Integration test with ninja_core
cd ../ninja_core
uv run ninja_core movement-tool
```

---

## 4. Abort Mechanism Design

> **Approved Enhancement:** Explicit abort signal propagation

### 4.1. Abort Signal via `threading.Event`

```python
import threading

class ServoGroup:
    def __init__(self, ...):
        self._abort_event = threading.Event()
    
    def abort(self):
        """Signal all ongoing movements to stop immediately."""
        self._abort_event.set()
    
    def _is_aborted(self) -> bool:
        """Check if abort was requested."""
        return self._abort_event.is_set()
    
    def _reset_abort(self):
        """Clear abort flag before starting a new movement."""
        self._abort_event.clear()
    
    def move_all_sync(self, angles, speed_mode="M"):
        """Synchronized movement with abort support."""
        self._reset_abort()
        
        for step in range(step_count):
            if self._is_aborted():
                self._log.warning("Movement aborted at step %d", step)
                return False  # Indicate incomplete movement
            
            # ... interpolation logic ...
            time.sleep(step_interval)
        
        return True  # Movement completed
```

### 4.2. Async Abort via `asyncio.Event`

```python
import asyncio

class ServoGroup:
    def __init__(self, ...):
        self._async_abort_event: asyncio.Event | None = None
    
    async def move_to_async(self, angles, speed_mode="M"):
        """Native async movement with abort support."""
        self._async_abort_event = asyncio.Event()
        
        for step in range(step_count):
            if self._async_abort_event.is_set():
                return False
            
            # ... interpolation logic ...
            await asyncio.sleep(step_interval)
        
        return True
    
    def abort_async(self):
        """Abort from any context (sync or async)."""
        if self._async_abort_event:
            self._async_abort_event.set()
```

### 4.3. Integration with ninja_core

```python
# ninja_core/web_server.py
@api_router.post("/emergency-stop")
async def emergency_stop():
    app_state.servos.abort()  # Threaded abort
    app_state.servos.abort_async()  # Async abort (if applicable)
    return {"status": "stopped"}
```

---

## 5. Async Support Design

> **Approved Enhancement:** Native `async move_to_async()`

### 5.1. Native Async Method

```python
class ServoGroup:
    async def move_to_async(
        self, 
        angles: list[float], 
        speed_mode: str = "M"
    ) -> bool:
        """Non-blocking async movement for use with asyncio.
        
        Args:
            angles: Target angles for each servo
            speed_mode: "F", "M", or "S"
        
        Returns:
            True if completed, False if aborted
        """
        self._async_abort_event = asyncio.Event()
        duration = self._calculate_max_duration(angles, speed_mode)
        step_count = max(1, int(duration * 50))  # 50 Hz update rate
        step_interval = duration / step_count
        
        start_angles = self.get_all_angles()
        
        for step in range(1, step_count + 1):
            if self._async_abort_event.is_set():
                return False
            
            progress = step / step_count
            eased_progress = ease_out(progress)
            
            next_angles = [
                start + (target - start) * eased_progress
                for start, target in zip(start_angles, angles)
            ]
            self._move_immediate(next_angles)
            
            await asyncio.sleep(step_interval)
        
        return True
```

### 5.2. Usage in ninja_core

```python
# ninja_core/movement_controller.py
async def execute_movement(self, angles, speed_mode="M"):
    """Execute movement using native async."""
    return await self._servos.move_to_async(angles, speed_mode)

# Alternative: wrap blocking call
async def execute_movement_threaded(self, angles, speed_mode="M"):
    """Execute movement in thread pool."""
    return await asyncio.to_thread(
        self._servos.move_all_sync, 
        angles, 
        speed_mode
    )
```

---

## 6. Implementation Phases (Detailed)

### Phase 1: Create Motion Module (Day 1)

**Files to create:**
```
pi0servo/src/pi0servo/motion/__init__.py
pi0servo/src/pi0servo/motion/easing.py
pi0servo/src/pi0servo/motion/calculator.py
```

**Step 1.1:** Create `motion/__init__.py`
```python
from .easing import ease_out, ease_in, ease_in_out, linear, EASING_FUNCTIONS
from .calculator import calculate_duration, PHYSICAL_MAX_VELOCITY, FMS_MULTIPLIERS

__all__ = [
    "ease_out", "ease_in", "ease_in_out", "linear", "EASING_FUNCTIONS",
    "calculate_duration", "PHYSICAL_MAX_VELOCITY", "FMS_MULTIPLIERS",
]
```

**Step 1.2:** Create `motion/easing.py`
```python
"""Easing functions for smooth servo movement."""

def linear(t: float) -> float:
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

**Step 1.3:** Create `motion/calculator.py`
```python
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

**Verification:**
```bash
cd pi0servo
uv run python -c "from pi0servo.motion import ease_out, calculate_duration; print(ease_out(0.5), calculate_duration(90, 80, 'F'))"
# Expected: 0.75 0.1875
```

---

### Phase 2: Create Command Parser (Day 1-2)

**Files to create:**
```
pi0servo/src/pi0servo/parser/__init__.py
pi0servo/src/pi0servo/parser/command.py
```

**Step 2.1:** Create `parser/command.py`
```python
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

**Verification:**
```bash
cd pi0servo
uv run python -c "from pi0servo.parser.command import parse_command; print(parse_command('F_20:45/21:M'))"
# Expected: ('F', {20: 45, 21: -90})
```

---

### Phase 3: Create Core Classes (Day 2-3)

**Files to create:**
```
pi0servo/src/pi0servo/core/servo.py        # New single servo class
pi0servo/src/pi0servo/core/multi_servos.py  # New multi-servo class
```

> **Important:** Keep old files (`piservo.py`, `calibrable_servo.py`, `multi_servo.py`) until Phase 7 to avoid breaking existing imports.

**Step 3.1:** Create `core/servo.py` following the API in ProjectUpgradePlan.md section 4.4.

**Step 3.2:** Create `core/multi_servos.py` following the API in ProjectUpgradePlan.md section 4.4.

**Step 3.3:** Add to `core/__init__.py`:
```python
from .servo import Servo
from .multi_servos import ServoGroup

# Backward compatibility aliases
from .multi_servo import MultiServo  # Keep old import working
```

---

### Phase 4: Create Config Manager (Day 3)

**Files to create:**
```
pi0servo/src/pi0servo/config/__init__.py
pi0servo/src/pi0servo/config/config_manager.py
```

**Key Changes from old `servo_config_manager.py`:**
1. Add `speed` field to schema
2. Support both library-relative and custom paths
3. Add `export()` and `import_from()` methods

---

### Phase 5: Create CLI Commands (Day 4)

**Files to create:**
```
pi0servo/src/pi0servo/cli/__init__.py
pi0servo/src/pi0servo/cli/servo_tool.py   # Interactive menu
pi0servo/src/pi0servo/cli/cmd.py          # Direct command
pi0servo/src/pi0servo/cli/move.py         # Single servo
pi0servo/src/pi0servo/cli/calib.py        # Calibration
pi0servo/src/pi0servo/cli/status.py       # Status display
pi0servo/src/pi0servo/cli/config_cmd.py   # Config management
```

**Update `__main__.py`:**
```python
from .cli import servo_tool, cmd, move, calib, status, config_cmd

cli.add_command(servo_tool.main, "servo-tool")
cli.add_command(cmd.main, "cmd")
cli.add_command(move.main, "move")
cli.add_command(calib.main, "calib")
cli.add_command(status.main, "status")
cli.add_command(config_cmd.main, "config")
```

---

### Phase 6: Update Exports (Day 5)

**Update `__init__.py`:**
```python
from .core.servo import Servo
from .core.multi_servos import ServoGroup
from .parser.command import parse_command

# Backward compatibility
MultiServo = ServoGroup

__all__ = ["Servo", "ServoGroup", "MultiServo", "parse_command"]
```

---

### Phase 7: Delete Old Files (Day 5)

**Only after verifying new code works:**
```bash
rm pi0servo/src/pi0servo/core/piservo.py
rm pi0servo/src/pi0servo/core/calibrable_servo.py
rm pi0servo/src/pi0servo/core/multi_servo.py
rm pi0servo/src/pi0servo/helper/thread_multi_servo.py
rm pi0servo/src/pi0servo/helper/thread_worker.py
rm pi0servo/src/pi0servo/utils/servo_config_manager.py
rmdir pi0servo/src/pi0servo/helper
rmdir pi0servo/src/pi0servo/utils
```

---

## 7. Verification Commands

```bash
# 1. Unit tests (create tests/ directory with pytest tests)
cd pi0servo && uv run pytest tests/ -v

# 2. CLI smoke test
uv run pi0servo servo-tool  # Should show menu
uv run pi0servo status      # Should show servo states:

# 3. Command parser test
uv run pi0servo cmd "20:45" --no-wait

# 4. Integration with ninja_core
cd ../ninja_core
uv run ninja_core movement-tool
# Record and play movement - should work unchanged
```

---

## 8. Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: pi0servo.motion` | New module not installed | Run `uv pip install -e .` in pi0servo dir |
| `AttributeError: 'ServoGroup' has no attribute 'move_all_angles_sync'` | Legacy method missing | Add legacy wrapper method (see ProjectUpgradePlan.md section 4.6) |
| `pigpio.error: 'unconnected pi'` | pigpiod not running | Run `sudo pigpiod` |
| Config file not found | CWD issue | Use absolute path or library-relative path |

---

## 9. File Inventory

### Files to Create (New)

| Path | Purpose | Priority |
|------|---------|----------|
| `motion/__init__.py` | Motion module exports | High |
| `motion/easing.py` | Easing functions | High |
| `motion/calculator.py` | Duration/velocity calculations | High |
| `parser/__init__.py` | Parser module exports | High |
| `parser/command.py` | Movement-tool format parser | High |
| `core/servo.py` | New single servo class | High |
| `core/multi_servos.py` | New multi-servo class | High |
| `config/__init__.py` | Config module exports | High |
| `config/config_manager.py` | Calibration persistence | High |
| `cli/__init__.py` | CLI module exports | Medium |
| `cli/servo_tool.py` | Interactive menu | Medium |
| `cli/cmd.py` | Direct command execution | Medium |
| `cli/move.py` | Single servo movement | Medium |
| `cli/calib.py` | Calibration command | Medium |
| `cli/status.py` | Status display | Medium |
| `cli/config_cmd.py` | Config management | Medium |

### Files to Delete (After Migration)

| Path | Lines | Replaced By |
|------|-------|-------------|
| `core/piservo.py` | ~170 | `core/servo.py` |
| `core/calibrable_servo.py` | ~270 | `core/servo.py` |
| `core/multi_servo.py` | ~320 | `core/multi_servos.py` |
| `helper/thread_multi_servo.py` | ~140 | (unused) |
| `helper/thread_worker.py` | ~215 | (unused) |
| `utils/servo_config_manager.py` | ~100 | `config/config_manager.py` |

---

**Document maintained by:** Development Team  
**Last updated:** 2026-02-07

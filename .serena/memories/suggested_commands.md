# NinjaRobotV5 - Suggested Commands

## Package Management (uv)
```bash
# Install all workspace packages in editable mode
uv sync

# Install a specific library
uv pip install -e ./pi0servo
uv pip install -e ./pi0disp
uv pip install -e ./pi0buzzer
uv pip install -e ./pi0vl53l0x
uv pip install -e ./ninja_core
uv pip install -e ./ninja_utils
uv pip install -e ./ninja_ble
```

## Linting & Formatting
```bash
# Lint a file
uv run ruff check <file>

# Lint entire project
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix <file>

# Format code
uv run ruff format <file>
```

## Running Tests
```bash
# Run tests for a specific library
cd pi0servo && uv run pytest tests/ -v
cd pi0vl53l0x && uv run pytest tests/ -v
```

## Core Application Commands
```bash
# Start the web server (interactive mode - prompts for ngrok token)
uv run ninja_core server

# Start in autostart mode (for systemd, non-interactive)
uv run ninja_core server --autostart

# Interactive AI chat (terminal)
uv run ninja_core chat

# Config management
uv run ninja_core config import-all    # Import all driver configs
uv run ninja_core config export-all    # Export to driver configs
uv run ninja_core config set-key gemini YOUR_API_KEY

# Movement tool (interactive)
uv run ninja_core movement-tool
```

## pi0servo Commands
```bash
# Interactive servo tool
uv run pi0servo servo-tool

# Direct command
uv run pi0servo cmd "F_20:45/21:M"

# Calibration
uv run pi0servo calib <pin>
uv run pi0servo calib --show

# Single move
uv run pi0servo move <pin> <angle>

# Config management
uv run pi0servo config show
uv run pi0servo config export backup.json
uv run pi0servo config import backup.json
```

## pi0disp Commands
```bash
# Display image
uv run pi0disp image assets/images/sample_face.jpg

# Ball animation test
uv run pi0disp ball_anime --num-balls 5
```

## pi0buzzer Commands
```bash
# Initialize buzzer
uv run pi0buzzer init 17

# Play a beep
uv run pi0buzzer beep 440 0.5

# Play music
uv run pi0buzzer playmusic
```

## pi0vl53l0x Commands
```bash
# Health check
uv run pi0vl53l0x status

# Single reading
uv run pi0vl53l0x get --count 10

# Performance test
uv run pi0vl53l0x performance --count 100
```

## Systemd Service (Raspberry Pi)
```bash
# Install autostart service
uv run ninja_utils install-startup

# Check service status
uv run ninja_utils status-startup

# Remove service
uv run ninja_utils remove-startup
```

## System Utilities (macOS/Darwin)
```bash
# File search
find . -name "*.py" -type f
fd -e py

# Content search
grep -r "pattern" --include="*.py" .
rg "pattern" -t py

# Git
git status
git log -n 10 --oneline
git diff
```

## Hardware Prerequisites (Raspberry Pi only)
```bash
# Start pigpio daemon (required for all GPIO operations)
sudo pigpiod

# Enable SPI/I2C via raspi-config
sudo raspi-config
```

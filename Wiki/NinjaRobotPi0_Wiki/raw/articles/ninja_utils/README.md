# ninja_utils

This library provides shared utilities for the NinjaRobotV4 project, including:
- Centralized logging
- Non-blocking keyboard input
- Systemd service management for autostart

## Installation

To install this library in editable mode for development:

```bash
cd /path/to/your/NinjaRobotV4/ninja_utils
uv pip install -e .
```

## CLI Commands

**`install-startup`**
- Installs the systemd service for automatic startup.
- Usage: `uv run ninja_utils install-startup`

**`remove-startup`**
- Removes the systemd service.
- Usage: `uv run ninja_utils remove-startup`

**`status-startup`**
- Checks the status of the service.
- Usage: `uv run ninja_utils status-startup`

## Usage

Refer to the `samples/sample.py` file for an example of how to use the utilities.

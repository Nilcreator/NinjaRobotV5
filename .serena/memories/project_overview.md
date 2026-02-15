# NinjaRobotV5 - Project Overview

## Purpose
NinjaRobotV5 is an AI-powered educational robot platform running on **Raspberry Pi Zero 2W**. It features **dual connectivity** (BLE + Web), a **Gemini AI agent** for natural language control, and a modular plugin architecture.

## Tech Stack
- **Language:** Python 3.11+
- **Async Framework:** asyncio (all I/O must be non-blocking)
- **Web Server:** FastAPI + Uvicorn + WebSocket
- **AI Agent:** Google Gemini via `google-genai` SDK
- **BLE:** `bless` (GATT server) + `bleak` (BLE backend) + `dbus-fast`
- **GPIO:** `pigpio` (daemon-based, precise PWM)
- **Display:** ST7789V via SPI (PIL/Pillow for rendering)
- **Package Manager:** `uv` (NOT pip)
- **Hardware:** Raspberry Pi Zero 2W, SG90 servos, ST7789V display, passive buzzer, VL53L0X ToF sensor

## Architecture

### Core Packages
| Package | Role |
|---------|------|
| `ninja_core` | Orchestrator: HAL, Config, CommandDispatcher, AI Agent, Web Server, Movement, Faces, Sound, Perception |
| `ninja_ble` | BLE GATT server with chunking protocol |
| `ninja_utils` | Shared utilities: logging, interfaces (ABCs), systemd service management |
| `ninja_webapp` | Web frontend (served by FastAPI) |

### Hardware Driver Libraries (Plugins)
| Library | Purpose | ABC |
|---------|---------|-----|
| `pi0servo` | Velocity-based servo control (8ch), easing curves, interactive calibration | `Actuator` |
| `pi0disp` | ST7789V display rendering, face animations | `Actuator` |
| `pi0buzzer` | Non-blocking PWM sound, thread-safe queue | `Actuator` |
| `pi0vl53l0x` | VL53L0X ToF distance sensor, continuous monitoring | `Sensor` |

### Key Design Patterns
- **Hardware Abstraction Layer (HAL):** `ninja_core/hal.py` - Dynamic driver loading via `importlib`, validates against ABCs
- **CommandDispatcher:** Singleton that routes BLE & Web commands to HAL/Agent
- **ABC Interfaces:** `ninja_utils/interfaces.py` - `Sensor` (initialize/get_data/close) and `Actuator` (initialize/execute/off)
- **Driver Registry:** Maps driver names to module.class paths for dynamic loading

## File Structure (Root)
```
NinjaRobotV5/
├── ninja_core/      # Orchestrator (HAL, Config, Agent, WebServer, Motion, etc.)
├── ninja_ble/       # BLE GATT service
├── ninja_utils/     # Shared utilities & ABCs (interfaces.py)
├── ninja_webapp/    # Web frontend
├── pi0servo/        # Servo library (rebuilt with velocity-based control)
├── pi0disp/         # Display library (ST7789V)
├── pi0buzzer/       # Buzzer library
├── pi0vl53l0x/      # Distance sensor library (rewritten)
├── pi0vl53l0x_bak/  # Backup of old VL53L0X lib
├── assets/          # Images, fonts, sounds
├── GEMINI.md        # AI development protocol
├── README.md        # Project README (EN/JA/ZH-TW)
├── DevelopmentGuide.md  # Full API reference (2265 lines)
├── DevelopmentLog.md    # Dev log (Dec 2025 - Feb 2026)
├── InstallationGuide.md # Complete setup guide
├── ProjectUpgradePlan.md # Driver upgrade plan
├── pyproject.toml       # Root workspace config
└── uv.lock
```

## Development Status
- **Phase 1 (Modularity):** ✅ Complete - Plugin HAL, dynamic loading, ABC validation
- **Phase 2 (Dual Connectivity):** ✅ Complete - BLE GATT + Web Server
- **Phase 3 (AI Agent):** ✅ Complete - Gemini NLP, emotions, movements, multilingual
- **Phase 4 (Code Platform):** ✅ Complete - Safe executor, NinjaCoder, API wrappers
- **Driver Upgrades:** pi0servo ✅ Complete, pi0vl53l0x ✅ Rewritten, pi0disp/pi0buzzer planned

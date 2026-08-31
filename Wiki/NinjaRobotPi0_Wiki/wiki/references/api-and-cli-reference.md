---
type: Reference
title: API and CLI Reference
description: Unified reference of all Python driver classes, wrapper APIs, REST/WebSocket
  endpoints, and CLI tools.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
- id: src-20260822-readme-2
  resource: urn:llmwiki:source:src-20260822-readme-2
  title: ninja_ble Readme
  content_hash: sha256:76bbd36ab8a5d9d81b4e73fd2e3910e4c8a9b79c82e7558e94044e6c81871910
- id: src-20260822-readme-3
  resource: urn:llmwiki:source:src-20260822-readme-3
  title: ninja_core Readme
  content_hash: sha256:4c4bc38f4de4851f444770bd63e6214e5d04a4ee12d30f0d8b0b2a5b5a453471
- id: src-20260822-readme-5
  resource: urn:llmwiki:source:src-20260822-readme-5
  title: pi0buzzer Readme
  content_hash: sha256:5b4e579a60463a96e8f0bec64a502a6bf78e068b0190f65e7793fa52666d0d45
- id: src-20260822-readme-6
  resource: urn:llmwiki:source:src-20260822-readme-6
  title: pi0disp Readme
  content_hash: sha256:2fe0452ebd0ffac5fad08cfc6c0452dd65acdc62f318b71d7050e123bb347682
- id: src-20260822-readme-7
  resource: urn:llmwiki:source:src-20260822-readme-7
  title: pi0servo Readme
  content_hash: sha256:23793729576aa0b8f5b460d7fe4e47ab1d7ad4f9a6af4348bf4c8208a6610a76
- id: src-20260822-readme-8
  resource: urn:llmwiki:source:src-20260822-readme-8
  title: pi0vl53l0x Readme
  content_hash: sha256:6d02713847e83b720c6093afade910a3989dc1e8d8b48d889d61c1e381b7b680
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:4b40690af4d22be81e9c99c7287b3dd4ab20fcfd19ccf2ab3b329ae83881190e
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - REST endpoints, CLI commands, and Python API method signatures verified against
    DevelopmentGuide.md.
---

# API and CLI Reference

This document provides a consolidated reference for all Python APIs, scriptable CLI commands, REST endpoints, and WebSocket channels.[^src-20260822-developmentguide]

## Python User API (`robot.*` Wrapper in SafeExecutor)

| Object / Method | Parameters | Description |
|-----------------|------------|-------------|
| `robot.servos.move_pin(pin, angle, speed_mode)` | `pin: int`, `angle: int`, `speed_mode: str="M"` | Move single GPIO pin (`20..27`) with speed `F`/`M`/`S`.[^src-20260822-developmentguide] [^src-20260822-readme-7] |
| `robot.servos.move_pins(targets, per_servo_speeds)` | `targets: dict[int, int]`, `per_servo_speeds: dict` | Simultaneous multi-pin move.[^src-20260822-developmentguide] [^src-20260822-readme-7] |
| `robot.expression(name)` | `name: str` | Display animated facial expression.[^src-20260822-developmentguide] [^src-20260822-readme-6] |
| `robot.display.text(text, scroll, lang)` | `text: str`, `scroll: bool`, `lang: str="auto"` | Render static or marquee text.[^src-20260822-developmentguide] [^src-20260822-readme-6] |
| `robot.display.clear()` | None | Clears display and maintains blank hold.[^src-20260822-developmentguide] [^src-20260822-readme-6] |
| `robot.buzzer.play_sound(freq, dur)` | `freq: int`, `dur: float` | Play tone in background thread.[^src-20260822-developmentguide] [^src-20260822-readme-5] |
| `robot.buzzer.play_emotion(name)` | `name: str` | Play predefined emotion sound effect.[^src-20260822-developmentguide] [^src-20260822-readme-5] |
| `robot.buzzer.play_song(name)` | `name: str` | Play named song melody.[^src-20260822-developmentguide] [^src-20260822-readme-5] |
| `robot.distance.read()` | None | Returns distance in mm (or `9999` fallback).[^src-20260822-developmentguide] [^src-20260822-readme-8] |
| `robot.check_stop()` | None | Cooperative cancellation check.[^src-20260822-developmentguide] |

## Web Server REST & WebSocket Endpoints

| Endpoint | Method | Payload / Params | Description |
|----------|--------|------------------|-------------|
| `/api/chat` | `POST` | `{"message": "...", "language": "en"}` | AI conversational agent endpoint.[^src-20260822-developmentguide] [^src-20260822-readme-3] |
| `/api/code/execute` | `POST` | `{"code": "..."}` | Submit Python script for sandboxed execution.[^src-20260822-developmentguide] [^src-20260822-readme-3] |
| `/api/code/stop` | `POST` | None | Halts active script execution immediately.[^src-20260822-developmentguide] [^src-20260822-readme-3] |
| `/api/system/shutdown` | `POST` | None | Triggers graceful shutdown animation and OS poweroff.[^src-20260822-developmentguide] [^src-20260822-readme-3] |
| `/ble/status` | `GET` | None | Returns active Bluetooth service status and name.[^src-20260822-developmentguide] [^src-20260822-readme-2] |
| `/ws/events` | `WebSocket` | None | Real-time event stream (distance, logs, status).[^src-20260822-developmentguide] [^src-20260822-readme-3] |

## Scriptable CLI Command Reference

```bash
# ninja_core
uv run ninja_core server [--autostart]    # Launch server and BLE
uv run ninja_core chat                    # Terminal AI chat
uv run ninja_core movement-tool           # Servo tool
uv run ninja_core init-tool               # Guided setup wizard
uv run ninja_core config set-name "<n>"   # Set Bluetooth name
uv run ninja_core config set-key <k> <v>  # Set API keys

# pi0servo
uv run pi0servo calib <pin>               # Calibrate servo pin
uv run pi0servo cmd "<command>"           # Execute move command

# pi0disp
uv run pi0disp init [--defaults]          # Setup wizard
uv run pi0disp image <path>               # Display image
uv run pi0disp text "<text>" [--scroll]   # Display text
uv run pi0disp brightness <0-100>         # Adjust backlight

# pi0buzzer
uv run pi0buzzer init <pin>               # Initialize pin
uv run pi0buzzer beep [freq] [dur]        # Play tone
uv run pi0buzzer play <emotion>           # Play emotion

# pi0vl53l0x
uv run pi0vl53l0x get [--count N]         # Read distance
uv run pi0vl53l0x calibrate --distance D  # Calibrate offset
uv run pi0vl53l0x status                  # Health check
```

[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-readme-2]: ninja_ble Readme.
[^src-20260822-readme-3]: ninja_core Readme.
[^src-20260822-readme-5]: pi0buzzer Readme.
[^src-20260822-readme-6]: pi0disp Readme.
[^src-20260822-readme-7]: pi0servo Readme.
[^src-20260822-readme-8]: pi0vl53l0x Readme.

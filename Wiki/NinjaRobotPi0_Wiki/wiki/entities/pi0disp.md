---
type: Entity
title: pi0disp Package
description: Thread-safe SPI display driver for ST7789V LCDs with smart delta rendering
  and multilingual text tickers.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-6
  resource: urn:llmwiki:source:src-20260822-readme-6
  title: pi0disp Readme
  content_hash: sha256:2fe0452ebd0ffac5fad08cfc6c0452dd65acdc62f318b71d7050e123bb347682
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:4d011c1a93e4a868bfd036f7193de8c832477a8af9b48b4671b54d3040745698
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - ST7789V display driver, SPI transactions, delta rendering, and PWM backlight control
    verified.
---

# pi0disp Package

`pi0disp` is a thread-safe SPI driver for ST7789V-based 2.0" and 2.8" IPS LCD displays (240×320 resolution).[^src-20260822-readme-6] [^src-20260822-developmentguide]

## Core Features

* **Smart Delta Rendering**: Computes bounding boxes of modified pixels via `RegionOptimizer` and `PIL.ImageChops.difference()`, transmitting only dirty regions (~90% bandwidth savings for face animations).[^src-20260822-readme-6]
* **Thread-Safe SPI Locking**: All SPI bus transactions are guarded by `threading.Lock()` for concurrent safety across web and animation threads.[^src-20260822-readme-6]
* **PWM Backlight Control**: Smooth brightness adjustment (0–100%) via hardware/software PWM.[^src-20260822-readme-6]
* **TextTicker**: Scrolling marquee text with bundled multilingual Noto fonts (English, Japanese, Traditional Chinese).[^src-20260822-readme-6]

## Key Classes & Modules

* **`ST7789V` (`pi0disp.core.driver`)**: Main driver class implementing `Actuator` ABC.[^src-20260822-readme-6]
* **`ColorConverter` (`pi0disp.core.renderer`)**: Fast RGB to RGB565 conversion using numpy lookup tables (LUT).[^src-20260822-readme-6]
* **`RegionOptimizer` (`pi0disp.core.renderer`)**: Dirty region bounding box calculation and merging.[^src-20260822-readme-6]
* **`ConfigManager` (`pi0disp.config.config_manager`)**: Manages `display.json` settings.[^src-20260822-readme-6]

## CLI Commands

* `uv run pi0disp init`: Interactive setup wizard for GPIO pins (DC, RST, BLK) and display profile.[^src-20260822-readme-6]
* `uv run pi0disp image <path>`: Displays an image file (auto-resized).[^src-20260822-readme-6]
* `uv run pi0disp text "<text>" [--scroll] [--lang ja|zh-tw|en]`: Displays static or scrolling text.[^src-20260822-readme-6]
* `uv run pi0disp display-tool`: Launches the 9-option interactive test menu.[^src-20260822-readme-6]

[^src-20260822-readme-6]: pi0disp Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.

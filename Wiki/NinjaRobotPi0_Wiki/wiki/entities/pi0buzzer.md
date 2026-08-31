---
type: Entity
title: pi0buzzer Package
description: Non-blocking passive buzzer driver with musical notes, 14 emotion sound
  signatures, and keyboard piano.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-5
  resource: urn:llmwiki:source:src-20260822-readme-5
  title: pi0buzzer Readme
  content_hash: sha256:5b4e579a60463a96e8f0bec64a502a6bf78e068b0190f65e7793fa52666d0d45
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:f92a230a44bfbb0f4e158d2c3b066d534bd21d0e2ff7d503731c47920fceef56
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Non-blocking audio queue, note frequencies, and emotion tunes verified against
    driver documentation.
---

# pi0buzzer Package

`pi0buzzer` is a non-blocking passive buzzer driver for Raspberry Pi, generating tones, musical notes, emotion sound signatures, and complete melodies.[^src-20260822-readme-5] [^src-20260822-developmentguide]

## Core Features

* **Non-Blocking Architecture**: Sound playback commands are placed into a thread-safe queue processed by a background worker thread, ensuring the main application and asyncio loops never block.[^src-20260822-readme-5]
* **Musical Scale**: 35 predefined note frequencies across 5 octaves (C3–B7).[^src-20260822-readme-5]
* **14 Emotion Sounds**: Acoustic signatures for `happy`, `sad`, `exciting`, `angry`, `confusing`, `cry`, `embarrassing`, `idle`, `laughing`, `scary`, `shy`, `sleepy`, `speaking`, and `surprising`.[^src-20260822-readme-5]
* **Built-in Melodies**: `happy_birthday`, `jingle_bells`, `twinkle_twinkle_little_star`, and `head_shoulders_knees_and_toes`.[^src-20260822-developmentguide]
* **Volume Control**: PWM duty cycle scaling (0–255).[^src-20260822-readme-5]

## Key Classes & Modules

* **`Buzzer` (`pi0buzzer.core.driver`)**: Base queue worker class implementing `Actuator` ABC.[^src-20260822-readme-5]
* **`MusicBuzzer` (`pi0buzzer.core.music`)**: High-level music, note, and emotion player.[^src-20260822-readme-5]
* **`notes.py`**: Central repository for frequencies, emotion sequences, and piano key mappings.[^src-20260822-readme-5]

## CLI Commands

* `uv run pi0buzzer init <pin>`: Sets the GPIO pin and verifies connection with a test beep.[^src-20260822-readme-5]
* `uv run pi0buzzer beep [freq] [dur]`: Plays a single tone (default: 440Hz, 0.5s).[^src-20260822-readme-5]
* `uv run pi0buzzer play <emotion>`: Plays an emotion sound effect.[^src-20260822-readme-5]
* `uv run pi0buzzer buzzer-tool`: Interactive menu including real-time keyboard piano mode.[^src-20260822-readme-5]

[^src-20260822-readme-5]: pi0buzzer Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.

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
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:a3c69490eb2e14be65edbd612e031769e172a4b410d3177197222be79033b821
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Queue-based playback, configuration, APIs, and CLI claims are supported; non-blocking language is
    scoped to caller-facing queue submission.
---

# pi0buzzer Package

`pi0buzzer` is a non-blocking passive buzzer driver for Raspberry Pi, generating tones, musical notes, emotion sound signatures, and complete melodies.[^src-20260822-readme-5] [^src-20260822-developmentguide]

## Core Features

* **Non-Blocking Architecture**: Sound playback commands are placed into a thread-safe queue processed by a background worker thread, so queued playback does not run on the calling thread.[^src-20260822-readme-5]
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

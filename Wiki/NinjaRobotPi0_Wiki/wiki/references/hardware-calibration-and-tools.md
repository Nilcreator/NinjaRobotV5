---
type: Reference
title: Hardware Calibration and Testing Tools Reference
description: Comprehensive guide to interactive calibration TUIs, setup wizards, and
  diagnostic tools.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-installationguide
  resource: urn:llmwiki:source:src-20260822-installationguide
  title: NinjaRobot V5 Installation Guide
  content_hash: sha256:0d1f5247e341259bd895e884f9e95c25bfa2ad083368dee35096b8ca1a12d163
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
- id: src-20260822-readme-7
  resource: urn:llmwiki:source:src-20260822-readme-7
  title: pi0servo Readme
  content_hash: sha256:23793729576aa0b8f5b460d7fe4e47ab1d7ad4f9a6af4348bf4c8208a6610a76
- id: src-20260822-readme-6
  resource: urn:llmwiki:source:src-20260822-readme-6
  title: pi0disp Readme
  content_hash: sha256:2fe0452ebd0ffac5fad08cfc6c0452dd65acdc62f318b71d7050e123bb347682
- id: src-20260822-readme-5
  resource: urn:llmwiki:source:src-20260822-readme-5
  title: pi0buzzer Readme
  content_hash: sha256:5b4e579a60463a96e8f0bec64a502a6bf78e068b0190f65e7793fa52666d0d45
- id: src-20260822-readme-8
  resource: urn:llmwiki:source:src-20260822-readme-8
  title: pi0vl53l0x Readme
  content_hash: sha256:6d02713847e83b720c6093afade910a3989dc1e8d8b48d889d61c1e381b7b680
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:4ae96f3a22a4e4c9e1479a762756e0dc6bc34394a24c0f7582ba044b92072884
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Interactive TUIs, calibration procedures, and zero-point alignment guides verified.
---

# Hardware Calibration and Testing Tools Reference

Every subsystem in NinjaRobot V5 includes dedicated interactive terminal tools (TUIs) for calibration, verification, and diagnostics without writing custom scripts.[^src-20260822-installationguide] [^src-20260822-developmentguide]

## Guided System Setup (`uv run ninja_core init-tool`)

The `init-tool` provides a guided top-level menu for end-to-end setup:[^src-20260822-developmentguide]
1. Set Google Gemini API key.[^src-20260822-developmentguide]
2. Set ngrok authtoken for remote access.[^src-20260822-developmentguide]
3. Configure custom Bluetooth robot name.[^src-20260822-developmentguide]
4. Select robot type (`tire`, `humanoid`, `spider`).[^src-20260822-developmentguide]
5. Import subsystem hardware configurations.[^src-20260822-developmentguide]
6. Launch web and BLE server.[^src-20260822-developmentguide]

## Servo Calibration (`uv run pi0servo servo-tool`)

> [!IMPORTANT]
> Uncalibrated servos will not move. Calibration is required to establish safe pulse width limits.[^src-20260822-readme-7]

* **Menu Option 3 (Calibrate)**:
  * `Tab` / `Shift+Tab`: Cycle between Min (-90°), Center (0°), and Max (+90°) positions.[^src-20260822-readme-7]
  * `Up` / `Down`: Coarse pulse adjustment (±20µs).[^src-20260822-readme-7]
  * `w` / `s`: Fine pulse adjustment (±1µs).[^src-20260822-readme-7]
  * `+` / `-`: Adjust servo maximum speed limit.[^src-20260822-readme-7]
  * `Enter`: Save calibration to `servo.json`.[^src-20260822-readme-7]

## Motion Recording (`uv run ninja_core movement-tool`)

* **Option 2 (Record new movement)**: Interactively create multi-servo postures (e.g. `20:45/21:-30`), preview transitions, and save named movements to `config.json`.[^src-20260822-developmentguide]

## Display Setup & Testing (`uv run pi0disp init` & `display-tool`)

* **`uv run pi0disp init`**: Guided wizard configuring DC, RST, BLK pins, rotation (0/90/180/270°), and brightness.[^src-20260822-readme-6]
* **`uv run pi0disp display-tool`**: 9-option interactive test menu (image rendering, multilingual marquee text, bouncing ball animation, backlight test).[^src-20260822-readme-6]

## Buzzer Initialization & Piano (`uv run pi0buzzer buzzer-tool`)

* **`uv run pi0buzzer init 17`**: Configures pin 17 and performs verification beep.[^src-20260822-readme-5]
* **`uv run pi0buzzer buzzer-tool`**: Menu offering emotion playback, melody demo, volume setting, and real-time keyboard piano mode.[^src-20260822-readme-5]

## Distance Sensor Calibration (`uv run pi0vl53l0x sensor-tool`)

* **Guided Offset Calibration**: Place a flat white target at exactly 100mm from the sensor and run `uv run pi0vl53l0x calibrate --distance 100` to compute and save the zero offset in `vl53l0x.json`.[^src-20260822-readme-8]

[^src-20260822-installationguide]: NinjaRobot V5 Installation Guide.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-readme-7]: pi0servo Readme.
[^src-20260822-readme-6]: pi0disp Readme.
[^src-20260822-readme-5]: pi0buzzer Readme.
[^src-20260822-readme-8]: pi0vl53l0x Readme.

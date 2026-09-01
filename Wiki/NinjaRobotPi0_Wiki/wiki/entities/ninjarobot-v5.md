---
type: Entity
title: NinjaRobot V5 Entity
description: Complete hardware platform entity specifications, configurations, robot
  types, and safety lifecycle.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme
  resource: urn:llmwiki:source:src-20260822-readme
  title: NinjaRobot V5 Readme
  content_hash: sha256:747c8c2e1e67d24b5d6f6b9c797a6eb7ec7b92b1ce4368623cc9b77b62c442a4
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
- id: src-20260822-installationguide
  resource: urn:llmwiki:source:src-20260822-installationguide
  title: NinjaRobot V5 Installation Guide
  content_hash: sha256:f1b95c621b3a1c6cfe77f2a1c3923a40314783c02fdde83f0cb4bbc881ae13a4
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:bc99f19ebc0a284733d79c783d26ffec23e9abf73355e4fb671b29ee11ffd27a
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Platform scope, package composition, setup, and hardware summary are supported by current project
    documentation; no physical validation is implied.
---

# NinjaRobot V5 Entity

**NinjaRobot V5** is the physical and logical robot entity integrating the Raspberry Pi Zero 2W single-board computer, 8 servo actuators, an ST7789V IPS display, a VL53L0X distance sensor, and a passive buzzer.[^src-20260822-readme] [^src-20260822-installationguide]

## Robot Types & Profiles

NinjaRobot V5 supports multiple physical configurations through the `robot_type` configuration:[^src-20260822-developmentguide]

* **`tire`**: Wheeled educational robot configuration.[^src-20260822-developmentguide]
* **`humanoid`**: Bipedal/humanoid articulated robot with arms and legs.[^src-20260822-developmentguide]
* **`spider`**: Multi-legged quadruped/hexapod walker configuration.[^src-20260822-developmentguide]

The robot profile is broadcast over BLE (`robot_info`) to enable the Code IDE to adapt Blockly block options dynamically.[^src-20260822-developmentguide]

## Power & Hardware Pinout Summary

```
Raspberry Pi Zero 2W GPIO Pinout (40-Pin Header)
┌─────────────────────────────────────┐
│  3.3V  [1] [2]  5V                  │  ← Sensor/Display Logic Power (3.3V)
│  SDA   [3] [4]  5V                  │  ← VL53L0X I2C Data (GPIO 2)
│  SCL   [5] [6]  GND                 │  ← VL53L0X I2C Clock (GPIO 3)
│  GPIO4 [7] [8]  GPIO14 (DC)         │  ← ST7789V Data/Command
│  GND   [9] [10] GPIO15 (RST)        │  ← ST7789V Reset
│  GPIO17[11] [12] GPIO18             │  ← Passive Buzzer (GPIO 17)
│  ...   [..] [..] ...                │
│  SPI0 MOSI [19] [20] GND            │  ← ST7789V SPI MOSI
│  SPI0 SCLK [23] [24] SPI0 CE0       │  ← ST7789V SPI SCLK & Chip Select
│  GPIO19[35] [36] GPIO16 (BLK)       │  ← ST7789V Backlight PWM
│  GPIO26[37] [38] GPIO20 (Servo 1)   │  ← Servo Motors (GPIO 20–27)
│  GND  [39] [40] GPIO21 (Servo 2)   │
└─────────────────────────────────────┘
```

> [!CAUTION]
> Servo power (5V Red wires) must always be supplied by an external 5V 3A+ power supply with common ground to the Raspberry Pi.[^src-20260822-installationguide]

## Safety & Graceful Shutdown

* **Emergency Halt**: Requests immediate cancellation of active servo motion and resets servo targets.[^src-20260822-readme] [^src-20260822-developmentguide]
* **Graceful Shutdown Sequence**:
  1. Displays `sleepy` face and plays `sleepy` sound in parallel.[^src-20260822-readme] [^src-20260822-developmentguide]
  2. Moves servos to the pre-configured `Poweroff` rest position.[^src-20260822-developmentguide]
  3. Releases all HAL handles and triggers Linux OS shutdown (`sudo poweroff`).[^src-20260822-developmentguide]

[^src-20260822-readme]: NinjaRobot V5 Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-installationguide]: NinjaRobot V5 Installation Guide.

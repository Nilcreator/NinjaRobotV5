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
  content_hash: sha256:7bbec02c276f0be133fbba91a5fed327c96bd6b30ff6e010dcd9c6376ab210cf
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
- id: src-20260822-installationguide
  resource: urn:llmwiki:source:src-20260822-installationguide
  title: NinjaRobot V5 Installation Guide
  content_hash: sha256:0d1f5247e341259bd895e884f9e95c25bfa2ad083368dee35096b8ca1a12d163
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:d31466a22441988f5ba298d311c6ed12d5627f1fbd3916f8a9ccab68fdaa2f55
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Top-level platform specifications, hardware BOM, and integration architecture
    verified.
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

* **Emergency Halt**: Instantly stops all PWM pulse trains and resets servo targets.[^src-20260822-readme]
* **Graceful Shutdown Sequence**:
  1. Displays `sleepy` face and plays `sleepy` sound in parallel.[^src-20260822-readme] [^src-20260822-developmentguide]
  2. Moves servos to the pre-configured `Poweroff` rest position.[^src-20260822-developmentguide]
  3. Releases all HAL handles and triggers Linux OS shutdown (`sudo poweroff`).[^src-20260822-developmentguide]

[^src-20260822-readme]: NinjaRobot V5 Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-installationguide]: NinjaRobot V5 Installation Guide.

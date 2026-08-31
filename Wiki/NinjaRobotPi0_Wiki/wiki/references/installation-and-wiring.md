---
type: Reference
title: Installation and Hardware Wiring Reference
description: Step-by-step assembly, complete GPIO wiring tables, Raspberry Pi OS Bookworm
  setup, and pigpio compilation.
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
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:c4a48b189d5ebd33f646891004b9299b83bbfd2f05f4a1c0240b074732757c1d
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - GPIO pin assignments, power distribution requirements, and OS installation steps
    verified.
---

# Installation and Hardware Wiring Reference

This guide details the complete hardware assembly, pinout connections, and operating system configuration for NinjaRobot V5 on the Raspberry Pi Zero 2W.[^src-20260822-installationguide] [^src-20260822-developmentguide]

## Hardware Requirements

* **Raspberry Pi Zero 2W** (with 40-pin header soldered).[^src-20260822-installationguide]
* **MicroSD Card** (16GB+ Class 10).[^src-20260822-installationguide]
* **8× SG90 / MG90S Micro Servos** (5V).[^src-20260822-installationguide]
* **External 5V 3A+ Power Supply** for servos.[^src-20260822-installationguide]
* **ST7789V 2.0" / 2.8" IPS LCD Display** (240×320, SPI).[^src-20260822-installationguide]
* **VL53L0X Time-of-Flight Distance Sensor** (I2C).[^src-20260822-installationguide]
* **Passive Buzzer** (3–5V, GPIO 17).[^src-20260822-installationguide]

## Complete Pinout Connection Table

| Subsystem | Component Pin | Raspberry Pi Pin | Pin Description |
|-----------|---------------|------------------|-----------------|
| **Power (Logic)** | Sensor/Display VCC | Pin 1 (3.3V) | 3.3V Logic Supply [^src-20260822-installationguide] |
| **Ground** | All Component GND | Pin 6 / 9 / 14 / 20 / 25 / 30 / 34 / 39 | Common Ground [^src-20260822-installationguide] |
| **VL53L0X** | SDA | Pin 3 (GPIO 2) | I2C Data [^src-20260822-installationguide] |
| **VL53L0X** | SCL | Pin 5 (GPIO 3) | I2C Clock [^src-20260822-installationguide] |
| **ST7789V** | DIN (MOSI) | Pin 19 (SPI0 MOSI) | SPI Data [^src-20260822-installationguide] |
| **ST7789V** | CLK (SCLK) | Pin 23 (SPI0 SCLK) | SPI Clock [^src-20260822-installationguide] |
| **ST7789V** | CS | Pin 24 (SPI0 CE0) | Chip Select [^src-20260822-installationguide] |
| **ST7789V** | DC | Pin 8 (GPIO 14) | Data/Command (configurable) [^src-20260822-installationguide] |
| **ST7789V** | RST | Pin 10 (GPIO 15) | Reset (configurable) [^src-20260822-installationguide] |
| **ST7789V** | BLK | Pin 36 (GPIO 16) | Backlight PWM (configurable) [^src-20260822-installationguide] |
| **Buzzer** | Signal (+) | Pin 11 (GPIO 17) | Hardware PWM [^src-20260822-installationguide] |
| **Servos 1–8**| Signals 1–8 | Pins 38, 40, 15, 16, 18, 22, 37, 13 (GPIO 20–27) | PWM Signal Channels [^src-20260822-installationguide] |

## Raspberry Pi OS (Bookworm 64-bit) & `pigpio` Setup

On Raspberry Pi OS Bookworm, `pigpio` must be compiled from source due to upstream repository package changes:[^src-20260822-installationguide]

```bash
# 1. Install build tools
sudo apt update && sudo apt install -y build-essential unzip wget git python3-pip

# 2. Download and compile C library
wget https://github.com/joan2937/pigpio/archive/master.zip
unzip master.zip && cd pigpio-master
make && sudo make install

# 3. Update library cache
sudo ldconfig

# 4. Install Python wrapper
sudo apt install python3-pigpio || sudo pip3 install pigpio --break-system-packages

# 5. Enable and start daemon
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

## Workspace Installation

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository and install dependencies
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5
uv sync

# Build web application frontend
cd ninja_webapp && npm install && npm run build && cd ..
```

[^src-20260822-installationguide]: NinjaRobot V5 Installation Guide.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.

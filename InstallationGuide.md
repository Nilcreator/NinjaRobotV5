# NinjaRobot V5 Complete Installation Guide

This guide will walk you through every step needed to build and run your NinjaRobot V5 on a Raspberry Pi Zero 2W. No programming experience is required—just follow each step carefully.

> [!NOTE]
> V5 introduces a modular architecture with non-blocking drivers. All hardware now uses standardized interfaces.

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [Hardware Wiring Guide](#2-hardware-wiring-guide)
3. [Raspberry Pi OS Installation](#3-raspberry-pi-os-installation)
4. [Software Installation](#4-software-installation)
5. [Service Setup (Gemini AI & ngrok)](#5-service-setup-gemini-ai--ngrok)
6. [Project Installation](#6-project-installation)
7. [Hardware Calibration](#7-hardware-calibration)
8. [Function Testing](#8-function-testing)
9. [Running the Robot](#9-running-the-robot)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Hardware Requirements

### Required Components

- **Raspberry Pi Zero 2W** (with headers soldered)
- **MicroSD Card** (16GB or larger, Class 10 recommended)
- **Power Supply** (5V 2.5A USB-C or Micro-USB)
- **8x Servo Motors** (SG90 or similar, 5V)
- **External 5V Power Supply** for servos (recommended: 5V 3A or higher)
- **ST7789V LCD Display** (240x240 pixels, SPI interface)
- **VL53L0X Distance Sensor** (Time-of-Flight, I2C interface)
- **Passive Buzzer** (3-5V)
- **Jumper Wires** (Male-to-Female and Male-to-Male)
- **Breadboard** (optional, for prototyping)
- **Keyboard, Mouse, and Monitor** (for initial setup)

### Optional but Recommended

- **Raspberry Pi Case**
- **Heatsinks** for the Raspberry Pi
- **USB Hub** (if you need multiple USB devices during setup)

---

## 2. Hardware Wiring Guide

### Important Safety Notes

> [!CAUTION]
> - **Always power off** the Raspberry Pi before connecting or disconnecting components.
> - **Never connect servo power** directly to the Raspberry Pi's 5V pin—use an external power supply.
> - **Double-check all connections** before powering on to avoid damage.

### GPIO Pin Layout

Here's the complete wiring diagram for all components:

```
Raspberry Pi Zero 2W GPIO Pinout (40-pin header)
┌─────────────────────────────────────┐
│  3.3V  [1] [2]  5V                  │
│  SDA   [3] [4]  5V                  │
│  SCL   [5] [6]  GND                 │
│  GPIO4 [7] [8]  GPIO14 (DC)         │
│  GND   [9] [10] GPIO15 (RST)        │
│  GPIO17[11] [12] GPIO18             │  ← Buzzer (17)
│  GPIO27[13] [14] GND                │
│  GPIO22[15] [16] GPIO23             │
│  3.3V [17] [18] GPIO24              │
│  SPI0 MOSI [19] [20] GND            │
│  GPIO9[21] [22] GPIO25              │
│  SPI0 SCLK [23] [24] SPI0 CE0       │
│  GND  [25] [26] SPI0 CE1            │
│  ID_SD[27] [28] ID_SC               │
│  GPIO5[29] [30] GND                 │
│  GPIO6[31] [32] GPIO12              │
│  GPIO13[33] [34] GND                │
│  GPIO19[35] [36] GPIO16 (BLK)       │
│  GPIO26[37] [38] GPIO20             │
│  GND  [39] [40] GPIO21              │
└─────────────────────────────────────┘
```

### Component Connection Table

#### Servo Motors (8 servos)

| Servo # | GPIO Pin | Signal Wire | Power (5V) | Ground |
|---------|----------|-------------|------------|--------|
| 1       | GPIO 20  | Orange/Yellow | External 5V | Common GND |
| 2       | GPIO 21  | Orange/Yellow | External 5V | Common GND |
| 3       | GPIO 22  | Orange/Yellow | External 5V | Common GND |
| 4       | GPIO 23  | Orange/Yellow | External 5V | Common GND |
| 5       | GPIO 24  | Orange/Yellow | External 5V | Common GND |
| 6       | GPIO 25  | Orange/Yellow | External 5V | Common GND |
| 7       | GPIO 26  | Orange/Yellow | External 5V | Common GND |
| 8       | GPIO 27  | Orange/Yellow | External 5V | Common GND |

> [!IMPORTANT]
> **Servo Power:** Connect all servo power wires (red) to your external 5V power supply (NOT the Raspberry Pi). Connect all servo ground wires (brown/black) to a common ground that is also connected to one of the Raspberry Pi's GND pins.

#### ST7789V LCD Display (SPI)

| Display Pin | Raspberry Pi Pin | Description |
|-------------|------------------|-------------|
| VCC         | 3.3V             | Power       |
| GND         | GND              | Ground      |
| DIN (MOSI)  | SPI0 MOSI        | SPI Data    |
| CLK (SCL)   | SPI0 SCLK        | SPI Clock   |
| CS          | SPI0 CE0         | Chip Select |
| DC          | GPIO 14          | Data/Command|
| RST         | GPIO 15          | Reset       |
| BLK         | GPIO 16          | Backlight   |

#### VL53L0X Distance Sensor (I2C)

| Sensor Pin | Raspberry Pi Pin | Description |
|------------|------------------|-------------|
| VCC        | Pin 1 (3.3V)     | Power       |
| GND        | Pin 6 (GND)      | Ground      |
| SCL        | Pin 5 (GPIO 3 - I2C SCL) | I2C Clock |
| SDA        | Pin 3 (GPIO 2 - I2C SDA) | I2C Data  |

#### Passive Buzzer

| Buzzer Pin | Raspberry Pi Pin | Description |
|------------|------------------|-------------|
| Positive (+) | Pin 11 (GPIO 17) | Signal    |
| Negative (-) | GND              | Ground    |

### Wiring Checklist

Before proceeding, verify:
- [ ] All servo signal wires are connected to the correct GPIO pins (20-27)
- [ ] Servo power comes from an external 5V supply (NOT the Pi)
- [ ] Common ground is shared between Pi and external servo power supply
- [ ] Display is connected via SPI (SCLK, MOSI, CE0) and GPIO 14, 15, 16
- [ ] Distance sensor is connected via I2C (SCL, SDA)
- [ ] Buzzer is connected to GPIO 17
- [ ] No loose wires or short circuits

---

## 3. Raspberry Pi OS Installation

### Step 3.1: Download Raspberry Pi Imager

1. On your computer, go to: https://www.raspberrypi.com/software/
2. Download **Raspberry Pi Imager** for your operating system (Windows, macOS, or Linux)
3. Install and open the Raspberry Pi Imager

### Step 3.2: Flash the OS to MicroSD Card

1. Insert your MicroSD card into your computer (use an adapter if needed)
2. In Raspberry Pi Imager:
   - Click **"Choose Device"** → Select **"Raspberry Pi Zero 2W"**
   - Click **"Choose OS"** → Select **"Raspberry Pi OS (64-bit)"** (recommended) or **"Raspberry Pi OS (32-bit)"**
   - Click **"Choose Storage"** → Select your MicroSD card

3. Click the **Settings (gear icon)** button to configure:
   - **Hostname**: `ninjarobot` (or your preferred name)
   - **Enable SSH**: Check this box and select "Use password authentication"
   - **Set username and password**: 
     - Username: `pi` (or your choice)
     - Password: (create a secure password)
   - **Configure WiFi** (if you want wireless):
     - SSID: Your WiFi network name
     - Password: Your WiFi password
     - Wireless LAN country: Select your country
   - **Set locale settings**: Choose your timezone and keyboard layout

4. Click **"SAVE"** to save settings
5. Click **"WRITE"** to flash the OS to the card
6. Wait for the process to complete (this may take 5-10 minutes)
7. When done, safely eject the MicroSD card

### Step 3.3: Boot the Raspberry Pi

1. Insert the MicroSD card into your Raspberry Pi Zero 2W
2. Connect your keyboard, mouse, and monitor (via HDMI adapter)
3. Connect the power supply
4. Wait for the Pi to boot (first boot may take 2-3 minutes)
5. Log in with the username and password you set earlier

---

## 4. Software Installation

### Step 4.1: Update System

Open a terminal and run:

```bash
sudo apt update && sudo apt upgrade -y
```

This may take 10-20 minutes depending on your internet speed.

### Step 4.2: Enable Required Interfaces

1. Open the Raspberry Pi configuration tool:
   ```bash
   sudo raspi-config
   ```

2. Navigate to **"3 Interface Options"**

3. Enable the following:
   - **I2C**: Select **"I5 I2C"** → **"Yes"**
   - **SPI**: Select **"I4 SPI"** → **"Yes"**

4. Select **"Finish"** and reboot when prompted:
   ```bash
   sudo reboot
   ```

### Step 4.3: Install System Dependencies

After reboot, open a terminal and install required packages:

```bash
sudo apt install -y git pigpio python3-pip
```

### Step 4.4: Install Python Package Manager (uv)

We use `uv` for faster and more reliable Python package management:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, close and reopen your terminal, or run:

```bash
source $HOME/.local/bin/env
```

Verify installation:

```bash
uv --version
```

You should see a version number like `uv 0.x.x`.

### Step 4.5: Start pigpio Daemon

The `pigpio` daemon must run in the background for hardware control:

```bash
sudo pigpiod
```

> [!TIP]
> To make `pigpiod` start automatically on boot, run:
> ```bash
> sudo systemctl enable pigpiod
> sudo systemctl start pigpiod
> ```

---

## 5. Service Setup (Gemini AI & ngrok)

### Step 5.1: Create Google Gemini API Key

The robot uses Google's Gemini AI for natural language understanding.

1. **Go to Google AI Studio**: https://aistudio.google.com/
2. **Sign in** with your Google account
3. Click **"Get API Key"** in the left sidebar
4. Click **"Create API Key"**
5. Select **"Create API key in new project"** or choose an existing project
6. **Copy the API key** that appears (it looks like: `AIzaSy...`)
7. **Save this key** somewhere safe—you'll need it later

> [!WARNING]
> Keep your API key private! Do not share it publicly or commit it to version control.

### Step 5.2: Create ngrok Account

`ngrok` creates a public URL so you can control your robot from anywhere.

1. **Go to ngrok**: https://ngrok.com/
2. Click **"Sign up"** and create a free account
3. After signing in, go to: https://dashboard.ngrok.com/get-started/your-authtoken
4. **Copy your Authtoken** (it looks like: `2a...`)
5. **Save this token**—you'll enter it when you first start the robot's web server

---

## 6. Project Installation

### Step 6.1: Clone the Repository

Navigate to your home directory and clone the project:

```bash
cd ~
git clone https://github.com/Nilcreator/NinjaRobotV4.git
cd NinjaRobotV4
```

> [!NOTE]
> If the repository is private or you're using a different source, adjust the URL accordingly.

### Step 6.2: Create a Virtual Environment

It is best practice to install Python packages in a virtual environment to avoid conflicts.

```bash
uv venv
source .venv/bin/activate
```

You should see `(NinjaRobotV4)` or `(.venv)` appear at the start of your terminal line.

### Step 6.3: Install All Dependencies

Now install the project dependencies into the virtual environment:

```bash
uv pip install -e .
```

This will:
- Install all Python dependencies
- Set up all the robot's libraries in editable mode
- Make all CLI commands available

The installation may take 5-10 minutes.

### Step 6.4: Verify Installation

Check that the main command is available:

```bash
ninja_core --help
```

You should see a list of available commands like `chat`, `server`, `config`, etc.

---

## 7. Hardware Calibration

Before running the robot, you need to calibrate the servos and configure the hardware.

### Step 7.1: Configure Buzzer
Tell the system which GPIO pin the buzzer is connected to:

```bash
uv run pi0buzzer init 17
```

Test the buzzer:

```bash
uv run pi0buzzer beep
```

You should hear a short beep.

### Step 7.2: Test Distance Sensor

Test the sensor:

```bash
uv run pi0vl53l0x get --count 5 --interval 1.0
```

You should see 5 distance readings in millimeters.

### Step 7.3: Calibrate Servos

Each servo needs to be calibrated to define its minimum, center, and maximum positions.

For each servo (example for GPIO 17):

```bash
uv run pi0servo calib 20
```

Follow the on-screen instructions:
1. Press `v` to select **Min** position
2. Use **Up/Down** arrow keys for large adjustments, **w/s** for fine-tuning
3. When the servo is at its minimum position, press **Enter** to save
4. Press `c` to select **Center** position, adjust, and press **Enter**
5. Press `x` to select **Max** position, adjust, and press **Enter**
6. Press `q` to quit

**Repeat this for all 8 servos** (GPIO pins: 20 through 27)

### Step 7.4: Import Hardware Configuration

After calibrating all servos, import the configurations:

```bash
uv run ninja_core config import
```

You should see:
```
Found servo config at 'servo.json'. Importing...
Found buzzer config at 'buzzer.json'. Importing...
Configuration updated and saved to config.json!
```

### Step 7.5: Set Gemini API Key

Configure the AI agent with your API key (replace `YOUR_API_KEY` with the actual key):

```bash
uv run ninja_core config set-key gemini YOUR_API_KEY
```

---

## 8. Function Testing

Now let's test each component individually.

### Test 8.1: Display Test

Test the LCD screen with an image:

```bash
uv run pi0disp image assets/images/sample_face.jpg
```

You should see an image on the display with changing brightness.

Test animation:

```bash
uv run pi0disp ball_anime --num-balls 5
```

Press **Ctrl+C** to stop.

### Test 8.2: Servo Movement Test

Move a servo to its center position:

```bash
uv run pi0servo servo 20 center
```

The servo on GPIO 20 should move to 0 degrees.

Try other positions:

```bash
uv run pi0servo servo 20 45
uv run pi0servo servo 20 -45
uv run pi0servo servo 20 max
```

### Test 8.3: Sound Test

Play a melody:

```bash
uv run pi0buzzer playmusic
```

### Test 8.4: Distance Sensor Performance

Measure sensor speed:

```bash
uv run pi0vl53l0x performance --count 100
```

### Test 8.5: AI Agent Test (Text Chat)

Test the AI chat in terminal mode:

```bash
uv run ninja_core chat
```

Try these commands:
- `Hello` (the robot should greet you)
- `Show me a happy face` (displays happy expression and sound)
- `こんにちは` (responds in Japanese)
- `你好` (responds in Chinese)
- Type `quit` or press **Ctrl+C** to exit

> [!NOTE]
> The robot will monitor distance continuously and react if you get too close (<50mm).

---

## 9. Running the Robot

### Start the Web Server

This is the main way to interact with your robot:

```bash
uv run ninja_core server
```

On **first run**, you'll be prompted to enter your **ngrok authtoken** (from Step 5.2). Paste it and press Enter.

The robot will:
1. Initialize all hardware
2. Start the web server
3. Create a public URL via ngrok
4. Display a QR code on its screen

### Access the Web Interface

You have two options:

#### Option A: Scan the QR Code (Recommended)

Use your smartphone to scan the QR code displayed on the robot's screen. This will open the web interface in your phone's browser.

#### Option B: Local Network

On any device on the same WiFi network, open a browser and go to:
```
http://ninjarobot.local:8000
```
(Replace `ninjarobot` with your hostname if different)

### Web Interface Features

Once connected, you can:

1. **Chat with the Robot**:
   - Type messages in the text box
   - Or click the **microphone icon** and speak (select language first)
   - The robot will respond in the same language

2. **Control Servos**:
   - Select a movement from the dropdown
   - Click **Execute**

3. **Show Facial Expressions**:
   - Select an expression (happy, sad, etc.)
   - Click **Show**

4. **Play Sounds**:
   - Select an emotion sound
   - Click **Play**

5. **Monitor Distance**:
   - Real-time distance readings appear at the top

### Supported Languages

- **English** (en-US)
- **日本語** (ja-JP) - Japanese
- **繁體中文** (zh-TW) - Traditional Chinese
- **简体中文** (zh-CN) - Simplified Chinese

### Stopping the Server

Press **Ctrl+C** in the terminal to stop the server. The robot will safely shut down all hardware.

---

## 10. Automatic Startup (Optional)

If you want the robot to start automatically when you turn on the power, follow these steps.

> [!IMPORTANT]
> **Prerequisites:** Ensure you have completed all previous steps, including hardware calibration and API key setup. The robot must be fully functional before enabling autostart.
>
> **Ngrok Requirement:** For autostart to work, you **must** have a valid ngrok authtoken configured. If the token is missing, the service will fail to start to avoid hanging in the background.

### Step 10.1: Install the Startup Service

Run the following command:

```bash
uv run ninja_utils install-startup
```

This will:
1. Check if your system is ready (config exists, pigpiod running, etc.)
2. Create a systemd service file
3. Enable the service to start on boot

### Step 10.2: Verify

You can check the status of the service:

```bash
uv run ninja_utils status-startup
```

### Step 10.3: Reboot

Reboot your Raspberry Pi:

```bash
sudo reboot
```

The robot should start automatically. You can access the web interface via the QR code or `http://ninjarobot.local:8000` after a minute or two.

> [!TIP]
> **Safe Shutdown:** You can safely shut down the robot using the "Power Off Robot" button at the bottom of the web interface. Wait for the green light on the Raspberry Pi to stop flashing before unplugging the power.

### Removing Autostart

If you want to stop the robot from starting automatically:

```bash
uv run ninja_utils remove-startup
```

---

## 11. Troubleshooting

### Problem: "Could not connect to pigpiod daemon"

**Solution**:
```bash
sudo pigpiod
```

Then try running your command again.

### Problem: Display not working

**Checks**:
1. Verify SPI is enabled: `sudo raspi-config` → Interface Options → SPI
2. Check wiring matches the pin table in Section 2
3. Reboot: `sudo reboot`

### Problem: Distance sensor not responding

**Checks**:
1. Verify I2C is enabled: `sudo raspi-config` → Interface Options → I2C
2. Check if sensor is detected:
   ```bash
   sudo i2cdetect -y 1
   ```
   You should see `29` or `52` in the output
3. Check wiring (VCC to 3.3V, not 5V)

### Problem: Servos not moving

**Checks**:
1. Ensure external 5V power supply is connected and turned on
2. Verify common ground between Pi and servo power supply
3. Check servo signal wire connections
4. Recalibrate servo: `uv run pi0servo calib <PIN>`

### Problem: "ImportError" or "ModuleNotFoundError"

**Solution**:
Reinstall the project:
```bash
cd ~/NinjaRobotV4
uv pip install -e . --force-reinstall
```

### Problem: "Component Initialization Failed" Warning

**Cause**: One hardware component (like the sensor or display) is disconnected or faulty.
**Solution**: The robot is designed to be **fault-tolerant**. It will log a warning and continue starting up with the working components. You can check connections later.

### Problem: Web server won't start

**Checks**:
1. Ensure port 8000 is not already in use
2. Check if ngrok authtoken is set correctly
3. Restart the server with verbose output:
   ```bash
   uv run ninja_core server --log-level debug
   ```

### Problem: AI agent not responding

**Checks**:
1. Verify Gemini API key is set:
   ```bash
   cat config.json | grep gemini
   ```
2. Check internet connection
3. Re-set API key:
   ```bash
   uv run ninja_core config set-key gemini YOUR_KEY
   ```

### Getting More Help

If you encounter issues not covered here:

1. Check the project's GitHub Issues page
2. Review the `DevelopmentLog.md` for known issues and fixes
3. Ensure all wiring matches the diagrams exactly
4. Try running individual component tests (Section 8) to isolate the problem

---

## Next Steps

- **Record Custom Movements**: Use `uv run ninja_core movement-tool` to create and save servo choreography
- **Customize Behavior**: Edit `config.json` to adjust settings
- **Build an Enclosure**: Design a robot body and mount all components
- **Explore the Code**: Check `ninja_core/README.md` for developer documentation

**Congratulations!** Your NinjaRobotV4 is now ready to use. Enjoy exploring and experimenting with your AI-powered robot! 🤖

---
---

# NinjaRobotV4 完全インストールガイド（日本語版）

このガイドでは、Raspberry Pi Zero 2WでNinjaRobotV4を構築して実行するために必要なすべての手順を説明します。プログラミング経験は不要です—各ステップを注意深く従ってください。

---

## 目次

1. [ハードウェア要件](#1-ハードウェア要件)
2. [ハードウェア配線ガイド](#2-ハードウェア配線ガイド)
3. [Raspberry Pi OSのインストール](#3-raspberry-pi-osのインストール)
4. [ソフトウェアのインストール](#4-ソフトウェアのインストール)
5. [サービスのセットアップ（Gemini AIとngrok）](#5-サービスのセットアップgemini-aiとngrok)
6. [プロジェクトのインストール](#6-プロジェクトのインストール)
7. [ハードウェアの校正](#7-ハードウェアの校正)
8. [機能テスト](#8-機能テスト)
9. [ロボットの起動](#9-ロボットの起動)
10. [自動起動（オプション）](#10-自動起動オプション)
11. [トラブルシューティング](#11-トラブルシューティング)

---

## 1. ハードウェア要件

### 必要な部品

- **Raspberry Pi Zero 2W**（ヘッダーがはんだ付けされたもの）
- **MicroSDカード**（16GB以上、Class 10推奨）
- **電源アダプター**（5V 2.5A USB-CまたはMicro-USB）
- **8個のサーボモーター**（SG90または類似品、5V）
- **サーボ用の外部5V電源**（推奨：5V 3A以上）
- **ST7789V液晶ディスプレイ**（240x240ピクセル、SPI接続）
- **VL53L0X距離センサー**（ToF：光の飛行時間で測る方式、I2C接続）
- **パッシブブザー**（3-5V）
- **ジャンパーワイヤー**（オス-メスとオス-オス）
- **ブレッドボード**（試作用、オプション）
- **キーボード、マウス、モニター**（初期セットアップ用）

### あると便利なもの

- **Raspberry Piケース**
- **ヒートシンク**（Raspberry Pi用の放熱板）
- **USBハブ**（セットアップ中に複数のUSBデバイスが必要な場合）

---

## 2. ハードウェア配線ガイド

### 重要な安全上の注意

> [!CAUTION]
> - **必ず電源を切ってから**部品を接続または取り外してください。
> - **サーボの電源を直接Raspberry Piの5Vピンに接続しないでください**—外部電源を使用してください。
> - **すべての接続を再確認**してから電源を入れて、損傷を避けてください。

### GPIOピン配置

すべての部品の完全な配線図は次のとおりです:

```
Raspberry Pi Zero 2W GPIOピン配置（40ピンヘッダー）
┌─────────────────────────────────────┐
│  3.3V  [1] [2]  5V                  │
│  SDA   [3] [4]  5V                  │
│  SCL   [5] [6]  GND                 │
│  GPIO4 [7] [8]  GPIO14 (DC)         │
│  GND   [9] [10] GPIO15 (RST)        │
│  GPIO17[11] [12] GPIO18             │  ← ブザー (17)
│  GPIO27[13] [14] GND                │
│  GPIO22[15] [16] GPIO23             │
│  3.3V [17] [18] GPIO24              │
│  SPI0 MOSI [19] [20] GND            │
│  GPIO9[21] [22] GPIO25              │
│  SPI0 SCLK [23] [24] SPI0 CE0       │
│  GND  [25] [26] SPI0 CE1            │
│  ID_SD[27] [28] ID_SC               │
│  GPIO5[29] [30] GND                 │
│  GPIO6[31] [32] GPIO12              │
│  GPIO13[33] [34] GND                │
│  GPIO19[35] [36] GPIO16 (BLK)       │
│  GPIO26[37] [38] GPIO20             │
│  GND  [39] [40] GPIO21              │
└─────────────────────────────────────┘
```

### 部品接続表

#### サーボモーター（8個）

| サーボ番号 | GPIOピン | 信号線 | 電源（5V） | グラウンド |
|---------|----------|-------------|------------|-----------|
| 1       | GPIO 20  | オレンジ/黄色 | 外部5V | 共通GND |
| 2       | GPIO 21  | オレンジ/黄色 | 外部5V | 共通GND |
| 3       | GPIO 22  | オレンジ/黄色 | 外部5V | 共通GND |
| 4       | GPIO 23  | オレンジ/黄色 | 外部5V | 共通GND |
| 5       | GPIO 24  | オレンジ/黄色 | 外部5V | 共通GND |
| 6       | GPIO 25  | オレンジ/黄色 | 外部5V | 共通GND |
| 7       | GPIO 26  | オレンジ/黄色 | 外部5V | 共通GND |
| 8       | GPIO 27  | オレンジ/黄色 | 外部5V | 共通GND |

> [!IMPORTANT]
> **サーボの電源:** すべてのサーボの電源線（赤）を外部5V電源に接続してください（Raspberry Piには接続しないでください）。すべてのサーボのグラウンド線（茶色/黒）を、Raspberry PiのGNDピン（例：ピン6、9、14、20、25、30、34、または39）にも接続された共通グラウンドに接続してください。

#### ST7789V液晶ディスプレイ（SPI接続）

| ディスプレイピン | Raspberry Piピン | 説明 |
|-------------|------------------|------|
| VCC         | 3.3V             | 電源 |
| GND         | GND              | グラウンド |
| DIN（MOSI） | SPI0 MOSI        | SPIデータ |
| CLK（SCL）  | SPI0 SCLK        | SPIクロック |
| CS          | SPI0 CE0         | チップセレクト |
| DC          | GPIO 14          | データ/コマンド |
| RST         | GPIO 15          | リセット |
| BLK         | GPIO 16          | バックライト |

#### VL53L0X距離センサー（I2C接続）

| センサーピン | Raspberry Piピン | 説明 |
|------------|------------------|------|
| VCC        | ピン1（3.3V）     | 電源 |
| GND        | ピン6（GND）      | グラウンド |
| SCL        | ピン5（GPIO 3 - I2C SCL） | I2Cクロック |
| SDA        | ピン3（GPIO 2 - I2C SDA） | I2Cデータ |

#### パッシブブザー

| ブザーピン | Raspberry Piピン | 説明 |
|------------|------------------|------|
| プラス（+） | ピン11（GPIO 17） | 信号 |
| マイナス（-） | GND               | グラウンド |

### 配線チェックリスト

続行する前に、以下を確認してください:
- [ ] すべてのサーボ信号線が正しいGPIOピンに接続されている（20-27）
- [ ] サーボの電源は外部5V電源から供給されている（Piからではない）
- [ ] Piとサーボ外部電源の間で共通グラウンドが共有されている
- [ ] ディスプレイがSPI経由で接続されている（SCLK, MOSI, CE0）およびGPIO 14, 15, 16
- [ ] 距離センサーがI2C経由で接続されている（SCL, SDA）
- [ ] ブザーがGPIO 17に接続されている
- [ ] 緩んだワイヤーやショート（短絡）がない

---

## 3. Raspberry Pi OSのインストール

### ステップ3.1: Raspberry Pi Imagerのダウンロード

1. コンピューターで次のサイトにアクセス: https://www.raspberrypi.com/software/
2. お使いのOS（Windows、macOS、またはLinux）用の**Raspberry Pi Imager**をダウンロード
3. インストールしてRaspberry Pi Imagerを開く

### ステップ3.2: MicroSDカードにOSを書き込む

1. MicroSDカードをコンピューターに挿入（必要に応じてアダプターを使用）
2. Raspberry Pi Imagerで:
   - **「デバイスを選択」**をクリック → **「Raspberry Pi Zero 2W」**を選択
   - **「OSを選択」**をクリック → **「Raspberry Pi OS（64ビット）」**（推奨）または**「Raspberry Pi OS（32ビット）」**を選択
   - **「ストレージを選択」**をクリック → MicroSDカードを選択

3. **設定（歯車アイコン）**ボタンをクリックして設定:
   - **ホスト名**: `ninjarobot`（または好きな名前）
   - **SSHを有効化**: このボックスにチェックを入れ、「パスワード認証を使用」を選択
   - **ユーザー名とパスワードを設定**:
     - ユーザー名: `pi`（または任意）
     - パスワード:（安全なパスワードを作成）
   - **WiFiを設定**（ワイヤレスを使用する場合）:
     - SSID: WiFiネットワーク名
     - パスワード: WiFiパスワード
     - 無線LAN国: 国を選択
   - **ロケール設定**: タイムゾーンとキーボードレイアウトを選択

4. **「保存」**をクリックして設定を保存
5. **「書き込む」**をクリックしてカードにOSを書き込む
6. プロセスが完了するまで待つ（5〜10分かかる場合があります）
7. 完了したら、MicroSDカードを安全に取り出す

### ステップ3.3: Raspberry Piを起動

1. MicroSDカードをRaspberry Pi Zero 2Wに挿入
2. キーボード、マウス、モニター（HDMIアダプター経由）を接続
3. 電源アダプターを接続
4. Piが起動するまで待つ（初回起動は2〜3分かかる場合があります）
5. 先ほど設定したユーザー名とパスワードでログイン

---

## 4. ソフトウェアのインストール

### ステップ4.1: システムの更新

ターミナル（黒い画面）を開いて実行:

```bash
sudo apt update && sudo apt upgrade -y
```

インターネット速度によっては10〜20分かかる場合があります。

### ステップ4.2: 必要なインターフェースを有効化

1. Raspberry Pi設定ツールを開く:
   ```bash
   sudo raspi-config
   ```

2. **「3 Interface Options」**（インターフェースオプション）に移動

3. 以下を有効化:
   - **I2C**: **「I5 I2C」**を選択 → **「はい」**
   - **SPI**: **「I4 SPI」**を選択 → **「はい」**

4. **「Finish」**（完了）を選択し、再起動を求められたら再起動:
   ```bash
   sudo reboot
   ```

### ステップ4.3: システム依存関係のインストール

再起動後、ターミナルを開いて必要なパッケージをインストール:

```bash
sudo apt install -y git pigpio python3-pip
```

**説明:**
- `git` - プログラムをダウンロードするツール
- `pigpio` - ハードウェアを制御するためのプログラム
- `python3-pip` - Pythonパッケージ（プログラムの部品）をインストールするツール

### ステップ4.4: Pythonパッケージマネージャー（uv）のインストール

より高速で信頼性の高いPythonパッケージ管理のために`uv`を使用します:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

インストール後、ターミナルを閉じて再度開くか、次を実行:

```bash
source $HOME/.local/bin/env
```

インストールを確認:

```bash
uv --version
```

`uv 0.x.x`のようなバージョン番号が表示されるはずです。

### ステップ4.5: pigpioデーモンの起動

ハードウェア制御のために`pigpio`デーモン（バックグラウンドで動くプログラム）を実行する必要があります:

```bash
sudo pigpiod
```

> [!TIP]
> 起動時に`pigpiod`を自動的に開始するには、次を実行:
> ```bash
> sudo systemctl enable pigpiod
> sudo systemctl start pigpiod
> ```

---

## 5. サービスのセットアップ（Gemini AIとngrok）

### ステップ5.1: Google Gemini APIキーの作成

ロボットは自然言語理解のためにGoogleのGemini AIを使用します。

1. **Google AI Studioにアクセス**: https://aistudio.google.com/
2. Googleアカウントで**サインイン**
3. 左サイドバーの**「Get API Key」**（APIキーを取得）をクリック
4. **「Create API Key」**（APIキーを作成）をクリック
5. **「Create API key in new project」**（新しいプロジェクトでAPIキーを作成）を選択するか、既存のプロジェクトを選択
6. 表示される**APIキーをコピー**（`AIzaSy...`のような形式）
7. このキーを**安全な場所に保存**—後で必要になります

> [!WARNING]
> APIキーは非公開にしてください！公開したり、バージョン管理（Gitなど）にコミットしたりしないでください。

### ステップ5.2: ngrokアカウントの作成

`ngrok`は、どこからでもロボットを制御できるように公開URL（インターネットアドレス）を作成します。

1. **ngrokにアクセス**: https://ngrok.com/
2. **「Sign up」**（サインアップ）をクリックして無料アカウントを作成
3. サインイン後、次にアクセス: https://dashboard.ngrok.com/get-started/your-authtoken
4. **Authtokenをコピー**（`2a...`のような形式）
5. このトークンを**保存**—ロボットのWebサーバーを初めて起動するときに入力します

---

## 6. プロジェクトのインストール

### ステップ6.1: リポジトリのクローン

ホームディレクトリに移動してプロジェクトをクローン（コピー）:

```bash
cd ~
git clone https://github.com/Nilcreator/NinjaRobotV4.git
cd NinjaRobotV4
```

> [!NOTE]
> リポジトリがプライベートまたは別のソースを使用している場合は、URLを適宜調整してください。

### ステップ6.2: 仮想環境の作成

競合を避けるために、Pythonパッケージを仮想環境にインストールすることをお勧めします。

```bash
uv venv
source .venv/bin/activate
```

ターミナルの行の先頭に`(NinjaRobotV4)`または`(.venv)`が表示されるはずです。

### ステップ6.3: すべての依存関係のインストール

プロジェクトの依存関係を仮想環境にインストールします:

```bash
uv pip install -e .
```

これにより:
- すべてのPython依存関係がインストールされます
- ロボットのすべてのライブラリが編集可能モードで設定されます
- すべてのCLIコマンドが使用可能になります

インストールには5〜10分かかる場合があります。

### ステップ6.4: インストールの確認

メインコマンドが使用可能か確認:

```bash
ninja_core --help
```

`chat`、`server`、`config`などの使用可能なコマンドのリストが表示されるはずです。

---

## 7. ハードウェアの校正

ロボットを実行する前に、サーボを校正してハードウェアを設定する必要があります。

### ステップ7.1: ブザーの設定

ブザーが接続されているGPIOピンをシステムに伝えます:

```bash
uv run pi0buzzer init 17
```

ブザーをテスト:

```bash
uv run pi0buzzer beep
```

短いビープ音が聞こえるはずです。

### ステップ7.2: 距離センサーのテスト

センサーをテスト:

```bash
uv run pi0vl53l0x get --count 5 --interval 1.0
```

ミリメートル単位で5つの距離測定値が表示されるはずです。

### ステップ7.3: サーボの校正

各サーボは、最小、中央、最大位置を定義するために校正する必要があります。

各サーボについて（GPIO 17の例）:

```bash
uv run pi0servo calib 20
```

画面の指示に従ってください:
1. `v`を押して**Min**（最小）位置を選択
2. **上/下**矢印キーで大きな調整、**w/s**で微調整
3. サーボが最小位置にあるときに**Enter**を押して保存
4. `c`を押して**Center**（中央）位置を選択、調整して**Enter**を押す
5. `x`を押して**Max**（最大）位置を選択、調整して**Enter**を押す
6. `q`を押して終了

**これを8つすべてのサーボで繰り返してください**（GPIOピン: 20から27）

### ステップ7.4: ハードウェア設定のインポート

すべてのサーボを校正した後、設定をインポート:

```bash
uv run ninja_core config import
```

次のように表示されるはずです:
```
Found servo config at 'servo.json'. Importing...
Found buzzer config at 'buzzer.json'. Importing...
Configuration updated and saved to config.json!
```

### ステップ7.5: Gemini APIキーの設定

APIキーでAIエージェントを設定（`YOUR_API_KEY`を実際のキーに置き換えてください）:

```bash
uv run ninja_core config set-key gemini YOUR_API_KEY
```

---

## 8. 機能テスト

それでは、各コンポーネントを個別にテストしましょう。

### テスト8.1: ディスプレイテスト

画像で液晶画面をテスト:

```bash
uv run pi0disp image assets/images/sample_face.jpg
```

明るさが変化する画像がディスプレイに表示されるはずです。

アニメーションをテスト:

```bash
uv run pi0disp ball_anime --num-balls 5
```

**Ctrl+C**を押して停止。

### テスト8.2: サーボ動作テスト

サーボを中央位置に移動:

```bash
uv run pi0servo servo 20 center
```

GPIO 20のサーボが0度に移動するはずです。

他の位置を試す:

```bash
uv run pi0servo servo 20 45
uv run pi0servo servo 20 -45
uv run pi0servo servo 20 max
```

### テスト8.3: サウンドテスト

メロディを再生:

```bash
uv run pi0buzzer playmusic
```

### テスト8.4: 距離センサーのパフォーマンス

センサーの速度を測定:

```bash
uv run pi0vl53l0x performance --count 100
```

### テスト8.5: AIエージェントテスト（テキストチャット）

ターミナルモードでAIチャットをテスト:

```bash
uv run ninja_core chat
```

これらのコマンドを試してください:
- `Hello`（ロボットが挨拶するはずです）
- `Show me a happy face`（嬉しい表情と音を表示）
- `こんにちは`（日本語で応答）
- `你好`（中国語で応答）
- `quit`と入力するか**Ctrl+C**を押して終了

> [!NOTE]
> ロボットは距離を継続的に監視し、近づきすぎると（<50mm）反応します。

---

## 9. ロボットの起動

### Webサーバーの起動

これがロボットと対話する主な方法です:

```bash
uv run ninja_core server
```

**初回実行時**、**ngrok authtoken**（ステップ5.2から）の入力を求められます。貼り付けてEnterを押してください。

ロボットは:
1. すべてのハードウェアを初期化
2. Webサーバーを起動
3. ngrok経由で公開URLを作成
4. 画面にQRコードを表示

### Webインターフェースへのアクセス

2つのオプションがあります:

#### オプションA: QRコードをスキャン（推奨）

スマートフォンを使用して、ロボットの画面に表示されているQRコードをスキャンします。これにより、スマートフォンのブラウザでWebインターフェースが開きます。

#### オプションB: ローカルネットワーク

同じWiFiネットワーク上の任意のデバイスで、ブラウザを開いて次にアクセス:
```
http://ninjarobot.local:8000
```
（ホスト名が異なる場合は`ninjarobot`を置き換えてください）

### Webインターフェースの機能

接続すると、次のことができます:

1. **ロボットとチャット**:
   - テキストボックスにメッセージを入力
   - または**マイクアイコン**をクリックして話す（最初に言語を選択）
   - ロボットは同じ言語で応答します

2. **サーボを制御**:
   - ドロップダウンから動作を選択
   - **Execute**（実行）をクリック

3. **表情を表示**:
   - 表情を選択（嬉しい、悲しいなど）
   - **Show**（表示）をクリック

4. **音を再生**:
   - 感情音を選択
   - **Play**（再生）をクリック

5. **距離を監視**:
   - リアルタイムの距離測定値が上部に表示されます

### サポートされている言語

- **English**（en-US）- 英語
- **日本語**（ja-JP）
- **繁體中文**（zh-TW）- 繁体字中国語
- **简体中文**（zh-CN）- 簡体字中国語

### サーバーの停止

ターミナルで**Ctrl+C**を押してサーバーを停止します。ロボットはすべてのハードウェアを安全にシャットダウンします。

---

---

## 10. 自動起動（オプション）

電源を入れたときにロボットを自動的に起動させたい場合は、次の手順に従ってください。

> [!IMPORTANT]
> **前提条件:** ハードウェアの校正やAPIキーの設定など、前のすべての手順を完了していることを確認してください。自動起動を有効にする前に、ロボットが完全に機能している必要があります。
>
> **Ngrokの要件:** 自動起動を機能させるには、有効なngrok authtokenが設定されている**必要があります**。トークンがない場合、バックグラウンドでのハングアップ（応答なし）を防ぐためにサービスは起動に失敗します。

### ステップ10.1: スタートアップサービスのインストール

次のコマンドを実行します:

```bash
uv run ninja_utils install-startup
```

これにより:
1. システムの準備ができているか確認します（configが存在するか、pigpiodが実行されているかなど）
2. systemdサービスファイルを作成します
3. 起動時にサービスが開始されるように有効化します

### ステップ10.2: 確認

サービスのステータスを確認できます:

```bash
uv run ninja_utils status-startup
```

### ステップ10.3: 再起動

Raspberry Piを再起動します:

```bash
sudo reboot
```

ロボットは自動的に起動するはずです。1〜2分後にQRコードまたは`http://ninjarobot.local:8000`からWebインターフェースにアクセスできます。

> [!TIP]
> **安全なシャットダウン:** Webインターフェースの下部にある「Power Off Robot」（ロボットの電源オフ）ボタンを使用して、ロボットを安全にシャットダウンできます。Raspberry Piの緑色のライトの点滅が止まるまで待ってから、電源を抜いてください。

### 自動起動の削除

ロボットの自動起動を停止したい場合:

```bash
uv run ninja_utils remove-startup
```

---

## 11. トラブルシューティング

### 問題:「Could not connect to pigpiod daemon」（pigpiodデーモンに接続できません）

**解決策**:
```bash
sudo pigpiod
```

その後、コマンドを再度実行してください。

### 問題: ディスプレイが動作しない

**確認事項**:
1. SPIが有効になっているか確認: `sudo raspi-config` → Interface Options → SPI
2. 配線がセクション2のピン表と一致しているか確認
3. 再起動: `sudo reboot`

### 問題: 距離センサーが応答しない

**確認事項**:
1. I2Cが有効になっているか確認: `sudo raspi-config` → Interface Options → I2C
2. センサーが検出されているか確認:
   ```bash
   sudo i2cdetect -y 1
   ```
   出力に`29`または`52`が表示されるはずです
3. 配線を確認（VCCは3.3Vに、5Vではない）

### 問題: サーボが動かない

**確認事項**:
1. 外部5V電源が接続され、オンになっているか確認
2. Piとサーボ電源の間で共通グラウンドが確認されているか
3. サーボ信号線の接続を確認
4. サーボを再校正: `uv run pi0servo calib <PIN>`

### 問題:「ImportError」または「ModuleNotFoundError」

**解決策**:
プロジェクトを再インストール:
```bash
cd ~/NinjaRobotV4
uv pip install -e . --force-reinstall
```

### 問題: Webサーバーが起動しない

**確認事項**:
1. ポート8000がすでに使用されていないか確認
2. ngrok authtokenが正しく設定されているか確認
3. 詳細出力でサーバーを再起動:
   ```bash
   uv run ninja_core server --log-level debug
   ```

### 問題: AIエージェントが応答しない

**確認事項**:
1. Gemini APIキーが設定されているか確認:
   ```bash
   cat config.json | grep gemini
   ```
2. インターネット接続を確認
3. APIキーを再設定:
   ```bash
   uv run ninja_core config set-key gemini YOUR_KEY
   ```

### さらなるヘルプ

ここでカバーされていない問題が発生した場合:

1. プロジェクトのGitHub Issuesページを確認
2. `DevelopmentLog.md`で既知の問題と修正を確認
3. すべての配線が図と正確に一致しているか確認
4. 個別のコンポーネントテスト（セクション8）を実行して問題を特定

---

## 次のステップ

- **カスタム動作を記録**: `uv run ninja_core movement-tool`を使用してサーボの振り付けを作成および保存
- **動作をカスタマイズ**: `config.json`を編集して設定を調整
- **筐体を作る**: ロボットの本体を設計してすべての部品を取り付ける
- **コードを探索**: 開発者向けドキュメントは`ninja_core/README.md`を確認

**おめでとうございます！** NinjaRobotV4が使用できる状態になりました。AI搭載ロボットの探索と実験を楽しんでください！🤖

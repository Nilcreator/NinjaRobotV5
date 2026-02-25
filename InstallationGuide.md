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

> [!IMPORTANT]
> The GPIO pins for DC, RST, and BLK are **configurable**. The table below shows the default wiring. After connecting, run `uv run pi0disp init` to register your pin assignments.

| Display Pin | Raspberry Pi Pin | Description |
|-------------|------------------|-------------|
| VCC         | 3.3V             | Power       |
| GND         | GND              | Ground      |
| DIN (MOSI)  | SPI0 MOSI        | SPI Data    |
| CLK (SCL)   | SPI0 SCLK        | SPI Clock   |
| CS          | SPI0 CE0         | Chip Select |
| DC          | GPIO (configurable, e.g. 14 or 18) | Data/Command |
| RST         | GPIO (configurable, e.g. 15 or 19) | Reset       |
| BLK         | GPIO (configurable, e.g. 16 or 20) | Backlight   |

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
- [ ] Display is connected via SPI (SCLK, MOSI, CE0) and your chosen GPIO pins for DC, RST, BLK
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

*For the lastest Raspberry Pi Bookworm 64-bit OS your will encounter "Package 'pigpio' has no installation candidate" error.
You can only install pigpio from the sorce, here is the step-by-step solution:

Here is the complete, step-by-step guide to installing `pigpio` on a Raspberry Pi Zero 2 W running the latest Raspberry Pi OS (Bookworm 64-bit).

This guide is designed to navigate the specific security changes in the new OS (PEP 668) and fix the common installation errors (missing candidates, `distutils` removal, and shared library linking issues).

---

## 🛠️ Complete pigpio Installation Guide (Raspberry Pi OS Bookworm 64-bit)

**Target Hardware:** Raspberry Pi Zero 2 W 
**Target OS:** Raspberry Pi OS "Bookworm" (64-bit)

## Phase 1: System Preparation

Before starting, ensure your system package list is up-to-date and you have the necessary tools to compile software from source.

1. **Install build tools:**
We need `make` and `gcc` (included in `build-essential`) to compile the C library, and `unzip` to handle the download.
```bash
sudo apt install -y build-essential unzip wget

```



---

## Phase 2: Compile and Install the C Library

Since the `pigpio` package was removed from the standard repository in Bookworm, we must install it from the source code.

1. **Download the source code:**
```bash
wget https://github.com/joan2937/pigpio/archive/master.zip

```


2. **Unzip and enter the directory:**
```bash
unzip master.zip
cd pigpio-master

```


3. **Compile the code:**
```bash
make

```


4. **Install the library:**
```bash
sudo make install

```


> **⚠️ IMPORTANT EXPECTED ERROR:**
> You will likely see an error at the end saying:
> `ModuleNotFoundError: No module named 'distutils'`
> `make: *** [Makefile:107: install] Error 1`


> **Ignore this error.** It happens because the installer tries to install the Python bindings using an outdated method. The core C library (which is what we really need from this step) has installed successfully. We will fix the Python part in Phase 4.



---

## Phase 3: Fix Shared Library Linking

This step fixes the error: `pigpiod: error while loading shared libraries: libpigpio.so.1: cannot open shared object file`.

1. **Update the system library cache:**
The installer placed `libpigpio.so` in `/usr/local/lib`, but the OS doesn't know it's there yet. Run this command to register it:
```bash
sudo ldconfig

```



---

## Phase 4: Install the Python Library

Since the automatic Python installation failed in Phase 2, we will install the Python interface manually using a method compatible with Bookworm.

**Option A: The Recommended Method (APT)**
Try this first. It installs the pre-compiled Python wrapper provided by the OS maintainers.

```bash
sudo apt install python3-pigpio

```

**Option B: The Fallback Method (PIP)**
If Option A fails (unable to locate package), use `pip`. Note the `--break-system-packages` flag, which is required on Bookworm to allow installation outside a virtual environment.

```bash
sudo pip3 install pigpio --break-system-packages

```

---

## Phase 5: Create the System Service (Auto-start)

This step fixes the error: `Failed to enable unit: Unit pigpiod.service does not exist`.
We must manually create the configuration file to tell the system how to run the daemon in the background.

1. **Create the service file:**
```bash
sudo nano /etc/systemd/system/pigpiod.service

```


2. **Paste the following configuration:**
(Copy and paste the text below into the editor)
```ini
[Unit]
Description=Pigpio daemon
Documentation=https://github.com/joan2937/pigpio
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/pigpiod
# ExecStart=/usr/local/bin/pigpiod -l
# (Uncomment the line above with -l if you want to restrict access to localhost only)

[Install]
WantedBy=multi-user.target

```


3. **Save and Exit:**
* Press `Ctrl + O` then `Enter` to save.
* Press `Ctrl + X` to exit.


4. **Enable and Start the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

```



---

## Phase 6: Verification

Let's verify everything is working correctly on your Raspberry Pi Zero 2 W.

1. **Check the Daemon:**
Run the `pigs` command (pigpio command-line tool).
```bash
pigs t

```


**Success:** You should see a large number (the current microsecond timestamp).
**Failure:** If it says "socket connect failed", ensure you ran `sudo systemctl start pigpiod`.
2. **Check Python:**
Create a quick test script:
```bash
python3 -c "import pigpio; pi=pigpio.pi(); print('Connected:', pi.connected)"

```


**Success:** It should print `Connected: True`.

---

## 🧹 Cleanup (Optional)

You can now remove the source code files to save space on your SD card.

```bash
cd ~
rm -rf pigpio-master master.zip

```

**Troubleshooting Tips for Zero 2 W:**

* 
**Performance:** The Zero 2 W is powerful (Quad-core), but if you are running heavy compiles, it may get warm. Ensure it's not enclosed in a case without ventilation during the `make` process.


* **Remote Access:** If you plan to control the GPIOs remotely from a PC, remember to remove the `-l` flag in the service file created in Phase 5 to allow network connections.

Reload systemd setting
```bash
sudo systemctl daemon-reload
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

### Step 4.6: Install Node.js

The web interface (`ninja_webapp`) requires Node.js to be built. Install it using NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
```

Verify installation:

```bash
node -v && npm -v
```

You should see version numbers like `v20.x.x` and `10.x.x`.

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
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5
```

> [!NOTE]
> If the repository is private or you're using a different source, adjust the URL accordingly.

### Step 6.2: Create a Virtual Environment

It is best practice to install Python packages in a virtual environment to avoid conflicts.

```bash
uv venv
source .venv/bin/activate
```

You should see `(NinjaRobotV5)` or `(.venv)` appear at the start of your terminal line.

### Step 6.3: Install All Dependencies

Install the project dependencies into the virtual environment using one of these methods:

**Method A: `uv sync` (Recommended)**

```bash
uv sync
```

`uv sync` automatically reads `pyproject.toml`, resolves all dependencies, and installs them into the `.venv`. This is the simplest and most reliable method.

**Method B: `uv pip install -e .` (Alternative)**

```bash
uv pip install -e .
```

This installs the project in editable (development) mode. Use this if you need more control over the installation process.

> **Difference:** `uv sync` creates/manages the `.venv` automatically and uses a lockfile for reproducible installs. `uv pip install -e .` installs into an existing virtual environment without a lockfile.

Both methods will:
- Install all Python dependencies (including `pigpio`)
- Set up all the robot's libraries in editable mode
- Make all CLI commands available (`pi0vl53l0x`, `pi0servo`, etc.)

The installation may take 5-10 minutes.

### Step 6.4: Build the Web Interface

The robot's web interface is built with React. Build it with:

```bash
cd ninja_webapp
npm install
npm run build
cd ..
```

This creates the `ninja_webapp/dist/` folder that the server will use.

> [!NOTE]
> If you see errors during `npm install`, ensure Node.js was installed correctly (Step 4.6).

### Step 6.5: Verify Installation

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

Run the built-in self-test to verify the sensor is connected and working:

```bash
uv run pi0vl53l0x test
```

Then take a few live readings:

```bash
uv run pi0vl53l0x get --count 5 --interval 1.0
```

You should see 5 distance readings in millimeters.

Check the sensor status (firmware, offset, health):

```bash
uv run pi0vl53l0x status
```

Optionally, calibrate the sensor by placing an object at a known distance (e.g., 100 mm) and running:

```bash
uv run pi0vl53l0x calibrate --distance 100 --count 10
```

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

> [!IMPORTANT]
> Make sure you have already run `uv run pi0disp init` (Step 8.1) before this step. The config import reads display pins from `pi0disp/display.json`.

```bash
uv run ninja_core config import
```

You should see:
```
Found servo config at 'servo.json'. Importing...
Found buzzer config at 'buzzer.json'. Importing...
Found display config at 'pi0disp/display.json'. Importing...
...imported display pins: DC=18, RST=19, BLK=20, rotation=90
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

First-time setup (if not already done):

```bash
uv run pi0disp init
```

Follow the prompts to configure your display pins and profile.

Test the LCD screen with an image:

```bash
uv run pi0disp image assets/images/sample_face.jpg
```

You should see the image on the display.

Test brightness control:

```bash
uv run pi0disp brightness 50
uv run pi0disp brightness 100
```

Test text display:

```bash
uv run pi0disp text "Hello NinjaRobot"
uv run pi0disp text "忍者ロボット" --lang ja --scroll
```

Test animation:

```bash
uv run pi0disp demo --num-balls 3
```

Press **Ctrl+C** to stop.

Check configuration and health:

```bash
uv run pi0disp info --health-check
```

### Test 8.2: Servo Movement Test

Move a servo to its center position:

```bash
uv run pi0servo move 20 0
```

The servo on GPIO 20 should move to 0 degrees.

Try other positions:

```bash
uv run pi0servo move 20 45
uv run pi0servo move 20 -- -45
uv run pi0servo cmd "20:X"
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

Check sensor status and current configuration:

```bash
uv run pi0vl53l0x status
uv run pi0vl53l0x config show
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

Press **Ctrl+C** in the terminal to stop the server. The robot will perform a **graceful shutdown animation**:
1. Display a "sleepy" face on the LCD
2. Play a "sleepy" sound melody
3. Move servos to the "Poweroff" rest position
4. Safely shut down all hardware

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
> **Safe Shutdown:** You can safely shut down the robot using the "Power Off Robot" button at the bottom of the web interface. The robot will display a "sleepy" face, play a sound, and move to its rest position before powering off. Wait for the green light on the Raspberry Pi to stop flashing before unplugging the power.

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
3. Run the display health check: `uv run pi0disp info --health-check`
4. **Verify GPIO pin configuration**: Run `uv run pi0disp init` to register your display pins, then `uv run ninja_core config import` to sync them to `config.json`. A common cause of blank displays is mismatched GPIO pins between `display.json` and `config.json`.
5. Reboot: `sudo reboot`

### Problem: Distance sensor not responding

**Checks**:
1. Verify I2C is enabled: `sudo raspi-config` → Interface Options → I2C
2. Check if sensor is detected:
   ```bash
   sudo i2cdetect -y 1
   ```
   You should see `29` or `52` in the output
3. Check wiring (VCC to 3.3V, not 5V)
4. Run the built-in diagnostic:
   ```bash
   uv run pi0vl53l0x test
   uv run pi0vl53l0x status
   ```
5. If status shows errors, try power-cycling the sensor and re-running `uv run pi0vl53l0x test`

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
cd ~/NinjaRobotV5
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

**Congratulations!** Your NinjaRobot V5 is now ready to use. Enjoy exploring and experimenting with your AI-powered robot! 🤖

---
---

# NinjaRobot V5 完全インストールガイド（日本語版）

このガイドでは、Raspberry Pi Zero 2WでNinjaRobot V5を構築して実行するために必要なすべての手順を説明します。プログラミング経験は不要です—各ステップを注意深く従ってください。

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

### ステップ4.6: Node.jsのインストール

Webインターフェース（`ninja_webapp`）のビルドにはNode.jsが必要です。NodeSourceを使用してインストール:

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
```

インストールを確認:

```bash
node -v && npm -v
```

`v20.x.x`と`10.x.x`のようなバージョン番号が表示されるはずです。

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
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5
```

> [!NOTE]
> リポジトリがプライベートまたは別のソースを使用している場合は、URLを適宜調整してください。

### ステップ6.2: 仮想環境の作成

競合を避けるために、Pythonパッケージを仮想環境にインストールすることをお勧めします。

```bash
uv venv
source .venv/bin/activate
```

ターミナルの行の先頭に`(NinjaRobotV5)`または`(.venv)`が表示されるはずです。

### ステップ6.3: すべての依存関係のインストール

以下のいずれかの方法で、プロジェクトの依存関係を仮想環境にインストールします:

**方法A: `uv sync`（推奨）**

```bash
uv sync
```

`uv sync` は `pyproject.toml` を自動的に読み取り、すべての依存関係を解決して `.venv` にインストールします。最もシンプルで信頼性の高い方法です。

**方法B: `uv pip install -e .`（代替方法）**

```bash
uv pip install -e .
```

プロジェクトを編集可能（開発）モードでインストールします。インストールプロセスをより細かく制御したい場合に使用してください。

> **違い:** `uv sync` は `.venv` を自動的に作成・管理し、ロックファイルで再現可能なインストールを行います。`uv pip install -e .` は既存の仮想環境にロックファイルなしでインストールします。

どちらの方法でも:
- すべてのPython依存関係がインストールされます（`pigpio`を含む）
- ロボットのすべてのライブラリが編集可能モードで設定されます
- すべてのCLIコマンドが使用可能になります（`pi0vl53l0x`、`pi0servo` など）

インストールには5〜10分かかる場合があります。

### ステップ6.4: Webインターフェースのビルド

ロボットのWebインターフェースはReactで構築されています。次のコマンドでビルド:

```bash
cd ninja_webapp
npm install
npm run build
cd ..
```

これにより、サーバーが使用する`ninja_webapp/dist/`フォルダーが作成されます。

> [!NOTE]
> `npm install`中にエラーが表示される場合は、Node.jsが正しくインストールされているか確認してください（ステップ4.6）。

### ステップ6.5: インストールの確認

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

内蔵セルフテストを実行して、センサーが正しく接続され動作していることを確認します：

```bash
uv run pi0vl53l0x test
```

次に、実際の測定を行います：

```bash
uv run pi0vl53l0x get --count 5 --interval 1.0
```

ミリメートル単位で5つの距離測定値が表示されるはずです。

センサーのステータス（ファームウェア、オフセット、ヘルスチェック）を確認：

```bash
uv run pi0vl53l0x status
```

オプションとして、既知の距離（例：100mm）にオブジェクトを配置してセンサーを校正できます：

```bash
uv run pi0vl53l0x calibrate --distance 100 --count 10
```

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

初回セットアップ（まだの場合）：

```bash
uv run pi0disp init
```

プロンプトに従ってディスプレイのピンとプロファイルを設定してください。

画像で液晶画面をテスト：

```bash
uv run pi0disp image assets/images/sample_face.jpg
```

画像がディスプレイに表示されるはずです。

明るさ制御をテスト：

```bash
uv run pi0disp brightness 50
uv run pi0disp brightness 100
```

テキスト表示をテスト：

```bash
uv run pi0disp text "Hello NinjaRobot"
uv run pi0disp text "忍者ロボット" --lang ja --scroll
```

アニメーションをテスト：

```bash
uv run pi0disp demo --num-balls 3
```

**Ctrl+C**を押して停止。

設定とヘルスチェック：

```bash
uv run pi0disp info --health-check
```

### テスト8.2: サーボ動作テスト

サーボを中央位置に移動:

```bash
uv run pi0servo move 20 0
```

GPIO 20のサーボが0度（中心）に移動します。

他の位置も試してみましょう：

```bash
uv run pi0servo move 20 45
uv run pi0servo move 20 -- -45
uv run pi0servo cmd "20:X"
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

センサーのステータスと現在の設定を確認:

```bash
uv run pi0vl53l0x status
uv run pi0vl53l0x config show
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

ターミナルで**Ctrl+C**を押してサーバーを停止します。ロボットは**グレースフルシャットダウンアニメーション**を実行します：
1. LCDに「眠い」顔を表示
2. 「眠い」音のメロディーを再生
3. サーボを「Poweroff」休憩位置に移動
4. すべてのハードウェアを安全にシャットダウン

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
> **安全なシャットダウン:** Webインターフェースの下部にある「Power Off Robot」（ロボットの電源オフ）ボタンを使用して、ロボットを安全にシャットダウンできます。ロボットは「眠い」顔を表示し、音を再生し、休憩位置に移動してから電源を切ります。Raspberry Piの緑色のライトの点滅が止まるまで待ってから、電源を抜いてください。

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
4. 内蔵診断ツールを実行:
   ```bash
   uv run pi0vl53l0x test
   uv run pi0vl53l0x status
   ```
5. ステータスにエラーが表示される場合は、センサーの電源を入れ直して `uv run pi0vl53l0x test` を再実行してください

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
cd ~/NinjaRobotV5
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

**おめでとうございます！** NinjaRobot V5が使用できる状態になりました。AI搭載ロボットの探索と実験を楽しんでください！🤖

---
---

# NinjaRobot V5 完整安裝指南（繁體中文版）

本指南將引導您完成在 Raspberry Pi Zero 2W 上建置和運行 NinjaRobot V5 所需的每個步驟。不需要程式設計經驗——只需仔細按照每個步驟操作即可。

> [!NOTE]
> V5 引入了具有非阻塞驅動程式的模組化架構。所有硬體現在都使用標準化介面。

---

## 目錄

1. [硬體需求](#1-硬體需求)
2. [硬體接線指南](#2-硬體接線指南)
3. [Raspberry Pi OS 安裝](#3-raspberry-pi-os-安裝)
4. [軟體安裝](#4-軟體安裝)
5. [服務設定（Gemini AI 與 ngrok）](#5-服務設定gemini-ai-與-ngrok)
6. [專案安裝](#6-專案安裝)
7. [硬體校準](#7-硬體校準)
8. [功能測試](#8-功能測試)
9. [啟動機器人](#9-啟動機器人)
10. [自動啟動（選用）](#10-自動啟動選用)
11. [疑難排解](#11-疑難排解)

---

## 1. 硬體需求

### 必要元件

- **Raspberry Pi Zero 2W**（已焊接排針）
- **MicroSD 卡**（16GB 或更大，建議 Class 10）
- **電源供應器**（5V 2.5A USB-C 或 Micro-USB）
- **8 個伺服馬達**（SG90 或類似型號，5V）
- **伺服馬達外部 5V 電源**（建議：5V 3A 或更高）
- **ST7789V LCD 顯示器**（240x240 像素，SPI 介面）
- **VL53L0X 距離感測器**（飛行時間感測器，I2C 介面）
- **被動蜂鳴器**（3-5V）
- **杜邦線**（公對母和公對公）
- **麵包板**（原型製作用，選用）
- **鍵盤、滑鼠和顯示器**（初始設定用）

### 建議選配

- **Raspberry Pi 保護殼**
- **散熱片**（Raspberry Pi 用）
- **USB 集線器**（如果設定期間需要多個 USB 裝置）

---

## 2. 硬體接線指南

### 重要安全注意事項

> [!CAUTION]
> - **務必在連接或拔除元件前關閉電源**。
> - **切勿將伺服馬達電源直接連接到 Raspberry Pi 的 5V 腳位**——請使用外部電源。
> - **在開啟電源前仔細檢查所有連接**以避免損壞。

### GPIO 腳位配置

以下是所有元件的完整接線圖：

```
Raspberry Pi Zero 2W GPIO 腳位配置（40 針排針）
┌─────────────────────────────────────┐
│  3.3V  [1] [2]  5V                  │
│  SDA   [3] [4]  5V                  │
│  SCL   [5] [6]  GND                 │
│  GPIO4 [7] [8]  GPIO14 (DC)         │
│  GND   [9] [10] GPIO15 (RST)        │
│  GPIO17[11] [12] GPIO18             │  ← 蜂鳴器 (17)
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

### 元件連接表

#### 伺服馬達（8 個）

| 伺服編號 | GPIO 腳位 | 訊號線 | 電源（5V） | 接地 |
|---------|----------|--------|------------|------|
| 1       | GPIO 20  | 橙/黃色 | 外部 5V | 共用 GND |
| 2       | GPIO 21  | 橙/黃色 | 外部 5V | 共用 GND |
| 3       | GPIO 22  | 橙/黃色 | 外部 5V | 共用 GND |
| 4       | GPIO 23  | 橙/黃色 | 外部 5V | 共用 GND |
| 5       | GPIO 24  | 橙/黃色 | 外部 5V | 共用 GND |
| 6       | GPIO 25  | 橙/黃色 | 外部 5V | 共用 GND |
| 7       | GPIO 26  | 橙/黃色 | 外部 5V | 共用 GND |
| 8       | GPIO 27  | 橙/黃色 | 外部 5V | 共用 GND |

> [!IMPORTANT]
> **伺服馬達電源：** 將所有伺服馬達的電源線（紅色）連接到外部 5V 電源（非 Raspberry Pi）。將所有伺服馬達的接地線（棕/黑色）連接到共用接地，該接地也需連接到 Raspberry Pi 的 GND 腳位。

#### ST7789V LCD 顯示器（SPI）

| 顯示器腳位 | Raspberry Pi 腳位 | 說明 |
|-----------|------------------|------|
| VCC       | 3.3V             | 電源 |
| GND       | GND              | 接地 |
| DIN (MOSI)| SPI0 MOSI        | SPI 資料 |
| CLK (SCL) | SPI0 SCLK        | SPI 時脈 |
| CS        | SPI0 CE0         | 晶片選擇 |
| DC        | GPIO 14          | 資料/命令 |
| RST       | GPIO 15          | 重置 |
| BLK       | GPIO 16          | 背光 |

#### VL53L0X 距離感測器（I2C）

| 感測器腳位 | Raspberry Pi 腳位 | 說明 |
|-----------|------------------|------|
| VCC       | 腳位 1（3.3V）    | 電源 |
| GND       | 腳位 6（GND）     | 接地 |
| SCL       | 腳位 5（GPIO 3 - I2C SCL） | I2C 時脈 |
| SDA       | 腳位 3（GPIO 2 - I2C SDA） | I2C 資料 |

#### 被動蜂鳴器

| 蜂鳴器腳位 | Raspberry Pi 腳位 | 說明 |
|-----------|------------------|------|
| 正極（+） | 腳位 11（GPIO 17）| 訊號 |
| 負極（-） | GND              | 接地 |

### 接線檢查清單

繼續之前，請確認：
- [ ] 所有伺服馬達訊號線連接到正確的 GPIO 腳位（20-27）
- [ ] 伺服馬達電源來自外部 5V 電源（非 Pi）
- [ ] Pi 與伺服馬達外部電源之間共用接地
- [ ] 顯示器透過 SPI 連接（SCLK、MOSI、CE0）及 GPIO 14、15、16
- [ ] 距離感測器透過 I2C 連接（SCL、SDA）
- [ ] 蜂鳴器連接到 GPIO 17
- [ ] 沒有鬆脫的線或短路

---

## 3. Raspberry Pi OS 安裝

### 步驟 3.1：下載 Raspberry Pi Imager

1. 在您的電腦上前往：https://www.raspberrypi.com/software/
2. 為您的作業系統（Windows、macOS 或 Linux）下載 **Raspberry Pi Imager**
3. 安裝並開啟 Raspberry Pi Imager

### 步驟 3.2：將 OS 燒錄到 MicroSD 卡

1. 將 MicroSD 卡插入電腦（如需要可使用轉接器）
2. 在 Raspberry Pi Imager 中：
   - 點擊 **「選擇裝置」** → 選擇 **「Raspberry Pi Zero 2W」**
   - 點擊 **「選擇作業系統」** → 選擇 **「Raspberry Pi OS（64位元）」**（建議）
   - 點擊 **「選擇儲存裝置」** → 選擇您的 MicroSD 卡

3. 點擊 **設定（齒輪圖示）** 按鈕進行設定：
   - **主機名稱**：`ninjarobot`（或您喜歡的名稱）
   - **啟用 SSH**：勾選此方塊並選擇「使用密碼認證」
   - **設定使用者名稱和密碼**：
     - 使用者名稱：`pi`（或您的選擇）
     - 密碼：（建立安全的密碼）
   - **設定 WiFi**（如果想使用無線網路）：
     - SSID：您的 WiFi 網路名稱
     - 密碼：您的 WiFi 密碼
     - 無線區域國家：選擇您的國家
   - **設定地區設定**：選擇您的時區和鍵盤配置

4. 點擊 **「儲存」** 儲存設定
5. 點擊 **「寫入」** 將 OS 燒錄到卡片
6. 等待程序完成（可能需要 5-10 分鐘）
7. 完成後，安全地退出 MicroSD 卡

### 步驟 3.3：啟動 Raspberry Pi

1. 將 MicroSD 卡插入 Raspberry Pi Zero 2W
2. 連接鍵盤、滑鼠和顯示器（透過 HDMI 轉接器）
3. 連接電源供應器
4. 等待 Pi 啟動（首次啟動可能需要 2-3 分鐘）
5. 使用您先前設定的使用者名稱和密碼登入

---

## 4. 軟體安裝

### 步驟 4.1：更新系統

開啟終端機並執行：

```bash
sudo apt update && sudo apt upgrade -y
```

這可能需要 10-20 分鐘，取決於您的網路速度。

### 步驟 4.2：啟用必要介面

1. 開啟 Raspberry Pi 設定工具：
   ```bash
   sudo raspi-config
   ```

2. 導航到 **「3 Interface Options」**

3. 啟用以下項目：
   - **I2C**：選擇 **「I5 I2C」** → **「是」**
   - **SPI**：選擇 **「I4 SPI」** → **「是」**

4. 選擇 **「Finish」** 並在提示時重新啟動：
   ```bash
   sudo reboot
   ```

### 步驟 4.3：安裝系統依賴項

重新啟動後，開啟終端機並安裝必要的套件：

```bash
sudo apt install -y git pigpio python3-pip
```

### 步驟 4.4：安裝 Python 套件管理員（uv）

我們使用 `uv` 來更快速且更可靠地管理 Python 套件：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安裝後，關閉並重新開啟終端機，或執行：

```bash
source $HOME/.local/bin/env
```

驗證安裝：

```bash
uv --version
```

您應該會看到類似 `uv 0.x.x` 的版本號。

### 步驟 4.5：啟動 pigpio 守護程式

`pigpio` 守護程式必須在背景執行以控制硬體：

```bash
sudo pigpiod
```

> [!TIP]
> 要讓 `pigpiod` 在開機時自動啟動，請執行：
> ```bash
> sudo systemctl enable pigpiod
> sudo systemctl start pigpiod
> ```

### 步驟 4.6：安裝 Node.js

網頁介面（`ninja_webapp`）需要 Node.js 來建置。使用 NodeSource 安裝：

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
```

驗證安裝：

```bash
node -v && npm -v
```

您應該會看到類似 `v20.x.x` 和 `10.x.x` 的版本號。

---

## 5. 服務設定（Gemini AI 與 ngrok）

### 步驟 5.1：建立 Google Gemini API 金鑰

機器人使用 Google 的 Gemini AI 進行自然語言理解。

1. **前往 Google AI Studio**：https://aistudio.google.com/
2. 使用您的 Google 帳戶**登入**
3. 點擊左側欄的 **「Get API Key」**
4. 點擊 **「Create API Key」**
5. 選擇 **「Create API key in new project」** 或選擇現有專案
6. **複製出現的 API 金鑰**（格式如：`AIzaSy...`）
7. **將此金鑰儲存在安全的地方**——稍後會需要

> [!WARNING]
> 請保密您的 API 金鑰！不要公開分享或提交到版本控制系統。

### 步驟 5.2：建立 ngrok 帳戶

`ngrok` 建立公開 URL，讓您可以從任何地方控制機器人。

1. **前往 ngrok**：https://ngrok.com/
2. 點擊 **「Sign up」** 建立免費帳戶
3. 登入後，前往：https://dashboard.ngrok.com/get-started/your-authtoken
4. **複製您的 Authtoken**（格式如：`2a...`）
5. **儲存此 token**——首次啟動機器人的 Web 伺服器時需要輸入

---

## 6. 專案安裝

### 步驟 6.1：複製儲存庫

導航到您的家目錄並複製專案：

```bash
cd ~
git clone https://github.com/Nilcreator/NinjaRobotV5.git
cd NinjaRobotV5
```

### 步驟 6.2：建立虛擬環境

最佳做法是在虛擬環境中安裝 Python 套件以避免衝突。

```bash
uv venv
source .venv/bin/activate
```

您應該會在終端機行首看到 `(NinjaRobotV5)` 或 `(.venv)`。

### 步驟 6.3：安裝所有依賴項

使用以下任一方法將專案依賴項安裝到虛擬環境中：

**方法 A：`uv sync`（推薦）**

```bash
uv sync
```

`uv sync` 會自動讀取 `pyproject.toml`，解析所有依賴項並安裝到 `.venv` 中。這是最簡單且最可靠的方法。

**方法 B：`uv pip install -e .`（替代方法）**

```bash
uv pip install -e .
```

以可編輯（開發）模式安裝專案。如果您需要更多安裝過程控制，請使用此方法。

> **差異：** `uv sync` 會自動建立/管理 `.venv`，並使用鎖定檔進行可重現的安裝。`uv pip install -e .` 安裝到現有虛擬環境中，不使用鎖定檔。

兩種方法都會：
- 安裝所有 Python 依賴項（包含 `pigpio`）
- 以可編輯模式設定機器人的所有函式庫
- 使所有 CLI 命令可用（`pi0vl53l0x`、`pi0servo` 等）

安裝可能需要 5-10 分鐘。

### 步驟 6.4：建置網頁介面

機器人的網頁介面是用 React 建置的。使用以下命令建置：

```bash
cd ninja_webapp
npm install
npm run build
cd ..
```

這會建立伺服器使用的 `ninja_webapp/dist/` 資料夾。

> [!NOTE]
> 如果 `npm install` 期間出現錯誤，請確保 Node.js 已正確安裝（步驟 4.6）。

### 步驟 6.5：驗證安裝

檢查主命令是否可用：

```bash
ninja_core --help
```

您應該會看到可用命令的清單，如 `chat`、`server`、`config` 等。

---

## 7. 硬體校準

在執行機器人之前，您需要校準伺服馬達並設定硬體。

### 步驟 7.1：設定蜂鳴器

告訴系統蜂鳴器連接到哪個 GPIO 腳位：

```bash
uv run pi0buzzer init 17
```

測試蜂鳴器：

```bash
uv run pi0buzzer beep
```

您應該會聽到一聲短促的嗶聲。

### 步驟 7.2：測試距離感測器

執行內建自我測試以確認感測器已正確連接且正常運作：

```bash
uv run pi0vl53l0x test
```

然後進行實際測量：

```bash
uv run pi0vl53l0x get --count 5 --interval 1.0
```

您應該會看到 5 個以毫米為單位的距離測量值。

檢查感測器狀態（韌體、偏移值、健康檢查）：

```bash
uv run pi0vl53l0x status
```

可選操作：將物體放置在已知距離（例如 100mm）處進行校準：

```bash
uv run pi0vl53l0x calibrate --distance 100 --count 10
```

### 步驟 7.3：校準伺服馬達

每個伺服馬達需要校準以定義其最小、中心和最大位置。

對於每個伺服馬達（以 GPIO 20 為例）：

```bash
uv run pi0servo calib 20
```

按照螢幕上的指示：
1. 按 `v` 選擇 **Min**（最小）位置
2. 使用 **上/下** 方向鍵進行大幅調整，**w/s** 進行微調
3. 當伺服馬達處於最小位置時，按 **Enter** 儲存
4. 按 `c` 選擇 **Center**（中心）位置，調整後按 **Enter**
5. 按 `x` 選擇 **Max**（最大）位置，調整後按 **Enter**
6. 按 `q` 退出

**對所有 8 個伺服馬達重複此操作**（GPIO 腳位：20 到 27）

### 步驟 7.4：匯入硬體設定

校準所有伺服馬達後，匯入設定：

```bash
uv run ninja_core config import
```

您應該會看到：
```
Found servo config at 'servo.json'. Importing...
Found buzzer config at 'buzzer.json'. Importing...
Configuration updated and saved to config.json!
```

### 步驟 7.5：設定 Gemini API 金鑰

使用您的 API 金鑰設定 AI 代理（將 `YOUR_API_KEY` 替換為實際金鑰）：

```bash
uv run ninja_core config set-key gemini YOUR_API_KEY
```

---

## 8. 功能測試

現在讓我們逐一測試每個元件。

### 測試 8.1：顯示器測試

首次設定（如果尚未完成）：

```bash
uv run pi0disp init
```

按提示配置顯示器的引腳和設定檔。

使用圖片測試 LCD 螢幕：

```bash
uv run pi0disp image assets/images/sample_face.jpg
```

您應該會在顯示器上看到圖片。

測試亮度控制：

```bash
uv run pi0disp brightness 50
uv run pi0disp brightness 100
```

測試文字顯示：

```bash
uv run pi0disp text "Hello NinjaRobot"
uv run pi0disp text "你好世界" --lang zh-tw --scroll
```

測試動畫：

```bash
uv run pi0disp demo --num-balls 3
```

按 **Ctrl+C** 停止。

檢查設定和健康狀態：

```bash
uv run pi0disp info --health-check
```

### 測試 8.2：伺服馬達動作測試

將伺服馬達移動到中心位置：

```bash
```bash
uv run pi0servo move 20 0
```

GPIO 20 上的伺服馬達應該移動到 0 度。

嘗試其他位置：

```bash
uv run pi0servo move 20 45
uv run pi0servo move 20 -- -45
uv run pi0servo cmd "20:X"
```

### 測試 8.3：聲音測試

播放旋律：

```bash
uv run pi0buzzer playmusic
```

### 測試 8.4：距離感測器性能

測量感測器速度：

```bash
uv run pi0vl53l0x performance --count 100
```

檢查感測器狀態和目前設定：

```bash
uv run pi0vl53l0x status
uv run pi0vl53l0x config show
```

### 測試 8.5：AI 代理測試（文字聊天）

在終端機模式下測試 AI 聊天：

```bash
uv run ninja_core chat
```

嘗試這些命令：
- `Hello`（機器人應該會問候您）
- `Show me a happy face`（顯示開心表情和聲音）
- `こんにちは`（以日語回應）
- `你好`（以中文回應）
- 輸入 `quit` 或按 **Ctrl+C** 退出

> [!NOTE]
> 機器人會持續監測距離，如果您靠得太近（<50mm）會做出反應。

---

## 9. 啟動機器人

### 啟動 Web 伺服器

這是與機器人互動的主要方式：

```bash
uv run ninja_core server
```

**首次執行時**，系統會提示您輸入 **ngrok authtoken**（來自步驟 5.2）。貼上並按 Enter。

機器人將會：
1. 初始化所有硬體
2. 啟動 Web 伺服器
3. 透過 ngrok 建立公開 URL
4. 在螢幕上顯示 QR 碼

### 存取 Web 介面

您有兩個選項：

#### 選項 A：掃描 QR 碼（建議）

使用手機掃描機器人螢幕上顯示的 QR 碼。這將在手機瀏覽器中開啟 Web 介面。

#### 選項 B：區域網路

在同一 WiFi 網路上的任何裝置上，開啟瀏覽器並前往：
```
http://ninjarobot.local:8000
```
（如果主機名稱不同，請替換 `ninjarobot`）

### Web 介面功能

連接後，您可以：

1. **與機器人聊天**：
   - 在文字方塊中輸入訊息
   - 或點擊 **麥克風圖示** 並說話（先選擇語言）
   - 機器人會以相同語言回應

2. **控制伺服馬達**：
   - 從下拉選單選擇動作
   - 點擊 **執行**

3. **顯示表情**：
   - 選擇表情（開心、難過等）
   - 點擊 **顯示**

4. **播放聲音**：
   - 選擇情緒聲音
   - 點擊 **播放**

5. **監測距離**：
   - 即時距離讀數顯示在頂部

### 支援的語言

- **English**（en-US）- 英語
- **日本語**（ja-JP）- 日語
- **繁體中文**（zh-TW）
- **简体中文**（zh-CN）- 簡體中文

### 停止伺服器

在終端機中按 **Ctrl+C** 停止伺服器。機器人將安全地關閉所有硬體。

---

## 10. 自動啟動（選用）

如果您希望機器人在開機時自動啟動，請按照以下步驟操作。

> [!IMPORTANT]
> **前提條件：** 確保您已完成所有先前步驟，包括硬體校準和 API 金鑰設定。在啟用自動啟動之前，機器人必須完全正常運作。
>
> **Ngrok 要求：** 要讓自動啟動運作，您**必須**設定有效的 ngrok authtoken。如果缺少 token，服務將無法啟動以避免在背景掛起。

### 步驟 10.1：安裝啟動服務

執行以下命令：

```bash
uv run ninja_utils install-startup
```

這將會：
1. 檢查您的系統是否準備就緒（config 存在、pigpiod 正在執行等）
2. 建立 systemd 服務檔案
3. 啟用服務以在開機時啟動

### 步驟 10.2：驗證

您可以檢查服務的狀態：

```bash
uv run ninja_utils status-startup
```

### 步驟 10.3：重新啟動

重新啟動您的 Raspberry Pi：

```bash
sudo reboot
```

機器人應該會自動啟動。一兩分鐘後，您可以透過 QR 碼或 `http://ninjarobot.local:8000` 存取 Web 介面。

> [!TIP]
> **安全關機：** 您可以使用 Web 介面底部的電源滑桿安全地關閉機器人。等待 Raspberry Pi 上的綠燈停止閃爍後再拔掉電源。

### 移除自動啟動

如果您想停止機器人自動啟動：

```bash
uv run ninja_utils remove-startup
```

---

## 11. 疑難排解

### 問題：「Could not connect to pigpiod daemon」

**解決方案**：
```bash
sudo pigpiod
```

然後再次嘗試執行您的命令。

### 問題：顯示器無法運作

**檢查項目**：
1. 驗證 SPI 已啟用：`sudo raspi-config` → Interface Options → SPI
2. 檢查接線是否與第 2 節的腳位表相符
3. 重新啟動：`sudo reboot`

### 問題：距離感測器沒有回應

**檢查項目**：
1. 驗證 I2C 已啟用：`sudo raspi-config` → Interface Options → I2C
2. 檢查感測器是否被偵測到：
   ```bash
   sudo i2cdetect -y 1
   ```
   輸出中應該會看到 `29` 或 `52`
3. 檢查接線（VCC 接 3.3V，不是 5V）
4. 執行內建診斷工具：
   ```bash
   uv run pi0vl53l0x test
   uv run pi0vl53l0x status
   ```
5. 如果狀態顯示錯誤，請將感測器電源重新啟動後再執行 `uv run pi0vl53l0x test`

### 問題：伺服馬達不動

**檢查項目**：
1. 確保外部 5V 電源已連接並開啟
2. 驗證 Pi 與伺服馬達電源之間的共用接地
3. 檢查伺服馬達訊號線連接
4. 重新校準伺服馬達：`uv run pi0servo calib <PIN>`

### 問題：「ImportError」或「ModuleNotFoundError」

**解決方案**：
重新安裝專案：
```bash
cd ~/NinjaRobotV5
uv pip install -e . --force-reinstall
```

### 問題：Web 伺服器無法啟動

**檢查項目**：
1. 確保連接埠 8000 沒有被佔用
2. 檢查 ngrok authtoken 是否正確設定
3. 使用詳細輸出重新啟動伺服器：
   ```bash
   uv run ninja_core server --log-level debug
   ```

### 問題：AI 代理沒有回應

**檢查項目**：
1. 驗證 Gemini API 金鑰已設定：
   ```bash
   cat config.json | grep gemini
   ```
2. 檢查網路連線
3. 重新設定 API 金鑰：
   ```bash
   uv run ninja_core config set-key gemini YOUR_KEY
   ```

### 取得更多協助

如果您遇到此處未涵蓋的問題：

1. 查看專案的 GitHub Issues 頁面
2. 查閱 `DevelopmentLog.md` 了解已知問題和修復
3. 確保所有接線與圖表完全相符
4. 執行個別元件測試（第 8 節）以隔離問題

---

## 後續步驟

- **錄製自訂動作**：使用 `uv run ninja_core movement-tool` 建立和儲存伺服馬達編排
- **自訂行為**：編輯 `config.json` 調整設定
- **製作外殼**：設計機器人外殼並安裝所有元件
- **探索程式碼**：查看 `ninja_core/README.md` 了解開發者文件

**恭喜！** 您的 NinjaRobot V5 現在已準備就緒。盡情探索和實驗您的 AI 機器人吧！🤖


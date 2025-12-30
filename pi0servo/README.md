# pi0servo

A library to control servo motors on a Raspberry Pi using the `pigpio` library.

## Features

- Control multiple servos.
- Calibrate servos interactively via a user-friendly CLI.
- Asynchronous, non-blocking control for smooth movements.

---

## V5 Changes

> [!NOTE]
> As of V5, this library implements the `Actuator` interface from `ninja_utils.interfaces`.

### Key Changes:
- **Implements `Actuator` ABC**: `initialize()`, `execute()`, `off()` methods.
- **Standardized commands**: `execute({"angles": [...]})` for batch control.

### Example (V5):
```python
from pi0servo.core.multi_servo import MultiServo
import pigpio

pi = pigpio.pi()
servos = MultiServo(pi=pi, pins=[20, 21, 22, 23, 24, 25, 26, 27])

servos.initialize()  # Centers all servos
servos.execute({"angles": [30, -30, 30, -30, 30, -30, 30, -30]})
servos.off()
pi.stop()
```

---

## Standalone Installation and Setup

This guide is for users who want to use the `pi0servo` library as a standalone package on a Raspberry Pi.

### 1. Hardware Prerequisites

- Raspberry Pi (Zero 2 W or better recommended)
- SG90 Servo Motor (or similar)
- Jumper Wires
- **Important:** An external 5V power supply for the servo(s). Powering more than one servo directly from the Pi can cause instability.

### 2. Hardware Connections

1.  **Connect the Servo:**
    *   **Signal Wire (Orange/Yellow):** Connect to a GPIO pin on the Raspberry Pi (e.g., GPIO 17).
    *   **Power Wire (Red):** Connect to the **positive (+)** terminal of your external 5V power supply.
    *   **Ground Wire (Brown/Black):** Connect to the **negative (-)** terminal of your external 5V power supply.

2.  **Connect the Pi to the Power Supply:**
    *   Connect a **Ground (GND)** pin from the Raspberry Pi to the **negative (-)** terminal of your external 5V power supply. This creates a common ground, which is essential for the signal to work correctly.

### 3. Software Prerequisites

On your Raspberry Pi, open a terminal and install the necessary system software.

1.  **Update System:**
    ```bash
    sudo apt-get update && sudo apt-get upgrade -y
    ```

2.  **Install Git, Python, and pip:**
    ```bash
    sudo apt-get install -y git python3-pip
    ```

3.  **Install `uv` (a fast Python package manager):**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

4.  **Install `pigpio` Library:**
    ```bash
    sudo apt-get install -y pigpio
    ```

### 4. Library Installation

1.  **Clone the Repository:**
    Clone this repository to your home directory.
    ```bash
    # Replace with the actual URL of your repository
    git clone <your-repository-url>
    cd pi0servo 
    ```

2.  **Install the Library:**
    Use `uv` to install `pi0servo` and its dependencies in editable mode.
    ```bash
    uv pip install -e .
    ```

### 5. Final Step: Start the `pigpio` Daemon

The `pigpio` library requires a background service (daemon) to be running. You must start it once after each reboot.

```bash
sudo pigpiod
```

You are now ready to use the library!

---

## Testing Guide

This guide walks you through testing the two main functionalities of the `pi0servo` library: direct servo movement and the interactive calibration tool.

**Prerequisites:**

1.  You have completed the standalone installation steps above.
2.  You have a servo motor connected to **GPIO 17**.
3.  The `pigpio` daemon is running (`sudo pigpiod`).

---

### Test 1: Direct Servo Movement

This test confirms that you can send basic commands to move the servo.

1.  **Move to Center:**
    Run the following command to move the servo to its default center position (0 degrees).

    ```bash
    uv run pi0servo servo 17 center
    ```
    *   **Expected Result:** The servo should quickly move to its middle position.

2.  **Move to Minimum:**
    Now, move the servo to its minimum position (-90 degrees).

    ```bash
    uv run pi0servo servo 17 min
    ```
    *   **Expected Result:** The servo should move to one end of its range of motion.

3.  **Move to Maximum:**
    Finally, move the servo to its maximum position (+90 degrees).

    ```bash
    uv run pi0servo servo 17 max
    ```
    *   **Expected Result:** The servo should move to the other end of its range of motion.

---

### Test 2: Interactive Calibration

This test walks you through using the interactive tool to fine-tune the servo's movement range and save the settings. This is crucial because not all servos are identical.

1.  **Start the Calibration Tool:**
    Run the following command to start the interactive calibration for the servo on GPIO 17.

    ```bash
    uv run pi0servo calib 17
    ```

2.  **Understand the Interface:**
    You will see an interactive prompt. The tool starts by targeting the **Center** position. Press **`h`** for a full list of commands.

    ```
    Calibration Tool: 'h' for help, 'q' for quit
    ...
    GPIO17 | Target: Center | pulse=1500>
    ```

3.  **Select a Target:**
    *   Use **`v`**, **`c`**, and **`x`** to directly select the **Min**, **Center**, or **Max** calibration targets.
    *   Alternatively, use **`Tab`** and **`Shift+Tab`** to cycle through the targets.

4.  **Adjust the Position:**
    *   Use the **Up and Down arrow keys** for large-step adjustments.
    *   Use the **`w`** and **`s`** keys for fine-tuning the position.

5.  **Save the Value:**
    *   Once the servo is in the perfect position for the selected target (Min, Center, or Max), press **`Enter`** or **`Space`** to save the value.

6.  **Repeat for All Targets:**
    *   Repeat steps 3-5 for all three targets (Min, Center, and Max) to complete the calibration.

7.  **Exit the Tool:**
    *   Press **`q`** to quit the calibration tool.

A `servo.json` file containing your calibration data will be created in the current directory. This file will be used by the `ninja_core` application in the next phase.

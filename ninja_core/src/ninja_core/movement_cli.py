import copy
import select
import subprocess
import sys
import termios
import time
import tty
from pathlib import Path

from ninja_core.config import (
    NinjaConfig,
    import_and_update_config,
    load_config,
    save_config,
)
from ninja_core.hal import HardwareAbstractionLayer
from ninja_core.movement_controller import MovementController


def parse_movement_command(
    command_str: str, definitions: dict
) -> tuple[str | None, dict | None]:
    """
    Parses the user's command string with optional per-servo speed.

    Format: [SPEED_]PIN:ANGLE[SPEED]/PIN:ANGLE[SPEED]...
    Examples:
        "22:45"           -> Medium speed, pin 22 to 45°
        "F_22:45/23:-30"  -> Fast global, multiple servos
        "22:45S/23:-30F"  -> Per-servo speeds (S=slow, F=fast)
        "F_22:45/23:-30S" -> Global fast, but pin 23 uses slow

    Returns a tuple: (global_speed, {pin: {"angle": value, "speed": str|None}}).
    """
    global_speed = "M"  # Default to Medium speed
    if command_str.startswith(("S_", "M_", "F_")):
        global_speed = command_str[0]
        command_str = command_str[2:]

    movements = {}
    parts = command_str.split("/")
    for part in parts:
        try:
            pin_str, value_part = part.split(":")
            pin = int(pin_str)
            # The keys in the definitions dict are strings
            if pin_str not in definitions:
                raise ValueError(f"Servo pin {pin} is not defined.")

            # Check for per-servo speed suffix (last character F/M/S)
            per_servo_speed = None
            if value_part and value_part[-1].upper() in ("F", "M", "S"):
                # Check if it's a speed suffix (not part of a number)
                if len(value_part) > 1 and not value_part[-2].isalpha():
                    per_servo_speed = value_part[-1].upper()
                    value_part = value_part[:-1]

            # Parse angle
            angle = 0
            if value_part.upper() == "X":
                angle = 90
            elif value_part.upper() == "M":
                angle = -90
            elif value_part.upper() == "C":
                angle = 0
            else:
                angle = int(value_part)
                if not -90 <= angle <= 90:
                    raise ValueError("Angle must be between -90 and 90.")

            movements[pin] = {"angle": angle, "speed": per_servo_speed}
        except ValueError as e:
            print(f"Error parsing '{part}': {e}")
            return None, None

    return global_speed, movements


def record_new_movement(controller: MovementController, config: NinjaConfig):
    """Handles the UI and logic for recording a new movement sequence."""
    print("\n--- Record New Movement ---")
    print("Commands: 'PIN:ANGLE[SPEED]/...' with optional global speed prefix.")
    print("Examples: 'F_22:45/23:-30'  or  '22:45S/23:-30F' (per-servo speeds)")

    servo_defs = controller.servo_definitions
    print("Available Servos (Pin):")
    for pin in servo_defs.keys():
        print(f"  - Pin {pin}")

    print("\nSetting all servos to center position to begin...")
    controller.center_all_servos()

    sequence = []
    previous_angles = controller.get_current_angles()

    while True:
        command_str = input("Enter servo movement command: ").strip()
        if not command_str:
            continue

        global_speed, moves = parse_movement_command(command_str, servo_defs)
        if not moves:
            continue

        all_servo_pins = servo_defs.keys()
        
        # Build completed moves: include all servos, using previous angles for missing
        completed_moves = {}
        for pin_str in all_servo_pins:
            pin = int(pin_str)
            if pin in moves:
                completed_moves[pin] = moves[pin]  # {angle, speed}
            else:
                previous_angle = previous_angles.get(pin, 0)
                completed_moves[pin] = {"angle": previous_angle, "speed": None}

        # Extract just angles for move_servos (it expects {pin: angle})
        angles_only = {pin: data["angle"] for pin, data in completed_moves.items()}

        print(f"Executing: {angles_only} with global speed {global_speed}")
        controller.move_servos(angles_only, global_speed)

        while True:
            choice = input(
                "1. Confirm & Next | 2. Reset | 3. Finish Recording: "
            ).strip()
            if choice == "1":
                # Store angles with global speed (per-servo speeds stored in moves)
                sequence.append({
                    "speed": global_speed,
                    "moves": angles_only,
                    "per_servo_speeds": {
                        pin: data["speed"]
                        for pin, data in completed_moves.items()
                        if data["speed"]
                    }
                })
                previous_angles = controller.get_current_angles()
                print("Movement step confirmed.")
                break
            elif choice == "2":
                print("Resetting to previous position...")
                controller.move_servos(previous_angles, "F")
                break
            elif choice == "3":
                sequence.append({
                    "speed": global_speed,
                    "moves": angles_only,
                    "per_servo_speeds": {
                        pin: data["speed"]
                        for pin, data in completed_moves.items()
                        if data["speed"]
                    }
                })
                print("Last movement step confirmed.")

                if not sequence:
                    print("No movements recorded. Aborting.")
                    return

                movement_name = input("Enter a name for this movement: ").strip()
                if not movement_name:
                    print("Name cannot be empty. Aborting save.")
                    controller.center_all_servos()
                    return

                # Correctly access and update the Pydantic model
                config.movements[movement_name] = sequence
                print(f"Movement '{movement_name}' saved!")
                controller.center_all_servos()
                return
            else:
                print("Invalid option.")


class NonBlockingKeyboard:
    """A class to handle non-blocking keyboard input."""

    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def kbhit(self):
        """Check if a key has been pressed."""
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    def getch(self):
        """Get the pressed character."""
        return sys.stdin.read(1)


def execute_movement_cli(controller: MovementController):
    """Handles the UI for executing a saved movement with looping."""
    print("\n--- Execute a Movement ---")
    all_movements = controller.movements
    if not all_movements:
        print("No movements have been recorded yet.")
        return

    print("Select a movement to execute:")
    names = list(all_movements.keys())
    for i, name in enumerate(names):
        print(f"{i + 1}. {name}")

    try:
        choice = int(input("Enter number: ")) - 1
        if not 0 <= choice < len(names):
            raise ValueError()
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    loop_input = (
        input("Enter number of times to loop, or 'loop' for infinite: ").strip().lower()
    )

    loop_count = 0
    infinite_loop = False
    if loop_input == "loop":
        infinite_loop = True
    else:
        try:
            loop_count = int(loop_input)
        except ValueError:
            print("Invalid input for loop count.")
            return

    selected_name = names[choice]
    print(f"Executing movement: '{selected_name}'...")
    print("Press Enter or Esc to interrupt.")
    controller.center_all_servos()

    interrupted = False
    with NonBlockingKeyboard() as nkb:
        loops_done = 0
        while infinite_loop or loops_done < loop_count:
            if nkb.kbhit():
                key = nkb.getch()
                if key == "\r" or key == "\x1b":  # Enter or Esc
                    interrupted = True
                    break
            controller.execute_movement(selected_name)
            if interrupted:
                break
            loops_done += 1

    if interrupted:
        print("\nMovement interrupted by user.")
    else:
        print(f"\nMovement '{selected_name}' finished.")

    time.sleep(1)
    controller.center_all_servos()


def edit_sequence_menu(
    controller: MovementController, sequence_to_edit: list
) -> list | None:
    """UI for editing a sequence. Operates on a copy."""
    temp_sequence = copy.deepcopy(sequence_to_edit)
    servo_defs = controller.servo_definitions

    try:
        while True:
            print("\n--- Editing Sequence ---")
            for i, step in enumerate(temp_sequence):
                print(f"Step {i + 1}: Speed={step['speed']}, Moves={step['moves']}")

            print(
                "\nOptions: 1. Edit Step | 2. Insert Step | 3. Delete Step | 4. Preview | 5. Save & Exit | 6. Abort"
            )
            edit_choice = input("Select an option: ").strip()

            # 1. Edit a step
            if edit_choice == "1":
                try:
                    step_num = int(input("Enter step number to edit: ")) - 1
                    if not 0 <= step_num < len(temp_sequence):
                        raise ValueError("Invalid step number.")

                    print(f"Current step: {temp_sequence[step_num]}")
                    command_str = input(
                        "Enter new movement command (e.g., 'S_17:30/27:C'): "
                    ).strip()
                    speed, moves = parse_movement_command(command_str, servo_defs)

                    if moves:
                        # Auto-complete the move based on previous step
                        completed_moves = moves.copy()
                        base_angles = (
                            temp_sequence[step_num - 1]["moves"]
                            if step_num > 0
                            else controller.get_current_angles()
                        )
                        for pin_str in servo_defs.keys():
                            pin = int(pin_str)
                            if pin not in completed_moves:
                                completed_moves[pin] = base_angles.get(
                                    str(pin), base_angles.get(pin, 0)
                                )

                        temp_sequence[step_num] = {
                            "speed": speed,
                            "moves": completed_moves,
                        }
                        print("Step updated.")

                except (ValueError, IndexError) as e:
                    print(f"Error: {e}")

            # 2. Insert a new step
            elif edit_choice == "2":
                try:
                    pos = (
                        int(
                            input(
                                f"Enter position to insert new step (1 to {len(temp_sequence) + 1}): "
                            )
                        )
                        - 1
                    )
                    if not 0 <= pos <= len(temp_sequence):
                        raise ValueError("Invalid position.")

                    command_str = input(
                        "Enter movement command for the new step: "
                    ).strip()
                    speed, moves = parse_movement_command(command_str, servo_defs)

                    if moves:
                        # Auto-complete based on the state before the insertion point
                        completed_moves = moves.copy()
                        base_angles = (
                            temp_sequence[pos - 1]["moves"]
                            if pos > 0
                            else controller.get_current_angles()
                        )
                        for pin_str in servo_defs.keys():
                            pin = int(pin_str)
                            if pin not in completed_moves:
                                completed_moves[pin] = base_angles.get(
                                    str(pin), base_angles.get(pin, 0)
                                )

                        temp_sequence.insert(
                            pos, {"speed": speed, "moves": completed_moves}
                        )
                        print("Step inserted.")

                except (ValueError, IndexError) as e:
                    print(f"Error: {e}")

            # 3. Delete a step
            elif edit_choice == "3":
                try:
                    step_num = int(input("Enter step number to delete: ")) - 1
                    if not 0 <= step_num < len(temp_sequence):
                        raise ValueError("Invalid step number.")

                    confirm = input(f"Delete Step {step_num + 1}? (y/n): ").lower()
                    if confirm == "y":
                        del temp_sequence[step_num]
                        print("Step deleted.")
                except (ValueError, IndexError) as e:
                    print(f"Error: {e}")

            # 4. Preview
            elif edit_choice == "4":
                print("Previewing sequence...")
                controller.center_all_servos()
                time.sleep(0.5)
                for i, step in enumerate(temp_sequence):
                    print(f"  - Step {i + 1}: {step['moves']}")
                    moves = {int(k): v for k, v in step["moves"].items()}
                    controller.move_servos(moves, step["speed"])
                print("Preview finished.")
                time.sleep(1)
                controller.center_all_servos()

            # 5. Finish and Save
            elif edit_choice == "5":
                print("Finishing and saving changes.")
                return temp_sequence

            # 6. Abort
            elif edit_choice == "6":
                print("Aborting without saving.")
                return None
            else:
                print("Invalid option.")

    except KeyboardInterrupt:
        print("\nModification cancelled. No changes were saved.")
        return None


def modify_existing_movement(controller: MovementController, config: NinjaConfig):
    """Handles the non-destructive modification of a movement sequence."""
    print("\n--- Modify Existing Movement ---")
    if not config.movements:
        print("No movements have been recorded yet.")
        return

    print("Select a movement to modify:")
    names = list(config.movements.keys())
    for i, name in enumerate(names):
        print(f"{i + 1}. {name}")

    try:
        choice = int(input("Enter number: ")) - 1
        if not 0 <= choice < len(names):
            raise ValueError()
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    selected_name = names[choice]
    original_sequence = config.movements[selected_name]

    print(f"\nLoading '{selected_name}' into the editor.")

    modified_sequence = edit_sequence_menu(controller, original_sequence)

    if modified_sequence is not None:
        config.movements[selected_name] = modified_sequence
        print(f"Successfully saved changes to '{selected_name}'.")
    else:
        print(f"No changes were made to '{selected_name}'.")


def clear_movement(controller: MovementController, config: NinjaConfig):
    """Handles clearing a movement sequence."""
    print("\n--- Clear Movement ---")
    if not config.movements:
        print("No movements have been recorded yet.")
        return

    print("Select a movement to clear:")
    names = list(config.movements.keys())
    for i, name in enumerate(names):
        print(f"{i + 1}. {name}")

    try:
        choice = int(input("Enter number: ")) - 1
        if not 0 <= choice < len(names):
            raise ValueError()
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    selected_name = names[choice]
    confirm = input(
        f"Are you sure you want to permanently delete '{selected_name}'? (y/n): "
    ).lower()
    if confirm == "y":
        del config.movements[selected_name]
        print(f"Movement '{selected_name}' has been deleted.")
    else:
        print("Deletion cancelled.")


def run_calibration(hal: HardwareAbstractionLayer):
    """
    Handles the servo calibration process by calling the external tool.
    Manages the hardware lifecycle (shutdown and re-initialization).
    """
    print("\n--- Calibrate a Servo ---")
    if not Path("servo.json").exists():
        print("Note: 'servo.json' not found. The calibration tool will create it.")

    # Check for servo config to get the list of pins
    if not hal.config.servos.calibration:
        print("No servos configured. Please run 'config import-all' first.")
        return

    pins = list(hal.config.servos.calibration.keys())
    print("Select a servo pin to calibrate:")
    for i, pin in enumerate(pins):
        print(f"{i + 1}. GPIO {pin}")

    try:
        choice = int(input("Enter number: ")) - 1
        if not 0 <= choice < len(pins):
            raise ValueError()
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    selected_pin = pins[choice]
    print(
        f"\nSelected GPIO {selected_pin}. Handing over to pi0servo calibration tool..."
    )
    print("Press 'q' in the tool to return here.")
    time.sleep(1)

    # Release hardware control before calling subprocess
    hal.shutdown()

    try:
        # Launch the external calibration tool
        subprocess.run(["uv", "run", "pi0servo", "calib", selected_pin])
    finally:
        # Re-acquire hardware control
        print("\nCalibration tool exited. Re-initializing hardware...")
        hal.initialize(components=["servos"])
        print("Hardware re-initialized.")


def run_cli():
    """Main entry point for the interactive movement CLI tool."""
    config = load_config()
    hal = HardwareAbstractionLayer(config)

    try:
        # Only initialize servos to prevent display/buzzer activation
        hal.initialize(components=["servos"])
        controller = MovementController(hal, config)

        while True:
            print("\n--- Servo Movement CLI Tool ---")
            print("1. Calibrate a Servo")
            print("2. Record new movement")
            print("3. Modify existing movement")
            print("4. Execute a movement")
            print("5. Clear movement")
            print("6. Exit")
            choice = input("Select an option: ")

            if choice == "1":
                run_calibration(hal)
                # Explicitly re-sync and reload everything to prevent stale objects
                print("\nSyncing calibration data to config.json...")
                import_and_update_config()
                config = load_config()
                controller = MovementController(hal, config)
                print("Controller has been updated with new calibration.")
            elif choice == "2":
                record_new_movement(controller, config)
            elif choice == "3":
                modify_existing_movement(controller, config)
            elif choice == "4":
                execute_movement_cli(controller)
            elif choice == "5":
                clear_movement(controller, config)
            elif choice == "6":
                break
            else:
                print("Invalid choice.")
    finally:
        hal.shutdown()
        # After CLI runs, save any potential changes made
        save_config(config)
        print("Configuration saved.")


if __name__ == "__main__":
    run_cli()

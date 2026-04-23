import click

from .config import import_and_update_config, set_api_key, set_robot_name

from .movement_cli import run_cli as run_movement_cli


@click.group()
def main():
    """Command-line interface for NinjaRobotV4 core application."""

    pass


@main.command("movement-tool")
def movement_tool():
    """Launch the interactive CLI tool for recording and editing servo movements."""

    run_movement_cli()


@main.group()
def config():
    """Manage the robot's configuration."""

    pass


@config.command("import-all")
@click.pass_context
def import_all(ctx):
    """
    Imports settings from hardware files (e.g., servo.json) into the main
    config.json, or applies defaults if files are missing.
    """
    import_and_update_config()


# Alias: 'import' -> 'import-all' for convenience
@config.command("import")
def import_config():
    """Alias for 'import-all'. Imports servo.json and buzzer.json into config.json."""
    import_and_update_config()


@config.command("set-key")
@click.argument("service")
@click.argument("key")
def set_key(service, key):
    """
    Set an API key for a service (e.g., gemini).

    Usage: ninja_core config set-key gemini YOUR_API_KEY
    """
    set_api_key(service, key)


@config.command("set-name")
@click.argument("name")
def set_name(name):
    """
    Set the BLE advertising name shown during Bluetooth discovery.

    Usage: ninja_core config set-name "Classroom Ninja 1"
    """
    set_robot_name(name)


@main.command("chat")
def chat():
    """
    Start an interactive text chat with the Ninja Agent.
    This initializes the robot hardware and allows you to type commands.
    """
    import asyncio
    import time
    import threading
    from .config import load_config
    from .hal import HardwareAbstractionLayer
    from .ninja_agent import NinjaAgent
    from .facial_expressions import AnimatedFaces
    from .robot_sound import RobotSoundPlayer
    from .perception import DistanceMonitor
    from .movement_controller import MovementController, EmergencyStop

    async def run_chat():
        print("Initializing NinjaRobot Hardware...")
        config = load_config()
        hal = HardwareAbstractionLayer(config)
        hal.initialize()
        
        # Initialize Distance Monitor
        distance_monitor = DistanceMonitor(hal)
        distance_monitor.start_continuous(interval=0.05)
        
        # Initialize Controllers (declare outside try for finally access)
        faces = None

        try:
            print("Initializing AI Agent...")
            agent = NinjaAgent(config)
            
            # Initialize Controllers
            faces = AnimatedFaces(hal)
            sound = RobotSoundPlayer(hal)
            movement = MovementController(hal, config)

            print("\n--- Ninja Agent Ready ---")
            print("Type 'exit' or 'quit' to stop.")
            
            # --- Welcome Greeting ---
            faces.play("happy", duration_s=3.0)
            print("Ninja: Hello! I am ready.")
            time.sleep(3.0)
            faces.play("idle", duration_s=float('inf'))
            # ------------------------

            # --- Safety Check Function ---
            last_reaction_time = 0.0
            
            def safety_check() -> bool:
                nonlocal last_reaction_time
                dist = distance_monitor.get_continuous_distance()
                vel = distance_monitor.get_velocity()
                
                # Display distance
                display_dist = dist if dist != -1 else "---"
                print(f"Dist: {display_dist}mm | Vel: {vel:.1f}mm/s   ", end="\r", flush=True)

                # Startle Response Check (Threshold 100mm)
                if distance_monitor.check_emergency_stop(distance_threshold=100):
                    current_time = time.time()
                    if current_time - last_reaction_time > 5.0:
                        last_reaction_time = current_time
                        print()
                        print(f"!!! STARTLE RESPONSE !!! Dist: {dist}mm, Vel: {vel:.2f}mm/s")
                        
                        # Reaction
                        if faces:
                            faces.play("scary", duration_s=2.0)
                        if sound:
                            sound.play("scary") # Blocking in main thread? No, sound.play IS blocking.
                            # We need to run sound in a thread here too or it blocks movement.
                            # But __main__ is sync. We can just let it block for a moment or use threading.
                            # The user said "do not stop servo movements".
                            # If sound.play blocks, servos might stutter if movement is interpolated.
                            # However, MovementController handles interpolation.
                            # But wait, sound.play IS blocking in robot_sound.py?
                            # Let's check robot_sound.py.
                            pass 

                        # We should probably run sound in bg thread if possible, 
                        # but robot_sound.play usually blocks. 
                        # For now, let's just trigger face and return False.
                        # If sound blocks, it stops servos. So we must put sound in thread.
                        threading.Thread(target=sound.play, args=("scary",), daemon=True).start()
                        
                    return False # Do not stop
                return False
            # -----------------------------
            
            while True:
                user_input = input("\nYou: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                print("Ninja is thinking...")
                result = await agent.process_command(user_input)
                
                action_plan = result["action_plan"]
                response_text = result["response"]
                
                # Execute Actions
                # Sound
                if (action_plan.get("sound_chain") or action_plan.get("sound")):
                    chain = action_plan.get("sound_chain", [])
                    if not chain and action_plan.get("sound"):
                        chain = [action_plan.get("sound")]
                    for name in chain:
                        sound.play(name)

                # Face (CLI doesn't run faces in background usually, but here we can)
                # For simplicity in CLI, we might just play the first or iterate blocking?
                # AnimatedFaces.play is non-blocking (starts thread).
                if (action_plan.get("face_chain") or action_plan.get("face")):
                    chain = action_plan.get("face_chain", [])
                    if not chain and action_plan.get("face"):
                        chain = [{"name": action_plan["face"], "duration": 2.0}]
                    
                    for item in chain:
                        name = item.get("name")
                        duration = item.get("duration")
                        faces.play(name)
                        if duration:
                            time.sleep(duration)
                
                if action_plan.get("chain") or action_plan.get("movement"):
                    try:
                        # Chain Logic
                        chain = action_plan.get("chain", [])
                        if not chain and action_plan.get("movement"):
                            chain = [{"name": action_plan["movement"], "repetitions": 1}]

                        for item in chain:
                            move_name = item["name"]
                            reps = item.get("repetitions", 1)
                            for _ in range(reps):
                                if safety_check():
                                     break
                                movement.execute_movement(move_name, abort_check=safety_check)
                    except EmergencyStop:
                        print("!!! OBSTACLE DETECTED - STOPPING !!!")
                        # Reaction: Frightened
                        if faces:
                            faces.play("scary")
                        if sound:
                            sound.play("scary")
                        print("Ninja: Whoa! Too close!")
                
                # Post-Task Reset
                if movement:
                    movement.center_all_servos()
                if faces:
                    faces.play("idle", float('inf'))

                print(f"Ninja: {response_text}")
                
                # --- Idle Status Management ---
                # Return to idle status 3 seconds after completion
                time.sleep(3.0)
                faces.play("idle", duration_s=float('inf'))
                # ------------------------------

        except Exception as e:
            print(f"\nError: {e}")
        finally:
            print("\nShutting down...")
            if faces:
                faces.stop()
            distance_monitor.stop_continuous()
            hal.shutdown()

    asyncio.run(run_chat())


@main.command("server")
@click.option("--autostart", is_flag=True, help="Run in autostart mode (non-interactive).")
def server(autostart):
    """
    Start the NinjaRobot Web Server.
    Provides a web interface for remote control and AI chat.
    """
    from .web_server import run_server
    run_server(autostart=autostart)


if __name__ == "__main__":
    main()

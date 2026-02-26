"""
Interactive Buzzer Tool — Menu-driven TUI for testing and configuration.

Provides a guided interface for all pi0buzzer functionality, matching
the pattern established by ``pi0disp display-tool`` and
``pi0vl53l0x sensor-tool``.

Usage::

    uv run pi0buzzer buzzer-tool
"""

import json
import time
from typing import Optional

import click

from pi0buzzer.config.config_manager import BuzzerConfigManager
from pi0buzzer.notes import DEMO_SONG, EMOTION_SOUNDS, get_emotion_names


def buzzer_tool(config_path: Optional[str] = None) -> None:
    """Launch the interactive buzzer tool.

    Args:
        config_path: Optional path to buzzer.json config file.
    """
    cm = BuzzerConfigManager(config_path)
    cm.load()

    # --- Connect to pigpio ---
    try:
        import pigpio
    except ImportError:
        click.echo("❌ pigpio is not installed.")
        click.echo("   Install with: pip install pigpio")
        return

    pi = pigpio.pi()
    if not pi.connected:
        click.echo("❌ Cannot connect to pigpiod.")
        click.echo("   Start it with: sudo pigpiod")
        return

    # --- Initialize buzzer ---
    try:
        from pi0buzzer.core.music import MusicBuzzer

        pin = cm.get_pin()
        volume = cm.get_volume()
        buzzer = MusicBuzzer(pin=pin, pi=pi, volume=volume)
        buzzer.initialize()

        click.echo(click.style("✓ Buzzer initialized", fg="green"))
        click.echo(click.style(f"  Pin: GPIO {pin}", fg="green"))
        click.echo(click.style(f"  Volume: {volume}/255", fg="green"))
        click.echo(click.style(f"  Config: {cm.path}", fg="green"))
    except Exception as e:
        click.echo(f"❌ Buzzer init failed: {e}")
        pi.stop()
        return

    # ==================================================================
    #  Menu functions
    # ==================================================================

    def show_menu():
        """Display the main menu."""
        click.echo()
        click.echo(click.style("╔══════════════════════════════════════════════════════════════╗", fg="cyan"))
        click.echo(click.style("║               pi0buzzer Interactive Tool                    ║", fg="cyan"))
        click.echo(click.style("╠══════════════════════════════════════════════════════════════╣", fg="cyan"))
        click.echo(click.style("║  1. Init          - Set up buzzer pin & save config         ║", fg="cyan"))
        click.echo(click.style("║  2. Beep          - Play a single tone (freq/duration)      ║", fg="cyan"))
        click.echo(click.style("║  3. Play Emotion  - Play an emotion sound by name           ║", fg="cyan"))
        click.echo(click.style("║  4. Play Music    - Interactive keyboard piano              ║", fg="cyan"))
        click.echo(click.style("║  5. Play Song     - Play the demo melody                   ║", fg="cyan"))
        click.echo(click.style("║  6. Volume        - Adjust buzzer volume                   ║", fg="cyan"))
        click.echo(click.style("║  7. Info          - Show config & health check              ║", fg="cyan"))
        click.echo(click.style("║  8. Config        - Show/export/import settings             ║", fg="cyan"))
        click.echo(click.style("║  9. Exit                                                    ║", fg="cyan"))
        click.echo(click.style("╚══════════════════════════════════════════════════════════════╝", fg="cyan"))

    def do_init():
        """Initialize buzzer pin configuration."""
        nonlocal buzzer, pin
        new_pin = click.prompt("\nGPIO pin for buzzer", type=int, default=pin)
        try:
            cm.set_pin(new_pin)
            cm.save()
            click.echo(f"  ✓ Config saved (pin={new_pin})")

            # Reinitialize buzzer with new pin
            buzzer.off()
            buzzer = MusicBuzzer(pin=new_pin, pi=pi, volume=cm.get_volume())
            buzzer.initialize()
            pin = new_pin

            # Test beep
            click.echo("  Playing test beep...")
            buzzer.play_sound(440, 0.3)
            time.sleep(0.5)
            click.echo("  ✓ Test beep successful!")
        except ValueError as e:
            click.echo(f"  ✗ Invalid pin: {e}")
        except Exception as e:
            click.echo(f"  ✗ Error: {e}")

    def do_beep():
        """Play a single tone with custom frequency and duration."""
        freq = click.prompt("\nFrequency (Hz)", type=int, default=440)
        dur = click.prompt("Duration (seconds)", type=float, default=0.5)

        click.echo(f"  Playing {freq} Hz for {dur}s...")
        buzzer.play_sound(freq, dur)
        time.sleep(dur + 0.1)
        click.echo("  ✓ Done")

    def do_play_emotion():
        """Show emotion list and play selected emotion."""
        emotions = get_emotion_names()
        click.echo("\nAvailable emotions:")
        for i, name in enumerate(emotions, 1):
            notes_count = len(EMOTION_SOUNDS[name])
            click.echo(f"  {i:2d}. {name:<15s} ({notes_count} notes)")

        try:
            choice = click.prompt("\nSelect emotion (number or name)", type=str)

            # Accept number or name
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(emotions):
                    emotion = emotions[idx]
                else:
                    click.echo("  ✗ Invalid number")
                    return
            elif choice in emotions:
                emotion = choice
            else:
                click.echo(f"  ✗ Unknown emotion: {choice}")
                return

            click.echo(f"  Playing: {emotion}")
            buzzer.play_emotion(emotion)
            time.sleep(2.0)
            click.echo("  ✓ Done")
        except (EOFError, KeyboardInterrupt):
            pass

    def do_play_music():
        """Launch interactive keyboard piano mode."""
        click.echo("\n🎹 Launching keyboard piano...")
        click.echo("  (Type note keys, 'quit' to return)\n")
        buzzer.play_music()

    def do_play_song():
        """Play the built-in demo melody."""
        click.echo("\n🎵 Playing demo: Twinkle Twinkle Little Star")
        buzzer.play_demo()

        # Calculate total duration
        total_dur = sum(d for _, d in DEMO_SONG) + 0.5
        time.sleep(total_dur)
        click.echo("  ✓ Song complete")

    def do_volume():
        """Adjust buzzer volume."""
        current = buzzer.volume
        click.echo(f"\nCurrent volume: {current}/255 ({current * 100 // 255}%)")

        percent = click.prompt("New volume (0-100%)", type=int, default=current * 100 // 255)
        new_vol = max(0, min(255, percent * 255 // 100))

        buzzer.volume = new_vol
        cm.set_volume(new_vol)
        cm.save()

        click.echo(f"  ✓ Volume set to {new_vol}/255 ({percent}%)")

        # Play confirmation beep
        buzzer.play_sound(440, 0.2)
        time.sleep(0.3)

    def do_info():
        """Show config and optionally run health check."""
        cfg = cm.config
        click.echo("\n📋 Buzzer Info:")
        click.echo(f"  Config file: {cm.path}")
        click.echo(f"  Pin:         GPIO {cfg.get('pin', 'N/A')}")
        click.echo(f"  Volume:      {cfg.get('volume', 'N/A')}/255")
        click.echo(f"  Initialized: {buzzer.is_initialized}")
        click.echo(f"  pigpio:      {'Connected' if pi.connected else 'Disconnected'}")

        if click.confirm("\nRun health check?", default=True):
            click.echo("  Testing beep...")
            buzzer.play_sound(440, 0.2)
            time.sleep(0.4)
            click.echo("  ✓ Health check passed")

    def do_config():
        """Config management submenu."""
        click.echo("\n  1. Show config")
        click.echo("  2. Export config")
        click.echo("  3. Import config")

        try:
            choice = click.prompt("  Choice", type=int, default=1)
        except (EOFError, KeyboardInterrupt):
            return

        if choice == 1:
            cfg = cm.config
            click.echo("\n" + json.dumps(cfg, indent=2))
        elif choice == 2:
            path = click.prompt("Export path", type=str)
            try:
                cm.export_config(path)
                click.echo(f"  ✓ Exported to {path}")
            except Exception as e:
                click.echo(f"  ✗ Export failed: {e}")
        elif choice == 3:
            path = click.prompt("Import path", type=str)
            try:
                cm.import_config(path)
                cm.save()
                buzzer.volume = cm.get_volume()
                click.echo(f"  ✓ Imported from {path}")
            except FileNotFoundError:
                click.echo(f"  ✗ File not found: {path}")
            except Exception as e:
                click.echo(f"  ✗ Import failed: {e}")

    # ==================================================================
    #  Main loop
    # ==================================================================

    show_menu()

    while True:
        try:
            choice = click.prompt("\nSelect an option", type=int, default=9)
        except (EOFError, KeyboardInterrupt):
            click.echo("\nExiting.")
            break

        if choice == 1:
            do_init()
        elif choice == 2:
            do_beep()
        elif choice == 3:
            do_play_emotion()
        elif choice == 4:
            do_play_music()
        elif choice == 5:
            do_play_song()
        elif choice == 6:
            do_volume()
        elif choice == 7:
            do_info()
        elif choice == 8:
            do_config()
        elif choice == 9:
            click.echo("Goodbye!")
            break
        else:
            click.echo("Invalid choice. Please enter 1-9.")

    # Cleanup
    buzzer.off()
    pi.stop()

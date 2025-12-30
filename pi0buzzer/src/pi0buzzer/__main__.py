import click
import pigpio
import json
import time
from .driver import Buzzer, MusicBuzzer


@click.group()
def cli():
    pass


@cli.command()
@click.argument('pin', type=int)
def init(pin):
    """Initializes the buzzer on the specified GPIO pin."""
    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException("Could not connect to pigpio daemon. Is it running?")
    
    # Save the pin to config file
    with open('buzzer.json', 'w') as f:
        json.dump({'pin': pin}, f)

    buzzer = Buzzer(pin, pi)
    buzzer.initialize()  # V5: Must call initialize to start worker thread
    buzzer.off()
    pi.stop()
    click.echo(f"Buzzer initialized on GPIO {pin} and config saved to buzzer.json")


@cli.command()
@click.option('--pin', type=int, default=None, help='GPIO pin for the buzzer. Reads from buzzer.json if not provided.')
@click.argument('frequency', type=float, default=440.0)
@click.argument('duration', type=float, default=0.5)
def beep(pin, frequency, duration):
    """Plays a simple beep."""
    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException("Could not connect to pigpio daemon. Is it running?")

    if pin is None:
        try:
            with open('buzzer.json', 'r') as f:
                config = json.load(f)
                pin = config['pin']
        except FileNotFoundError:
            raise click.ClickException("Buzzer not initialized. Please run 'pi0buzzer init <pin>' first or specify a pin with --pin.")

    buzzer = Buzzer(pin, pi)
    buzzer.initialize()  # V5: Must call initialize to start worker thread
    click.echo(f"Beeping at {frequency} Hz for {duration}s...")
    buzzer.play_sound(frequency, duration)
    time.sleep(duration + 0.1)  # Wait for sound to finish (non-blocking playback)
    buzzer.off()
    pi.stop()


@cli.command()
@click.option('--pin', type=int, default=None, help='GPIO pin for the buzzer')
def playmusic(pin):
    """Play music with the buzzer using the keyboard."""
    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException("Could not connect to pigpio daemon. Is it running?")

    if pin is None:
        try:
            with open('buzzer.json', 'r') as f:
                config = json.load(f)
                pin = config['pin']
        except FileNotFoundError:
            raise click.ClickException("Buzzer not initialized. Please run 'pi0buzzer init <pin>' first or specify a pin with --pin.")

    music_buzzer = MusicBuzzer(pin, pi)
    music_buzzer.initialize()  # V5: Must call initialize to start worker thread
    music_buzzer.play_music()
    music_buzzer.off()
    pi.stop()


if __name__ == '__main__':
    cli()

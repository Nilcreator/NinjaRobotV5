"""Info command — Display driver state and configuration."""

import click


@click.command()
def info():
    """Show display driver state and current configuration."""
    from ..config.config_manager import DISPLAY_PROFILES, ConfigManager

    cm = ConfigManager()
    cfg = cm.load()

    profile_key = cfg.get("display_profile", "st7789v_2inch8")
    profile = DISPLAY_PROFILES.get(profile_key, {})
    profile_name = profile.get("name", profile_key)

    click.echo()
    click.echo(click.style("╔══════════════════════════════════════════════════════════════╗", fg="cyan"))
    click.echo(click.style("║               pi0disp — Display Information                  ║", fg="cyan"))
    click.echo(click.style("╚══════════════════════════════════════════════════════════════╝", fg="cyan"))
    click.echo()
    click.echo(f"  Display:     {profile_name}")
    click.echo(f"  Resolution:  {cfg.get('width', 240)} × {cfg.get('height', 320)}")
    click.echo(f"  Rotation:    {cfg.get('rotation', 0)}°")
    click.echo(f"  Brightness:  {cfg.get('brightness', 100)}%")
    click.echo(f"  SPI Speed:   {cfg.get('spi_speed_mhz', 32)} MHz")
    click.echo()
    click.echo(click.style("  GPIO Pins:", bold=True))
    click.echo(f"    DC:        BCM {cfg.get('dc_pin', 14)}")
    click.echo(f"    RST:       BCM {cfg.get('rst_pin', 15)}")
    click.echo(f"    BLK:       BCM {cfg.get('backlight_pin', 16)}")
    click.echo()
    click.echo(f"  Config:      {cm.config_path}")
    click.echo()

    # Try to check hardware status
    try:
        import pigpio

        from ..core.driver import ST7789V

        pi = pigpio.pi()
        if pi.connected:
            lcd = ST7789V(
                pi=pi,
                dc_pin=cfg.get("dc_pin", 14),
                rst_pin=cfg.get("rst_pin", 15),
                backlight_pin=cfg.get("backlight_pin", 16),
                width=cfg.get("width", 240),
                height=cfg.get("height", 320),
                rotation=cfg.get("rotation", 0),
            )
            health = lcd.health_check()
            status = click.style("✅ Connected", fg="green") if health else click.style("❌ Error", fg="red")
            click.echo(f"  Hardware:    {status}")
            lcd.close()
        else:
            click.echo(f"  Hardware:    {click.style('⚠️  pigpio not connected', fg='yellow')}")
    except ImportError as e:
        click.echo(f"  Hardware:    {click.style(f'ℹ️  {e} (install pigpio on RPi)', fg='blue')}")
    except Exception as e:
        click.echo(f"  Hardware:    {click.style(f'❌ {e}', fg='red')}")

    click.echo()

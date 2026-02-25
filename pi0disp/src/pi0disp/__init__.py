"""pi0disp — ST7789V display driver with smart delta rendering."""

from .config.config_manager import ConfigManager
from .core.driver import ST7789V

__all__ = ["ST7789V", "ConfigManager"]
__version__ = "2.0.0"

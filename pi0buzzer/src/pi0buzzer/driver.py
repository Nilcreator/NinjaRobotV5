"""
Compatibility shim — ensures ``from pi0buzzer.driver import MusicBuzzer`` works.

ninja_core/hal.py loads the buzzer driver via:

    DRIVER_REGISTRY = {
        "buzzer": {
            "module": "pi0buzzer.driver",
            "class": "MusicBuzzer",
        },
    }

This file re-exports from the new module paths so that existing code
continues to work without any changes to ninja_core.
"""

from pi0buzzer.core.driver import Buzzer
from pi0buzzer.core.music import MusicBuzzer

__all__ = ["Buzzer", "MusicBuzzer"]

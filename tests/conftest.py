from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    ROOT / "ninja_core" / "src",
    ROOT / "ninja_ble" / "src",
    ROOT / "ninja_utils" / "src",
    ROOT / "pi0buzzer" / "src",
)

for source_path in SOURCE_PATHS:
    source_str = str(source_path)
    if source_str not in sys.path:
        sys.path.insert(0, source_str)

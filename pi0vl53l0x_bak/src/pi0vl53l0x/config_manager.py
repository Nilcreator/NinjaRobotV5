import json
from pathlib import Path
from typing import Any, cast

CONFIG_FILE_NAME = "vl53l0x.json"

def get_default_config_filepath() -> Path:
    """
    デフォルトの設定ファイルのパスを返します。
    例: ~/vl53l0x.json
    """
    home_dir = Path.home()
    return home_dir / CONFIG_FILE_NAME

def load_config(filepath: Path) -> dict[str, Any]:
    """
    指定されたパスから設定ファイルを読み込みます。
    """
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))

def save_config(filepath: Path, config: dict[str, Any]) -> None:
    """
    指定されたパスに設定ファイルを保存します。
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

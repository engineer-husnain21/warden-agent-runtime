import tomllib
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[3] / ".streamlit" / "config.toml"


def test_theme_config_when_loaded_is_dark_with_one_accent_and_custom_font() -> None:
    theme = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["theme"]

    assert theme["base"] == "dark"
    assert theme["primaryColor"].startswith("#")
    assert theme["font"].startswith("Inter:https://fonts.googleapis.com/")

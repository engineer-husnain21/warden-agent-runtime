import re
import tomllib
from pathlib import Path

from web import theme
from web.console_styles import build_styles

CONFIG = Path(__file__).resolve().parents[3] / ".streamlit" / "config.toml"
HEX = re.compile(r"^#[0-9A-F]{6}$")


def test_theme_when_loaded_every_kind_and_status_has_a_hex_colour() -> None:
    for kind in ("plan", "tool_selection", "permission_check", "approval", "tool_call", "review"):
        assert HEX.match(theme.kind_color(kind))
    for status in ("pending", "running", "awaiting_approval", "completed", "failed"):
        assert HEX.match(theme.status_color(status))


def test_theme_when_unknown_kind_or_status_falls_back_to_muted() -> None:
    assert theme.kind_color("mystery") == theme.MUTED
    assert theme.status_color("mystery") == theme.MUTED


def test_theme_when_compared_with_streamlit_config_uses_same_accent_and_surfaces() -> None:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["theme"]

    assert config["primaryColor"] == theme.INDIGO
    assert config["backgroundColor"] == theme.BACKGROUND
    assert config["secondaryBackgroundColor"] == theme.SURFACE


def test_build_styles_when_called_exposes_palette_as_css_variables() -> None:
    styles = build_styles()

    assert f"--w-indigo: {theme.INDIGO};" in styles
    assert f"--w-amber: {theme.AMBER};" in styles

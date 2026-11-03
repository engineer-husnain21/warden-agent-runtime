"""The console's CSS. Colours come from web/theme.py as CSS variables, so the palette lives in
one place; the rules below only refer to `var(--w-...)`."""

from web import theme

_PALETTE = {
    "background": theme.BACKGROUND,
    "surface": theme.SURFACE,
    "border": theme.BORDER,
    "text": theme.TEXT,
    "muted": theme.MUTED,
    "indigo": theme.INDIGO,
    "purple": theme.PURPLE,
    "pink": theme.PINK,
    "blue": theme.BLUE,
    "cyan": theme.CYAN,
    "teal": theme.TEAL,
    "green": theme.GREEN,
    "amber": theme.AMBER,
    "red": theme.RED,
}

_RULES = """
.warden-header { display: flex; align-items: baseline; gap: 0.9rem; flex-wrap: wrap;
  padding: 1.1rem 1.5rem; margin-bottom: 1rem; border-radius: 0.9rem;
  background: linear-gradient(115deg, var(--w-indigo) 0%, var(--w-purple) 55%, var(--w-pink) 100%);
  box-shadow: 0 8px 30px color-mix(in srgb, var(--w-purple) 30%, transparent); }
.warden-header .brand { font-size: 2.1rem; font-weight: 800; letter-spacing: -0.03em;
  line-height: 1; color: #FFFFFF; }
.warden-header .tagline { color: rgba(255, 255, 255, 0.85); font-size: 1rem; font-weight: 500; }
.warden-pill { display: inline-block; padding: 0.1rem 0.6rem; border-radius: 999px;
  font-size: 0.78rem; font-weight: 600; white-space: nowrap;
  color: var(--pill); background: color-mix(in srgb, var(--pill) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--pill) 40%, transparent); }
.w-metric-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.9rem; margin: 0.5rem 0 1.25rem; }
.w-metric { display: flex; align-items: center; gap: 0.85rem; padding: 0.95rem 1.1rem;
  border-radius: 0.85rem;
  background: linear-gradient(135deg, color-mix(in srgb, var(--c) 24%, transparent),
    color-mix(in srgb, var(--c) 5%, transparent));
  border: 1px solid color-mix(in srgb, var(--c) 50%, transparent);
  box-shadow: 0 0 22px color-mix(in srgb, var(--c) 22%, transparent); }
.w-metric-icon { flex: none; width: 2.5rem; height: 2.5rem; border-radius: 0.65rem;
  display: flex; align-items: center; justify-content: center; color: var(--c);
  background: color-mix(in srgb, var(--c) 20%, transparent); }
.w-metric-icon svg { width: 1.35rem; height: 1.35rem; }
.w-metric-label { color: var(--w-muted); font-size: 0.8rem; font-weight: 500; }
.w-metric-value { font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em;
  line-height: 1.2; color: var(--w-text); }
.warden-timeline { position: relative; margin: 0.25rem 0 1rem 0.9rem; padding-left: 1.6rem;
  border-left: 1px solid var(--w-border); }
.warden-timeline .tl-item { position: relative; margin-bottom: 0.7rem; padding: 0.55rem 0.9rem;
  border-left: 3px solid var(--k); border-radius: 0 0.6rem 0.6rem 0;
  background: linear-gradient(90deg, color-mix(in srgb, var(--k) 14%, transparent),
    transparent 75%); }
.warden-timeline .tl-icon { position: absolute; left: calc(-2.5rem - 3px); top: 0.45rem;
  width: 1.8rem; height: 1.8rem; display: flex; align-items: center; justify-content: center;
  border-radius: 999px; font-size: 0.9rem; border: 1px solid var(--k);
  background: color-mix(in srgb, var(--k) 25%, var(--w-surface));
  box-shadow: 0 0 12px color-mix(in srgb, var(--k) 45%, transparent); }
.warden-timeline .tl-title { font-weight: 600; display: flex; align-items: center;
  gap: 0.5rem; flex-wrap: wrap; }
.warden-timeline .tl-tool { font-family: 'JetBrains Mono', monospace; font-weight: 500;
  font-size: 0.82rem; color: var(--w-indigo); }
.warden-timeline .tl-meta { color: var(--w-muted); font-size: 0.82rem; margin-top: 0.15rem; }
"""


def build_styles() -> str:
    variables = "".join(f"--w-{name}: {value}; " for name, value in _PALETTE.items())
    return f"<style>\n:root {{ {variables}}}\n{_RULES}</style>"

"""Page chrome shared by every console page: page config, styles and the Warden header."""

import streamlit as st

BRAND = "Warden"
TAGLINE = "Governed AI agents"

_STYLES = """
<style>
.warden-header { display: flex; align-items: baseline; gap: 0.75rem;
  padding: 0.25rem 0 0.75rem; margin-bottom: 0.5rem; border-bottom: 1px solid #262A33; }
.warden-header .brand { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }
.warden-header .brand::before { content: ""; display: inline-block; width: 0.6rem; height: 0.6rem;
  margin-right: 0.5rem; border-radius: 0.15rem; background: #6E7BF2; }
.warden-header .tagline { color: #8A90A0; font-size: 0.9rem; }
</style>
"""


def setup_page(title: str) -> None:
    """Call first on every page: sets the tab title and draws the shared header."""
    st.set_page_config(page_title=f"{title} · {BRAND}", page_icon="🛡️", layout="wide")
    st.markdown(_STYLES, unsafe_allow_html=True)
    st.markdown(
        f'<div class="warden-header"><span class="brand">{BRAND}</span>'
        f'<span class="tagline">{TAGLINE}</span></div>',
        unsafe_allow_html=True,
    )

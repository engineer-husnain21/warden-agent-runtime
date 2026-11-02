"""Shared console setup: the API key in the sidebar and the API client for the current session."""

import streamlit as st

from web.api_client import WardenApiClient
from web.console_settings import ConsoleSettings

CLIENT_KEY = "api_client"


def render_sidebar() -> None:
    settings = ConsoleSettings()
    st.sidebar.title("Warden")
    st.sidebar.caption(f"API: {settings.api_url}")
    st.sidebar.text_input("API key", value=settings.api_key, type="password", key="api_key_input")


def get_api_client() -> WardenApiClient:
    """The client for this session. Tests put a fake under `api_client` in session_state."""
    existing = st.session_state.get(CLIENT_KEY)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings = ConsoleSettings()
    api_key = (st.session_state.get("api_key_input") or settings.api_key).strip()
    return WardenApiClient(settings.api_url, api_key, settings.timeout_seconds)

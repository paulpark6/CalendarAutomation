import time
import streamlit as st
from streamlit_autorefresh import st_autorefresh
# Only keep what we actually use now.
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from project_code.auth import *
from streamlit_app import ui

# --- Idle / timeout configuration ---
TIMEOUT_SECS = 2 * 60 * 60        # hard auto-logout at 2 hours
HEARTBEAT_MS = 15_000             # refresh every 15s to detect idle & show modal


def _touch_activity():
    """
    Record 'last activity' as now.
    Call this from user actions (login, switching pages, major buttons).
    """
    st.session_state["last_activity_ts"] = time.time()


def _do_logout(reason: str = "manual"):
    """
    Revoke token, clear session, and rerun the app.
    NOTE: logout_and_delete_token will best-effort revoke with Google.
    """
    logout_and_delete_token(st.session_state.get("credentials"))

    # Clear all auth-related session state
    for k in ["service", "credentials", "user_email", "calendars", "active_calendar"]:
        st.session_state.pop(k, None)

    # Remember why we logged out (optional banner UX)
    st.session_state["logout_reason"] = reason

    st.rerun()


def _seconds_idle() -> float | None:
    """Return seconds since last activity, or None if never set."""
    ts = st.session_state.get("last_activity_ts")
    return None if not ts else (time.time() - ts)


def _maybe_timeout_logout():
    """
    If idle >= TIMEOUT_SECS → logout immediately.
    Guarded by presence of a logged-in service.
    """
    if st.session_state.get("service") is None:
        return
    idle = _seconds_idle()
    if idle is None:
        return
    if idle >= TIMEOUT_SECS:
        _do_logout("timeout")


def main():
    st.set_page_config(page_title="Calendar Automation", page_icon="📅", layout="wide")

    # --- Session defaults ---
    st.session_state.setdefault("service", None)
    st.session_state.setdefault("credentials", None)
    st.session_state.setdefault("user_email", None)
    st.session_state.setdefault("last_activity_ts", None)

    # --- Login gate (UI now owns OAuth flow) ---

    svc = st.session_state.get("service")
    creds = st.session_state.get("credentials")

    def _has_usable_token(c):
        return bool(c and getattr(c, "token", None))

    if svc is None or not _has_usable_token(creds):
        # Optional one-shot notice if prior run logged out due to timeout
        if st.session_state.pop("logout_reason", None) == "timeout":
            st.warning("You were logged out due to 2 hours of inactivity.")

        # This renders the Google link or completes the redirect
        ui.show_login_page()

        # CRITICAL: stop here so the rest of the app doesn't render
        st.stop()
    # always take creds from session
    creds = st.session_state.get("credentials")
    if creds is None:
        st.error("Auth problem: no credentials in session.")
        st.stop()

    # If token is expired and we have a refresh_token, refresh now and rebind service
    if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        try:
            creds.refresh(Request())
            st.session_state["credentials"] = creds
            st.session_state["service"] = build_calendar_service(creds)
            st.sidebar.success("Access token refreshed")
        except Exception as e:
            st.sidebar.error(f"Token refresh failed: {e}")
            st.stop()

    # use the (possibly refreshed) service
    service = st.session_state["service"]

    try:
        user_email = assert_service_has_identity(service)  # calls userinfo with the same token
        st.session_state["user_email"] = user_email
        # st.sidebar.info(f"Signed in as {user_email}") # Sidebar is minimal now
    except AssertionError as e:
        st.sidebar.error(f"Auth problem: {e}")
        st.stop()

    # Seed the idle timer on first page after login
    if st.session_state.get("last_activity_ts") is None:
        _touch_activity()

    # 1) Heartbeat: light auto-refresh so idle modal/timeout can appear without user clicks
    st_autorefresh(interval=HEARTBEAT_MS, key="idle_heartbeat")

    # 2) Check for hard timeout first (logs out if exceeded)
    _maybe_timeout_logout()

    # 3) Layout Implementation
    _touch_activity() # Any interaction refreshes activity

    # Top Bar (minimal)
    c_top1, c_top2 = st.columns([0.8, 0.2])
    with c_top1:
        st.title("Calendar Agent 📅")
    with c_top2:
        if st.button("Log out", key="top_logout"):
            _do_logout("manual")

    # 3-Column Dashboard
    # Left: Chat/Input (25%)
    # Mid: Calendar (50%)
    # Right: Tasks/Info (25%)
    
    col_left, col_mid, col_right = st.columns([0.25, 0.50, 0.25], gap="medium")

    with col_left:
        ui.render_chat_column(service)

    with col_mid:
        ui.render_calendar_column(service)

    with col_right:
        ui.render_right_column(service)

    # 4) Bottom / Full width specific tools
    # We place the data entry/validation table here as it needs width
    ui.render_event_loader_section(service)


if __name__ == "__main__":
    main()

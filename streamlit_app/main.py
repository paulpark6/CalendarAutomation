import time
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Only keep what we actually use now.
from project_code.auth import logout_and_delete_token
import streamlit_app.ui as ui

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
    st.session_state.setdefault("nav", "Home")
    st.session_state.setdefault("last_activity_ts", None)

    # --- Login gate (UI now owns OAuth flow) ---
    if st.session_state.get("service") is None:
        # Optional one-shot notice if prior run logged out due to timeout
        if st.session_state.pop("logout_reason", None) == "timeout":
            st.warning("You were logged out due to 2 hours of inactivity.")

        # This renders the Google link or completes the redirect
        ui.show_login_page()

        # CRITICAL: stop here so the rest of the app doesn't render
        st.stop()

    # --- Logged-in flow ---
    service = st.session_state.service

    # Seed the idle timer on first page after login
    if st.session_state.get("last_activity_ts") is None:
        _touch_activity()

    # 1) Heartbeat: light auto-refresh so idle modal/timeout can appear without user clicks
    st_autorefresh(interval=HEARTBEAT_MS, key="idle_heartbeat")

    # 2) Check for hard timeout first (logs out if exceeded)
    _maybe_timeout_logout()

    # 3) Sidebar nav (count page switch as activity)
    with st.sidebar:
        st.markdown("### 📚 Navigation")
        current = st.session_state.get("nav", "Home")

        page = st.radio(
            label="",
            options=["Home", "Event Builder", "Settings"],
            index=["Home", "Event Builder", "Settings"].index(current),
            key="nav_radio",
        )

        # Switching pages counts as activity
        if page != current:
            _touch_activity()
        st.session_state.nav = page

        # Manual logout
        if st.button("Log out", type="secondary", key="sidebar_logout"):
            _do_logout("manual")

    # 4) Render pages (sprinkle _touch_activity() inside important actions if needed)
    if page == "Home":
        ui.show_home(service)
    elif page == "Event Builder":
        ui.show_event_builder(service)
    else:
        ui.show_settings(service)


if __name__ == "__main__":
    main()

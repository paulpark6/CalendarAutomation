"""
LazyCal - Calendar Agent Main Entry Point

This is the app's entry point. It handles:
1. Authentication (OAuth with Google)
2. Redirecting to login or main app
3. Session management
"""

import time
import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from project_code.auth import web_exchange_code, build_calendar_service, logout_and_delete_token
from google.auth.transport.requests import Request
from streamlit_app import ui


# ============================================================================
# SESSION DEFAULTS
# ============================================================================

st.set_page_config(page_title="LazyCal - Calendar Agent", page_icon="📅", layout="wide")

st.session_state.setdefault("service", None)
st.session_state.setdefault("credentials", None)
st.session_state.setdefault("user_email", None)


# ============================================================================
# OAUTH CALLBACK HANDLER
# ============================================================================

if "code" in st.query_params:
    """
    User was redirected from Google OAuth with authorization code.
    Exchange code for credentials and save to session.
    """
    try:
        code = st.query_params["code"]
        
        # Get OAuth config from secrets
        cfg = st.secrets["google_oauth"]
        app_cfg = st.secrets.get("app", {})
        
        # Determine redirect URI based on environment
        redirect_uri = (
            app_cfg["local_redirect_uri"]
            if app_cfg.get("mode") == "local"
            else app_cfg["cloud_redirect_uri"]
        )

        # Exchange code for credentials
        creds = web_exchange_code(
            cfg["client_id"],
            cfg["client_secret"],
            redirect_uri,
            code
        )
        
        # Save to session
        st.session_state["credentials"] = creds
        st.session_state["service"] = build_calendar_service(creds)
        st.session_state["user_email"] = "authenticated_user@gmail.com"
        
        # Clear OAuth params and rerun
        st.query_params.clear()
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Login failed: {e}")
        st.stop()


# ============================================================================
# MAIN APP LOGIC
# ============================================================================

def main():
    # 1. User not logged in -> Show login page
    if not st.session_state.get("credentials"):
        ui.show_login_page()
        st.stop()
    
    # 2. User logged in -> Check credentials and refresh if needed
    creds = st.session_state.get("credentials")
    
    if creds is None:
        st.error("Auth problem: no credentials in session.")
        st.stop()

    # Refresh token if expired
    if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        try:
            creds.refresh(Request())
            st.session_state["credentials"] = creds
            st.session_state["service"] = build_calendar_service(creds)
        except Exception as e:
            if "invalid_grant" in str(e):
                st.error("Session expired. Please log in again.")
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
            st.error(f"Token refresh failed: {e}")
            st.stop()

    # 3. User authenticated and token valid -> Show main app
    service = st.session_state["service"]
    ui.render_app(service)


if __name__ == "__main__":
    main()
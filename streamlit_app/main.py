"""
LazyCal - Calendar Agent Main Entry Point

FIXED: Infinite Login Loop Issue

THE PROBLEM:
- After OAuth callback, st.query_params.clear() doesn't reliably clear the URL
- Page reruns, but Streamlit might still see the "code" parameter
- OAuth code block runs again, but credentials might not persist properly
- Result: Infinite loop back to login page

THE SOLUTION:
- Use a session state flag (_oauth_code_processed) to track if we've already exchanged this code
- This prevents re-exchanging the same code on subsequent reruns
- Much more reliable than trying to clear query params
"""

import streamlit as st
import sys
import os
from google.auth.transport.requests import Request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from project_code.auth import web_exchange_code, build_calendar_service, logout_and_delete_token
from streamlit_app import ui


# ============================================================================
# SESSION DEFAULTS
# ============================================================================

st.set_page_config(page_title="LazyCal - Calendar Agent", page_icon="📅", layout="wide")

st.session_state.setdefault("service", None)
st.session_state.setdefault("credentials", None)
st.session_state.setdefault("user_email", None)
st.session_state.setdefault("_oauth_code_processed", False)  # ← KEY FIX


# ============================================================================
# OAUTH CALLBACK HANDLER
# ============================================================================
code = st.query_params.get("code")

if code and not st.session_state.get("_oauth_code_processed", False):
    try:
        cfg = st.secrets["google_oauth"]
        app_cfg = st.secrets.get("app", {})

        redirect_uri = (
            app_cfg["local_redirect_uri"]
            if app_cfg.get("mode") == "local"
            else app_cfg["cloud_redirect_uri"]
        )

        creds = web_exchange_code(
            cfg["client_id"],
            cfg["client_secret"],
            redirect_uri,
            code
        )

        user_email = getattr(creds, "id_token", {}).get("email", "Unknown")

        st.session_state["credentials"] = creds
        st.session_state["service"] = build_calendar_service(creds)
        st.session_state["user_email"] = user_email
        st.session_state["_oauth_code_processed"] = True

        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.error(f"❌ Login failed: {e}")
        st.session_state["_oauth_code_processed"] = True
        st.stop()


# ============================================================================
# MAIN APP LOGIC
# ============================================================================

def main():
    """Main application logic after authentication."""
    
    # 1. User not logged in -> Show login page
    if st.session_state.get("credentials") is None:
        ui.show_login_page()
        st.stop()
    
    # 2. User logged in -> Check credentials
    creds = st.session_state.get("credentials")
    
    if creds is None:
        st.error("❌ Auth problem: no credentials in session.")
        st.stop()

    # 3. Refresh token if expired
    if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        try:
            creds.refresh(Request())
            st.session_state["credentials"] = creds
            st.session_state["service"] = build_calendar_service(creds)
        except Exception as e:
            if "invalid_grant" in str(e):
                st.error("❌ Session expired. Please log in again.")
                # Clear all session state to force re-login
                for k in ["service", "credentials", "user_email", "calendars_cache", "target_calendar_id"]:
                    st.session_state.pop(k, None)
                st.session_state["_oauth_code_processed"] = False
                st.query_params.clear()
                st.rerun()
            st.error(f"❌ Token refresh failed: {e}")
            st.stop()

    # 4. User authenticated and token valid -> Show main app
    service = st.session_state["service"]
    ui.render_app(service)


if __name__ == "__main__":
    main()
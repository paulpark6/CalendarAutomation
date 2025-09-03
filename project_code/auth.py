# project_code/auth.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from googleapiclient.discovery import build

# ---------------------------------------------------------------------
# OAuth scopes & token storage
# (You can later narrow to calendar.events + calendar.readonly)
# ---------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]  # full Calendar scope
TOKEN_PATH = Path("UserData/token.json")               # single cached token file
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

from typing import Optional

# --- Logout helpers -----------------------------------------------------------
import requests

def revoke_google_token(creds) -> None:
    """
    Best-effort revoke of the current access/refresh token with Google.
    Safe to call even if token is already invalidated.
    """
    try:
        token = getattr(creds, "token", None) or getattr(creds, "refresh_token", None)
        if not token:
            return
        requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            timeout=5,
        )
    except Exception:
        pass  # ignore network errors; we'll still delete the cached token file

def delete_token_file(token_path: Path = TOKEN_PATH) -> None:
    """Remove the persisted token file from disk (if it exists)."""
    try:
        token_path.unlink(missing_ok=True)
    except Exception:
        pass

def logout_and_delete_token(creds=None, token_path: Path = TOKEN_PATH) -> None:
    """
    Full logout routine:
    1) Revoke token with Google (best-effort)
    2) Delete token.json from disk
    """
    revoke_google_token(creds)
    delete_token_file(token_path)


def get_authenticated_email(service, creds: Optional[Credentials] = None) -> Optional[str]:
    """
    Returns the signed-in user's email. Tries the OAuth userinfo endpoint first,
    then falls back to the primary calendar id.
    """
    # Try OAuth userinfo (works for many tokens even without explicit userinfo scope)
    if creds is not None:
        try:
            sess = AuthorizedSession(creds)
            me = sess.get("https://www.googleapis.com/oauth2/v2/userinfo", timeout=10).json()
            if isinstance(me, dict):
                email = me.get("email")
                if email:
                    return email
        except Exception:
            pass

    # Fallback via Calendar API: primary calendar id is the email
    try:
        data = service.calendarList().list(maxResults=50).execute()
        primary = next((c for c in data.get("items", []) if c.get("primary")), None)
        return primary.get("id") if primary else None
    except Exception:
        return None



# ---------------------------------------------------------------------
# Local (desktop) OAuth flow — for development
# ---------------------------------------------------------------------
def _client_cfg_from_secrets() -> dict:
    gi = st.secrets["google_oauth"]["client_id"]
    gs = st.secrets["google_oauth"]["client_secret"]
    ru = st.secrets["google_oauth"]["redirect_uri"]
    return {
        "web": {
            "client_id": gi,
            "project_id": "streamlit-app",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_secret": gs,
            "redirect_uris": [ru],
        }
    }

def get_default_calendar_timezone(service, calendar_id: str = "primary") -> str:
    """Return the timeZone of the specified calendar (default: primary)."""
    try:
        cal = service.calendars().get(calendarId=calendar_id).execute()
        return cal.get("timeZone", "UTC")
    except Exception:
        return "UTC"

def _installed_client_cfg_from_secrets() -> dict:
    gi = st.secrets["google_oauth_installed"]["client_id"]
    gs = st.secrets["google_oauth_installed"]["client_secret"]
    return {
        "installed": {
            "client_id": gi,
            "client_secret": gs,
            "auth_uri":  "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

def get_user_service_local():
    # TEMP DEBUG: confirm which client you're using
    gi = st.secrets["google_oauth_installed"]["client_id"]
    st.info(f"LOCAL DEBUG → Desktop client startswith: {gi[:12]}… len={len(gi)}")

    flow = InstalledAppFlow.from_client_config(_installed_client_cfg_from_secrets(), SCOPES)
    creds = flow.run_local_server(host="localhost", port=0, prompt="consent")
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service, creds

# ---------------------------------------------------------------------
# Web (Streamlit Cloud) OAuth flow — for production
# ---------------------------------------------------------------------
def _one(x):
    """Normalize Streamlit query param values (list|str|None) to a single value."""
    if isinstance(x, list):
        return x[0] if x else None
    return x


def get_user_service_web():
    client_cfg = _client_cfg_from_secrets()
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]

    # If creds already in session, refresh if needed and return
    sess_creds: Optional[Credentials] = st.session_state.get("credentials")
    if sess_creds:
        try:
            if sess_creds.expired and sess_creds.refresh_token:
                sess_creds.refresh(Request())
        except Exception:
            pass
        service = build("calendar", "v3", credentials=sess_creds, cache_discovery=False)
        return service, sess_creds

    # --- IMPORTANT: read query params BEFORE generating a new state ---
    params = st.query_params
    code = _one(params.get("code"))
    returned_state = _one(params.get("state"))
    expected_state = st.session_state.get("oauth_state")  # may be None if session was new

       # If Google redirected back with a code, try to complete the flow now
    if code:
        # If state mismatched, continue anyway (Streamlit reruns can refresh state)
        if expected_state and returned_state != expected_state:
            st.warning("Session refreshed during sign-in; continuing.")

        flow = Flow.from_client_config(client_cfg, scopes=SCOPES, redirect_uri=redirect_uri)
        flow.fetch_token(code=code)
        creds: Credentials = flow.credentials
        st.session_state["credentials"] = creds
        st.session_state["google_creds_json"] = creds.to_json()

        # clean up params & stored state
        st.session_state.pop("oauth_state", None)
        st.session_state.pop("oauth_auth_url", None)
        try:
            st.query_params.clear()
        except Exception:
            pass

        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return service, creds





# ---------------------------------------------------------------------
# Dispatcher — choose dev or cloud flow based on secrets
# ---------------------------------------------------------------------
def get_user_service():
    mode = st.secrets.get("app", {}).get("mode", "cloud")
    return get_user_service_local() if mode == "dev" else get_user_service_web()
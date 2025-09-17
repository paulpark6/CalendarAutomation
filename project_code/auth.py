# project_code/auth.py
from __future__ import annotations

from typing import Optional, Tuple, Dict, Any

import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from googleapiclient.discovery import build

# ---------------------------------------------------------------------
# OAuth scope (you can narrow later to calendar.events + calendar.readonly)
# ---------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]


SCOPES = ["https://www.googleapis.com/auth/calendar"]

def build_calendar_service(creds):
    # Ensure the access token is fresh before building the client
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def assert_service_has_identity(service):
    """Raise fast if the client is anonymous or token is bad."""
    http = getattr(service, "_http", None)
    creds = getattr(http, "credentials", None)
    assert creds is not None, "No credentials on service._http (anonymous client)"
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    r = AuthorizedSession(creds).get("https://www.googleapis.com/oauth2/v2/userinfo", timeout=6)
    assert r.status_code == 200, f"userinfo failed: {r.status_code} {r.text}"
    return r.json().get("email")

def authorized_session_from_service(service):
    http = getattr(service, "_http", None)
    creds = getattr(http, "credentials", None)
    return AuthorizedSession(creds)
# ---------------------------------------------------------------------
# Cloud/Web OAuth helpers (NO Streamlit here)
# UI is responsible for: reading secrets, managing session/query params,
# rendering the login link, and storing creds in st.session_state.
# ---------------------------------------------------------------------
def web_authorization_url(client_id: str, client_secret: str, redirect_uri: str) -> tuple[str, str]:
    """
    Build the Google OAuth authorization URL for the Web flow.
    Returns (auth_url, state). Does not render UI and does not touch files.
    """
    client_cfg = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri":  "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_cfg, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, state


def web_exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Credentials:
    """
    Exchange the returned ?code=... for OAuth Credentials (Web flow).
    Does not render UI and does not touch files.
    """
    client_cfg = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri":  "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_cfg, scopes=SCOPES, redirect_uri=redirect_uri)
    flow.fetch_token(code=code)
    return flow.credentials

# ---------------------------------------------------------------------
# Token/service utilities (pure; no Streamlit)
# ---------------------------------------------------------------------
def refresh_if_needed(creds: Credentials) -> Credentials:
    """
    Refresh the access token if expired and a refresh_token is available.
    """
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def get_authenticated_email(service, creds: Optional[Credentials] = None) -> Optional[str]:
    """
    Return the signed-in user's email.
    Tries the OAuth userinfo endpoint first, then falls back to the primary calendar id.
    """
    # Prefer userinfo (works even without explicit userinfo scope in many cases)
    if creds is not None:
        try:
            me = AuthorizedSession(creds).get(
                "https://www.googleapis.com/oauth2/v2/userinfo", timeout=10
            ).json()
            if isinstance(me, dict) and me.get("email"):
                return me["email"]
        except Exception:
            pass

    # Fallback via Calendar API: the 'primary' calendar id is the email
    try:
        data = service.calendarList().list(maxResults=50).execute()
        primary = next((c for c in data.get("items", []) if c.get("primary")), None)
        return primary.get("id") if primary else None
    except Exception:
        return None


def get_default_calendar_timezone(service, calendar_id: str = "primary") -> str:
    """
    Return the timeZone of the specified calendar (default: 'primary').
    """
    try:
        cal = service.calendars().get(calendarId=calendar_id).execute()
        return cal.get("timeZone", "UTC")
    except Exception:
        return "UTC"


# ---------------------------------------------------------------------
# Logout helpers (cloud-safe)
# ---------------------------------------------------------------------
def revoke_google_token(creds: Optional[Credentials]) -> bool:
    """
    Best-effort revoke of the current token with Google.
    Tries refresh_token first (stronger invalidation), falls back to access token.
    Returns True if a revoke request was attempted, False if no token was present.
    """
    token = None
    if creds is not None:
        token = getattr(creds, "refresh_token", None) or getattr(creds, "token", None)
    if not token:
        return False
    try:
        requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            timeout=5,
        )
    except Exception:
        pass  # best-effort only
    return True


def logout_and_delete_token(creds: Optional[Credentials]) -> None:
    """
    Cloud logout: revoke the token with Google, then let the UI clear session.
    (No local file deletion in cloud/MVP.)
    """
    revoke_google_token(creds)

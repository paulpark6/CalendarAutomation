# project_code/auth.py
import os
from pathlib import Path
from dotenv import load_dotenv

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from google.auth.transport.requests import AuthorizedSession  # for a robust email fetch

# --- 1) Load environment ------------------------------------------------------
# Loads .env so CLIENT_ID / CLIENT_SECRET (if you use env vars) are available.
load_dotenv()

# --- 2) Constants -------------------------------------------------------------
SCOPES     = ["https://www.googleapis.com/auth/calendar"]  # full Calendar scope
TOKEN_PATH = Path("UserData/token.json")                   # where we cache tokens

# project_code/auth.py  (append these helpers near the bottom)
from pathlib import Path
import requests

# Reuse your existing constants
# SCOPES     = ["https://www.googleapis.com/auth/calendar"]
# TOKEN_PATH = Path("UserData/token.json")

def revoke_google_token(creds) -> None:
    """
    Try to revoke the current access/refresh token with Google.
    - Safe to call even if token already invalidated.
    - Network errors are ignored; deletion of token file will still proceed.
    """
    try:
        token = getattr(creds, "token", None) or getattr(creds, "refresh_token", None)
        if not token:
            return  # nothing to revoke
        # Google OAuth 2.0 token revocation endpoint
        requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            timeout=5,
        )
    except Exception:
        pass  # best-effort revoke only

def delete_token_file(token_path: Path = TOKEN_PATH) -> None:
    """
    Remove the persisted token file from disk (if it exists).
    """
    try:
        token_path.unlink(missing_ok=True)
    except Exception:
        pass  # ignore OS errors

def logout_and_delete_token(creds=None, token_path: Path = TOKEN_PATH) -> None:
    """
    Full logout routine:
    1) Revoke token with Google (best-effort)
    2) Delete token.json from disk
    """
    revoke_google_token(creds)
    delete_token_file(token_path)


def _build_flow_from_env() -> InstalledAppFlow:
    """
    Build an OAuth flow using a DESKTOP/INSTALLED client configuration.
    """
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET", "")  # some desktop clients omit secret

    if not client_id:
        raise RuntimeError(
            "CLIENT_ID missing. Put your Desktop App OAuth client id in .env as CLIENT_ID "
            "or provide a client_secret.json and use from_client_secrets_file instead."
        )

    # Minimal installed-app config; redirect URIs are handled by the library.
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri":  "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

def get_user_service():
    """
    Return a Google Calendar API service AND the credentials object.

    Flow:
    1) Load cached token (if present)
    2) Refresh it if expired
    3) Otherwise run the local OAuth server on a FREE port (no clash with Streamlit)
    4) Save token to disk for next time
    5) Build discovery service and return (service, creds)
    """
    creds = None

    # 1) Try loading existing token from disk
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # 2) Refresh if needed (silent, no browser)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # 3) If no valid creds, do the local server flow (desktop)
    if not creds or not creds.valid:
        flow = _build_flow_from_env()
        # Use port=0 so OS chooses a free port (prevents clash with Streamlit 8501)
        creds = flow.run_local_server(
            host="localhost",
            port=0,                          # <-- key: pick an available port
            open_browser=True,
            authorization_prompt_message="Please authorize access in your browser...",
            success_message="You may close this window and return to the app.",
            prompt="consent",                # force consent if you like
        )

        # 4) Persist token for reuse next runs
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())

    # 5) Build the Calendar discovery client
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    # Return BOTH so UI can also use creds with requests transport if needed
    return service, creds

def get_authenticated_email(service, creds: Credentials | None = None):
    """
    Return the primary calendar's ID (which is the Google account's email).
    Uses requests transport if creds are provided (more robust on Python 3.13).
    """
    # Prefer a requests-based call (avoids httplib2 TLS edge cases)
    if creds is not None:
        try:
            sess = AuthorizedSession(creds)
            # List my calendars; find 'primary'
            url = "https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=50"
            data = sess.get(url, timeout=30).json()
            for cal in data.get("items", []):
                if cal.get("primary"):
                    return cal.get("id")
        except Exception:
            pass  # fall back to discovery client

    # Fallback: use the discovery client
    try:
        calendar_list = service.calendarList().list(maxResults=50).execute()
        primary = next((c for c in calendar_list.get("items", []) if c.get("primary")), None)
        return primary["id"] if primary else None
    except Exception:
        return None

def get_default_calendar_timezone(service, calendar_id="primary"):
    """
    Return the timeZone of the specified calendar (default: 'primary').
    """
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    return calendar.get("timeZone", "UTC")

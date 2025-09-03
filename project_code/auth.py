# project_code/auth.py  — streamlit-free OAuth helpers
from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import requests
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request, AuthorizedSession
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = Path("UserData/token.json")
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------- token utils ----------
def load_credentials(path: Path = TOKEN_PATH) -> Optional[Credentials]:
    if not path.exists():
        return None
    return Credentials.from_authorized_user_file(str(path), SCOPES)

def save_credentials(creds: Credentials, path: Path = TOKEN_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json())

def refresh_if_needed(creds: Credentials) -> Credentials:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def revoke_google_token(creds: Optional[Credentials]) -> None:
    try:
        token = getattr(creds, "token", None) or getattr(creds, "refresh_token", None)
        if token:
            requests.post("https://oauth2.googleapis.com/revoke",
                          params={"token": token}, timeout=5)
    except Exception:
        pass

def delete_token_file(path: Path = TOKEN_PATH) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass

def logout_and_delete_token(creds: Optional[Credentials]) -> None:
    revoke_google_token(creds)
    delete_token_file(TOKEN_PATH)

# ---------- service helpers ----------
def build_calendar_service(creds: Credentials):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def get_authenticated_email(service, creds: Optional[Credentials] = None) -> Optional[str]:
    if creds is not None:
        try:
            me = AuthorizedSession(creds).get(
                "https://www.googleapis.com/oauth2/v2/userinfo", timeout=10
            ).json()
            if isinstance(me, dict) and me.get("email"):
                return me["email"]
        except Exception:
            pass
    try:
        data = service.calendarList().list(maxResults=50).execute()
        primary = next((c for c in data.get("items", []) if c.get("primary")), None)
        return primary.get("id") if primary else None
    except Exception:
        return None

def get_default_calendar_timezone(service, calendar_id: str = "primary") -> str:
    try:
        cal = service.calendars().get(calendarId=calendar_id).execute()
        return cal.get("timeZone", "UTC")
    except Exception:
        return "UTC"

# ---------- desktop (installed) flow ----------
def run_installed_flow(installed_client_cfg: Dict[str, Any]) -> Credentials:
    """Launches local server flow and returns creds."""
    flow = InstalledAppFlow.from_client_config(installed_client_cfg, SCOPES)
    creds = flow.run_local_server(host="localhost", port=0, prompt="consent")
    return creds

# ---------- web (redirect) flow ----------
class WebOAuth:
    """Stateless helper; your UI supplies state management & query params."""
    def __init__(self, web_client_cfg: Dict[str, Any], redirect_uri: str):
        self.web_client_cfg = web_client_cfg
        self.redirect_uri = redirect_uri

    def make_authorization_url(self) -> Tuple[str, str]:
        flow = Flow.from_client_config(self.web_client_cfg, scopes=SCOPES, redirect_uri=self.redirect_uri)
        url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        return url, state

    def exchange_code(self, code: str) -> Credentials:
        flow = Flow.from_client_config(self.web_client_cfg, scopes=SCOPES, redirect_uri=self.redirect_uri)
        flow.fetch_token(code=code)
        return flow.credentials

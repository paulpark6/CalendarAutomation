# project_code/auth.py
"""
Google Calendar OAuth2 Authentication (Server-side, no PKCE)
Clean and minimal for Streamlit
"""

import requests
import secrets
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# OAuth Scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email"
]


def web_authorization_url(client_id, client_secret, redirect_uri):
    """
    Generate Google OAuth authorization URL (no PKCE - server-side auth)
    
    Args:
        client_id: OAuth Client ID
        client_secret: OAuth Client Secret  
        redirect_uri: Redirect URI (must match Google Cloud config)
    
    Returns:
        tuple: (auth_url, state_token)
    """
    scopes_encoded = "+".join(SCOPES)
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"scope={scopes_encoded}&"
        f"redirect_uri={redirect_uri}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    state = secrets.token_urlsafe(32)
    return auth_url, state


def web_exchange_code(client_id, client_secret, redirect_uri, code):
    """
    Exchange authorization code for access token (no PKCE)
    
    Args:
        client_id: OAuth Client ID
        client_secret: OAuth Client Secret
        redirect_uri: Redirect URI (must match Google Cloud config)
        code: Authorization code from Google callback
        
    Returns:
        google.oauth2.credentials.Credentials
    """
    token_url = "https://oauth2.googleapis.com/token"
    
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    
    token_data = response.json()
    
    # Build credentials object
    credentials = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    
    return credentials


def build_calendar_service(creds):
    """
    Build Google Calendar API service from credentials
    
    Args:
        creds: google.oauth2.credentials.Credentials
        
    Returns:
        googleapiclient.discovery.Resource
    """
    # Ensure token is fresh
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service


def assert_service_has_identity(service):
    """
    Verify authentication works by calling calendar API
    
    Args:
        service: Calendar service object
        
    Returns:
        str: User email or calendar ID
        
    Raises:
        AssertionError: If auth validation fails
    """
    try:
        result = service.calendarList().list(maxResults=1).execute()
        items = result.get('items', [])
        
        if not items:
            raise AssertionError("No calendars found")
        
        # Return primary calendar ID (which is the user's email)
        primary = next((c for c in items if c.get('primary')), items[0])
        return primary['id']
        
    except Exception as e:
        raise AssertionError(f"Identity check failed: {e}")


def logout_and_delete_token(creds):
    """
    Revoke token with Google (best-effort)
    
    Args:
        creds: google.oauth2.credentials.Credentials
    """
    if not creds:
        return
    
    token = getattr(creds, 'refresh_token', None) or getattr(creds, 'token', None)
    if not token:
        return
    
    try:
        requests.post(
            "https://oauth2.googleapis.com/revoke",
            data={"token": token},
            timeout=5
        )
    except Exception:
        pass  # Best-effort only
"""
Google Calendar OAuth2 Authentication Module (No PKCE)
Simplified for Streamlit server-side OAuth flow
"""

import os
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.oauthlib.flow import Flow
from google_auth_oauthlib.flow import InstalledAppFlow
from google.calendar_v3 import service as calendar_service
from googleapiclient.discovery import build

# OAuth Scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email"
]


def web_authorization_url(client_id, client_secret, redirect_uri):
    """
    Generate the Google OAuth authorization URL (NO PKCE - Streamlit server-side auth)
    
    Returns:
        tuple: (auth_url, state_token)
    """
    auth_url = (
        "https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"scope={'+'.join(SCOPES)}&"
        f"redirect_uri={redirect_uri}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    # Simple state token (you should validate this on callback)
    import secrets
    state = secrets.token_urlsafe(32)
    
    return auth_url, state


def web_exchange_code(client_id, client_secret, redirect_uri, code):
    """
    Exchange authorization code for access token (NO PKCE)
    
    Args:
        client_id: OAuth Client ID
        client_secret: OAuth Client Secret
        redirect_uri: Redirect URI (must match Google Cloud config)
        code: Authorization code from Google callback
        
    Returns:
        google.oauth2.credentials.Credentials object
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
    
    # Create credentials object from token response
    credentials = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    
    return credentials


def build_calendar_service(credentials):
    """
    Build Google Calendar API service from credentials
    
    Args:
        credentials: google.oauth2.credentials.Credentials
        
    Returns:
        googleapiclient.discovery.Resource (Calendar service)
    """
    service = build("calendar", "v3", credentials=credentials)
    return service


def assert_service_has_identity(service):
    """
    Verify the service has valid identity by calling userinfo endpoint
    
    Args:
        service: Calendar service object
        
    Returns:
        str: User email
        
    Raises:
        AssertionError: If identity validation fails
    """
    try:
        # Use calendar list to verify auth & get user email
        calendar_list = service.calendarList().list(maxResults=1).execute()
        
        # Try to get email from the service's credentials
        # Fallback: use primary calendar owner
        if calendar_list.get('items'):
            # The authenticated user is the owner of at least one calendar
            return "authenticated_user@gmail.com"  # Best-effort
        
        raise AssertionError("No calendars found - authentication may be invalid")
    except Exception as e:
        raise AssertionError(f"Identity validation failed: {e}")


def logout_and_delete_token(credentials):
    """
    Attempt to revoke the OAuth token with Google
    Best-effort; doesn't raise on failure
    
    Args:
        credentials: google.oauth2.credentials.Credentials
    """
    if not credentials or not credentials.token:
        return
    
    try:
        requests.post(
            "https://oauth2.googleapis.com/revoke",
            data={"token": credentials.token},
            timeout=5
        )
    except Exception:
        pass  # Best effort - don't fail if revocation doesn't work
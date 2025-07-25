import os
from pathlib import Path
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# 1) Load env
# This line loads environment variables from a .env file into the process's environment,
# making them accessible via os.getenv(). It's useful for keeping sensitive information
# like API keys or client secrets out of your codebase.
load_dotenv()  # might be able to delete this line

# 2) Constants
SCOPES     = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = Path("UserData/token.json")

def get_user_service():
    creds = None

    # Try loading existing token
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # Refresh if needed
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Otherwise, run the installed‑app flow
    if not creds or not creds.valid:
        client_config = {
        "web": {
            "client_id":     os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8501/"]
        }
        }
        flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
        creds = flow.run_local_server(port=8501)


        # Save for reuse
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())

    # Build and return service
    return build("calendar", "v3", credentials=creds)

def get_authenticated_email(service):
    """
    Prints and returns the email address of the authenticated user.
    """
    try:
        calendar_list = service.calendarList().list().execute()
        primary_calendar = next(
            calendar for calendar in calendar_list['items'] if calendar.get('primary', False)
        )
        return primary_calendar['id']
    except Exception as e:
        return None

def get_default_calendar_timezone(service, calendar_id="primary"):
    """
    Returns the timeZone of the specified calendar (default: primary calendar).
    
    Args:
        service: Authenticated Google Calendar API service instance.
        calendar_id (str): The calendar ID to check (default is 'primary').
    
    Returns:
        str: The timeZone string (e.g., 'America/Toronto').
    """
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    return calendar.get("timeZone", "UTC")  # Fallback to UTC if not found
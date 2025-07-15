# auth.py
import os
from pathlib import Path
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# 1) Load env
load_dotenv()  # might be able to delete this line

# 2) Constants
SCOPES     = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = Path("UserCredentials/token.json")

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
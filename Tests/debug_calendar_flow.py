"""
debug_calendar_flow.py

Manual integration script to verify the new Calendar Refactor against the real Google API.
This script will:
1. Authenticate using your local credentials.
2. Create a 'Test - Do Not Use' calendar.
3. Add an event.
4. Update that event.
5. Create a duplicate event (to test dedupe).
6. Delete the calendar.

Usage:
    python debug_calendar_flow.py
"""

import os
import sys
import datetime
import json
import sys

# Ensure we can find project_code (path relative to tests/ folder)
# We need to go up one level from 'tests/' to the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project_code import auth
from project_code import calendar_creation
from project_code import event_creation

def main():
    print("--- 1. Authenticating ---")
    
    creds = None
    token_path = 'token.json'
    
    # 1. Try loading existing token
    if os.path.exists(token_path):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(token_path, auth.SCOPES)

    # 2. If no valid token, verify if we can refresh or need new login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            print("Token missing or invalid. Attempting local login using .streamlit/secrets.toml...")
            try:
                # Attempt to parse secrets.toml manually to avoid extra dependencies
                secrets_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')
                import toml
                with open(secrets_path, "r") as f:
                    secrets = toml.load(f)
                    
                client_id = secrets["google_oauth"]["client_id"]
                client_secret = secrets["google_oauth"]["client_secret"]
                
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                        }
                    },
                    auth.SCOPES
                )
                creds = flow.run_local_server(port=8501)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                    print("Token saved to 'token.json'.")
                    
            except Exception as e:
                print(f"\n[Error] Could not auto-login: {e}")
                print(f"Make sure you have a valid .streamlit/secrets.toml or a token.json file in this directory.")
                return

    try:
        service = auth.build_calendar_service(creds)
        print("Authenticated successfully.")
    except Exception as e:
        print(f"Auth failed: {e}")
        return

    print("\n--- 2. Create Calendar ---")
    cal_name = "Test Integration Calendar (Safe to Delete)"
    try:
        new_cal = calendar_creation.create_calendar(
            service, 
            cal_name, 
            default_reminders=[{"method": "popup", "minutes": 45}]
        )
        cal_id = new_cal["id"]
        print(f"Created Calendar: {cal_name} (ID: {cal_id})")
    except Exception as e:
        print(f"Failed to create calendar: {e}")
        return

    try:
        print("\n--- 3. Create Event ---")
        start_time = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        end_time = (datetime.datetime.now() + datetime.timedelta(days=1, hours=1)).isoformat()
        
        evt_body = {
            "summary": "Integration Test Event",
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
            "description": "Testing creation."
        }
        
        # 1st Create
        evt1 = event_creation.create_event(service, cal_id, evt_body, dedupe=True)
        print(f"Event 1 Created: {evt1.get('created')} (ID: {evt1.get('event_id')})")

        print("\n--- 4. Update Event ---")
        # Update description
        patch = {"description": "Updated Description!"}
        evt1_updated = event_creation.update_event(service, cal_id, evt1["event_id"], patch)
        print(f"Event Updated: {evt1_updated['status']}")

        print("\n--- 5. Test Dedupe (Skip) ---")
        # Try creating exact same event again
        evt2 = event_creation.create_event(service, cal_id, evt_body, dedupe=True, if_exists="skip")
        print(f"Event 2 (Duplicate): Created={evt2.get('created')}, Status={evt2.get('status')}")
        if evt2.get("created") is False and evt2.get("event_id") == evt1["event_id"]:
            print("Dedupe SUCCESS: Skipped creation and found existing ID.")
        else:
            print("Dedupe FAILURE: Did not skip correctly.")

    except Exception as e:
        print(f"Error during event operations: {e}")

    finally:
        print("\n--- 6. Cleanup (Delete Calendar) ---")
        try:
            res = calendar_creation.delete_calendar(service, cal_id)
            print(f"Cleanup Result: {res}")
        except Exception as e:
            print(f"Cleanup failed (Manual delete required for {cal_id}): {e}")

if __name__ == "__main__":
    main()

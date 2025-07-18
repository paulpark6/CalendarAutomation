from project_code.auth import *
from project_code.creating_calendar import *
import pandas as pd
import os
import json

def load_recent_events(filepath="UserData/user_created_events.json"):
    """
    Loads recent events from JSON file. If file contains tuples, convert to dicts with default fields.
    """
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # If data is a list of dicts, return as is
            if data and isinstance(data[0], dict):
                return data
            # If data is a list of tuples/lists, convert to dicts
            elif data and isinstance(data[0], (list, tuple)):
                # Assume (unique_key, google_event_id)
                return [
                    {
                        "unique_key": item[0],
                        "google_calendar_id": item[1],
                        "user_email": "",
                        "service": "",
                        "title": "",
                        "event_date": "",
                        "description": "",
                        "calendar_id": "",
                        "event_time": "",
                        "end_date": "",
                        "timezone": "America/Toronto",
                        "notifications": [],
                        "invitees": [],
                    }
                    for item in data
                ]
            else:
                return []
    except Exception:
        return []

def main():
    # INITIALIZATIONS
    # Authenticate and get Google Calendar service
    service = get_user_service()
    
    recent_events = load_recent_events()  # Always a list of dicts
    # User's calendar ID (must already exist in Google Calendar)
    calendar_id = get_or_create_calendar(
        service
    )

    # Reading user's input
    user_response = load_user_input()

    # ADDING EVENTS TO GOOGLE CALENDAR
    # Convert the dictionary into a DataFrame
    df_calendar = pd.DataFrame(user_response)
    # Create new events (skipping duplicates) and get back the updated list
    recent_events = create_schedule (
        service,
        calendar_id,
        df_calendar,
        recent_events
    )
    # Save the updated list to a JSON file
    save_recent_keys(recent_events)
    
    # # DELETING ALL EVENTS IN THE CALENDAR SESSION
    # recent_events = delete_all_events(
    #     service,
    #     calendar_id,
    #     recent_events
    # )
    # # save the new list to JSON file
    # save_recent_keys(recent_events)

if __name__ == "__main__":
    main()

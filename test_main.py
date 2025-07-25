from project_code.auth import *
from project_code.calendar_methods import *
import pandas as pd
import os
import json

def main():
    service = get_user_service()
    email = get_authenticated_email(service)
    calendar_id = ensure_calendar(service, "Test_automation_calendar")

    event,status = create_event(
        service = service, 
        calendar_id=calendar_id, 
        email=email,
        title="Test Event", 
        description="This is a test event", 
        start_iso="2025-07-25T09:00:00Z", 
        end_iso="2025-07-25T10:00:00Z", 
        timezone_id="UTC", 
        if_exists="skip")
    print(status)
    # # INITIALIZATIONS
    # # Authenticate and get Google Calendar service
    # service = get_user_service()
    
    # recent_events = load_recent_events()  # Always a list of dicts
    # # User's calendar ID (must already exist in Google Calendar)
    # calendar_id = get_or_create_calendar(
    #     service
    # )

    # # Reading user's input
    # user_response = load_user_input()

    # # ADDING EVENTS TO GOOGLE CALENDAR
    # # Convert the dictionary into a DataFrame
    # df_calendar = pd.DataFrame(user_response)
    # # Create new events (skipping duplicates) and get back the updated list
    # recent_events = create_schedule (
    #     service,
    #     calendar_id,
    #     df_calendar,
    #     recent_events
    # )
    # # Save the updated list to a JSON file
    # save_recent_keys(recent_events)
    
    # # # DELETING ALL EVENTS IN THE CALENDAR SESSION
    # # recent_events = delete_all_events(
    # #     service,
    # #     calendar_id,
    # #     recent_events
    # # )
    # # # save the new list to JSON file
    # # save_recent_keys(recent_events)

if __name__ == "__main__":
    main()

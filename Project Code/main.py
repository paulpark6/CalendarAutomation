import pandas as pd
from methods import *
from auth import *
from creating_calendar import *

def main():
    # INITIALIZATIONS
    recent_keys_stack = []  # list of tuples (event_key, google_event_id)

    # Authenticate and get Google Calendar service
    service = get_user_service()

    # User’s calendar ID (must already exist in Google Calendar)
    calendar_id = (
        "712bca2ad174d70e6f53a3a479e17159a4f8de4d159f1b7a9fc18aac76bfa5f6"
        "@group.calendar.google.com"
    )

    # Example “user_response” dictionary (could be replaced by store_response or file input)
    user_response = {
        "title": [
            "Test 1",
            "Test 1",
            "Test 2"
        ],
        "event_date": [
            "2025-06-01",
            "2025-06-01",
            "2025-06-02"
        ],
        "description": [
            "desc1",
            "desc1",
            "desc2"
        ]
    }

    # Convert the dictionary into a DataFrame
    df_calendar = pd.DataFrame(user_response)

    # Create new events (skipping duplicates) and get back the updated stack
    recent_keys_stack = create_schedule(
        service,
        calendar_id,
        df_calendar,
        recent_keys_stack
    )

    # Persist each newly generated (key, google_event_id) tuple into JSON
    for key, mapping in recent_keys_stack:
        save_recent_keys({key: mapping})

    # Print the final stack for confirmation
    print("Final recent keys stack: \n", recent_keys_stack)

    # Deleting some events given the key
    delete_event(service, calendar_id, recent_keys_stack[0])
    recent_keys_stack.pop(0)  # Remove the first event after deletion
    
    # Print the final stack for confirmation
    print("Final recent keys stack: \n", recent_keys_stack)
    # If you want to clear the stack after saving:
    # recent_keys_stack = []

if __name__ == "__main__":
    main()

from project_code.methods import *
from project_code.auth import *
from project_code.creating_calendar import *

def main():
    # INITIALIZATIONS
    # Need to initialize stack using the function
    recent_keys_stack = load_recent_keys()
    # Authenticate and get Google Calendar service
    service = get_user_service()
    # User’s calendar ID (must already exist in Google Calendar)
    calendar_id = get_or_create_calendar(
        service
    )

    # Reading user's input
    user_response = load_user_input()

    # ADDING EVENTS TO GOOGLE CALENDAR
    # Convert the dictionary into a DataFrame
    df_calendar = pd.DataFrame(user_response)
    # Create new events (skipping duplicates) and get back the updated stack
    recent_keys_stack = create_schedule(
        service,
        calendar_id,
        df_calendar,
        recent_keys_stack
    )
    # Save the stack to a JSON file
    save_recent_keys(recent_keys_stack)
    
    # DELETING ALL EVENTS IN THE CALENDAR SESSION
    recent_keys_stack = delete_all_events(
        service,
        calendar_id,
        recent_keys_stack
    )
    # save the new stack to JSON file
    save_recent_keys(recent_keys_stack)


if __name__ == "__main__":
    main()

# creating_calendar.py
# file should have functions to create calendar
from .methods import *
from .llm_methods import *
from .auth import *
import pandas as pd
from typing import List, Tuple
import json
import os

def get_or_create_calendar(service, filepath : str = "UserData/calendar_id.txt") -> str:
    """
    Gets the calendar ID for the given name. If it doesn't exist, creates it.

    Args:
        service: Authenticated Google Calendar API service instance.
        filepath: the location of the user input file containing the calendar name.

    Returns:
        calendar_id: The ID of the found or newly created calendar. If no calendar name is found in the file,
                      a default calendar name, Automated Calendar, is used.
    """
    calendar_name = ""

    with open(filepath, 'r') as f:
        calendar_name = f.read()
    if not os.path.exists(filepath) or not calendar_name:
        calendar_name = "Automated Calendar"
    # 1. Check if calendar already exists
    calendar_list = service.calendarList().list().execute()
    for calendar_entry in calendar_list.get("items", []):
        if calendar_entry.get("summary") == calendar_name:
            return calendar_entry["id"]

    # 2. Calendar not found — create a new one
    calendar = {
        'summary': calendar_name,
        'timeZone': 'America/Toronto',
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    return created_calendar["id"]


# deleting all events in the calendar session
def delete_all_events(
    service,
    calendar_id: str,
    recent_keys_stack: List[Tuple[str, str]]
) -> List[Tuple[str, str]]:
    """
    Deletes all events in the specified calendar.

    Args:
      service: Authenticated Google Calendar API service instance.
      calendar_id: The ID of the calendar from which events will be deleted.
      recent_keys_stack: List of (event_key, google_event_id) tuples.

    Returns:
      An empty list, indicating all tracked events have been deleted.
    """
    for key, google_event_id in recent_keys_stack:
        try:
            delete_event(service, calendar_id, (key,google_event_id))
        except Exception as e:
            print(f"Failed to delete event {key} ({google_event_id}): {e}")
    return []

def load_recent_keys(filepath="UserData/user_created_events.json") -> List[Tuple[str, str]]:
    """
    Loads recent keys stack from JSON file. If file is missing or empty/corrupt, returns empty list.
    """
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return [tuple(item) for item in data]
    except (json.JSONDecodeError, ValueError):
        # Handles empty file or corrupt JSON
        return []

# function that saves the user's input to a jSON file
def save_recent_keys(stack, filepath="UserData/user_created_events.json"):
    """
    Saves the stack of (event_key, google_event_id) tuples to a JSON file.
    """
    serializable_stack = [list(t) for t in stack]
    with open(filepath, 'w') as f:
        json.dump(serializable_stack, f)


# function that reads the user's input from a text file
def load_user_input(filepath="UserData/user_input.txt"):
    """
    Reads a dictionary from a plain text file and returns it as a Python dict.
    The txt file format should look like below, Note that even with only one event,
    the values should still be lists, so that it can be converted to a DataFrame easily.:
    {
        "title": ["Event Title"],
        "event_date": ["2025-06-18"],
        "description": ["Event Description"]
    }
    """
    with open(filepath, 'r') as f:
        content = f.read().strip()

    try:
        data = eval(content)
        if isinstance(data, dict):
            return data
        else:
            raise ValueError("File content is not a dictionary.")
    except Exception as e:
        raise ValueError(f"Error parsing user input file: {e}")

# functino to create a simple schedule given a DataFrame of events
def create_schedule(
    service,
    calendar_id: str,
    df_calendar,
    recent_keys_stack: List[Tuple[str, str]]
) -> List[Tuple[str, str]]:
    """
    Add events from `df_calendar` into Google Calendar, skipping any that already exist
    in `recent_keys_stack`.  Treats `recent_keys_stack` as a list of (event_key, google_id) tuples.
    
    Args:
      service: Authenticated Google Calendar API service instance.
      calendar_id: The ID of the calendar where events will be added.
      df_calendar: pandas DataFrame containing columns ['title', 'description', 'event_date'].
      recent_keys_stack: List of (event_key, google_event_id) tuples representing events
                         that have already been created in previous runs.

    Returns:
      The updated `recent_keys_stack`, with new (key, google_event_id) tuples appended
      for any events that did not already exist.
    """
    # 1) Process each row of df_calendar
    for _, row in df_calendar.iterrows():
        title       = row['title']
        description = row.get('description', "")   # default to empty string if no description
        event_date  = row.get('event_date', None)   # should always exist, but fallback to None
        # 2) build a set of all existing event_keys for duplicate checks
        existing_keys = {past_key for past_key, _ in recent_keys_stack}

        # 3) Generate the same “unique_key” that will be used by create_single_event.
        #    Make sure to pass exactly the same arguments (including defaults) here
        #    as create_single_event uses, so that the hash will match.
        unique_key = generate_event_key(
            title=title,
            description=description,
            calendar_id=calendar_id,
            event_date=event_date
        )
        duplicate_found = False
        for keys in recent_keys_stack:
            if keys[0] == unique_key:
                # 4) If the key already exists, skip to the next row
                duplicate_found = True
                break

        # 5) Not a duplicate: call create_single_event(...) to insert the event into Google Calendar.
        #    create_single_event returns a tuple (key, google_event_id):
        #       - key: the same unique_key we generated above
        #       - google_event_id: the actual event ID returned by Google
        if duplicate_found:
            continue
        else:
            mapping = create_single_event(
                service,
                calendar_id=calendar_id,
                title=title,
                description=description,
                event_date=event_date,
                key=unique_key
            )

            # 6) Append the newly created (key, google_event_id) tuple to our list...
            recent_keys_stack.append(mapping)

    # 7) After all rows processed, return the updated list of tuples
    return recent_keys_stack


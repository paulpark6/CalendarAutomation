# creating_calendar.py
# file should have functions to create calendar
import pandas as pd
from typing import List, Tuple, Any, Dict, Optional
import json
import os
import hashlib
import datetime
from .llm_methods import *
from .auth import *

def save_user_events_from_dataframe(email, event_records):
    """
    Accepts either a DataFrame or a list of dicts.
    """
    if hasattr(event_records, 'to_dict'):  # DataFrame
        records = event_records.to_dict(orient="records")
    else:
        records = event_records
    for event_record in records:
        save_user_event(email, event_record)

def save_user_event(email, event_record):
    """
    Save a single event record for a user to their personal created events JSON file.

    Args:
        email (str): The user's email address, used to determine the file path.
        event_record (Any): The event data to be saved (typically a dictionary).
        event_record = {
                    "user_email": email,                     # str, the user's email address 
                    "unique_key": unique_key,                # str, from generate_event_key (hash)
                    "google_calendar_id": google_event_id,   # str, from Google API
                    "service": str(service),                 # optional, usually not serializable; store service info if needed
                    "title": title,                          # str
                    "event_date": event_date,                # str
                    "description": description,              # str
                    "calendar_id": calendar_id,              # str
                    "event_time": event_time or "",          # str or ""
                    "end_date": end_date or "",              # str or ""
                    "timezone": timezone,                    # str
                    "notifications": notifications or "",    # str or list or ""
                    "invitees": invitees or "",              # str or list or ""
                }

    Side Effects:
        - Reads from and writes to 'UserData/{email}_created_events.json'.
        - Appends the new event to the existing list of events for the user.
    Ensures no duplicate events by unique_key. If the file does not exist, creates it with the new event.
    Does not return anything.
    """
    path = f"UserData/{email}_created_events.json"
    # Load existing events if file exists, else start with empty list
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                events = json.load(f)
            except Exception:
                events = []
    else:
        events = []

    # Remove any existing event with the same unique_key
    unique_key = event_record.get("unique_key")
    if unique_key is not None:
        events = [e for e in events if e.get("unique_key") != unique_key]

    # Append the new event
    events.append(event_record)

    # Write back to JSON
    with open(path, "w") as f:
        json.dump(events, f, indent=2)

def load_user_events(email):
    """
    Load all event records for a user from their personal created events JSON file and return as a pandas DataFrame.

    Args:
        email (str): The user's email address, used to determine the file path.

    Returns:
        pd.DataFrame: DataFrame of event records (empty if the file does not exist).
    """
    path = f"UserData/{email}_created_events.json"
    if not os.path.exists(path):
        # Return an empty DataFrame with expected columns
        columns = [
            "user_email", "unique_key", "google_calendar_id", "service", "title", "event_date",
            "description", "calendar_id", "event_time", "end_date", "timezone", "notifications", "invitees"
        ]
        return pd.DataFrame({col: [] for col in columns})
    with open(path, "r") as f:
        events = json.load(f)
        # Defensive: ensure events is a list of dicts
        if not isinstance(events, list):
            return pd.DataFrame()
        return pd.DataFrame(events)

def get_or_create_calendar(service, filepath : str = "UserData/calendar_id.txt") -> str:
    """
    Gets the calendar ID for the given name. If it doesn't exist, creates it with a default name Automated Calendar.

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
    calendar_id: Optional[str],
    recent_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
    """
    Deletes all events in the specified calendar using the new event_record structure.
    Args:
      service: Authenticated Google Calendar API service instance.
      calendar_id: The ID of the calendar from which events will be deleted.
      recent_events: List of event_record dicts.
    Returns:
      An empty list, indicating all tracked events have been deleted.
    """
    if service is None:
        return []
    calendar_id = str(calendar_id or "")
    for event in recent_events:
        google_event_id = event.get("google_calendar_id")
        google_event_id = str(google_event_id or "")
        if not google_event_id:
            continue
        try:
            delete_event(service, calendar_id, google_event_id)
        except Exception as e:
            print(f"Failed to delete event {event.get('unique_key', '')} ({event.get('google_calendar_id', '')}): {e}")
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
    recent_events: List[Dict[str, Any]],
    user_email: str = "",
    event_time: str = "",
    end_date: str = "",
    timezone: str = "America/Toronto",
    notifications: Optional[List[Dict[str, Any]]] = None,
    invitees: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
    """
    Add events from `df_calendar` into Google Calendar, skipping any that already exist
    in `recent_events`. Uses event_record dicts for tracking.
    """
    if notifications is None:
        notifications = []
    if invitees is None:
        invitees = []
    user_email = user_email or ""
    existing_keys = {event['unique_key'] for event in recent_events}
    for _, row in df_calendar.iterrows():
        title       = row.get('title', "") or ""
        description = row.get('description', "") or ""
        event_date  = row.get('event_date', "") or ""
        unique_key = generate_event_key(
            title=title,
            description=description,
            calendar_id=calendar_id,
            event_date=event_date,
            event_time=event_time or "",
            end_date=end_date or "",
            timezone=timezone,
            notifications=notifications,
            invitees=invitees
        )
        if unique_key in existing_keys:
            continue
        event_record = create_single_event(
            service,
            calendar_id=calendar_id,
            title=title,
            description=description,
            event_date=event_date,
            event_time=event_time or "",
            end_date=end_date or "",
            timezone=timezone,
            notifications=notifications,
            invitees=invitees,
            key=unique_key,
            user_email=user_email
        )
        recent_events.append(event_record)
        existing_keys.add(unique_key)
    return recent_events

# --- Event Key Generation ---
def generate_event_key(
    title: str = "title",
    description: str = "description",
    calendar_id: str = "primary",
    event_date: str = "",
    event_time: Optional[str] = "",
    end_date: str = "",
    timezone: str = "America/Toronto",
    notifications: Optional[List[Dict[str, Any]]] = None,
    invitees: Optional[List[str]] = None
) -> str:
    """
    Generate a deterministic unique key for an event based only on its input parameters.
    """
    event_time_part = event_time or ""
    notifications_part = (
        "|".join([f"{n['method']}@{n['minutes']}" for n in notifications])
        if notifications else ""
    )
    invitees_part = ",".join(sorted(invitees)) if invitees else ""
    key_string = "\x1F".join([
        "automated",
        title,
        description,
        calendar_id,
        event_date,
        event_time_part,
        end_date,
        timezone,
        notifications_part,
        invitees_part
    ])
    key_hash = hashlib.sha1(key_string.encode('utf-8')).hexdigest()
    return key_hash

# --- Single Event Creation ---
def create_single_event(
    service,
    calendar_id: str = 'primary',
    title: str = 'title',
    description: str = 'description',
    event_date: str = "",
    event_time: str = "",
    end_date: str = "",
    timezone: str = 'America/Toronto',
    notifications: Optional[List[Dict[str, Any]]] = None,
    invitees: Optional[List[str]] = None,
    key: str = "",
    user_email: str = ""
) -> Dict[str, Any]:
    """
    Create a single Google Calendar event and return an event_record dict.
    """
    today = datetime.date.today().strftime('%Y-%m-%d')
    event_date = event_date or today
    end_date = end_date or event_date
    title = title or ""
    description = description or ""
    calendar_id = calendar_id or ""
    if notifications is None:
        notifications = []
    if invitees is None:
        invitees = []
    if not notifications:
        if event_time:
            overrides = [
                {'method': 'email',  'minutes': 24 * 60},
                {'method': 'popup',  'minutes': 7  * 24 * 60},
                {'method': 'popup',  'minutes': 2  * 60},
                {'method': 'popup',  'minutes': 24 * 60},
                {'method': 'popup',  'minutes': 2  * 24 * 60}
            ]
        else:
            overrides = [
                {'method': 'popup',  'minutes': 7  * 24 * 60},
                {'method': 'email',  'minutes': 1  * 24 * 60},
                {'method': 'popup',  'minutes': 1  * 24 * 60},
                {'method': 'popup',  'minutes': 2  * 24 * 60},
                {'method': 'popup',  'minutes': 3  * 24 * 60},
            ]
    else:
        overrides = notifications
    # Generate unique_key if not provided
    unique_key = key or generate_event_key(
        title=title,
        description=description,
        calendar_id=calendar_id,
        event_date=event_date,
        event_time=event_time,
        end_date=end_date,
        timezone=timezone,
        notifications=notifications,
        invitees=invitees
    )
    event = {
        'summary': title,
        'description': description,
        'start':  (
            {'dateTime': f"{event_date}T{event_time}", 'timeZone': timezone}
            if event_time else {'date': event_date}
        ),
        'end':    (
            {'dateTime': f"{end_date}T{event_time}", 'timeZone': timezone}
            if event_time else {'date': end_date}
        ),
        'reminders': {
            'useDefault': False,
            'overrides': overrides
        },
        'attendees': [{'email': e} for e in invitees]
    }
    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    google_calendar_id = created['id']
    event_record = {
        "user_email": user_email or "",
        "unique_key": unique_key,
        "google_calendar_id": google_calendar_id,
        "service": str(service),
        "title": title,
        "event_date": event_date,
        "description": description,
        "calendar_id": calendar_id,
        "event_time": event_time or "",
        "end_date": end_date or "",
        "timezone": timezone,
        "notifications": overrides,
        "invitees": invitees,
    }
    return event_record

# --- Delete Event ---
def delete_event(
    service,
    calendar_id: Optional[str],
    google_event_id: Optional[str]
) -> str:
    """
    Delete an event from Google Calendar using its event ID.
    """
    if service is None:
        return ""
    calendar_id = str(calendar_id or "")
    google_event_id = str(google_event_id or "")
    if not calendar_id or not google_event_id:
        return ""
    service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()
    return google_event_id




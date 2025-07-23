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
from numpy import array

def save_events(email: str, event_records):
    """
    Save one or more event records for a user to their personal created events JSON file.

    This function accepts any of the following as event_records:
        - A pandas DataFrame with columns matching the event record fields.
        - A list of dictionaries, where each dictionary represents an event.
        - A single dictionary representing one event.

    It will save each event for the specified user, ensuring that
    duplicate events (by unique_key) are not created. If an event with the same unique_key already
    exists, it will be replaced with the new one.

    Args:
        email (str): The user's email address, used to determine the file path.
        event_records (Union[pd.DataFrame, List[dict], dict]): The events to be saved.

    Example of event_records as a list of dicts:
        event_records = [
            {
                "user_email": "user@example.com",
                "unique_key": "abc123",
                "google_calendar_id": "gcal1",
                "service": "test_service",
                "title": "Test Event 1",
                "event_date": "2024-07-01",
                "description": "First event",
                "calendar_id": "cal1",
                "event_time": "10:00",
                "end_date": "2024-07-01",
                "timezone": "America/Toronto",
                "notifications": [],
                "invitees": []
            },
            {
                "user_email": "user@example.com",
                "unique_key": "def456",
                "google_calendar_id": "gcal2",
                "service": "test_service",
                "title": "Test Event 2",
                "event_date": "2024-07-02",
                "description": "Second event",
                "calendar_id": "cal1",
                "event_time": "14:00",
                "end_date": "2024-07-02",
                "timezone": "America/Toronto",
                "notifications": [],
                "invitees": []
            }
        ]

    Example of event_records as a single dict:
        event_records = {
            "user_email": "user@example.com",
            "unique_key": "abc123",
            "google_calendar_id": "gcal1",
            "service": "test_service",
            "title": "Test Event 1",
            "event_date": "2024-07-01",
            "description": "First event",
            "calendar_id": "cal1",
            "event_time": "10:00",
            "end_date": "2024-07-01",
            "timezone": "America/Toronto",
            "notifications": [],
            "invitees": []
        }

    Side Effects:
        - Calls save_event for each event record, which writes to 'UserData/{email}_created_events.json'.
        - Ensures no duplicate events by unique_key.

    Returns:
        None
    """
    # Define all required keys for an event record
    REQUIRED_EVENT_KEYS = [
        "user_email",
        "unique_key",
        "google_calendar_id",
        "service",
        "title",
        "event_date",
        "description",
        "calendar_id",
        "event_time",
        "end_date",
        "timezone",
        "notifications",
        "invitees"
    ]

    # Convert DataFrame to list of dicts if needed
    if hasattr(event_records, 'to_dict'):  # DataFrame
        records = event_records.to_dict(orient="records")
    elif isinstance(event_records, dict):
        # Single event dict
        records = [event_records]
    else:
        # Assume it's already a list of dicts
        records = event_records

    for event_record in records:
        # Ensure all required keys are present in the event_record
        for key in REQUIRED_EVENT_KEYS:
            if key not in event_record:
                # Use empty string for most, but [] for notifications/invitees
                if key in ("notifications", "invitees"):
                    event_record[key] = []
                else:
                    event_record[key] = ""
        save_event(email, event_record)

def save_event(email, event_record):
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

def load_events(email):
    """
    Loads all event records for a user from their personal created events JSON file and returns them as a pandas DataFrame.

    Args:
        email (str): The user's email address, which is used to determine the file path for their saved events.

    Returns:
        pd.DataFrame: A DataFrame containing all event records for the user. 
            - If the file 'UserData/{email}_created_events.json' does not exist, or if the file exists but contains no data, 
              an empty DataFrame with the expected columns is returned. 
            - If the file exists and contains event data, a DataFrame with one row per event is returned, with columns:
              ["user_email", "unique_key", "google_calendar_id", "service", "title", "event_date", "description", "calendar_id", "event_time", "end_date", "timezone", "notifications", "invitees"].
            - If the file exists but is corrupted or does not contain a list of event records, an empty DataFrame with the expected columns is returned.
    """
    columns = [
        "user_email", "unique_key", "google_calendar_id", "service", "title", "event_date",
        "description", "calendar_id", "event_time", "end_date", "timezone", "notifications", "invitees"
    ]
    path = f"UserData/{email}_created_events.json"
    if not os.path.exists(path):
        # Return an empty DataFrame with expected columns (0 rows, 13 columns)
        return pd.DataFrame(columns=array(columns))
    try:
        with open(path, "r") as f:
            content = f.read()
            if not content.strip():
                # File is empty, return empty DataFrame with columns
                return pd.DataFrame(columns=array(columns))
            events = json.loads(content)
    except Exception:
        # File is corrupted or unreadable, return empty DataFrame with columns
        return pd.DataFrame(columns=array(columns))
    # Defensive: ensure events is a list of dicts
    if not isinstance(events, list):
        return pd.DataFrame(columns=array(columns))
    df = pd.DataFrame(events)
    # Ensure all expected columns exist, even if empty
    for col in columns:
        if col not in df.columns:
            df[col] = []
    # Reorder columns to match the expected order
    df = df[columns]
    return df

def set_calendar_id(service, filepath : str = "UserData/calendar_id.txt") -> str:
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




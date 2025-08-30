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
from datetime import datetime, date, timedelta



def save_events(email: str, service, event_records):
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

    Side Effects:
        - Calls save_event for each event record, which writes to 'UserData/{email}_created_events.json'.
        - Ensures no duplicate events by unique_key.

    Returns:
        None
    """
    # Convert DataFrame to list of dicts if needed
    if hasattr(event_records, 'to_dict'):  # DataFrame
        records = event_records.to_dict(orient="records")
    elif isinstance(event_records, dict):
        # Single event dict
        records = [event_records]
    else:
        # Assume it's already a list of dicts
        records = event_records

    saved_events = []
    for event_record in records:
        saved_event = save_event(email, service, event_record)
        if saved_event is not None:
            saved_events.append(saved_event)

    # No need to deduplicate here, as save_event() already handles duplicates
    df = pd.DataFrame(saved_events)
    return df

def clean_event_record(event_record, service):
    """
    Cleans and standardizes an event record by ensuring all required fields are present, filling in default values where necessary, and generating a unique key for the event.

    Parameters:
        event_record (dict): 
            A dictionary representing a single event. It may be incomplete or missing some required fields. 
            Expected keys include (but are not limited to): 
                - "unique_key"
                - "calendar_name"
                - "title"
                - "event_date"
                - "description"
                - "calendar_id"
                - "event_time"
                - "end_date"
                - "timezone"
                - "notifications"
                - "invitees"
        service: 
            The Google Calendar API service object, used to look up or create calendar IDs if needed.

    Purpose:
        This function ensures that the event record contains all necessary fields for saving or pushing to Google Calendar. 
        If any required field is missing or set to None, it fills in a sensible default (e.g., default timezone, calendar name, or notification settings).
        It also generates a unique key for the event based on its content, which is used to identify and deduplicate events.

    Returns:
        dict: 
            A cleaned and fully populated event record dictionary, ready for saving or further processing.
    """

    # Define all required keys for an event record
    REQUIRED_EVENT_KEYS = [
        "unique_key", "calendar_name", "title", "event_date",
        "description", "calendar_id", "event_time", "end_date",
        "timezone", "notifications", "invitees",
        "location", "recurrence"   # NEW
    ]

    # Make a copy to avoid mutating the input
    event_record = dict(event_record)

    for key in REQUIRED_EVENT_KEYS:
        if key not in event_record or event_record[key] is None:
            if key == "timezone":
                event_record['timezone'] = "America/Toronto"
            elif key == "calendar_name":
                event_record['calendar_name'] = "Automated Calendar"
            elif key == "calendar_id":
                event_record['calendar_id'] = set_calendar_id(
                    service, "Automated Calendar", event_record.get("timezone", "America/Toronto")
                )
            elif key == "location":
                event_record["location"] = ""
            elif key == "recurrence":
                event_record["recurrence"] = ""    # can be "", "RRULE:...", or list[str]
            elif key == "title":
                event_record['title'] = "Enter Title Here"
            elif key == "event_date":
                event_record['event_date'] = datetime.now().strftime("%y-%m-%d")
            elif key == "notifications":
                event_record['notifications'] = [
                    {'method': 'popup',  'minutes': 7  * 24 * 60},   # 7 days before
                    {'method': 'email',  'minutes': 1  * 24 * 60},   # 1 day before
                    {'method': 'popup',  'minutes': 1  * 24 * 60},   # 1 day before
                    {'method': 'popup',  'minutes': 2  * 24 * 60},   # 2 days before
                    {'method': 'popup',  'minutes': 3  * 24 * 60}    # 3 days before
                ]
            elif key == "invitees":
                event_record['invitees'] = []
            else:
                event_record[key] = ""

    # Generate unique_key after all fields are filled in
    event_record["unique_key"] = generate_event_key(
        title=event_record["title"],
        description=event_record["description"],
        calendar_id=event_record["calendar_id"],
        event_date=event_record["event_date"],
        event_time=event_record["event_time"],
        end_date=event_record["end_date"],
        timezone=event_record["timezone"],
        notifications=event_record["notifications"],
        invitees=event_record["invitees"]
    )
    return event_record

def save_event(email, service, event_record):
    """
    Save a single event record for a user to their personal created events JSON file.

    This function uses clean_event_record to ensure all required fields are present and filled.
    It guarantees that no duplicate events (by unique_key) are stored for the user.
    If an event with the same unique_key already exists, it is replaced with the new one.

    Args:
        email (str): The user's email address, used to determine the file path.
        service: The authenticated Google Calendar API service instance (used for calendar_id assignment if needed).
        event_record (dict): The event data to be saved.

    Returns:
        dict: The cleaned and saved event record.
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

    # Clean and fill the event record
    cleaned_event = clean_event_record(event_record, service)

    # Remove any existing event with the same unique_key before appending the new/updated event
    events = [e for e in events if e.get("unique_key") != cleaned_event["unique_key"]]
    events.append(cleaned_event)

    # Write back to JSON
    with open(path, "w") as f:
        json.dump(events, f, indent=2)
    return cleaned_event  # Return the single event

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
              ["user_email", "unique_key", "calendar_name", "title", "event_date", "description", "calendar_id", "event_time", "end_date", "timezone", "notifications", "invitees"].
            - If the file exists but is corrupted or does not contain a list of event records, an empty DataFrame with the expected columns is returned.
    """
    columns = [
        "user_email", "unique_key", "calendar_name", "title", "event_date",
        "description", "calendar_id", "event_time", "end_date", "timezone",
        "notifications", "invitees",
        "location",          # NEW
        "recurrence"         # NEW (string RRULE or list[str])
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

# function that reads the user's input from a text file
def read_inputs(input, service=None):
    """
    This function should read read the input.
    The input is the output given from function load_events().
    Then this function will upload every events from the dataframe to google calendar.
    """

def set_calendar_id(service, calendar_name: str = "Automated Calendar", timeZone: str = "America/Toronto") -> str:
    """
    Gets the calendar ID for the given calendar name. If it doesn't exist, creates it with the provided name,
    or uses the default name "Automated Calendar" if no name is given.
    This function will be used by another function to generate the calendar_id.
    Args:
        service: Authenticated Google Calendar API service instance.
        calendar_name (str): The name of the calendar to look up or create. If empty, uses "Automated Calendar".
        timeZone (str): The time zone of the calendar. If empty, uses "America/Toronto".

    Returns:
        str: The ID of the found or newly created calendar.
    """
    if timeZone == "":
        timeZone = "America/Toronto"
    if calendar_name == "":
        calendar_name = "Automated Calendar"
    # 1. Check if calendar already exists
    calendar_list = service.calendarList().list().execute()
    for calendar_entry in calendar_list.get("items", []):
        if calendar_entry.get("summary") == calendar_name:
            return calendar_entry["id"]

    # 2. Calendar not found — create a new one
    calendar = {
        'summary': calendar_name,
        'timeZone': timeZone,
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    return created_calendar["id"]

def get_or_create_calendar(service, calendar_name: str = "Automated Calendar", timeZone: str = "America/Toronto") -> str:
    """
    Gets the calendar ID for the given calendar name. If it doesn't exist, creates it.
    """
    return set_calendar_id(service, calendar_name, timeZone)

def generate_event_key(
    title: str = "title",
    description: str = "description",
    calendar_id: str = "primary",
    event_date: str = "",
    event_time: Optional[str] = "",
    end_date: str = "",
    timezone: str = "America/Toronto",
    notifications: Optional[List[Dict[str, Any]]] = None,
    invitees: Optional[List[str]] = None,
    location: str = "",                       # NEW
    recurrence: Any = ""                      # NEW
) -> str:
    event_time_part = event_time or ""
    notifications_part = (
        "|".join([f"{n['method']}@{n['minutes']}" for n in notifications]) if notifications else ""
    )
    invitees_part = ",".join(sorted(invitees)) if invitees else ""
    recurrence_part = (
        ";".join(recurrence) if isinstance(recurrence, list) else (recurrence or "")
    )
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
        invitees_part,
        location,            # NEW
        recurrence_part      # NEW
    ])
    key_hash = hashlib.sha1(key_string.encode("utf-8")).hexdigest()
    return key_hash


def push_all_local_events_to_google(service, email):
    df = load_events(email)
    for _, event in df.iterrows():
        create_single_event(
            service,
            calendar_id=event["calendar_id"],
            title=event["title"],
            description=event["description"],
            event_date=event["event_date"],
            event_time=event["event_time"],
            end_date=event["end_date"],
            timezone=event["timezone"],
            notifications=event["notifications"],
            invitees=event["invitees"],
            user_email=event.get("user_email", "")
        )


def _normalize_time_str(t: str) -> str:
    """Return HH:MM:SS from an input like '10', '10:00', or '10:00:00'."""
    if not t:
        return ""
    t = t.strip()
    if len(t) == 1:
        t = f"0{t}:00:00"
    elif len(t) == 2 and t.isdigit():
        t = f"{t}:00:00"
    elif len(t) == 5 and t[2] == ":":
        t = f"{t}:00"
    return t

def _exclusive_end_for_all_day(d: str) -> str:
    """Google requires end.date to be exclusive."""
    try:
        return (date.fromisoformat(d) + timedelta(days=1)).isoformat()
    except Exception:
        return d  # fallback

def _as_list_rrule(recurrence) -> Optional[list]:
    """Accept '', 'RRULE:...', or list[str]; normalize to list[str] or None."""
    if not recurrence:
        return None
    if isinstance(recurrence, list):
        return [str(x) for x in recurrence if str(x).strip()]
    s = str(recurrence).strip()
    if not s:
        return None
    if not s.upper().startswith("RRULE:"):
        s = "RRULE:" + s
    return [s]

def create_single_event(
    service,
    calendar_id: str,
    title: str,
    description: str,
    event_date: str,
    event_time: str = "",
    end_date: str = "",
    timezone: str = "",
    notifications: Optional[List[Dict[str, Any]]] = None,
    invitees: Optional[List[str]] = None,
    location: str = "",                          # NEW
    recurrence: Any = None,                      # NEW (string RRULE or list[str])
    user_email: str = "",
    send_updates: str = "none",
):
    """
    Backward-compatible creator used by UI. Builds correct all-day/timed bodies,
    and supports location + recurrence.
    """
    # Clean/sensible defaults
    notifications = notifications or []
    invitees = invitees or []
    event_time = (event_time or "").strip()
    timezone = (timezone or "").strip()

    # Determine timed vs all-day
    is_timed = bool(event_time)
    if is_timed:
        t = _normalize_time_str(event_time)  # 'HH:MM:SS'
        start = {"dateTime": f"{event_date}T{t}", "timeZone": timezone or "UTC"}
        # If end_date is missing, keep same date; creator can set duration elsewhere if desired
        end_dt_date = (end_date or event_date)
        end = {"dateTime": f"{end_dt_date}T{t}", "timeZone": timezone or "UTC"}
    else:
        # TRUE all-day: date only, and end.date must be exclusive
        start = {"date": event_date}
        end_base = end_date or event_date
        end = {"date": _exclusive_end_for_all_day(end_base)}

    body = {
        "summary": title,
        "description": description or None,
        "start": start,
        "end": end,
        "reminders": {"useDefault": False, "overrides": notifications},
        "attendees": [{"email": e} for e in invitees if e],
    }

    if location:
        body["location"] = location

    rr = _as_list_rrule(recurrence)
    if rr:
        body["recurrence"] = rr

    created = service.events().insert(calendarId=calendar_id, body=body, sendUpdates=send_updates).execute()
    # Return the API's event payload so callers can read 'id'
    return created
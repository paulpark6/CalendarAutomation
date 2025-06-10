# creating_calendar.py
# file should have functions to create calendar
from methods import *
from llm_methods import *
from auth import *
import pandas as pd
from typing import List, Tuple

def save_recent_keys(stack, filename='recent_keys.json'):
    """
    Save the recent keys stack to a JSON file.

    This function serializes the list of (event_key, google_event_id) tuples
    into a JSON file. It allows easy persistence and retrieval of created events.

    Args:
        stack: List of (event_key, google_event_id) tuples representing
               events that have been created.
        filename: The name of the JSON file where the stack will be saved.

    Returns:
        None
    """
    import json
    with open(filename, 'w') as f:
        json.dump(stack, f)


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


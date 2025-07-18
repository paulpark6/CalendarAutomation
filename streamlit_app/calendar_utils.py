import pandas as pd
import ast
import json
from requests.utils import dict_from_cookiejar
from project_code.creating_calendar import create_schedule, get_or_create_calendar, load_user_input
# from project_code.llm_methods import *

def show_calendar(service, calendar_id='primary'):
    """
    Fetches events from the specified Google Calendar and returns them as a DataFrame.
    If a calendar_id is not provided, the function will use the primary calendar of the authenticated user.

    Args:
        service: Authenticated Google Calendar API service instance.
        calendar_id (str): The calendar ID to fetch events from. Defaults to 'primary'.

    Returns:
        pd.DataFrame: DataFrame containing columns ['title', 'description', 'event_date'] for each event.
    """
    # Retrieve up to 100 events from the specified calendar, ordered by start time.
    events_result = service.events().list(
        calendarId=calendar_id,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    # Extract the list of event dictionaries from the API response.
    events = events_result.get('items', [])

    # Build a DataFrame from the event data.
    # For each event:
    #   - 'title' is taken from the 'summary' field (defaulting to empty string if missing).
    #   - 'event_date' is taken from the 'start' field:
    #         - If the event is all-day, 'date' will be present.
    #         - If the event is timed, 'dateTime' will be present.
    #         - If neither is present, defaults to empty string.
    #   - 'description' is taken from the 'description' field (defaulting to empty string if missing).
    df = pd.DataFrame([
        {
            'title': e.get('summary', ''),
            'event_date': e['start'].get('date', e['start'].get('dateTime', '')),
            'description': e.get('description', '')
        }
        for e in events
    ])

    # Return the resulting DataFrame to the caller.
    return df

def list_events(service, calendar_id='primary', max_results=20):
    """
    Fetches upcoming events from the user's Google Calendar.

    Args:
        service: Authenticated Google Calendar API service instance.
        calendar_id (str): The calendar ID to fetch events from.
        max_results (int): Maximum number of events to fetch.

    Returns:
        list: A list of event dictionaries.
    """
    events_result = service.events().list(
        calendarId=calendar_id,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

def parse_chat(prompt):
    """
    Parses a natural language prompt into an event dictionary.

    Args:
        prompt (str): The user's natural language event description.
    Returns:
        dict: An event dictionary with keys 'title', 'description', 'event_date'.
    """
    # TODO: Implement LLM or rule-based parsing here
    # This is a stub that returns a dummy event
    return {'title': 'Sample Event', 'description': prompt, 'event_date': '2025-01-01'}


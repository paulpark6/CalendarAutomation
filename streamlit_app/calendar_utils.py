import pandas as pd
import streamlit as st
import ast
import pandas as pd
import json
from project_code.creating_calendar import create_schedule, get_or_create_calendar, load_user_input
from project_code.llm_methods import *


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

def parse_bulk(text):
    """
    Parses bulk-pasted text into a DataFrame of events.

    Args:
        text (str): The pasted text containing event information.
    Returns:
        pd.DataFrame: DataFrame with columns ['title', 'event_date', 'description'].
    """
    # TODO: Implement actual parsing logic. This is a stub.
    # For now, return an empty DataFrame with the right columns.
    return pd.DataFrame(columns=pd.Index(['title', 'event_date', 'description']))

def create_event(user, event):
    """
    Creates a single event in Google Calendar for the given user.

    Args:
        user (dict): The user information (from session state).
        event (dict): The event details (should have 'title', 'description', 'event_date').
    Returns:
        dict: The created event's details or API response.
    """
    service = st.session_state['service']
    calendar_id = 'primary'  # You may want to make this dynamic
    # TODO: Use your actual event creation logic here
    # This is a stub that returns the event dict
    # Replace with call to create_single_event or similar
    return {'status': 'created', **event}

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

def show_bulk():
    """
    Renders the Bulk Upload page in the Streamlit app, allowing users to add multiple events to their Google Calendar
    either by pasting text (to be parsed by an LLM) or by uploading a .txt file.

    Purpose:
        - Provides a UI for users to input multiple events at once.
        - Supports two input methods: free-form text (LLM parsing) and file upload.
        - Displays parsed events in a DataFrame.
        - Allows users to create all parsed events in their Google Calendar.

    Parameters:
        None (uses Streamlit's session state and UI components).

    Returns:
        None (renders UI components and triggers event creation as a side effect).
    """
    # Render the Bulk Upload page header
    st.header("📋 Bulk Upload")
    # Let user choose input method: paste text or upload file
    option = st.radio("Choose input method:", ["Paste text (LLM)", "Upload .txt file"])
    df = None  # DataFrame to hold parsed events

    if option == "Paste text (LLM)":
        st.info("LLM-based parsing is under development and not available yet. Please use the file upload option with a correctly formatted file.")
    elif option == "Upload .txt file":
        # File uploader for .txt files
        file = st.file_uploader("Upload a .txt file", type=["txt"])
        if file and st.button("Parse file"):
            # Convert the dictionary to a pandas DataFrame
            df = project_code.load_user_input()

    if df is not None:
        # Display the parsed events as a DataFrame
        st.dataframe(df)
        if st.button("Create Events"):
            # Get the Google Calendar API service from session state
            service = st.session_state['service']
            # Get or create the target calendar
            calendar_id = get_or_create_calendar(service)
            # Load or initialize recent_keys_stack as needed (replace with actual logic)
            recent_keys_stack = []  # Replace with actual loading logic
            # Create events in the calendar and update the stack
            updated_stack = create_schedule(service, calendar_id, df, recent_keys_stack)
            # Show success message after events are created
            st.success("Events created!")
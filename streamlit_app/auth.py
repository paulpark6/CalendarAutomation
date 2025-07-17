import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle
import os


# Authentication and user data management for Google Calendar integration in Streamlit.

# This module provides functions to handle Google OAuth login, persistent user data storage,
# and session management for a privacy-respecting calendar assistant app.


SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'client_secret.json'  # Downloaded from Google Cloud Console
USER_DATA_DIR = 'UserData'  # Directory to store user data

def get_user_data_path(email):
    """
    Returns the file path for storing a user's data based on their email address.

    Parameters:
        email (str): The user's email address, used as a unique identifier.
    Returns:
        str: The file path where the user's data (credentials and app data) is stored.
    """
    return os.path.join(USER_DATA_DIR, f"{email}.pkl")

def save_user_data(email, creds, app_data):
    """
    Saves the user's credentials and application data to a file for persistent storage.

    Parameters:
        email (str): The user's email address (used as the file key).
        creds (Credentials): Google OAuth credentials object.
        app_data (dict): Arbitrary application data to persist for the user.
    Side Effects:
        Writes a pickle file to disk in USER_DATA_DIR named after the user's email.
    """
    with open(get_user_data_path(email), 'wb') as f:
        pickle.dump({'creds': creds, 'app_data': app_data}, f)

def load_user_data(email):
    """
    Loads the user's credentials and application data from persistent storage.

    Parameters:
        email (str): The user's email address (used as the file key).
    Returns:
        dict or None: A dictionary with keys 'creds' and 'app_data' if found, else None.
    Side Effects:
        Reads a pickle file from disk. Returns None if file does not exist.
    """
    try:
        with open(get_user_data_path(email), 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None

def login_with_google():
    """
    Runs the Google OAuth flow, obtains user credentials, and builds a Google Calendar service object.

    Returns:
        tuple: (email, creds, service)
            email (str): The user's Google account email address.
            creds (Credentials): The OAuth credentials object.
            service (Resource): The Google Calendar API service object.
    Side Effects:
        Opens a browser window for user authentication.
        May create a local server for OAuth redirect.
    """
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('calendar', 'v3', credentials=creds)
    # Get user email
    user_info = service.calendarList().list().execute()
    email = user_info['items'][0]['id']  # This is a hack; for robust email, use the People API
    return email, creds, service

def show_login_page():
    """
    Renders the Streamlit login page for Google authentication.
    Handles the login button, runs the OAuth flow, stores credentials and user data in session state,
    and persists new user data if needed.

    Parameters:
        None (uses Streamlit session state and UI).
    Side Effects:
        Updates st.session_state with 'email', 'creds', 'service', and optionally 'app_data'.
        May write new user data to disk if first login.
        Reruns the Streamlit app after successful login.
    """
    st.title("🔐 Sign in with Google")
    if st.button("Sign in with Google"):
        email, creds, service = login_with_google()
        st.session_state['email'] = email
        st.session_state['creds'] = creds
        st.session_state['service'] = service
        # Load or create user data
        user_data = load_user_data(email)
        if user_data is None:
            save_user_data(email, creds, {})  # Empty app data
        else:
            st.session_state['app_data'] = user_data['app_data']
        st.success(f"Signed in as {email}")
        st.rerun()

# In your main app:
if 'service' not in st.session_state:
    show_login_page()
    st.stop()
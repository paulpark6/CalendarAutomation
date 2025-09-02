# auth.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import json
import os
import streamlit as st

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = Path("UserData/token.json")  # keep your existing path

def _client_cfg_from_secrets() -> Dict[str, Any]:
    # Expect st.secrets["google_oauth"]["client_id"] and ["client_secret"]
    gi = st.secrets["google_oauth"]["client_id"]
    gs = st.secrets["google_oauth"]["client_secret"]
    return {
        "web": {
            "client_id": gi,
            "project_id": "streamlit-app",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_secret": gs,
            "redirect_uris": [st.secrets["google_oauth"]["redirect_uri"]],
            "javascript_origins": ["https://"+st.secrets["google_oauth"]["redirect_uri"].split("://",1)[-1].split("/",1)[0]],
        }
    }

def get_user_service_local() -> Tuple[Optional[Any], Optional[Credentials]]:
    """Your existing local flow using flow.run_local_server(...)."""
    # --- keep your current implementation; example skeleton:
    client_cfg = _client_cfg_from_secrets()
    flow = Flow.from_client_config(client_cfg, scopes=SCOPES)
    flow.run_local_server(host="localhost", port=0, prompt="consent", access_type="offline", include_granted_scopes="true")
    creds = flow.credentials
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds, cache_discovery=False), creds

def get_user_service_web() -> Tuple[Optional[Any], Optional[Credentials]]:
    """Streamlit Cloud-friendly OAuth using query params."""
    client_cfg = _client_cfg_from_secrets()
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]  # e.g. "https://calendarautomation.streamlit.app/"
    flow = Flow.from_client_config(client_cfg, scopes=SCOPES, redirect_uri=redirect_uri)

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    st.session_state["oauth_state"] = state

    # Show the sign-in link until we have a ?code=...&state=... in the URL
    params = st.query_params  # Streamlit Cloud-friendly
    # st.query_params values can be str or list-like; normalize:
    def _get(q, default=None):
        v = params.get(q, default)
        if isinstance(v, list):
            return v[0] if v else default
        return v

    code = _get("code")
    returned_state = _get("state")

    if not code:
        st.info("To use Google Calendar, please sign in.")
        st.link_button("Sign in with Google", auth_url, use_container_width=True)
        return None, None

    # Validate state (CSRF protection)
    if not returned_state or returned_state != state:
        st.error("Invalid OAuth state. Please try signing in again.")
        st.link_button("Sign in with Google", auth_url)
        return None, None

    # Exchange the code for tokens
    flow.fetch_token(code=code)
    creds: Credentials = flow.credentials

    # Persist
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    st.session_state["google_creds_json"] = creds.to_json()

    return build("calendar", "v3", credentials=creds, cache_discovery=False), creds

def get_user_service():
    mode = st.secrets.get("app", {}).get("mode", "cloud")
    if mode == "dev":
        return get_user_service_local()   # your existing localhost flow
    else:
        return get_user_service_web()     # the Streamlit Cloud-friendly flow


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
    """Streamlit Cloud-friendly OAuth using query params, but NO UI here."""
    client_cfg = _client_cfg_from_secrets()
    redirect_uri = st.secrets["google_oauth"]["redirect_uri"]

    # --- Read query params FIRST (avoid minting a new state too early) ---
    params = st.query_params
    def _one(v): return v[0] if isinstance(v, list) else v
    code = _one(params.get("code"))
    returned_state = _one(params.get("state"))
    expected_state = st.session_state.get("oauth_state")  # may be None on fresh session

    # If Google redirected back with a code → exchange it (be permissive on state)
    if code:
        flow = Flow.from_client_config(client_cfg, scopes=SCOPES, redirect_uri=redirect_uri)
        # If you really want to enforce state, uncomment the next 3 lines:
        # if expected_state and returned_state != expected_state:
        #     # session refreshed; start over
        #     st.session_state.pop("oauth_state", None); st.session_state.pop("oauth_auth_url", None); return None, None
        flow.fetch_token(code=code)
        creds: Credentials = flow.credentials

        # persist & cache
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
        st.session_state["credentials"] = creds
        st.session_state["google_creds_json"] = creds.to_json()

        # cleanup query params so we don't loop
        try: st.query_params.clear()
        except Exception: pass

        return build("calendar", "v3", credentials=creds, cache_discovery=False), creds

    # No code yet → prepare an auth URL ONCE and hand it to the UI to render
    if "oauth_auth_url" not in st.session_state or "oauth_state" not in st.session_state:
        flow_tmp = Flow.from_client_config(client_cfg, scopes=SCOPES, redirect_uri=redirect_uri)
        auth_url, state = flow_tmp.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        st.session_state["oauth_auth_url"] = auth_url
        st.session_state["oauth_state"] = state

    # IMPORTANT: no st.info / no st.link_button here — UI renders the button.
    return None, None

def get_user_service():
    mode = st.secrets.get("app", {}).get("mode", "cloud")
    if mode == "dev":
        return get_user_service_local()   # your existing localhost flow
    else:
        return get_user_service_web()     # the Streamlit Cloud-friendly flow


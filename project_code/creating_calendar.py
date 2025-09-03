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


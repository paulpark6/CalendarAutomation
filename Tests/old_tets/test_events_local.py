import sys
import os

# Ensure the parent directory is in sys.path so 'project_code' can be imported as a package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project_code.old_methods.creating_calendar import save_events, load_events
from project_code.auth import *

import pandas as pd
service = get_user_service()
email = get_authenticated_email(service)
# example usage of saving events
data = save_events(email, service,
[    {
            "user_email": email,
            "title": "Test Event",
            "description": "This is a test event",
            "event_date": "2025-01-01",
            "event_time": "10:00",
            "end_date": "2025-01-01",
            "timezone": "America/Toronto"
    },
    {
            "user_email": email,
            "title": "Test Event3",
            "description": "This is a test event",
            "event_date": "2025-01-01",
            "event_time": "10:00",
            "end_date": "2025-01-01",
            "timezone": "America/Toronto"
    }])

data = save_events(email, service,
[    {
            "user_email": email,
            "title": "Test Event2",
            "description": "This is a test event",
            "event_date": "2025-01-01",
            "event_time": "10:00",
            "end_date": "2025-01-01",
            "timezone": "America/Toronto"
    }])

print(data)

# example usage of loading saved events
print(load_events(email).head())

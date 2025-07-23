import sys
import os

# Ensure the parent directory is in sys.path so 'project_code' can be imported as a package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project_code.creating_calendar import save_events, load_events
import pandas as pd
TEST_EMAIL = "test@test.com"

# example usage of saving events
save_events(TEST_EMAIL, 
[    {
            "user_email": TEST_EMAIL,
            "unique_key": "abc12w3",
            "google_calendar_id": "gcal1",
            "service": "test_service",
    }])

# example usage of loading saved events
print(load_events(TEST_EMAIL).head())

from project_code.creating_calendar import save_user_event, load_user_events, save_user_events_from_dataframe
import os
import json
import pandas as pd
import pytest

# Test email and path
TEST_EMAIL = "testuser@example.com"
TEST_PATH = f"UserData/{TEST_EMAIL}_created_events.json"

# Clean up before test
if os.path.exists(TEST_PATH):
    os.remove(TEST_PATH)

# 1. Add a new event
event1 = {
    "user_email": TEST_EMAIL,
    "unique_key": "abc123",
    "google_calendar_id": "gcal1",
    "service": "test_service",
    "title": "Test Event 1",
    "event_date": "2024-07-01",
    "description": "First event",
    "calendar_id": "cal1",
    "event_time": "10:00",
    "end_date": "2024-07-01",
    "timezone": "America/Toronto",
    "notifications": [],
    "invitees": []
}
save_user_event(TEST_EMAIL, event1)

# 2. Add a second event with a different unique_key
event2 = event1.copy()
event2["unique_key"] = "def456"
event2["title"] = "Test Event 2"
save_user_event(TEST_EMAIL, event2)

# 3. Add an event with the same unique_key as event1 (should replace event1)
event1_update = event1.copy()
event1_update["description"] = "First event UPDATED"
save_user_event(TEST_EMAIL, event1_update)

# 4. Load and print all events
df = load_user_events(TEST_EMAIL)
print("DataFrame loaded from file:")
print(df)

# 5. Check file contents directly (optional)
with open(TEST_PATH, "r") as f:
    print("Raw JSON file contents:")
    print(json.load(f))

test_email = "pytestuser@example.com"
test_path = f"UserData/{test_email}_created_events.json"

def setup_module(module):
    # Clean up before tests
    if os.path.exists(test_path):
        os.remove(test_path)

def teardown_module(module):
    # Clean up after tests
    if os.path.exists(test_path):
        os.remove(test_path)

def make_event(unique_key, title):
    return {
        "user_email": test_email,
        "unique_key": unique_key,
        "google_calendar_id": f"gcal_{unique_key}",
        "service": "pytest_service",
        "title": title,
        "event_date": "2024-07-01",
        "description": f"Event {title}",
        "calendar_id": "pytest_cal",
        "event_time": "10:00",
        "end_date": "2024-07-01",
        "timezone": "America/Toronto",
        "notifications": [],
        "invitees": []
    }

def test_save_user_events_from_dataframe_with_dataframe():
    df = pd.DataFrame([
        make_event("key1", "Event 1"),
        make_event("key2", "Event 2")
    ])
    save_user_events_from_dataframe(test_email, df)
    df_loaded = load_user_events(test_email)
    assert len(df_loaded) == 2
    assert set(df_loaded["unique_key"]) == {"key1", "key2"}

def test_save_user_events_from_dataframe_with_list():
    events = [
        make_event("key3", "Event 3"),
        make_event("key4", "Event 4")
    ]
    save_user_events_from_dataframe(test_email, events)
    df_loaded = load_user_events(test_email)
    # Should now have 4 unique events
    assert len(df_loaded) == 4
    assert set(df_loaded["unique_key"]) == {"key1", "key2", "key3", "key4"}

def test_save_user_events_from_dataframe_deduplication():
    # Add duplicate key
    events = [make_event("key1", "Event 1 updated"), make_event("key5", "Event 5")]
    save_user_events_from_dataframe(test_email, events)
    df_loaded = load_user_events(test_email)
    # key1 should be updated, key5 added
    assert len(df_loaded) == 5
    assert "key5" in set(df_loaded["unique_key"])
    # The title for key1 should be "Event 1 updated"
    updated_row = df_loaded[df_loaded["unique_key"] == "key1"].iloc[0]
    assert updated_row["title"] == "Event 1 updated" 
import pytest
import project_code.calendar_methods as calendar_methods
from project_code.calendar_methods import _cache_path, _load_cache, _save_cache, _store_minimal_local, USER_DATA_DIR
import os
import json
import importlib
from typing import Dict, Any

# --- testing cache path ---
def test_cache_path():
    email = "bob@example.com"
    expected = os.path.join(USER_DATA_DIR, "bob@example.com_events.json")
    assert _cache_path(email) == expected

# --- testing load cache and save cache ---
@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """
    Redirect USER_DATA_DIR to a tmp dir for the lifetime of the test
    and reload the module so internal code picks up the new path.
    """
    original = calendar_methods.USER_DATA_DIR
    monkeypatch.setattr(calendar_methods, "USER_DATA_DIR", str(tmp_path))
    importlib.reload(calendar_methods)
    yield tmp_path          # give the test a handle to the temp folder
    monkeypatch.setattr(calendar_methods, "USER_DATA_DIR", original)
    importlib.reload(calendar_methods)

# test to see if the file does not exist, it returns an empty list
def test_load_file_missing(sandbox):
    # 1️⃣ File does NOT exist
    assert calendar_methods._load_cache("nobody@example.com") == []

# test to see if the file exists, it returns the events in the file

def test_load_valid_json(sandbox):
    email = "alice@example.com"
    records = [{"title": "Meeting", "start": "2024-06-10T10:00:00", "end": "2024-06-10T11:00:00", "unique_key": "123"}]
    calendar_methods._save_cache(email, records)
    assert calendar_methods._load_cache(email) == records

# test to see if the file is empty, it returns an empty list
def test_load_empty_file(sandbox):
    email = "alice@example.com"
    cache_path = calendar_methods._cache_path(email)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    # Create an empty file (simulate empty cache)
    with open(cache_path, "w") as f:
        f.write("")
    assert calendar_methods._load_cache(email) == []

# test to see if the file is invalid JSON, it returns an empty list
def test_load_invalid_json(sandbox):
    email = "alice@example.com"
    cache_path = calendar_methods._cache_path(email)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    # Write invalid JSON directly
    with open(cache_path, "w") as f:
        f.write("{not: valid json}")
    assert calendar_methods._load_cache(email) == []

# test to see if the file is not a list, it returns an empty list
def test_load_json_not_list(sandbox):
    email = "alice@example.com"
    # Use _save_cache to write a non-list (invalid) structure
    calendar_methods._save_cache(email, [{"not": "a list"}])
    assert calendar_methods._load_cache(email) == [{"not": "a list"}]

# --- testing save cache ---
def test_save_cache(sandbox):
    email = "alice@example.com"
    records = [{"title": "Meeting", "start": "2024-06-10T10:00:00", "end": "2024-06-10T11:00:00", "unique_key": "123"}]
    calendar_methods._save_cache(email, records)
    assert calendar_methods._load_cache(email) == records




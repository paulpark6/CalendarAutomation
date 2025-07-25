import pytest
from project_code.calendar_methods import _sha1, generate_unique_key

# --------- SHA1 tests ---------
def test_sha1_known_value():
    # Test known value from docstring
    assert _sha1("hello") == 'aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d'

def test_sha1_consistency():
    # Test that repeated calls with the same input give the same result
    s = "pytest"
    assert _sha1(s) == _sha1(s)

def test_sha1_different_inputs():
    # Test that different inputs give different hashes
    assert _sha1("a") != _sha1("b")

# --------- Unique key tests ---------  

def test_generate_unique_key_determinism():
    key1 = generate_unique_key("Meeting", "2024-06-10T10:00:00", "2024-06-10T11:00:00", "America/Toronto")
    key2 = generate_unique_key("Meeting", "2024-06-10T10:00:00", "2024-06-10T11:00:00", "America/Toronto")
    assert key1 == key2

def test_generate_unique_key_uniqueness():
    key1 = generate_unique_key("Meeting", "2024-06-10T10:00:00", "2024-06-10T11:00:00", "America/Toronto")
    key2 = generate_unique_key("Meeting", "2024-06-10T10:00:00", "2024-06-10T12:00:00", "America/Toronto")
    assert key1 != key2

def test_generate_unique_key_empty_fields():
    key1 = generate_unique_key("", "", "", "")
    key2 = generate_unique_key("", "", "", "")
    assert key1 == key2
    key3 = generate_unique_key("A", "", "", "")
    assert key1 != key3

def test_generate_unique_key_different_fields():
    key1 = generate_unique_key(title = "Meeting", start_iso = "2024-06-10T10:00:00", tz = "America/New_York")
    key2 = generate_unique_key(title = "Meeting", start_iso = "2024-06-10T10:00:00", end_iso = "2024-06-10T11:00:00", tz = "America/New_York")
    assert key1 != key2

def test_generate_unique_key_same_fields():
    key1 = generate_unique_key(title = "Meeting", start_iso = "2024-06-10T10:00:00", tz = "America/Toronto")
    key2 = generate_unique_key(title = "Meeting", start_iso = "2024-06-10T10:00:00", tz = "America/Toronto")
    assert key1 == key2

def test_generate_unique_key_empty_parameters():
    key1 = generate_unique_key(title="", start_iso="")
    key2 = generate_unique_key(title="", start_iso="")
    assert key1 == key2
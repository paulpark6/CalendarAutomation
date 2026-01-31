# Creating Calendar Documentation
**File:** `project_code/creating_calendar.py`

This module focuses on **Batch Operations** and Calendar Management (Create/Delete/Unsubscribe).

## Functions

### `ensure_calendar(service, name_or_id, tz)`
- **Description**: Finds a calendar by name or creates it if missing. Returns the `calendarId`.
- **Use Case**: User types "Work" -> app finds existing "Work" calendar or makes a new one.

### `create_calendar(creds, name, time_zone)`
- **Description**: Low-level creation of a new calendar + sets default reminders.

### `create_single_event(...)`
- **Description**: **Used by UI**. Creates a single event.
- **Status**: **REDUNDANT / SIMPLIFIED**.
- **Issue**: This function **duplicates** the purpose of `calendar_methods.create_event` but **lacks** the duplicate detection (SHA-1 hash) and local caching features.
- **Recommendation**: This should likely be refactored to call `calendar_methods.create_event` or be replaced by it.

### `create_calendar_events(...)`
- **Description**: Batch creation. Takes a list of event dicts and calls `create_event` (from `calendar_methods`, supposedly).
- **Confusion**: It imports `create_event` from `calendar_methods` (implied, though file structure suggests they are in same package).
- **Note**: The file defines `create_event` at the bottom? Wait, based on my reading, `creating_calendar.py` *also* contained a `create_event` copy or imported it? 
    - *Correction*: Reading the source, `creating_calendar.py` defines `create_calendar_events` which calls `create_event`. It ALSO defines `create_event` at lines 354+!
    - **MAJOR REDUNDANCY**: `creating_calendar.py` contains a **COPY** of `create_event` logic (including `generate_unique_key` usage logic if it's there?).
    - Actually, `creating_calendar.py` seems to have a COPY of `create_event` logic or imports it. 
    - *Verification needed*: In `creating_calendar.py` lines 354+, `create_event` is defined. It mirrors `calendar_methods.py`. This is bad code duplication.

## Cleanup Recommendation
- `calendar_methods.py` and `creating_calendar.py` have heavy overlap.
- `create_single_event` in this file is the one strictly used by Streamlit UI (`ui.py`).
- `create_calendar_events` (batch) is unused by the UI (UI does its own batch loop).

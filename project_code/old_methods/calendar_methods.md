# Calendar Methods Documentation
**File:** `project_code/calendar_methods.py`

This module provides utility functions for Google Calendar integration, including a **local JSON cache** for resilience and duplicate detection.

## Key Features
- **Duplicate Detection**: Uses SHA-1 properties to prevent re-creating the same event.
- **Local Cache**: Stores a minimal record of events in `UserData/<email>_events.json`.

## Functions

### `generate_unique_key(title, start_iso, end_iso, tz)`
- **Description**: Creates a deterministic SHA-1 hash to uniquely identify an event.

### `_load_cache(email)` / `_save_cache(email, records)`
- **Description**: Internal helpers to read/write the JSON cache file.

### `create_event(...)`
- **Description**: **Core Function**. Inserts or Updates an event with robust duplicate handling.
- **Parameters**: `calendar_id`, `email`, `title`, `start_iso`, `end_iso`, `timezone_id`, `if_exists` ("skip", "update", "error").
- **Logic**:
    1. Generates a unique ID (`appCreated_<hash>`).
    2. Checks if event exists (using `calendar.events.get`).
    3. If exists: skips, updates, or errors based on `if_exists`.
    4. If new: inserts with `source` metadata.
    5. **Updates Local Cache**.

### `find_events(service, calendar_id, title, event_date)`
- **Description**: Searches for events by title or date.
- **Returns**: List of event dicts.

### `delete_event_by_fields(...)`
- **Description**: user-friendly deletion by title/date.

## Redundancy & Issues
- **`create_event` vs `create_single_event` (in `creating_calendar.py`)**:
    - This file contains the **smart** `create_event` that handles duplicates and caching.
    - `creating_calendar.py` contains a simpler `create_single_event` which is **currently used by the UI**.
    - **RESULT**: The current app is **NOT** using the duplicate detection or local caching defined here.

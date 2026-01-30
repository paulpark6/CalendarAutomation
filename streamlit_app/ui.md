# UI Documentation
**File:** `streamlit_app/ui.py`

This file handles the Frontend rendering. It has been recently refactored into a Dashboard layout.

## Active Functions (Used in `main.py`)

### `render_chat_column(service)`
- **Description**: Renders the left-hand chat instructions, "Import" button, and Session Stats (Assignments/Completed tasks).

### `render_calendar_column(service)`
- **Description**: Renders the middle column with the `streamlit-calendar` widget and View controls (Month/Week/Day).

### `render_right_column(service)`
- **Description**: Renders the right-column "Tasks" list (Today / This Week).

### `render_event_loader_section(service)`
- **Description**: Renders the bottom section for "Event Entry & Validation". Includes JSON paste and `st.data_editor` for fixing events before creation.

### `show_login_page()`
- **Description**: Renders the Google Sign-In button if not authenticated.

## Unused / Legacy Functions (Recommend Deletion)

### `show_home(service)`
- **Status**: **Unused**. Replaced by the Dashboard columns. 
- **Recommendation**: Delete.

### `show_event_builder(service)`
- **Status**: **Unused**. Replaced by `render_event_loader_section`.
- **Recommendation**: Delete.

## Redundancy & Issues
- **Batch Creation Logic**: `_create_events_batch` implements its own loop to create events. It calls `create_mod.create_single_event` (from `creating_calendar.py`). 
    - **Issue**: It bypasses the "smart" `create_event` (with deduplication) found in `calendar_methods.py`.
    - **Fix**: Update `_create_events_batch` to use `calendar_methods.create_event` (or a unified helper) so that duplicate prevention works.
- **Event Fetching**: `_fetch_upcoming_events` is a simple wrapper around `service.events().list`. It works fine but duplicates similar logic in `calendar_methods.find_events`.

## Clean Up Plan
1. Delete `show_home`.
2. Delete `show_event_builder`.
3. Refactor `_create_events_batch` to use the robust `calendar_methods.create_event`.

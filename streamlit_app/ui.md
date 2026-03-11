# UI Package Documentation
**File:** `streamlit_app/ui.py`

This module handles all Streamlit frontend rendering. It has been recently refactored into a Dashboard layout with three columns (left, middle, right) plus a bottom section.

## Session State Management

### `init_session_state(service)`
- **Description**: Initializes session state with calendars and defaults.
- **Parameters**: `service` - Google Calendar API service instance
- **Side Effects**: Populates `st.session_state` with:
  - `calendars`: List of user's calendars
  - `active_calendar`: Primary calendar ID
  - `events_stack`: Stack for undo operations (if not already set)

## Page Rendering Functions (Used in `main.py`)

### `show_login_page()`
- **Description**: Renders the Google Sign-In button and OAuth flow instructions.
- **Returns**: None
- **Implementation**:
  - Generates OAuth authorization URL via `auth.web_authorization_url()`
  - Displays a styled "Continue with Google" button
  - Button links to the OAuth URL, which redirects back with `?code=` parameter
  - Main.py handles the callback code exchange

### `render_chat_column(service)`
- **Description**: Renders the left-hand column (25% width) with chat/input instructions and session stats.
- **Parameters**: `service` - Google Calendar API service
- **Content**:
  - Import/Chat instructions
  - Session statistics (events created, undo stack size)
  - Session usage counter

### `render_calendar_column(service)`
- **Description**: Renders the middle column (50% width) with the calendar widget and controls.
- **Parameters**: `service` - Google Calendar API service
- **Content**:
  - Streamlit-calendar widget showing month/week/day view
  - View toggle (Month / Week / Day)
  - Upcoming events display

### `render_right_column(service)`
- **Description**: Renders the right-hand column (25% width) with task information.
- **Parameters**: `service` - Google Calendar API service
- **Content**:
  - "Tasks" list (Today and This Week)
  - Quick stats and calendar info

### `render_event_loader_section(service)`
- **Description**: Renders the bottom full-width section for event entry, validation, and batch creation.
- **Parameters**: `service` - Google Calendar API service
- **Content**:
  - Tabs for different input modes (JSON paste, file upload, chat)
  - `st.data_editor` for reviewing/editing events before creation
  - "Create Events" button that triggers batch creation
  - Undo/history controls

## Internal Helper Functions

### `_fetch_upcoming_events(service, calendar_id: str, limit: int = 5)`
- **Description**: Fetches upcoming events from a calendar.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Calendar to fetch from
  - `limit`: Number of events to return
- **Returns**: List of event dictionaries
- **Implementation**: Calls `service.events().list()` with appropriate time bounds

### `_create_events_batch(service, calendar_id: str, events: List[Dict])`
- **Description**: Creates multiple events in a batch operation.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Target calendar ID
  - `events`: List of event dictionaries (Google Calendar API format)
- **Returns**: Dictionary with creation results and statistics
- **Implementation**:
  - Loops through each event
  - Calls `create_single_event()` from `project_code.creating_calendar`
  - Tracks created IDs for undo stack
  - Shows progress to user

### `_render_event_preview_table(events: List[Dict])`
- **Description**: Displays events in an editable table for user review.
- **Parameters**: `events` - List of event dictionaries
- **Returns**: None (renders to Streamlit)
- **Implementation**: Uses `st.data_editor()` for inline editing before creation

## Legacy / Unused Functions (Recommend Deletion)

### `show_home(service)` 
- **Status**: **UNUSED** — Replaced by the Dashboard columns
- **Recommendation**: Delete

### `show_event_builder(service)`
- **Status**: **UNUSED** — Replaced by `render_event_loader_section`
- **Recommendation**: Delete

## Known Issues & Refactoring Needs

### Issue 1: Bypass of Deduplication Logic
- **Problem**: `_create_events_batch()` calls `create_single_event()` which bypasses the smart deduplication in `calendar_methods.create_event()`
- **Impact**: Duplicate events may be created if user re-runs batch
- **Fix**: Update `_create_events_batch()` to use `calendar_methods.create_event()` instead

### Issue 2: Event Fetching Duplication
- **Problem**: `_fetch_upcoming_events()` duplicates similar logic in `project_code.calendar_methods.find_events()`
- **Impact**: Maintenance burden if one changes
- **Fix**: Consolidate into single function in `calendar_methods.py`

### Issue 3: Missing Undo Implementation
- **Status**: Undo stack is created but may not be fully connected to the "Undo" button
- **Fix**: Ensure `_create_events_batch()` properly pushes to undo stack and delete operations pop from it

## Clean Up Plan
1. Delete `show_home()`
2. Delete `show_event_builder()`
3. Refactor `_create_events_batch()` to use `calendar_methods.create_event()` for deduplication
4. Consolidate event fetching logic
5. Verify undo stack is fully connected to UI buttons

## Data Flow

```
main.py
  ├── show_login_page() → User clicks Google Sign In
  ├── exchange OAuth code → credentials saved to session_state
  ├── init_session_state() → load calendars
  └── render_columns()
      ├── render_chat_column() → display stats
      ├── render_calendar_column() → show calendar widget
      ├── render_right_column() → show tasks
      └── render_event_loader_section()
          ├── Show input tabs (paste/upload/chat)
          ├── _render_event_preview_table() → editable table
          └── "Create Events" button
              └── _create_events_batch() → create on Google Calendar
```

## Styling & Customization
- Column widths: 25% / 50% / 25% (left / center / right)
- Gap: "medium"
- Layout: "wide" (full browser width)
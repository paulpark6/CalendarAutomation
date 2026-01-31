# Debug Calendar Flow Script

**File**: `debug_calendar_flow.py`

## Purpose
This script runs a full "integration test" against your **real** Google Calendar account. It verifies that the new `calendar_creation` and `event_creation` modules work correctly with the actual Google API.

## What it does
1.  **Authenticates**: Uses your local `token.json` (if available) to log in.
2.  **Creates a Calendar**: Makes a new calendar named "Test Integration Calendar (Safe to Delete)".
3.  **Creates an Event**: Adds a test event to that calendar.
4.  **Updates an Event**: Modifies the event description.
5.  **Tests Deduplication**: Tries to add the *exact same event* again. Logic should catch it and return `status="skipped"`.
6.  **Cleanup**: Deletes the test calendar, ensuring your account isn't cluttered.

## How to Run
1.  Ensure you have a valid `token.json` in your project root (run the main app once to generate it if needed).
2.  Run the script:
    ```bash
    python debug_calendar_flow.py
    ```

## Expected Output
```text
--- 1. Authenticating ---
Authenticated successfully.

--- 2. Create Calendar ---
Created Calendar: Test Integration Calendar (Safe to Delete) (ID: <some_id>)

--- 3. Create Event ---
Event 1 Created: True (ID: <event_id>)

--- 4. Update Event ---
Event Updated: updated

--- 5. Test Dedupe (Skip) ---
Event 2 (Duplicate): Created=False, Status=skipped
Dedupe SUCCESS: Skipped creation and found existing ID.

--- 6. Cleanup (Delete Calendar) ---
Cleanup Result: {'calendar_id': '<some_id>', 'action': 'deleted'}
```

# Auth Package Documentation
**File:** `project_code/auth.py`

This module handles Google OAuth authentication and session management. It provides helpers for both "Service Account" style (or pre-authed) checks and "Web Flow" (OAuth 2.0) for user login.

## Functions

### `build_calendar_service(creds)`
- **Description**: Builds a Google Calendar API service instance. Refreshes credentials if expired.
- **Parameters**: `creds` (google.oauth2.credentials.Credentials)
- **Returns**: `googleapiclient.discovery.Resource`

### `assert_service_has_identity(service)`
- **Description**: Validates that the service has valid credentials and can access the user's `calendarList`.
- **Returns**: The ID of the primary calendar (usually the user's email).
- **Raises**: `AssertionError` if auth fails.

### `authorized_session_from_service(service)`
- **Description**: Returns an `AuthorizedSession` from a given service instance.
- **Dependency**: `google.auth.transport.requests.AuthorizedSession`

### `web_authorization_url(client_id, client_secret, redirect_uri)`
- **Description**: Generates the Google OAuth authorization URL for the user to visit.
- **Use Case**: Step 1 of the OAuth flow (Log in button).

### `web_exchange_code(client_id, client_secret, redirect_uri, code)`
- **Description**: Exchanges the auth code returned by Google for credentials.
- **Use Case**: Step 2 of the OAuth flow (Callback handling).

### `refresh_if_needed(creds)`
- **Description**: Refreshes the access token if it is expired and a refresh token exists.
- **Returns**: `creds` (updated)

### `get_authenticated_email(service, creds)`
- **Description**: Retrieves the user's email via the `userinfo` endpoint or falls back to the primary calendar ID.

### `get_default_calendar_timezone(service, calendar_id)`
- **Description**: Helper to fetch the timezone of a specific calendar.
- **Returns**: Timezone string (e.g. "America/New_York") or "UTC".

### `revoke_google_token(creds)`
- **Description**: Attempts to revoke the current token with Google (best-effort logout).

### `logout_and_delete_token(creds)`
- **Description**: Wrapper to revoke the token. (Does not actually delete local files in this implementation).

## Usage & Dependencies
- **Dependencies**: `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `requests`.
- **Primary User**: `streamlit_app/ui.py` (for login flow) and `main.py` (for session management).

## Redundancy / Improvements
- `authorized_session_from_service` is similar to `creating_calendar._credentials_from_service` logic but slightly cleaner.

# 📅 Calendar Automation Project

This project automates calendar-related tasks using the **Google Calendar API** and provides a user interface via Streamlit. It includes tools for creating, managing, and interacting with Google Calendar events programmatically and through a web app.

---

## 🚀 Project Overview

- **Automates Google Calendar tasks**: Create, update, and manage events.
- **Streamlit web app**: User-friendly interface for calendar operations.
- **Modular codebase**: Organized into authentication, calendar logic, database, and UI components.

---

## ✅ Prerequisites

- Python 3.8 or newer
- The provided `requirements.txt` file
- A Google Cloud project with the Google Calendar API enabled
- Your `credentials.json` file downloaded from the Google Developer Console

---

## 💻 Environment Setup

### 1. Create and Activate a Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv sandboxenv
source sandboxenv/bin/activate
```

**Windows:**
```powershell
python -m venv sandboxenv
.\sandboxenv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🔐 Google Calendar API Authentication

### Step 1: Obtain Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Calendar API** for your project.
3. Download the OAuth 2.0 Client ID credentials and save as:
   ```
   ./UserData/credentials.json
   ```

### Step 2: Automatic Authentication & Token Generation
When you first log in to the app with your Google account, you will be prompted to authenticate with Google. The app will automatically generate and store the required `token.json` file in the `UserData/` directory after successful authentication. You do **not** need to run any manual Python commands for token generation.

> If browser authentication does not open automatically, follow the troubleshooting steps below.

---

## 🏗️ Project Structure

Your project directory should look like this:

```
CalendarProject/
├── Notebooks/
│   └── calendar_functions.ipynb
├── project_code/
│   ├── __init__.py
│   ├── auth.py              # Google authentication logic
│   ├── creating_calendar.py # Calendar creation and event logic
│   ├── db.py                # Database helpers (if used)
│   ├── llm_methods.py       # LLM-related methods (if any)
│   └── methods.py           # General utility methods
├── streamlit_app/
│   ├── __init__.py
│   ├── auth.py              # Streamlit authentication helpers
│   ├── calendar_utils.py    # Calendar utility functions for UI
│   ├── main.py              # Streamlit app entry point
│   └── ui.py                # UI components
├── UserData/
│   ├── credentials.json     # Google API credentials
│   └── token.json           # Generated after authentication
├── Tests/
│   ├── __init__.py
│   ├── test_calendar_api.py
│   ├── test_creating_calendar.py
│   └── test_parsers.py
├── run_app.py               # (If present) Script to run the app
├── requirements.txt
├── dev-requirements.txt
├── ReadMe.md
└── ...
```

---

## 🗂️ Main Code Modules

- **project_code/auth.py**: Handles Google OAuth and token management.
- **project_code/creating_calendar.py**: Functions for creating and managing calendar events.
- **project_code/db.py**: (Optional) Database interaction helpers.
- **project_code/llm_methods.py**: (Optional) LLM-related methods.
- **project_code/methods.py**: General utility functions.
- **streamlit_app/main.py**: Entry point for the Streamlit web app.
- **streamlit_app/ui.py**: UI components for the web app.
- **streamlit_app/calendar_utils.py**: Calendar-related utilities for the UI.

---

## ▶️ Running the Project

### 1. Run the Streamlit App
After authentication, start the web app:
```bash
streamlit run streamlit_app/main.py
```

### 2. Run Scripts Directly
You can also run scripts (e.g., for testing or automation):
```bash
python run_app.py
```
Or run individual modules as needed.

---

## 🧪 Testing

Run tests using your preferred test runner, e.g.:
```bash
pytest Tests/
```

---

## 🛟 Troubleshooting

- **PowerShell script restrictions (Windows):**
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
- **Browser authentication doesn't open:**
  In your code, use:
  ```python
  flow.run_local_server(open_browser=False)
  ```
- **Virtual environment issues:**
  Ensure you activate the correct environment before running scripts.

---

## ℹ️ Additional Notes

- Always use the Python executable from your activated virtual environment.
- Place your `credentials.json` and `token.json` in the `UserData/` directory.
- For more details, see comments in the code files and docstrings.

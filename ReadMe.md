# 📅 Calendar Automation Project

This project automates calendar-related tasks using the **Google Calendar API** and provides a user interface via Streamlit. It includes tools for creating, managing, and interacting with Google Calendar events programmatically and through a web app.

---

## 🚀 Project Overview

- **Automates Google Calendar tasks**: Create, update, and manage events.
- **Streamlit web app**: User-friendly interface for calendar operations.
- **Modular codebase**: Organized into authentication, calendar logic, database, and UI components.

---
🚀 How to Start the Project
1. Prerequisites
Ensure you have your credentials.json file inside the UserData/ folder.

2. Setup Environment
Open your terminal in the project root (CalendarProject/):

# Create virtual environment (if you haven't already)
python3 -m venv sandboxenv
# Activate it
## For APPLE
source sandboxenv/bin/activate
## For WINDOWS
.\sandboxenv\Scripts\Activate.ps1 
# Install dependencies
pip install -r requirements.txt
3. Run the App
Launch the Streamlit server:

streamlit run streamlit_app/main.py
A browser window will open (usually at http://localhost:8501).
Follow the "Continue with Google" prompt to sign in.

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
│   ├── db.py                # Database helpers (NOT CURRENTLY IN USE)
│   ├── llm_methods.py       # LLM-related methods (if any)
│   └── calendar_methods.py  # Calendar utility methods
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

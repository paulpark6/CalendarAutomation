# run_app.py
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent   # repo root that contains streamlit_app/ and project_code/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit_app.main import main  # this import happens after we fix sys.path

if __name__ == "__main__":
    main()
import streamlit as st
import sys
import os

print("DEBUG: Test 1 - Basic streamlit import works", flush=True)
st.write("✅ Basic Streamlit works!")

# Test path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print(f"DEBUG: Test 2 - Path setup done: {ROOT}", flush=True)

# Test auth import
try:
    from project_code.auth import *
    print("DEBUG: Test 3 - Auth import successful", flush=True)
    st.write("✅ Auth module imported!")
except Exception as e:
    print(f"DEBUG: Test 3 FAILED - Auth import error: {e}", flush=True)
    st.error(f"❌ Auth import failed: {e}")
    st.stop()

# Test ui import
try:
    from streamlit_app import ui
    print("DEBUG: Test 4 - UI import successful", flush=True)
    st.write("✅ UI module imported!")
except Exception as e:
    print(f"DEBUG: Test 4 FAILED - UI import error: {e}", flush=True)
    st.error(f"❌ UI import failed: {e}")
    st.stop()

st.success("✅ All imports successful!")
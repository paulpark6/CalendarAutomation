import streamlit as st

def main():
    st.set_page_config(page_title="Calendar Automation", page_icon="📅", layout="wide")
    st.title("Calendar Agent 📅")
    st.write("Hello! The app is running.")
    st.success("✅ Simple version works!")

if __name__ == "__main__":
    main()
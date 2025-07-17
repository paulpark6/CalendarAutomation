import streamlit as st
from project_code.llm_methods import *
from project_code.creating_calendar import *

def show_home():
    st.header("🏠 Home")
    user = st.session_state.user
    st.write(f"Welcome, **{user['name']}**!")
    events = list_events(user)
    st.dataframe(events)

def show_bulk():
    st.header("📋 Bulk Upload")
    text = st.text_area("Paste events…")
    if st.button("Parse Bulk"):
        df = parse_bulk(text)
        st.dataframe(df)
        if st.button("Create Events"):
            for ev in df.to_dict(orient="records"):
                create_event(user=st.session_state.user, event=ev)
            st.success("Events created!")

def show_chat():
    st.header("💬 Chat Parser")
    prompt = st.chat_input("Describe your event")
    if prompt:
        ev = parse_chat(prompt)
        st.json(ev)
        if st.button("Add to Calendar"):
            create_event(user=st.session_state.user, event=ev)
            st.success("Event added!")

def show_settings():
    st.header("⚙️ Settings")
    st.write("…your settings UI here…")

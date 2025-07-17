# import os
# import sqlite3
# from typing import Dict, List
# def get_conn():
#     conn = sqlite3.connect("UserData/app.db", check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     return conn

# def init_db():
#     with get_conn() as conn:
#         conn.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             sub TEXT PRIMARY KEY,
#             email TEXT,
#             name TEXT,
#             calendar_id TEXT
#         )""")
#         conn.execute("""
#         CREATE TABLE IF NOT EXISTS history (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_sub TEXT,
#             action TEXT,
#             payload TEXT,
#             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY(user_sub) REFERENCES users(sub)
#         )""")

# def get_or_create_user(sub: str, email: str, name: str):
#     conn = get_conn()
#     cur = conn.execute("SELECT * FROM users WHERE sub = ?", (sub,))
#     row = cur.fetchone()
#     if row:
#         return row
#     conn.execute(
#         "INSERT INTO users (sub, email, name) VALUES (?, ?, ?)",
#         (sub, email, name)
#     )
#     conn.commit()
#     return {"sub": sub, "email": email, "name": name, "calendar_id": None}

# def save_calendar_id(sub: str, calendar_id: str):
#     conn = get_conn()
#     conn.execute(
#         "UPDATE users SET calendar_id = ? WHERE sub = ?",
#         (calendar_id, sub)
#     )
#     conn.commit()

# def record_history(sub: str, action: str, payload: str):
#     conn = get_conn()
#     conn.execute(
#         "INSERT INTO history (user_sub, action, payload) VALUES (?, ?, ?)",
#         (sub, action, payload)
#     )
#     conn.commit()

# def load_history(sub: str) -> List[Dict]:
#     conn = get_conn()
#     cur = conn.execute(
#         "SELECT action, payload, timestamp FROM history WHERE user_sub = ? ORDER BY timestamp DESC",
#         (sub,)
#     )
#     return [dict(row) for row in cur.fetchall()]

import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import datetime as dt
import os
from typing import Optional

# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = os.path.abspath("users.db")

# ============================================================
# DATABASE
# ============================================================

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_auth_tables():
    """Ensure DB and tables exist."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            event TEXT,
            success INTEGER,
            note TEXT,
            ts TEXT
        )
    """)
    conn.commit()
    conn.close()
    seed_default_users()

# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt())

def verify_password(plain: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed)
    except:
        return False

def log_event(username: str, event: str, success: int, note: str = None):
    conn = get_conn()
    cur = conn.cursor()
    ts = dt.datetime.utcnow().isoformat()
    cur.execute("INSERT INTO auth_log(username, event, success, note, ts) VALUES (?, ?, ?, ?, ?)",
                (username, event, success, note, ts))
    conn.commit()
    conn.close()

def add_user(username: str, plain_password: str, role: str = "user") -> bool:
    conn = get_conn()
    cur = conn.cursor()
    now = dt.datetime.utcnow().isoformat()
    try:
        ph = hash_password(plain_password)
        cur.execute("INSERT INTO users(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                    (username, ph, role, now))
        conn.commit()
        log_event(username, "create_user", 1, f"role={role}")
        return True
    except sqlite3.IntegrityError:
        log_event(username, "create_user", 0, "username_exists")
        return False
    finally:
        conn.close()

def reset_password(username: str, new_password: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    ph = hash_password(new_password)
    cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (ph, username))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    log_event(username, "reset_password", 1 if updated else 0, None)
    return updated

def get_user(username: str) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, password_hash, role, created_at FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"username": row[0], "password_hash": row[1], "role": row[2], "created_at": row[3]}

def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, role, created_at FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_logs(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, event, success, note, ts FROM auth_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ============================================================
# DEFAULT USERS (ADDED AUTOMATICALLY)
# ============================================================

def seed_default_users():
    """Create default admin and test accounts if DB empty."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()

    if count == 0:
        defaults = [
            ("Admin", "123456", "admin"),
            ("Test", "12345", "user"),
            ("Basel", "1122", "user")
        ]
        for u, p, r in defaults:
            add_user(u, p, r)
        print("✅ Default users created successfully.")

# ============================================================
# STREAMLIT LOGIN LOGIC
# ============================================================

def login_form():
    st.sidebar.subheader("🔐 Login")
    username = st.sidebar.text_input("Username", key="auth_username")
    password = st.sidebar.text_input("Password", type="password", key="auth_password")

    if st.sidebar.button("Login"):
        user = get_user(username)
        if not user:
            log_event(username, "login_attempt", 0, "no_user")
            st.sidebar.error("User not found.")
            return None

        stored = user["password_hash"]
        if isinstance(stored, str):
            stored = stored.encode('latin1')

        ok = verify_password(password, stored)
        if ok:
            st.session_state["user"] = user["username"]
            st.session_state["role"] = user["role"]
            log_event(username, "login_attempt", 1, "success")
            st.rerun()
        else:
            log_event(username, "login_attempt", 0, "wrong_password")
            st.sidebar.error("Incorrect password.")
            return None

def logout():
    if "user" in st.session_state:
        log_event(st.session_state.get("user"), "logout", 1, None)
    for k in ["user", "role"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

def require_login():
    init_auth_tables()
    if st.session_state.get("user"):
        st.sidebar.markdown(f"**Logged in as:** {st.session_state['user']} ({st.session_state.get('role','user')})")
        if st.sidebar.button("Logout"):
            logout()
        return True
    else:
        login_form()
        st.sidebar.info("Please log in to access the dashboard.")
        return False

# ============================================================
# ADMIN PANEL
# ============================================================

def admin_panel():
    st.header("🛡️ Admin Panel")
    st.subheader("➕ Create New User")

    new_user = st.text_input("New Username", key="admin_new_user")
    new_pass = st.text_input("New Password", type="password", key="admin_new_pass")
    new_role = st.selectbox("Role", ["user", "admin"], key="admin_new_role")

    if st.button("Create User"):
        if new_user and new_pass:
            ok = add_user(new_user, new_pass, new_role)
            if ok:
                st.success("✅ User created successfully.")
            else:
                st.error("⚠️ Username already exists.")
        else:
            st.error("Please enter username and password.")

    st.markdown("---")
    st.subheader("🔁 Reset Password")

    r_user = st.text_input("Username to Reset", key="admin_reset_user")
    r_pass = st.text_input("New Password", type="password", key="admin_reset_pass")

    if st.button("Reset Password"):
        if reset_password(r_user, r_pass):
            st.success("✅ Password reset successfully.")
        else:
            st.error("⚠️ User not found.")

    st.markdown("---")
    st.subheader("📋 Registered Users")

    users = list_users()
    if users:
        df = pd.DataFrame(users, columns=["Username", "Role", "Created At"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No users found.")

    st.markdown("---")
    st.subheader("📝 Login Activity Log")

    logs = get_logs(100)
    if logs:
        df_logs = pd.DataFrame(logs, columns=["ID", "Username", "Event", "Success", "Note", "Timestamp"])
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No logs recorded yet.")
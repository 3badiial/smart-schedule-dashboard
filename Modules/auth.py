import sqlite3
import bcrypt
import streamlit as st
import datetime as dt
import os
from typing import Optional

# ============================================================
# Database Configuration
# ============================================================
# users.db is stored at the root of your project (beside app.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "users.db")


# ============================================================
# Database Setup and Utilities
# ============================================================
def get_conn():
    """Connect to the SQLite database."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_auth_tables():
    """Create authentication tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash BLOB NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auth_log (
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


def log_event(username: str, event: str, success: int, note: str = None):
    """Record authentication-related events."""
    conn = get_conn()
    cur = conn.cursor()
    ts = dt.datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO auth_log (username, event, success, note, ts)
        VALUES (?, ?, ?, ?, ?)
    """, (username, event, success, note, ts))
    conn.commit()
    conn.close()


# ============================================================
# Password Hashing and Verification
# ============================================================
def hash_password(plain_password: str) -> bytes:
    """Return a bcrypt hash for a plain password."""
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())


def verify_password(plain_password: str, hashed: bytes) -> bool:
    """Verify a plain password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed)
    except Exception:
        return False


# ============================================================
# User Management
# ============================================================
def add_user(username: str, plain_password: str, role: str = "user") -> bool:
    """Add a new user to the database."""
    conn = get_conn()
    cur = conn.cursor()
    now = dt.datetime.utcnow().isoformat()
    try:
        pw_hash = hash_password(plain_password)
        cur.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, pw_hash, role, now),
        )
        conn.commit()
        log_event(username, "create_user", 1, f"role={role}")
        return True
    except sqlite3.IntegrityError:
        log_event(username, "create_user", 0, "username_exists")
        return False
    finally:
        conn.close()


def reset_password(username: str, new_password: str) -> bool:
    """Reset a user's password."""
    conn = get_conn()
    cur = conn.cursor()
    pw_hash = hash_password(new_password)
    cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (pw_hash, username))
    conn.commit()
    updated = cur.rowcount > 0
    log_event(username, "reset_password", 1 if updated else 0)
    conn.close()
    return updated


def get_user(username: str) -> Optional[dict]:
    """Retrieve user info by username."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, password_hash, role, created_at FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"username": row[0], "password_hash": row[1], "role": row[2], "created_at": row[3]}


def list_users():
    """List all users."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, role, created_at FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_logs(limit=200):
    """Return the most recent authentication logs."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, event, success, note, ts FROM auth_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================================================
# Streamlit Authentication Flow
# ============================================================
def login_form():
    """Render the Streamlit login form."""
    st.sidebar.subheader("🔐 Login")

    username = st.sidebar.text_input("Username", key="auth_username")
    password = st.sidebar.text_input("Password", type="password", key="auth_password")

    if st.sidebar.button("Sign In"):
        user = get_user(username)
        if not user:
            st.sidebar.error("User does not exist.")
            log_event(username, "login_attempt", 0, "no_user")
            return None

        stored_pw = user["password_hash"]
        if isinstance(stored_pw, str):
            stored_pw = stored_pw.encode("latin1")

        if verify_password(password, stored_pw):
            st.session_state["user"] = user["username"]
            st.session_state["role"] = user["role"]
            log_event(username, "login_attempt", 1, "success")
            st.rerun()
        else:
            st.sidebar.error("Incorrect password.")
            log_event(username, "login_attempt", 0, "bad_password")
            return None


def logout():
    """Log out the current user."""
    if "user" in st.session_state:
        log_event(st.session_state.get("user"), "logout", 1)
    for key in ["user", "role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def require_login() -> bool:
    """Ensure that a user is logged in; otherwise, show login form."""
    init_auth_tables()

    if st.session_state.get("user"):
        st.sidebar.markdown(f"**Logged in as:** {st.session_state['user']} ({st.session_state.get('role', 'user')})")
        if st.sidebar.button("Logout"):
            logout()
        return True
    else:
        login_form()
        st.sidebar.info("Please log in to access the app.")
        return False


# ============================================================
# Admin Panel (for managing users)
# ============================================================
def admin_panel():
    """Admin-only panel for managing users and viewing logs."""
    st.header("🛡️ Admin Panel")

    # ============================================================
    # CREATE NEW USER
    # ============================================================
    st.subheader("➕ Create New User")

    # Form prevents rerun when typing inside input fields
    with st.form("create_user_form"):
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        new_role = st.selectbox("Role", ["user", "admin"])
        submitted = st.form_submit_button("Create User")

        if submitted:
            if new_user and new_pass:
                if add_user(new_user, new_pass, new_role):
                    st.success(f"✅ User '{new_user}' created successfully.")
                else:
                    st.error("⚠️ Username already exists.")
            else:
                st.warning("Please enter both username and password.")

    # ============================================================
    # RESET PASSWORD
    # ============================================================
    st.markdown("---")
    st.subheader("🔁 Reset User Password")

    with st.form("reset_password_form"):
        r_user = st.text_input("Username to Reset")
        r_pass = st.text_input("New Password", type="password")
        reset = st.form_submit_button("Reset Password")

        if reset:
            if r_user and r_pass:
                if reset_password(r_user, r_pass):
                    st.success(f"✅ Password for '{r_user}' has been reset.")
                else:
                    st.error("⚠️ Username not found.")
            else:
                st.warning("Please fill in both fields.")

    # ============================================================
    # LIST USERS
    # ============================================================
    st.markdown("---")
    st.subheader("📋 Registered Users")

    users = list_users()
    if users:
        df_users = pd.DataFrame(users, columns=["Username", "Role", "Created At"])
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("No users registered yet.")

    # ============================================================
    # VIEW AUTHENTICATION LOG
    # ============================================================
    st.markdown("---")
    st.subheader("🪵 Authentication Log")

    logs = get_logs(100)
    if logs:
        df_logs = pd.DataFrame(
            logs, columns=["ID", "Username", "Event", "Success", "Note", "Timestamp"]
        )
        df_logs["Success"] = df_logs["Success"].map({1: "✅", 0: "❌"})
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No login logs available yet.")
# auth.py
import sqlite3
import bcrypt
import streamlit as st
import datetime as dt
import os
from typing import Optional

# Path to the same DB you already use (تأكد من أنه نفس DB_PATH في التطبيق الرئيسي)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "users.db")

# ---------------- DB Init ----------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_auth_tables():
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

# ---------------- Utilities ----------------
def hash_password(plain: str) -> bytes:
    # bcrypt gensalt default cost is fine; returns bytes
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt())

def verify_password(plain: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed)
    except:
        return False

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
    log_event(username, "reset_password", 1 if updated else 0, None)
    conn.close()
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

def log_event(username: str, event: str, success: int, note: str = None):
    conn = get_conn()
    cur = conn.cursor()
    ts = dt.datetime.utcnow().isoformat()
    cur.execute("INSERT INTO auth_log(username, event, success, note, ts) VALUES (?, ?, ?, ?, ?)",
                (username, event, success, note, ts))
    conn.commit()
    conn.close()

def get_logs(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, event, success, note, ts FROM auth_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ---------------- Streamlit UI Flow ----------------
def login_form():
    st.sidebar.subheader("🔐 تسجيل الدخول")
    username = st.sidebar.text_input("اسم المستخدم", key="auth_username")
    password = st.sidebar.text_input("كلمة المرور", type="password", key="auth_password")
    if st.sidebar.button("تسجيل دخول"):
        user = get_user(username)
        if not user:
            log_event(username, "login_attempt", 0, "no_user")
            st.sidebar.error("اسم المستخدم غير موجود.")
            return None
        # password_hash stored as bytes in sqlite - ensure bytes
        stored = user["password_hash"]
        if isinstance(stored, str):
            stored = stored.encode('latin1')  # fallback if stored as str
        ok = verify_password(password, stored)
        if ok:
            st.session_state["user"] = user["username"]
            st.session_state["role"] = user["role"]
            log_event(username, "login_attempt", 1, "success")
            st.rerun()
        else:
            log_event(username, "login_attempt", 0, "bad_password")
            st.sidebar.error("كلمة المرور خاطئة.")
            return None
    return None

def logout():
    if "user" in st.session_state:
        log_event(st.session_state.get("user"), "logout", 1, None)
    for k in ["user", "role"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

def require_login():
    # initialize tables if not exist
    init_auth_tables()

    if st.session_state.get("user"):
        st.sidebar.markdown(f"**متصل باسم:** {st.session_state['user']} — {st.session_state.get('role','user')}")
        if st.sidebar.button("تسجيل خروج"):
            logout()
        return True
    else:
        login_form()
        st.sidebar.info("للوصول للتطبيق، سجّل الدخول أولاً.")
        return False

# Admin UI (create user / view logs) — only for role == admin
def admin_panel():
    st.header("🛡️ إدارة المستخدمين (Admin)")
    st.subheader("➕ إنشاء مستخدم جديد")

    # ✅ نستخدم نموذج (Form) لتجنب إعادة تحميل الصفحة أثناء الكتابة
    with st.form("create_user_form", clear_on_submit=True):
        new_user = st.text_input("اسم المستخدم جديد", key="admin_new_user")
        new_pass = st.text_input("كلمة المرور الجديدة", type="password", key="admin_new_pass")
        new_role = st.selectbox("الدور", ["user", "admin"], key="admin_new_role")
        submitted = st.form_submit_button("إنشاء مستخدم")
        if submitted:
            if new_user and new_pass:
                ok = add_user(new_user, new_pass, new_role)
                if ok:
                    st.success("✅ تم إنشاء المستخدم.")
                else:
                    st.error("⚠️ اسم المستخدم موجود مسبقًا.")
            else:
                st.warning("⚠️ أدخل اسم المستخدم وكلمة المرور.")

    st.markdown("---")
    st.subheader("🔁 إعادة تعيين كلمة مرور مستخدم")

    # ✅ نفس الفكرة هنا: نحطها داخل نموذج آخر
    with st.form("reset_password_form", clear_on_submit=True):
        r_user = st.text_input("اسم المستخدم لإعادة التعيين", key="admin_reset_user")
        r_pass = st.text_input("كلمة المرور الجديدة", type="password", key="admin_reset_pass")
        reset_submitted = st.form_submit_button("إعادة تعيين كلمة المرور")
        if reset_submitted:
            if reset_password(r_user, r_pass):
                st.success("تم إعادة التعيين بنجاح ✅")
            else:
                st.error("اسم المستخدم غير موجود ⚠️")

    st.markdown("---")
    st.subheader("📋 قائمة المستخدمين")
    rows = list_users()
    if rows:
        for u, role, created in rows:
            st.write(f"- **{u}** — {role} — created: {created}")
    else:
        st.info("لا يوجد مستخدمين بعد.")

    st.markdown("---")
    st.subheader("📝 سجل الدخول (Audit Log)")
    logs = get_logs(200)
    if logs:
        for _id, username, event, success, note, ts in logs:
            ok_text = "✅" if success else "❌"
            st.write(f"{_id} | {ts} | {ok_text} | {username} | {event} | {note}")
    else:
        st.info("لا سجلات حتى الآن.")




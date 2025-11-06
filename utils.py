import os
import requests
import pandas as pd
import sqlite3
import streamlit as st

# ==========================================================
# 🚀 إعداد روابط Google Drive / Google Sheets
# ==========================================================

# 🔹 روابط التحميل المباشر
DB_URL = "https://drive.google.com/uc?export=download&id=103uhKTui5IWqx8pFBLawr9SeeWA_xP4t"
EMP_URL = "https://docs.google.com/spreadsheets/d/1GacKW13ZhE5uZqtiPhkar4c60dCNXzW8/export?format=xlsx"

# 🔹 أسماء الملفات المحلية المؤقتة
DB_PATH = "schedules.db"
EMP_INFO = "employees_info.xlsx"

# ==========================================================
# 🧩 دالة لتحميل الملفات من Google Drive إذا لم تكن موجودة
# ==========================================================
def download_if_missing(url, path, display_name=None):
    if not os.path.exists(path):
        name = display_name or path
        st.info(f"Downloading **{name}** from Google Drive...")
        try:
            r = requests.get(url)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
                st.success(f"✅ {name} downloaded successfully!")
            else:
                st.error(f"⚠️ Failed to download {name} (HTTP {r.status_code}).")
                st.stop()
        except Exception as e:
            st.error(f"❌ Error downloading {name}: {e}")
            st.stop()

# ==========================================================
# 📥 تحميل قاعدة البيانات وملف Excel عند التشغيل
# ==========================================================
def ensure_files():
    download_if_missing(DB_URL, DB_PATH, "Schedules Database")
    download_if_missing(EMP_URL, EMP_INFO, "Employee Info")

# ==========================================================
# 📚 تحميل بيانات الجداول
# ==========================================================
@st.cache_data
def load_schedules():
    ensure_files()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM schedules", conn, parse_dates=["date"])
    conn.close()
    df["code"] = df["code"].astype(str).str.strip().str.upper()
    df["name"] = df["name"].astype(str).str.strip()
    df["day"] = df["date"].dt.day
    df["month"] = df["date"].dt.month_name().str[:3]
    df["weekday"] = df["date"].dt.day_name()
    return df

@st.cache_data
def load_employee_info():
    ensure_files()
    emp = pd.read_excel(EMP_INFO)
    emp["name"] = emp["name"].astype(str).str.strip()
    emp["position"] = emp["position"].astype(str).str.strip()
    return emp

# ==========================================================
# 🧮 دوال التصنيف والتحليل العامة (تُستخدم عبر الصفحات)
# ==========================================================
WORK_CODES = {"M","T","N","M1","M2","M3","T1","T2","T3","N1","N2","N3","1","2","3"}
REST_CODES = {"D"}
ANNUAL_LEAVE = {"V"}
COMP_LEAVE = {"F"}
ABSENT = {"AB"}
SICK = {"B"}

def classify(code):
    if code in WORK_CODES: return "Work"
    if code in REST_CODES: return "Rest"
    if code in ANNUAL_LEAVE: return "AnnualLeave"
    if code in COMP_LEAVE: return "CompLeave"
    if code in ABSENT: return "Absent"
    if code in SICK: return "Sick"
    return "Other"

def summarize(df_emp):
    from collections import Counter
    df_emp = df_emp.copy()
    df_emp["class"] = df_emp["code"].apply(classify)
    cnt = Counter(df_emp["class"])
    summary = {
        "Work": cnt.get("Work", 0),
        "Rest": cnt.get("Rest", 0),
        "V": cnt.get("AnnualLeave", 0),
        "F": cnt.get("CompLeave", 0),
        "AB": cnt.get("Absent", 0),
        "B": cnt.get("Sick", 0)
    }

    correct, total, stretch = 0, 0, 0
    for _, r in df_emp.iterrows():
        if classify(r["code"]) == "Work":
            stretch += 1
        elif classify(r["code"]) == "Rest":
            if stretch > 0:
                total += 1
                if 4 <= stretch <= 6:
                    correct += 1
                stretch = 0
    if stretch > 0:
        total += 1
        if 4 <= stretch <= 6:
            correct += 1

    summary["Rotation%"] = round(correct / total * 100, 2) if total > 0 else 0
    return summary

def eid_report(df_emp):
    SPECIAL_DAYS = {
        "Foundation Day": [pd.Timestamp("2025-02-22").date()],
        "Eid Al-Fitr": [pd.Timestamp(d).date() for d in pd.date_range("2025-03-30","2025-04-03")],
        "Eid Al-Adha": [pd.Timestamp(d).date() for d in pd.date_range("2025-06-06","2025-06-10")],
        "National Day": [pd.Timestamp("2025-09-23").date()]
    }
    out = {}
    for k, dates in SPECIAL_DAYS.items():
        codes = []
        for d in dates:
            r = df_emp[df_emp["date"].dt.date == d]
            code_str = ', '.join(r['code'].tolist()) if not r.empty else 'No Record'
            codes.append(f"{d.strftime('%Y-%m-%d')}: {code_str}")
        out[k] = codes
    return out

def weekend_pattern(df_emp):
    rests = df_emp[df_emp["code"] == "D"].copy()
    if rests.empty:
        return None
    rests["weekday"] = rests["date"].dt.day_name()
    fri = rests["weekday"].value_counts().get("Friday", 0)
    sat = rests["weekday"].value_counts().get("Saturday", 0)
    others = len(rests) - fri - sat
    ratio = round((fri + sat) / len(rests) * 100, 2) if len(rests) > 0 else 0
    return fri, sat, others, ratio

def create_metric_card(label, value, icon="📊"):
    return f"""
    <div class="metric-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <p class="metric-value">{value}</p>
                <p class="metric-label">{label}</p>
            </div>
            <div style="font-size: 2.5rem; opacity: 0.3;">{icon}</div>
        </div>
    </div>
    """

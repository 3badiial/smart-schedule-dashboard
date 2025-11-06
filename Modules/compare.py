import streamlit as st
import datetime as dt
import pandas as pd
import plotly.graph_objects as go
from collections import Counter

# ======= صفحة مقارنة الموظفين =======
def show(df, emp_info, names):
    st.title("👥 Compare Employees")

    # ========== اختيار الموظفين ==========
    col1, col2 = st.columns(2)
    with col1:
        n1 = st.selectbox("👤 Employee 1", names, key="compare_n1")
    with col2:
        n2 = st.selectbox("👤 Employee 2", [n for n in names if n != n1], key="compare_n2")

    # ========== نطاق التاريخ ==========
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("📅 Start Date", dt.date(2025, 1, 1), key="compare_start")
    with col2:
        end = st.date_input("📅 End Date", dt.date(2025, 11, 30), key="compare_end")

    d1 = df[(df["name"] == n1) & (df["date"].dt.date.between(start, end))].copy()
    d2 = df[(df["name"] == n2) & (df["date"].dt.date.between(start, end))].copy()

    # ========== أكواد العمل ==========
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

    s1, s2 = summarize(d1), summarize(d2)

    st.markdown("---")

    # ========== جدول المقارنة ==========
    comp = pd.DataFrame({
        "Metric": ["Work Days", "Rest Days", "Annual Leave", "Comp Leave", "Absent", "Sick Leave", "Rotation Score (%)"],
        n1: [s1["Work"], s1["Rest"], s1["V"], s1["F"], s1["AB"], s1["B"], s1["Rotation%"]],
        n2: [s2["Work"], s2["Rest"], s2["V"], s2["F"], s2["AB"], s2["B"], s2["Rotation%"]]
    })

    st.dataframe(comp, use_container_width=True, hide_index=True)
    st.markdown("---")

    # ========== الرسومات ==========
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"📊 {n1} Distribution")
        fig1 = go.Figure(data=[go.Bar(
            x=["Work", "Rest", "V", "F", "AB", "B"],
            y=[s1["Work"], s1["Rest"], s1["V"], s1["F"], s1["AB"], s1["B"]],
            marker_color=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899']
        )])
        fig1.update_layout(height=400, showlegend=False, yaxis_title="Days")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader(f"📊 {n2} Distribution")
        fig2 = go.Figure(data=[go.Bar(
            x=["Work", "Rest", "V", "F", "AB", "B"],
            y=[s2["Work"], s2["Rest"], s2["V"], s2["F"], s2["AB"], s2["B"]],
            marker_color=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899']
        )])
        fig2.update_layout(height=400, showlegend=False, yaxis_title="Days")
        st.plotly_chart(fig2, use_container_width=True)

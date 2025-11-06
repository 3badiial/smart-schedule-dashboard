import streamlit as st
import datetime as dt
import plotly.graph_objects as go
from collections import Counter
import pandas as pd

# ======= الصفحة الرئيسية (Overview) =======
def show(df, emp_info, names):
    st.title("🏠 Employee Overview")

    # ========== اختيار الموظف ==========
    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.selectbox("👤 Select Employee", names, key="overview_name")
    with col2:
        position = emp_info.loc[emp_info["name"] == name, "position"].values
        pos_text = position[0] if len(position) > 0 else "N/A"
        st.info(f"**Position:** {pos_text}")

    # ========== نطاق التاريخ ==========
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("📅 Start Date", dt.date(2025, 1, 1), key="overview_start")
    with col2:
        end = st.date_input("📅 End Date", dt.date(2025, 11, 30), key="overview_end")

    d = df[(df["name"] == name) & (df["date"].dt.date.between(start, end))].copy()

    if d.empty:
        st.warning("⚠️ No data available for the selected period.")
        st.stop()

    # ========== الدوال المساعدة ==========
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

    # ========== استخراج الملخص ==========
    s = summarize(d)
    st.markdown("---")

    # ======= Metrics Row =======
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(create_metric_card("Work Days", s['Work'], "💼"), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("Rest Days", s['Rest'], "🏖️"), unsafe_allow_html=True)
    with col3:
        st.markdown(create_metric_card("Annual Leave", s['V'], "✈️"), unsafe_allow_html=True)
    with col4:
        st.markdown(create_metric_card("Rotation Score", f"{s['Rotation%']}%", "🔄"), unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(create_metric_card("Comp Leave", s['F'], "🎁"), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("Absent", s['AB'], "⚠️"), unsafe_allow_html=True)
    with col3:
        st.markdown(create_metric_card("Sick Leave", s['B'], "🏥"), unsafe_allow_html=True)

    st.markdown("---")

    # ======= الرسوم البيانية =======
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Schedule Distribution")
        labels = ["Work", "Rest", "Annual Leave", "Comp Leave", "Absent", "Sick"]
        vals = [s['Work'], s['Rest'], s['V'], s['F'], s['AB'], s['B']]
        colors_pie = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899']

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=vals,
            hole=0.4,
            marker=dict(colors=colors_pie, line=dict(color='white', width=2)),
            textinfo='label+percent',
            textfont=dict(size=12)
        )])
        fig.update_layout(
            showlegend=True,
            height=400,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📈 Monthly Trend")
        d_copy = d.copy()
        d_copy["class"] = d_copy["code"].apply(classify)
        monthly_trend = d_copy.groupby([d_copy["date"].dt.to_period("M"), "class"]).size().unstack(fill_value=0)
        if not monthly_trend.empty:
            monthly_trend.index = monthly_trend.index.astype(str)
            fig = go.Figure()
            if 'Work' in monthly_trend.columns:
                fig.add_trace(go.Scatter(x=monthly_trend.index, y=monthly_trend['Work'], mode='lines+markers', name='Work', line=dict(color='#3b82f6', width=3)))
            if 'Rest' in monthly_trend.columns:
                fig.add_trace(go.Scatter(x=monthly_trend.index, y=monthly_trend['Rest'], mode='lines+markers', name='Rest', line=dict(color='#10b981', width=3)))
            fig.update_layout(
                height=400,
                hovermode='x unified',
                xaxis_title="Month",
                yaxis_title="Days",
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🎊 Special Calendar Events")
    eid = eid_report(d)
    for k, v in eid.items():
        with st.expander(f"**{k}**", expanded=False):
            for item in v:
                st.write(f"• {item}")

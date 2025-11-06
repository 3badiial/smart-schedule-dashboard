import streamlit as st
import datetime as dt
import plotly.graph_objects as go

# ======= التحليل الشهري =======
def show(df, names):
    st.title("📅 Monthly Analysis")

    # ========== اختيار الموظف ==========
    name = st.selectbox("👤 Select Employee", names, key="monthly_name")
    emp = df[df["name"] == name].copy()

    # ========== تصنيف الرموز ==========
    WORK_CODES = {"M","T","N","M1","M2","M3","T1","T2","T3","N1","N2","N3","1","2","3"}
    REST_CODES = {"D"}
    ANNUAL_LEAVE = {"V"}
    COMP_LEAVE = {"F"}

    def classify(code):
        if code in WORK_CODES: return "Work"
        if code in REST_CODES: return "Rest"
        if code in ANNUAL_LEAVE: return "AnnualLeave"
        if code in COMP_LEAVE: return "CompLeave"
        return "Other"

    emp["class"] = emp["code"].apply(classify)

    # ========== إنشاء الجدول الشهري ==========
    monthly = emp.groupby([emp["month"], "class"]).size().unstack(fill_value=0)
    order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = monthly.reindex([m for m in order if m in monthly.index])

    st.markdown("---")
    st.subheader("📋 Monthly Breakdown Table")
    st.dataframe(monthly, use_container_width=True)

    # ========== رسم الاتجاه الشهري ==========
    st.markdown("---")
    st.subheader("📈 Monthly Trend Visualization")

    fig = go.Figure()

    colors_line = {
        'Work': '#3b82f6',
        'Rest': '#10b981',
        'AnnualLeave': '#f59e0b',
        'CompLeave': '#8b5cf6'
    }

    for col in ['Work', 'Rest', 'AnnualLeave', 'CompLeave']:
        if col in monthly.columns:
            fig.add_trace(go.Scatter(
                x=monthly.index,
                y=monthly[col],
                mode='lines+markers',
                name=col,
                line=dict(color=colors_line.get(col, '#000'), width=3),
                marker=dict(size=8)
            ))

    fig.update_layout(
        height=500,
        hovermode='x unified',
        xaxis_title="Month",
        yaxis_title="Days",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True)

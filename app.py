# ============================================
# 🚀 Smart Schedule Dashboard (Final Organized Version)
# by Abdulrahman AlShehri
# ============================================

import streamlit as st

#for theme
with open("adif_theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 👇 أول دالة Streamlit لازم تكون أول شيء
st.set_page_config(
    page_title="Smart Schedule Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== الاستيرادات =====
from utils import load_schedules, load_employee_info
from Modules import overview, compare, monthly, viewer, events, weekends, coworking


# ===== تحميل البيانات =====
df = load_schedules()
emp_info = load_employee_info()
names = sorted(df["name"].unique())

# ===== الشريط الجانبي =====
st.sidebar.title("🎯 Navigation")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Select Page:",
    [
        "🏠 Overview",
        "👥 Compare Employees",
        "📅 Monthly Analysis",
        "🕓 Schedule Viewer",
        "🎊 Special Events",
        "🗓️ Weekend Patterns",
        "🤝 Co-Working Analysis"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# ===== عرض معلومات المستخدم الحالي =====
user = st.session_state.get("user")
role = st.session_state.get("role", "user")
st.sidebar.markdown(
    f"<p style='text-align:center;color:white;'>Logged in as <b>{user}</b> ({role})</p>",
    unsafe_allow_html=True,
)

# ===== زر فتح لوحة المشرف (Admin فقط) =====
if role == "admin":
    st.sidebar.markdown("---")
    if st.sidebar.button("🛡️ Open Admin Panel"):
        st.title("🛡️ Admin Panel - Manage Users")
        auth.admin_panel()
        st.stop()  # نوقف باقي الكود بعد عرض اللوحة

# ===== تحميل الصفحة المختارة =====
if page == "🏠 Overview":
    overview.show(df, emp_info, names)
elif page == "👥 Compare Employees":
    compare.show(df, emp_info, names)
elif page == "📅 Monthly Analysis":
    monthly.show(df, names)
elif page == "🕓 Schedule Viewer":
    viewer.show(df, names)
elif page == "🎊 Special Events":
    events.show(df, names)
elif page == "🗓️ Weekend Patterns":
    weekends.show(df, names)
elif page == "🤝 Co-Working Analysis":
    coworking.show(df, emp_info, names)

# ===== الفوتر =====
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#64748b;padding:1rem 0;'>
    <p style='margin:0;font-size:0.875rem;'>
        <strong>Schedule Dashboard</strong> | Version 2.0
    </p>
    <p style='margin:0.5rem 0 0 0;font-size:0.75rem;'>
        Powered by Abdulrahman AlShehri | For Traffic
    </p>
</div>
""", unsafe_allow_html=True)





import streamlit as st
import plotly.graph_objects as go
from utils import weekend_pattern, create_metric_card

def show(df, names):
    st.title("🗓️ Weekend Pattern Analysis")
    name = st.selectbox("👤 Select Employee", names)
    emp = df[df["name"]==name]
    res = weekend_pattern(emp)
    if not res:
        st.warning("⚠️ No rest days found.")
        return
    fri,sat,others,ratio=res
    col1,col2,col3,col4=st.columns(4)
    with col1: st.markdown(create_metric_card("Friday Rests", fri, "🕌"), unsafe_allow_html=True)
    with col2: st.markdown(create_metric_card("Saturday Rests", sat, "📅"), unsafe_allow_html=True)
    with col3: st.markdown(create_metric_card("Other Days", others, "📆"), unsafe_allow_html=True)
    with col4: st.markdown(create_metric_card("Weekend Ratio", f"{ratio}%", "✅"), unsafe_allow_html=True)

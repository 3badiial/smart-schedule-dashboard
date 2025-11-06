import streamlit as st
import datetime as dt
import pandas as pd

def show(df, names):
    st.title("🕓 Schedule Viewer")
    months = sorted(df["month"].unique(), key=lambda m: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(m))
    sel_month = st.selectbox("📅 Select Month", months)
    sel_name = st.selectbox("👤 Select Employee", ["All Employees"]+names)
    subset = df[df["month"]==sel_month].copy()
    if sel_name!="All Employees": subset=subset[subset["name"]==sel_name]
    if subset.empty:
        st.warning("⚠️ No data available.")
        return
    subset["day"]=subset["date"].dt.day
    pivot=subset.pivot_table(index="name",columns="day",values="code",aggfunc="first").fillna("-")
    st.dataframe(pivot, use_container_width=True, height=600)

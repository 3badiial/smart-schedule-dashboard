import streamlit as st
from utils import eid_report

def show(df, names):
    st.title("🎊 Special Calendar Events")
    name = st.selectbox("👤 Select Employee", names)
    emp = df[df["name"]==name]
    report = eid_report(emp)
    for k,v in report.items():
        with st.expander(f"**{k}**", expanded=True):
            for item in v:
                st.write("•", item)

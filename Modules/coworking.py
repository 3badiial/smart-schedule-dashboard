import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
from collections import Counter
from utils import WORK_CODES, create_metric_card

def show(df, emp_info, names):
    st.title("🤝 Co-Working Analysis")
    target = st.selectbox("👤 Select Employee", names)
    top_n = st.slider("Show Top N", 5, 30, 10)
    start = st.date_input("📅 Start Date", dt.date(2025,1,1))
    end = st.date_input("📅 End Date", dt.date(2025,11,30))
    df_work=df[df["code"].isin(WORK_CODES)&(df["date"].dt.date.between(start,end))].copy()
    def shift_type(c):
        if c in {"M","M1","M2","M3","1"}: return "Morning"
        if c in {"T","T1","T2","T3","2"}: return "Afternoon"
        if c in {"N","N1","N2","N3","3"}: return "Night"
        return "Other"
    df_work["shift"]=df_work["code"].apply(shift_type)
    target_df=df_work[df_work["name"]==target]
    cowork_counter=Counter()
    for _,row in target_df.iterrows():
        same=df_work[(df_work["date"]==row["date"])&(df_work["shift"]==row["shift"])&(df_work["name"]!=target)]
        cowork_counter.update(same["name"].tolist())
    if not cowork_counter:
        st.info("ℹ️ No coworkers found.")
        return
    results=pd.DataFrame(cowork_counter.items(),columns=["Coworker","SharedDays"]).sort_values("SharedDays",ascending=False)
    if not emp_info.empty:
        results=results.merge(emp_info[["name","position"]],left_on="Coworker",right_on="name",how="left").drop(columns="name")
        results.rename(columns={"position":"Position"},inplace=True)
    st.dataframe(results.head(top_n), use_container_width=True)

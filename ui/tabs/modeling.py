import streamlit as st
import pandas as pd

def render(fin_filtered):
    st.subheader("Default Label (3 consecutive yearly losses)")
    df = fin_filtered.copy()
    if df.empty:
        st.info("No data.")
        return
    # crude label based on Net Profit/(Loss) After Tax < 0 three years in a row
    inc = df[df["statement"].str.contains("income", case=False, na=False)]
    profit = inc[inc["account"].str.contains("net profit", case=False, na=False)]
    pv = profit.pivot_table(index="ticker", columns="period", values="value", aggfunc="sum")
    lab = []
    for t, row in pv.iterrows():
        vals = (row.fillna(0) < 0).astype(int).tolist()
        default = 1 if any(sum(vals[i:i+3])==3 for i in range(max(0, len(vals)-2))) else 0
        lab.append((t, default))
    label_df = pd.DataFrame(lab, columns=["ticker","Default"])
    st.dataframe(label_df, use_container_width=True)

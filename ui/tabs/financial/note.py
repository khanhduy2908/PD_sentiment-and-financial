import streamlit as st
from core.transforms import select_statement, pivot_statement

def render(fin_filtered):
    st.subheader("Notes")
    df = select_statement(fin_filtered, "note")
    if df.empty:
        st.info("No notes data found for this ticker.")
        return
    pv = pivot_statement(df)
    st.dataframe(pv, use_container_width=True)
    st.download_button("Download CSV", pv.to_csv().encode("utf-8"), file_name="notes.csv")


import io
import pandas as pd
import streamlit as st

def download_df_button(df: pd.DataFrame, label: str, filename: str):
    if df is None or df.empty:
        return
    buffer = io.BytesIO()
    df.to_csv(buffer, index=True)
    st.download_button(label, data=buffer.getvalue(), file_name=filename, mime="text/csv")

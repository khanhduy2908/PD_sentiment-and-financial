import streamlit as st
import pandas as pd
from core.transforms import select_statement, pivot_statement


def render(fin_filtered):
    st.subheader("Financial Report – Charts")

    # Chọn nhóm dữ liệu tài chính (Income, Balance, Cashflow, Indicators, Note)
    statement_options = [
        "income",
        "balance",
        "cashflow",
        "indicators",
        "note",
    ]
    selected_statement = st.selectbox(
        "Select statement to view chart", statement_options, index=0
    )

    df = select_statement(fin_filtered, selected_statement)
    if df.empty:
        st.info("No data available for the selected statement.")
        return

    pv = pivot_statement(df)
    if pv.empty:
        st.warning("No pivotable data found.")
        return

    # Hiển thị bảng dữ liệu gốc
    st.dataframe(pv, use_container_width=True)

    # Vẽ biểu đồ đơn giản minh hoạ biến động theo kỳ
    numeric_cols = pv.columns
    selected_accounts = st.multiselect(
        "Select accounts to chart", pv.index.tolist(), default=pv.index[:3]
    )

    if not selected_accounts:
        st.warning("Please select at least one account to visualize.")
        return

    chart_df = pv.loc[selected_accounts].T
    st.line_chart(chart_df)

    # Cho phép tải về CSV
    csv = pv.to_csv().encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"{selected_statement}_report.csv",
        mime="text/csv",
    )

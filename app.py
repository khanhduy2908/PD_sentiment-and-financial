import sys
import os
import streamlit as st

# ===========================================
# 1. Thiết lập đường dẫn để Python nhận dạng module
# ===========================================
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "ui") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "ui"))

# ===========================================
# 2. Import các module giao diện (layout, tabs)
# ===========================================
try:
    from layout import sidebar_inputs, get_data, inject_css_theme
except ModuleNotFoundError:
    from ui.layout import sidebar_inputs, get_data, inject_css_theme

from ui.tabs.financial import income as tab_income
from ui.tabs.financial import balance as tab_balance
from ui.tabs.financial import cashflow as tab_cashflow
from ui.tabs.financial import indicators as tab_indicators
from ui.tabs.financial import note as tab_note
from ui.tabs.financial import report as tab_report

# ===========================================
# 3. Cấu hình giao diện Streamlit
# ===========================================
st.set_page_config(
    page_title="Financial Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css_theme()

# ===========================================
# 4. Nhập thông tin đầu vào từ sidebar
# ===========================================
ticker, section = sidebar_inputs()

# ===========================================
# 5. Tải dữ liệu (với kiểm tra lỗi)
# ===========================================
try:
    data = get_data(ticker, years=10)
except Exception as e:
    st.error(f"❌ Cannot load data from 'data/bctc_final.csv'. Detail: {e}")
    st.stop()

# ===========================================
# 6. Tổ chức layout hiển thị theo từng section
# ===========================================
if section == "Financial":
    tabs = st.tabs([
        "Income Statement",
        "Balance Sheet",
        "Cashflow Statement",
        "Financial Indicators",
        "Notes",
        "Report"
    ])

    with tabs[0]:
        tab_income.render(data)
    with tabs[1]:
        tab_balance.render(data)
    with tabs[2]:
        tab_cashflow.render(data)
    with tabs[3]:
        tab_indicators.render(data)
    with tabs[4]:
        tab_note.render(data)
    with tabs[5]:
        tab_report.render(data)

elif section == "Sentiment":
    st.info("Sentiment analysis module coming soon...")

elif section == "Summary":
    st.info("Summary module under development...")

else:
    st.warning("Please select a valid section from the sidebar.")

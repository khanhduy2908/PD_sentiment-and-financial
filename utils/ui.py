# utils/ui.py — Professional UI
import streamlit as st

PRIMARY = "#0055a5"          
PRIMARY_HOVER = "#003f7d"
TAB_TEXT = "#ffffff"
INACTIVE_BG = "#f2f2f2"
FRAME_BG = "#ffffff"
BORDER = "#d0d0d0"

def inject_global_css():
    st.markdown(f"""
    <style>
      .block-container {{
        padding-top: 1rem;
        padding-bottom: 1.25rem;
        max-width: 1500px;
      }}

      [data-testid="stElementToolbar"] {{ display:none !important; }}
      [data-testid="StyledFullScreenButton"] {{ display:none !important; }}
      [data-testid="stDataFrameResizable"] button {{ display:none !important; }}

      /* Tabs */
      [data-testid="stTabs"] div[role="tablist"] {{
        gap: 10px;
        margin-bottom: 8px;
        border-bottom: 1px solid #e5e5e5;
        padding-bottom: 4px;
      }}

      [data-testid="stTabs"] button[role="tab"] {{
        background: {INACTIVE_BG};
        padding: 8px 16px;
        font-weight: 600;
        border-radius: 12px;
        border: 1px solid #ccc;
        color: #333;
      }}

      [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
        background: {PRIMARY};
        color: {TAB_TEXT};
        border-color: {PRIMARY};
        font-weight: 700;
      }}

      [data-testid="stTabs"] button[role="tab"][aria-selected="true"]:hover {{
        background: {PRIMARY_HOVER};
      }}

      h2 {{
        font-weight: 700;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
      }}

      [data-testid="stDataFrame"] div[role="grid"] {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        background: {FRAME_BG};
      }}

      thead tr th {{ font-weight: 700 !important; font-size: 13px; }}
      tbody tr td {{ font-size: 13px; }}
    </style>
    """, unsafe_allow_html=True)

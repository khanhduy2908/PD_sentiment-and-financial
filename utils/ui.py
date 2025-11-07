# utils/ui.py
import streamlit as st

PRIMARY = "#0b5ed7"          # Active tab blue
PRIMARY_HOVER = "#0a53be"
TAB_TEXT = "#ffffff"
INACTIVE_BG = "#e9ecef"
FRAME_BG = "#ffffff"
BORDER = "#dee2e6"

def inject_global_css():
    """Inject global CSS to style top tabs, tables and hide toolbars/icons."""
    st.markdown(f"""
    <style>
      /* Page paddings & max width */
      .block-container {{
        padding-top: 1rem;
        padding-bottom: 1.25rem;
        max-width: 1280px;
      }}

      /* Hide all toolbars/icons (download, fullscreen, ... ) */
      [data-testid="stElementToolbar"] {{ display:none !important; }}
      [data-testid="StyledFullScreenButton"] {{ display:none !important; }}
      [data-testid="stDataFrameResizable"] button {{ display:none !important; }}

      /* Tabs layout */
      [data-testid="stTabs"] div[role="tablist"] {{
        gap: 12px;
        margin-bottom: 12px;
      }}

      /* Tab pill (inactive) */
      [data-testid="stTabs"] button[role="tab"] {{
        background: {INACTIVE_BG};
        color: #212529;
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 8px 18px;
        font-weight: 700;
        letter-spacing: .2px;
      }}

      /* Tab pill (active) */
      [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
        background: {PRIMARY};
        color: {TAB_TEXT};
        border-color: {PRIMARY};
      }}
      [data-testid="stTabs"] button[role="tab"][aria-selected="true"]:hover {{
        background: {PRIMARY_HOVER};
      }}

      /* Headings */
      h2 {{
        font-weight: 700;
        margin: .25rem 0 .75rem 0;
      }}

      /* DataFrame frame */
      [data-testid="stDataFrame"] div[role="grid"] {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        background: {FRAME_BG};
      }}

      /* Table fonts */
      thead tr th {{ font-weight: 700 !important; }}
      tbody tr td {{ font-weight: 500; }}
    </style>
    """, unsafe_allow_html=True)

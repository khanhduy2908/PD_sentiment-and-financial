import streamlit as st

def inject_css_theme():
    st.markdown(
        '''
        <style>
          .red-accent h2, .red-accent h3 { color: #8B0000; }
        </style>
        ''',
        unsafe_allow_html=True
    )

def sidebar_controls():
    st.sidebar.header("Ticker")
    ticker = st.sidebar.text_input("Enter ticker", value="", help="Example: AAA")
    st.sidebar.markdown("---")
    st.sidebar.header("Report")
    section = st.sidebar.radio("",
        options=["Financial","Sentiment","Summary"],
        index=0,
        label_visibility="collapsed"
    )
    apply = st.sidebar.button("Apply")
    return ticker, section, apply

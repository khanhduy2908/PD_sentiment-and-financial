import streamlit as st
from ui.layout import sidebar_inputs, get_data
from ui.tabs.financial import income as tab_income
from ui.tabs.financial import balance as tab_balance
from ui.tabs.financial import cashflow as tab_cash
from ui.tabs.financial import indicators as tab_indicators
from ui.tabs.financial import note as tab_note
from ui.tabs.financial import report as tab_report
from ui.tabs.sentiment import news as tab_news, aggregates as tab_sagg
from ui.tabs.summary import modeling as tab_model

st.set_page_config(page_title="AI Default Risk", layout="wide", page_icon="📊", initial_sidebar_state="expanded")

# theme via CSS (blue + dark red accents)
st.markdown('''
<style>
:root {
    --blue:#1E3A8A; --red:#8B0000;
}
h1,h2,h3 { color: var(--blue); }
.red-accent { color: var(--red); font-weight:700; }
</style>
''', unsafe_allow_html=True)

ticker, section = sidebar_inputs()
data = get_data(ticker)

if section == "Financial":
    tabs = st.tabs(["Income statement","Balance Sheet","Cashflow Statement","Financial Indicator","Note","Report"])
    with tabs[0]: tab_income.render(data)
    with tabs[1]: tab_balance.render(data)
    with tabs[2]: tab_cash.render(data)
    with tabs[3]: tab_indicators.render(data)
    with tabs[4]: tab_note.render(data)
    with tabs[5]: tab_report.render(data)
elif section == "Sentiment":
    tabs = st.tabs(["News","Aggregates"])
    with tabs[0]: tab_news.render(data)
    with tabs[1]: tab_sagg.render(data)
else:
    tab_model.render(data)

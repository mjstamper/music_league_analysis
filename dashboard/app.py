"""Music League dashboard.   streamlit run app.py   (set ML_OUT to the analysis output folder)"""
import streamlit as st

from mld import ui

st.set_page_config(page_title="Music League", page_icon=":musical_note:", layout="wide")
ui.inject_css()

pages = [st.Page("screens/league.py", title="League view", icon=":material/leaderboard:", default=True),
         st.Page("screens/recap.py", title="Recap (Wrapped)", icon=":material/celebration:")]
st.navigation(pages).run()

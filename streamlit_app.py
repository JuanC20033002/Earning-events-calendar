import streamlit as st
from menu import render_menu

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "traffic_light": st.Page(
        "pages/1_🚦_Traffic_Light.py",
        title="Traffic Light",
        icon="🚦",
        default=True,
    ),
    "pandora_universe": st.Page(
        "pages/2_📈_Pandora_Universe.py",
        title="Pandora Universe",
        icon="📈",
    ),
    "calendar": st.Page(
        "pages/3_🗓️_Calendar.py",
        title="Calendar",
        icon="🗓️",
    ),
    "external_news": st.Page(
        "pages/4_🌐_External_News.py",
        title="External News",
        icon="🌐",
    ),
    "assign_dates": st.Page(
        "pages/5_📝_Assign_Dates.py",
        title="Assign Dates",
        icon="📝",
    ),
}

pg = st.navigation(list(pages.values()), position="hidden")
render_menu(pages)
pg.run()
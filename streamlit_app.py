import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar & Pandora Universe",
    page_icon="📊",
    layout="wide"
)

traffic_light_page = st.Page(
    "pages/1_🚦_Traffic_Light.py",
    title="Traffic Light",
    icon="🚦",
    default=True,
)

pandora_universe_page = st.Page(
    "pages/2_📈_Pandora_Universe.py",
    title="Pandora Universe",
    icon="📈",
)

calendar_page = st.Page(
    "pages/3_📅_Calendar.py",
    title="Calendar",
    icon="📅",
)

external_news_page = st.Page(
    "pages/4_🌐_External_News.py",
    title="Add External News",
    icon="🌐",
)

assign_dates_page = st.Page(
    "pages/5_📌_Assign_Dates.py",
    title="Assign Dates",
    icon="📌",
)

pg = st.navigation(
    {
        "Main": [
            traffic_light_page,
            pandora_universe_page,
            calendar_page,
        ],
        "Admin": [
            external_news_page,
            assign_dates_page,
        ],
    },
    position="sidebar",
    expanded=True,
)

pg.run()
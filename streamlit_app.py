import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

traffic_light = st.Page(
    "pages/1_🚦_Traffic_Light.py",
    title="Traffic Light",
    icon="🚦",
    default=True,
)

pandora_universe = st.Page(
    "pages/2_📈_Pandora_Universe.py",
    title="Pandora Universe",
    icon="📈",
)

calendar_page = st.Page(
    "pages/3_🗓️_Calendar.py",
    title="Calendar",
    icon="🗓️",
)

external_news = st.Page(
    "pages/4_🌐_External_News.py",
    title="External News",
    icon="🌐",
)

assign_dates = st.Page(
    "pages/5_📝_Assign_Dates.py",
    title="Assign Dates",
    icon="📝",
)

pages = [
    traffic_light,
    pandora_universe,
    calendar_page,
    external_news,
    assign_dates,
]

pg = st.navigation(pages, position="hidden")

with st.sidebar:
    st.markdown("## Economic Events Calendar")
    st.caption("Navigation")

    st.page_link("pages/1_🚦_Traffic_Light.py", label="Traffic Light", icon="🚦")
    st.page_link("pages/2_📈_Pandora_Universe.py", label="Pandora Universe", icon="📈")
    st.page_link("pages/3_🗓️_Calendar.py", label="Calendar", icon="🗓️")
    st.page_link("pages/4_🌐_External_News.py", label="External News", icon="🌐")
    st.page_link("pages/5_📝_Assign_Dates.py", label="Assign Dates", icon="📝")

pg.run()
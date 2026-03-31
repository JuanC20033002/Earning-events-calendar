import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation(
    [
        st.Page("pages/1_traffic_light.py", title="Traffic Light", icon="🚦", default=True),
        st.Page("pages/2_pandora_universe.py", title="Pandora Universe", icon="📈"),
        st.Page("pages/3_calendar.py", title="Calendar", icon="🗓️"),
        st.Page("pages/4_external_news.py", title="External News", icon="🌐"),
        st.Page("pages/5_assign_dates.py", title="Assign Dates", icon="📝"),
    ],
    position="sidebar",
)

pg.run()
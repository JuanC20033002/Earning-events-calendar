import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = []

try:
    pages.append(st.Page("pages/1_traffic_light.py", title="Traffic Light", icon="🚦", default=True))
    pages.append(st.Page("pages/2_pandora_universe.py", title="Pandora Universe", icon="📈"))
    pages.append(st.Page("pages/3_calendar.py", title="Calendar", icon="🗓️"))
    pages.append(st.Page("pages/4_external_news.py", title="External News", icon="🌐"))
    pages.append(st.Page("pages/5_assign_dates.py", title="Assign Dates", icon="📝"))
except Exception as e:
    st.title("Economic Events Calendar")
    st.error("A page path is invalid in streamlit_app.py.")
    st.code(str(e))
    st.info("Check that the filenames inside pages/ exactly match the paths used in st.Page(...).")
    st.stop()

pg = st.navigation(pages, position="sidebar")
pg.run()
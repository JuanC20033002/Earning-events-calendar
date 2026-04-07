import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] > div:first-child {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True
)

try:
    traffic_light_page = st.Page(
        "pages/1_🚦_Traffic_Light.py",
        title="Traffic Light",
        icon="🚦",
        default=True
    )
    pandora_universe_page = st.Page(
        "pages/2_📈_Pandora_Universe.py",
        title="Pandora Universe",
        icon="📈"
    )
    calendar_page = st.Page(
        "pages/3_🗓️_Calendar.py",
        title="Calendar",
        icon="🗓️"
    )
    external_news_page = st.Page(
        "pages/4_🌐_Admin_Add_External_News.py",
        title="Add External News",
        icon="🌐"
    )
    assign_dates_page = st.Page(
        "pages/5_📝_Admin_Assign_Dates.py",
        title="Assign Dates",
        icon="📝"
    )
except Exception as e:
    st.title("Economic Events Calendar")
    st.error("A page path is invalid in streamlit_app.py.")
    st.code(str(e))
    st.info("Check that the filenames inside pages/ exactly match the paths used in st.Page(...).")
    st.stop()

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
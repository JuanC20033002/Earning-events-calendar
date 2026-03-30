import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation(
    [
        st.Page("pages/1_🚦_Traffic_Light.py", title="Traffic Light", icon="🚦", default=True),
        st.Page("pages/2_📈_Pandora_Universe.py", title="Pandora Universe", icon="📈"),
        st.Page("pages/3_🗓️_Calendar.py", title="Calendar", icon="🗓️"),
        st.Page("pages/4_🌐_External_News.py", title="External News", icon="🌐"),
        st.Page("pages/5_📝_Assign_Dates.py", title="Assign Dates", icon="📝"),
    ],
    position="sidebar",
    expanded=True,
)

st.title("Economic Events Calendar")
st.caption("A multipage Streamlit app for economic events, earnings events, external news, and date assignment.")

st.markdown("## Available pages")
st.markdown("- 🚦 **Traffic Light** — Multi-month impact overview by sector and event type.")
st.markdown("- 📈 **Pandora Universe** — Reserved for future development.")
st.markdown("- 🗓️ **Calendar** — Weekly event list by month, sector, category, and impact.")
st.markdown("- 🌐 **External News** — Create and manage custom external news events.")
st.markdown("- 📝 **Assign Dates** — Assign manual dates to economic events.")

st.markdown("---")
st.markdown("## How to use")
st.markdown("1. Select a page from the sidebar.")
st.markdown("2. Use sector, category, and impact filters where available.")
st.markdown("3. Add or update event data from the corresponding management pages.")

st.info("Use the sidebar to open any page in the app.")

pg.run()
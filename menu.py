import streamlit as st

def render_menu(pages_dict):
    with st.sidebar:
        st.markdown("## Economic Events Calendar")
        st.caption("Navigation")

        st.page_link(pages_dict["traffic_light"], label="Traffic Light", icon="🚦")
        st.page_link(pages_dict["pandora_universe"], label="Pandora Universe", icon="📈")
        st.page_link(pages_dict["calendar"], label="Calendar", icon="🗓️")
        st.page_link(pages_dict["external_news"], label="External News", icon="🌐")
        st.page_link(pages_dict["assign_dates"], label="Assign Dates", icon="📝")
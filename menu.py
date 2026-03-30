import streamlit as st

def render_menu():
    with st.sidebar:
        st.markdown("## Economic Events Calendar")
        st.caption("Navigation")
        st.page_link("pages/1_🚦_Traffic_Light.py", label="Traffic Light", icon="🚦")
        st.page_link("pages/2_📈_Pandora_Universe.py", label="Pandora Universe", icon="📈")
        st.page_link("pages/3_🗓️_Calendar.py", label="Calendar", icon="🗓️")
        st.page_link("pages/4_🌐_External_News.py", label="External News", icon="🌐")
        st.page_link("pages/5_📝_Assign_Dates.py", label="Assign Dates", icon="📝")
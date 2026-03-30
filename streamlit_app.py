import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation(
    [
        st.Page("pages/1_🚦_Semaforo.py", title="Traffic Light", icon="🚦"),
        st.Page("pages/2_📈_Pandora_Universe.py", title="Pandora Universe", icon="📈"),
        st.Page("pages/3_🗓️_Calendario.py", title="Calendar", icon="🗓️"),
        st.Page("pages/4_🌐_Noticias_Externas.py", title="External News", icon="🌐"),
        st.Page("pages/5_📝_Asignar_Fechas.py", title="Assign Dates", icon="📝"),
    ]
)

pg.run()
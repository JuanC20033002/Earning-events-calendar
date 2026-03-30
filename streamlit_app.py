import streamlit as st

st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .hero-box {
        background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
        border: 1px solid #f0f0f0;
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .feature-card {
        background: white;
        border: 1px solid #f0f0f0;
        border-radius: 12px;
        padding: 1rem;
        height: 100%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    h1 {
        color: #FF4B4B;
        padding-bottom: 0.5rem;
    }
    h2, h3 {
        color: #262730;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Economic Events Calendar")

st.markdown("""
<div class="hero-box">
    <h3>Bienvenido</h3>
    <p>
        Esta app está organizada en páginas independientes para que la navegación,
        el mantenimiento y el despliegue sean más limpios.
    </p>
    <p>
        Usa el menú lateral para entrar a cada módulo.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("## Módulos disponibles")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>🚦 Semáforo</h4>
        <p>Vista de impacto por mes y por día para eventos económicos y earnings.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card">
        <h4>📅 Calendario</h4>
        <p>Explora eventos filtrados por período, categoría, sector e impacto.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>📈 Pandora Buy</h4>
        <p>Revisión fundamental y comparativa de acciones.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card">
        <h4>🌐 Noticias Externas</h4>
        <p>Alta manual de noticias con impacto sectorial.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h4>✏️ Asignar Fechas</h4>
        <p>Completa eventos pendientes y mantén actualizada la base.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card">
        <h4>🌍 Macro 2026</h4>
        <p>Consulta score macro, régimen y drivers mensuales.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.info("⬅️ Selecciona una página desde la barra lateral para comenzar.")

st.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 0.85rem; margin-top: 2rem;'>
        📊 Economic Events Calendar | Powered by Streamlit & Supabase
    </div>
    """,
    unsafe_allow_html=True
)
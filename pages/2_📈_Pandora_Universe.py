
import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os
import plotly.graph_objects as go


# ==========================================
# CONFIG
# ==========================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==========================================
# ESTILOS
# ==========================================
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        border-radius: 5px;
        padding: 0.5rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF6B6B;
        border-color: #FF4B4B;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    h1 {
        color: #FF4B4B;
        padding-bottom: 1rem;
    }
    h2 {
        color: #262730;
        padding-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# FUNCIONES
# ==========================================
def convertir_calificacion_a_numero(calificacion):
    conversion = {
        'A+': 12, 'A': 11, 'A-': 10,
        'B+': 9, 'B': 8, 'B-': 7,
        'C+': 6, 'C': 5, 'C-': 4,
        'D+': 3, 'D': 2, 'D-': 1,
        'F': 0
    }

    if pd.isna(calificacion):
        return 0

    return conversion.get(str(calificacion).strip(), 0)


@st.cache_data(ttl=600)
def obtener_pandora_buy():
    try:
        response = supabase.table("pandora_buy").select("*").order("ticker").execute()
        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.error(f"Error al obtener datos de Pandora Buy: {str(e)}")
        return pd.DataFrame()


def obtener_datos_ticker(df_pandora, ticker):
    try:
        resultado = df_pandora[df_pandora["ticker"] == ticker]
        if not resultado.empty:
            return resultado.iloc[0]
        return None
    except Exception:
        return None


# ==========================================
# PAGE
# ==========================================
st.title("📈 Pandora Buy")
st.markdown("Análisis fundamental para comparar tickers y revisar métricas por empresa.")

df_pandora = obtener_pandora_buy()

if df_pandora.empty:
    st.warning("⚠️ No hay datos disponibles en Pandora Buy.")
else:
    st.markdown("### 🔍 Seleccionar Acciones")

    opciones_tickers = [
        f"{row['ticker']} - {row['empresa']}"
        for _, row in df_pandora.iterrows()
    ]
    tickers_dict = {
        f"{row['ticker']} - {row['empresa']}": row["ticker"]
        for _, row in df_pandora.iterrows()
    }

    tickers_seleccionados_display = st.multiselect(
        "Busca por ticker o nombre de empresa",
        opciones_tickers,
        default=[],
        placeholder="Ejemplo: AAPL, MSFT, JPM..."
    )

    tickers_seleccionados = [
        tickers_dict[t]
        for t in tickers_seleccionados_display
    ]

    if not tickers_seleccionados:
        st.info("👆 Selecciona una o más acciones para comenzar.")
    else:
        st.markdown("---")

        if len(tickers_seleccionados) > 1:
            st.markdown(f"### 📊 Comparativa de {len(tickers_seleccionados)} Acciones")

            categorias = ["Calidad", "Salud Financiera", "Earnings", "Revisiones", "Valoración"]
            fig = go.Figure()

            for ticker in tickers_seleccionados:
                datos_ticker = obtener_datos_ticker(df_pandora, ticker)

                if datos_ticker is not None:
                    valores = [
                        convertir_calificacion_a_numero(datos_ticker["calidad"]),
                        convertir_calificacion_a_numero(datos_ticker["salud_financiera"]),
                        convertir_calificacion_a_numero(datos_ticker["earnings"]),
                        convertir_calificacion_a_numero(datos_ticker["revisiones"]),
                        convertir_calificacion_a_numero(datos_ticker["valoracion"])
                    ]

                    fig.add_trace(go.Bar(
                        name=ticker,
                        x=categorias,
                        y=valores,
                        text=[
                            datos_ticker["calidad"],
                            datos_ticker["salud_financiera"],
                            datos_ticker["earnings"],
                            datos_ticker["revisiones"],
                            datos_ticker["valoracion"]
                        ],
                        textposition="auto"
                    ))

            fig.update_layout(
                barmode="group",
                title="Comparación de Métricas Fundamentales",
                xaxis_title="Categorías",
                yaxis_title="Score (0-12)",
                yaxis=dict(range=[0, 13]),
                height=500,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")

        st.markdown("### 🔍 Detalle por Acción")

        for ticker in tickers_seleccionados:
            datos = obtener_datos_ticker(df_pandora, ticker)

            if datos is None:
                st.error(f"❌ No se encontraron datos para {ticker}")
                continue

            with st.expander(f"📊 {ticker} - {datos['empresa']}", expanded=True):
                col1, col2 = st.columns([1, 2])

                with col1:
                    overall_score = datos["overall"]
                    st.markdown(
                        f"<h1 style='text-align: center; font-size: 5rem; color: #FF4B4B;'>{overall_score}</h1>",
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        "<h3 style='text-align: center; color: #666;'>Overall Score</h3>",
                        unsafe_allow_html=True
                    )

                    st.markdown("---")
                    st.markdown(f"**🏢 Empresa:** {datos['empresa']}")
                    st.markdown(f"**📌 Ticker:** `{datos['ticker']}`")

                with col2:
                    categorias = ["Calidad", "Salud\nFinanciera", "Earnings", "Revisiones", "Valoración"]
                    valores = [
                        convertir_calificacion_a_numero(datos["calidad"]),
                        convertir_calificacion_a_numero(datos["salud_financiera"]),
                        convertir_calificacion_a_numero(datos["earnings"]),
                        convertir_calificacion_a_numero(datos["revisiones"]),
                        convertir_calificacion_a_numero(datos["valoracion"])
                    ]
                    calificaciones = [
                        datos["calidad"],
                        datos["salud_financiera"],
                        datos["earnings"],
                        datos["revisiones"],
                        datos["valoracion"]
                    ]

                    colores = []
                    for val in valores:
                        if val >= 10:
                            colores.append("#00CC66")
                        elif val >= 7:
                            colores.append("#FFD700")
                        elif val >= 4:
                            colores.append("#FF8C00")
                        else:
                            colores.append("#FF4444")

                    fig_individual = go.Figure(data=[
                        go.Bar(
                            x=categorias,
                            y=valores,
                            text=calificaciones,
                            textposition="auto",
                            marker=dict(color=colores),
                            hovertemplate="<b>%{x}</b><br>Score: %{text}<br>Valor: %{y}<extra></extra>"
                        )
                    ])

                    fig_individual.update_layout(
                        title=f"Métricas Fundamentales - {ticker}",
                        xaxis_title="Categorías",
                        yaxis_title="Score (0-12)",
                        yaxis=dict(range=[0, 13]),
                        height=400,
                        showlegend=False
                    )

                    st.plotly_chart(fig_individual, use_container_width=True)

                st.markdown("---")
                st.markdown("#### 📋 Resumen de Calificaciones")

                col_tabla1, col_tabla2, col_tabla3 = st.columns(3)

                with col_tabla1:
                    st.metric("🎯 Calidad", datos["calidad"])
                    st.metric("💰 Salud Financiera", datos["salud_financiera"])

                with col_tabla2:
                    st.metric("📈 Earnings", datos["earnings"])
                    st.metric("📊 Revisiones", datos["revisiones"])

                with col_tabla3:
                    st.metric("💵 Valoración", datos["valoracion"])
                    st.metric("⭐ Overall", datos["overall"])

            st.markdown("")
import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, time
import os


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
@st.cache_data(ttl=300)
def cargar_earnings_desde_csv(csv_path="Earnings_Events.csv"):
    try:
        df_raw = pd.read_csv(csv_path)

        if df_raw.empty:
            return pd.DataFrame(), pd.DataFrame()

        df_raw.columns = [c.strip() for c in df_raw.columns]

        categorias_map = {
            "Magnificent 7": "Magnificent 7",
            "Dow Jones 30 that are not mentioned": "Dow Jones 30",
            "3 big companies for each sector": "Top 3 Sector"
        }

        columnas_base = {"Fecha", "Symbol", "Tipo_Evento"}
        columnas_sector = [c for c in df_raw.columns if c not in columnas_base]

        eventos = []
        impactos = []

        for _, row in df_raw.iterrows():
            symbol = str(row.get("Symbol", "")).strip()
            tipo_evento = str(row.get("Tipo_Evento", "")).strip()
            categoria = categorias_map.get(tipo_evento, tipo_evento)
            fecha = pd.to_datetime(row.get("Fecha"), errors="coerce")

            if not symbol:
                continue

            evento_nombre = f"{symbol} Earnings"

            eventos.append({
                "id": f"csv_{symbol}_{categoria}",
                "evento_nombre": evento_nombre,
                "categoria": categoria,
                "tipo": "earning",
                "fecha": fecha,
                "descripcion": f"{categoria} earnings event",
                "ticker": symbol,
                "pais": "USA",
                "source": "csv"
            })

            for sector in columnas_sector:
                valor = row.get(sector)

                if pd.notna(valor) and str(valor).strip() != "":
                    try:
                        impacto_score = int(float(valor))
                    except Exception:
                        continue

                    if impacto_score > 0:
                        impactos.append({
                            "evento_tipo": evento_nombre,
                            "sector": sector.strip(),
                            "impacto_score": impacto_score,
                            "source": "csv"
                        })

        return pd.DataFrame(eventos), pd.DataFrame(impactos)

    except Exception as e:
        st.error(f"Error al cargar earnings desde CSV: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=300)
def obtener_sectores_disponibles():
    try:
        sectores = set()

        impactos_response = supabase.table("impacto_sectores").select("sector").execute()
        if impactos_response.data:
            sectores.update(
                item["sector"].strip()
                for item in impactos_response.data
                if item.get("sector")
            )

        _, df_impactos_csv = cargar_earnings_desde_csv("Earnings_Events.csv")
        if not df_impactos_csv.empty:
            sectores.update(df_impactos_csv["sector"].dropna().astype(str).str.strip().tolist())

        sectores = sorted(list(sectores))
        return sectores if sectores else ["General"]

    except Exception as e:
        st.error(f"Error al obtener sectores: {str(e)}")
        return ["General"]


@st.cache_data(ttl=300)
def obtener_eventos_con_impacto():
    try:
        impactos_response = supabase.table("impacto_sectores").select("*").execute()
        eventos_response = (
            supabase.table("eventos_unicos")
            .select("*")
            .in_("categoria", ["Evento Económico", "Noticia Externa"])
            .execute()
        )

        df_eventos_sb = pd.DataFrame(eventos_response.data or [])
        df_impactos_sb = pd.DataFrame(impactos_response.data or [])

        if not df_eventos_sb.empty:
            df_eventos_sb["fecha"] = pd.to_datetime(df_eventos_sb["fecha"], errors="coerce")
            df_eventos_sb["source"] = "supabase"

        df_eventos_csv, df_impactos_csv = cargar_earnings_desde_csv("Earnings_Events.csv")

        df_eventos = pd.concat([df_eventos_sb, df_eventos_csv], ignore_index=True, sort=False)
        df_impactos = pd.concat([df_impactos_sb, df_impactos_csv], ignore_index=True, sort=False)

        if not df_eventos.empty and "fecha" in df_eventos.columns:
            df_eventos["fecha"] = pd.to_datetime(df_eventos["fecha"], errors="coerce")

        return df_eventos, df_impactos

    except Exception as e:
        st.error(f"Error al obtener eventos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()


def crear_noticia_externa(titulo, sectores_seleccionados, impacto, descripcion, fecha):
    try:
        fecha_datetime = datetime.combine(fecha, time(0, 0, 0))

        evento_data = {
            "evento_nombre": titulo,
            "categoria": "Noticia Externa",
            "tipo": "economico",
            "fecha": fecha_datetime.isoformat(),
            "descripcion": descripcion if descripcion else None,
            "ultima_actualizacion": datetime.now().isoformat()
        }

        response_evento = supabase.table("eventos_unicos").insert(evento_data).execute()

        if not response_evento.data:
            return False, "❌ Error al crear el evento"

        for sector in sectores_seleccionados:
            impacto_data = {
                "evento_tipo": titulo,
                "sector": sector,
                "impacto_score": impacto
            }
            supabase.table("impacto_sectores").insert(impacto_data).execute()

        return True, f"✅ Noticia externa creada exitosamente con impacto en {len(sectores_seleccionados)} sector(es)"

    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# ==========================================
# PAGE
# ==========================================
st.title("🌐 Noticias Externas")
st.info("📌 Crea eventos personalizados con impacto en uno o varios sectores.")

sectores_disponibles = obtener_sectores_disponibles()
df_eventos, df_impactos = obtener_eventos_con_impacto()

with st.form("form_noticia_externa"):
    titulo = st.text_input(
        "📰 Título de la Noticia *",
        placeholder="Ej: Cambio en regulación bancaria"
    )

    st.markdown("---")
    st.markdown("### 🎯 Sectores Afectados")

    seleccionar_todos = st.checkbox("✅ Seleccionar todos los sectores")

    if seleccionar_todos:
        sectores_seleccionados = sectores_disponibles
        st.info(f"📊 {len(sectores_seleccionados)} sectores seleccionados")
    else:
        sectores_seleccionados = st.multiselect(
            "Selecciona uno o más sectores",
            sectores_disponibles,
            default=[]
        )

    st.markdown("---")

    impacto = st.select_slider(
        "📊 Nivel de Impacto *",
        options=[1, 2, 3, 4],
        value=2,
        format_func=lambda x: f"{'⭐' * x} {x}/4 - {['Bajo', 'Medio', 'Alto', 'Muy Alto'][x-1]}"
    )

    st.markdown("---")

    descripcion = st.text_area(
        "📝 Descripción (Opcional)",
        placeholder="Agrega contexto adicional sobre esta noticia...",
        height=100
    )

    st.markdown("---")

    fecha = st.date_input("📅 Fecha del Evento *", value=datetime.now().date())

    submitted = st.form_submit_button("💾 Crear Noticia Externa", use_container_width=True)

    if submitted:
        if not titulo:
            st.error("❌ El título es obligatorio")
        elif not sectores_seleccionados:
            st.error("❌ Debes seleccionar al menos un sector")
        else:
            exito, mensaje = crear_noticia_externa(
                titulo=titulo,
                sectores_seleccionados=sectores_seleccionados,
                impacto=impacto,
                descripcion=descripcion if descripcion else None,
                fecha=fecha
            )

            if exito:
                st.success(mensaje)
                st.cache_data.clear()
                st.balloons()
                st.rerun()
            else:
                st.error(mensaje)

st.markdown("---")
st.markdown("### 📋 Noticias Externas Registradas")

if df_eventos.empty:
    st.info("📭 No hay eventos disponibles.")
else:
    df_noticias_externas = df_eventos[df_eventos["categoria"] == "Noticia Externa"].copy()

    if df_noticias_externas.empty:
        st.info("📭 No hay noticias externas registradas.")
    else:
        df_noticias_externas = df_noticias_externas.sort_values("fecha", ascending=False)

        for _, noticia in df_noticias_externas.iterrows():
            impactos_noticia = df_impactos[df_impactos["evento_tipo"] == noticia["evento_nombre"]]
            sectores_afectados = impactos_noticia["sector"].tolist()
            impacto_noticia = impactos_noticia["impacto_score"].iloc[0] if not impactos_noticia.empty else 0

            fecha_titulo = noticia["fecha"].strftime("%d/%m/%Y") if pd.notna(noticia["fecha"]) else "Sin fecha"

            with st.expander(f"🌐 {noticia['evento_nombre']} - {fecha_titulo}"):
                col1, col2 = st.columns(2)

                with col1:
                    if pd.notna(noticia["fecha"]):
                        st.markdown(f"**📅 Fecha:** {noticia['fecha'].strftime('%d de %B de %Y')}")
                    else:
                        st.markdown("**📅 Fecha:** Sin fecha")

                    st.markdown(f"**📊 Impacto:** {'⭐' * int(impacto_noticia)} {int(impacto_noticia)}/4")

                with col2:
                    st.markdown(f"**🎯 Sectores:** {len(sectores_afectados)}")
                    preview = ", ".join(sectores_afectados[:3])
                    sufijo = "..." if len(sectores_afectados) > 3 else ""
                    st.markdown(f"_{preview}{sufijo}_")

                if noticia.get("descripcion"):
                    st.markdown(f"**📝 Descripción:** {noticia['descripcion']}")
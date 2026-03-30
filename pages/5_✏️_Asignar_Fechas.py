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
def obtener_eventos_con_impacto():
    try:
        impactos_response = supabase.table("impacto_sectores").select("*").execute()
        eventos_response = supabase.table("eventos_unicos").select("*").execute()

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


def actualizar_fecha_manual(evento_id, fecha):
    try:
        fecha_datetime = datetime.combine(fecha, time(0, 0, 0))

        data = {
            "fecha": fecha_datetime.isoformat(),
            "ultima_actualizacion": datetime.now().isoformat()
        }

        supabase.table("eventos_unicos").update(data).eq("id", evento_id).execute()
        return True, "✅ Fecha actualizada exitosamente"

    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# ==========================================
# PAGE
# ==========================================
st.title("✏️ Asignar Fechas")
st.info("📌 Usa esta sección para agregar fechas a eventos sin fecha. Solo se pueden editar eventos almacenados en Supabase.")

df_eventos, _ = obtener_eventos_con_impacto()

if df_eventos.empty:
    st.warning("⚠️ No hay eventos disponibles.")
else:
    df_editables = df_eventos[df_eventos["source"] == "supabase"].copy()

    if df_editables.empty:
        st.info("📭 No hay eventos editables desde Supabase.")
    else:
        df_sin_fecha = df_editables[df_editables["fecha"].isna()].sort_values("evento_nombre")

        if df_sin_fecha.empty:
            st.success("✅ ¡Todos los eventos editables ya tienen fecha asignada!")
        else:
            st.warning(f"⏳ **{len(df_sin_fecha)} eventos sin fecha**")

            cat_filtro = st.selectbox(
                "Filtrar por categoría:",
                ["Todos"] + sorted(df_sin_fecha["categoria"].dropna().unique().tolist())
            )

            if cat_filtro != "Todos":
                df_sin_fecha = df_sin_fecha[df_sin_fecha["categoria"] == cat_filtro]

            if df_sin_fecha.empty:
                st.info(f"✅ No hay eventos de categoría '{cat_filtro}' sin fecha")
            else:
                st.info(f"📊 {len(df_sin_fecha)} eventos sin fecha en esta categoría")

                evento_idx = st.selectbox(
                    "Selecciona un evento",
                    range(len(df_sin_fecha)),
                    format_func=lambda x: f"{df_sin_fecha.iloc[x]['evento_nombre']} ({df_sin_fecha.iloc[x]['categoria']})"
                )

                evento_seleccionado = df_sin_fecha.iloc[evento_idx]

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 📋 Información del Evento")
                    st.markdown(f"**Nombre:** {evento_seleccionado['evento_nombre']}")
                    st.markdown(f"**Categoría:** {evento_seleccionado['categoria']}")
                    st.markdown(f"**Tipo:** {evento_seleccionado['tipo']}")

                    if pd.notna(evento_seleccionado.get("pais")) and evento_seleccionado.get("pais"):
                        st.markdown(f"**País:** {evento_seleccionado['pais']}")

                    if pd.notna(evento_seleccionado.get("ticker")) and evento_seleccionado.get("ticker"):
                        st.markdown(f"**Ticker:** {evento_seleccionado['ticker']}")

                    if pd.notna(evento_seleccionado.get("descripcion")) and evento_seleccionado.get("descripcion"):
                        st.markdown(f"**Descripción:** {evento_seleccionado['descripcion']}")

                with col2:
                    st.markdown("### 📅 Asignar Fecha")

                    with st.form("form_fecha"):
                        fecha_nueva = st.date_input("📅 Fecha", value=datetime.now().date())

                        st.info("ℹ️ La hora se establecerá automáticamente a las 00:00")

                        if st.form_submit_button("💾 Guardar Fecha", use_container_width=True):
                            exito, mensaje = actualizar_fecha_manual(evento_seleccionado["id"], fecha_nueva)

                            if exito:
                                st.success(mensaje)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(mensaje)

st.markdown("---")
st.caption("Los eventos cargados desde Excel/CSV se visualizan en la app, pero sus fechas deben modificarse desde el archivo fuente.")
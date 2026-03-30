import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, time, date
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


def vaciar_fecha_evento(evento_id):
    try:
        data = {
            "fecha": None,
            "ultima_actualizacion": datetime.now().isoformat()
        }
        supabase.table("eventos_unicos").update(data).eq("id", evento_id).execute()
        return True, "✅ Fecha removida exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def eliminar_evento(evento_id, evento_nombre):
    try:
        supabase.table("impacto_sectores").delete().eq("evento_tipo", evento_nombre).execute()
        supabase.table("eventos_unicos").delete().eq("id", evento_id).execute()
        return True, "✅ Noticia eliminada exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# ==========================================
# PAGE
# ==========================================
st.title("🗄️ Noticias Expiradas")
st.info("📌 Administra eventos con fecha que ya pasaron o revisa todos los eventos editables con fecha.")

df_eventos, df_impactos = obtener_eventos_con_impacto()

if df_eventos.empty:
    st.warning("⚠️ No hay eventos disponibles.")
else:
    df_editables = df_eventos[df_eventos["source"] == "supabase"].copy()

    if df_editables.empty:
        st.info("📭 No hay eventos editables desde Supabase.")
    else:
        col_toggle1, col_toggle2 = st.columns(2)

        with col_toggle1:
            mostrar_todas = st.checkbox("📋 Mostrar TODOS los eventos con fecha", value=False)

        with col_toggle2:
            if mostrar_todas:
                st.info("✅ Mostrando todos los eventos editables con fecha")
            else:
                st.info("⏰ Mostrando solo expirados")

        st.markdown("---")

        fecha_hoy = date.today()

        if mostrar_todas:
            df_noticias = df_editables[df_editables["fecha"].notna()].copy()
        else:
            df_noticias = df_editables[
                (df_editables["fecha"].notna()) &
                (df_editables["fecha"].dt.date < fecha_hoy)
            ].copy()

        if df_noticias.empty:
            if mostrar_todas:
                st.info("📭 No hay eventos editables con fecha asignada.")
            else:
                st.success("✅ ¡No hay noticias o eventos expirados!")
        else:
            if mostrar_todas:
                st.info(f"📋 **{len(df_noticias)} eventos con fecha encontrados**")
            else:
                st.warning(f"⏰ **{len(df_noticias)} eventos expirados encontrados**")

            categorias_disponibles_filtro = sorted(df_noticias["categoria"].dropna().unique().tolist())

            cat_filtro_exp = st.selectbox(
                "Filtrar por categoría:",
                ["Todos"] + categorias_disponibles_filtro,
                key="cat_noticias"
            )

            if cat_filtro_exp != "Todos":
                df_noticias = df_noticias[df_noticias["categoria"] == cat_filtro_exp]

            if df_noticias.empty:
                st.info(f"✅ No hay eventos de categoría '{cat_filtro_exp}'")
            else:
                df_noticias = df_noticias.sort_values("fecha", ascending=False)

                st.markdown("---")

                for _, evento in df_noticias.iterrows():
                    esta_expirada = evento["fecha"].date() < fecha_hoy
                    dias_diferencia = abs((fecha_hoy - evento["fecha"].date()).days)

                    impactos_evento = df_impactos[df_impactos["evento_tipo"] == evento["evento_nombre"]]["impacto_score"]
                    impacto_promedio = impactos_evento.mean() if not impactos_evento.empty else 0

                    if esta_expirada:
                        titulo_expander = f"⏰ {evento['evento_nombre']} - Expiró hace {dias_diferencia} día(s)"
                    else:
                        titulo_expander = f"📅 {evento['evento_nombre']} - En {dias_diferencia} día(s)"

                    with st.expander(titulo_expander):
                        col1, col2 = st.columns([2, 1])

                        with col1:
                            st.markdown(f"**📅 Fecha:** {evento['fecha'].strftime('%d de %B de %Y')}")
                            st.markdown(f"**📂 Categoría:** {evento['categoria']}")

                            if esta_expirada:
                                st.markdown(f"**🔴 Estado:** Expirada hace {dias_diferencia} día(s)")
                            else:
                                st.markdown(f"**🟢 Estado:** Próxima en {dias_diferencia} día(s)")

                            if pd.notna(evento.get("descripcion")) and evento.get("descripcion"):
                                st.markdown(f"**📝 Descripción:** {evento['descripcion']}")

                            if pd.notna(evento.get("ticker")) and evento.get("ticker"):
                                st.markdown(f"**📌 Ticker:** `{evento['ticker']}`")

                            if pd.notna(evento.get("pais")) and evento.get("pais"):
                                st.markdown(f"**🌍 País:** {evento['pais']}")

                            if impacto_promedio > 0:
                                st.markdown(f"**📊 Impacto Promedio:** {'⭐' * int(round(impacto_promedio))} {impacto_promedio:.1f}/4")

                        with col2:
                            st.markdown("### 🛠️ Acciones")

                            if evento["categoria"] == "Noticia Externa":
                                st.info("🌐 Noticia Externa: Se eliminará completamente")

                                if st.button(f"🗑️ Eliminar Noticia", key=f"del_{evento['id']}", use_container_width=True):
                                    exito, mensaje = eliminar_evento(evento["id"], evento["evento_nombre"])
                                    if exito:
                                        st.success(mensaje)
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(mensaje)
                            else:
                                st.info("📅 Evento recurrente: Se removerá la fecha")

                                if st.button(f"🗑️ Remover Fecha", key=f"del_{evento['id']}", use_container_width=True):
                                    exito, mensaje = vaciar_fecha_evento(evento["id"])
                                    if exito:
                                        st.success(mensaje)
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(mensaje)

                            st.markdown("---")

                            with st.form(f"form_actualizar_{evento['id']}"):
                                st.markdown("**📅 Nueva Fecha**")

                                fecha_minima = fecha_hoy + timedelta(days=1)

                                fecha_default = (
                                    evento["fecha"].date()
                                    if evento["fecha"].date() >= fecha_hoy
                                    else fecha_minima
                                )

                                nueva_fecha = st.date_input(
                                    "Selecciona nueva fecha",
                                    value=fecha_default,
                                    min_value=fecha_minima,
                                    key=f"fecha_{evento['id']}"
                                )

                                if st.form_submit_button("✅ Actualizar Fecha", use_container_width=True):
                                    exito, mensaje = actualizar_fecha_manual(evento["id"], nueva_fecha)

                                    if exito:
                                        st.success(mensaje)
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(mensaje)

st.markdown("---")
st.caption("Los eventos provenientes del Excel/CSV no se administran aquí; su mantenimiento se hace desde el archivo fuente.")
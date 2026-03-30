import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import calendar
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

        df_eventos_csv = pd.DataFrame(eventos)
        df_impactos_csv = pd.DataFrame(impactos)

        if not df_eventos_csv.empty:
            df_eventos_csv["fecha"] = pd.to_datetime(df_eventos_csv["fecha"], errors="coerce")

        return df_eventos_csv, df_impactos_csv

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


def obtener_impacto_evento(evento_nombre, sector, df_impactos):
    try:
        resultado = df_impactos[
            (df_impactos["evento_tipo"] == evento_nombre) &
            (df_impactos["sector"] == sector)
        ]
        if not resultado.empty:
            return resultado.iloc[0]["impacto_score"]
        return 0
    except Exception:
        return 0


def obtener_semanas_del_mes(anio, mes):
    primer_dia = datetime(anio, mes, 1).date()
    ultimo_dia = datetime(anio, mes, calendar.monthrange(anio, mes)[1]).date()

    semanas = []
    fecha_actual = primer_dia

    while fecha_actual <= ultimo_dia:
        inicio_semana = fecha_actual - timedelta(days=fecha_actual.weekday())
        fin_semana = inicio_semana + timedelta(days=6)

        if inicio_semana < primer_dia:
            inicio_semana = primer_dia

        if fin_semana > ultimo_dia:
            fin_semana = ultimo_dia

        semanas.append((inicio_semana, fin_semana))
        fecha_actual = fin_semana + timedelta(days=1)

    return semanas


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("# 📊 Filtros y Controles")
    st.markdown("---")

    sectores_disponibles = obtener_sectores_disponibles()
    sector_seleccionado = st.selectbox(
        "🎯 Sector",
        sectores_disponibles,
        index=sectores_disponibles.index("General") if "General" in sectores_disponibles else 0
    )

    st.markdown("---")
    st.subheader("📅 Período")

    col_mes, col_anio = st.columns(2)

    with col_mes:
        mes_seleccionado = st.selectbox(
            "Mes",
            range(1, 13),
            index=datetime.now().month - 1,
            format_func=lambda x: calendar.month_name[x]
        )

    with col_anio:
        anio_seleccionado = st.selectbox(
            "Año",
            range(2026, 2028),
            index=0
        )

    primer_dia = datetime(anio_seleccionado, mes_seleccionado, 1).date()
    ultimo_dia = datetime(
        anio_seleccionado,
        mes_seleccionado,
        calendar.monthrange(anio_seleccionado, mes_seleccionado)[1]
    ).date()

    st.info(f"📆 {primer_dia.strftime('%d/%m/%Y')} - {ultimo_dia.strftime('%d/%m/%Y')}")

    st.markdown("---")
    st.subheader("🔍 Tipo de Eventos")

    mostrar_economicos = st.checkbox("📊 Eventos Económicos", value=True)
    mostrar_magnificent7 = st.checkbox("💎 Magnificent 7", value=True)
    mostrar_dow_jones = st.checkbox("🏛️ Dow Jones 30", value=True)
    mostrar_top3_sector = st.checkbox("🏆 Top 3 Sector", value=True)
    mostrar_noticias_externas = st.checkbox("🌐 Noticias Externas", value=True)

    st.markdown("---")

    impacto_minimo = st.select_slider(
        "Impacto mínimo",
        options=[1, 2, 3, 4],
        value=1,
        format_func=lambda x: f"{'⭐' * x} {x}/4"
    )

    st.markdown("---")

    if st.button("🔄 Refrescar Datos", use_container_width=True):
        st.cache_data.clear()
        st.session_state.semana_actual = 0
        st.rerun()


# ==========================================
# PAGE
# ==========================================
st.title("📅 Calendario")
st.markdown(f"**Sector:** `{sector_seleccionado}` | **Período:** {calendar.month_name[mes_seleccionado]} {anio_seleccionado}")

df_eventos, df_impactos = obtener_eventos_con_impacto()

if df_eventos.empty:
    st.warning("⚠️ No hay eventos disponibles.")
else:
    categorias_permitidas = []
    if mostrar_economicos:
        categorias_permitidas.append("Evento Económico")
    if mostrar_magnificent7:
        categorias_permitidas.append("Magnificent 7")
    if mostrar_dow_jones:
        categorias_permitidas.append("Dow Jones 30")
    if mostrar_top3_sector:
        categorias_permitidas.append("Top 3 Sector")
    if mostrar_noticias_externas:
        categorias_permitidas.append("Noticia Externa")

    df_filtrado = df_eventos[
        (df_eventos["fecha"].notna()) &
        (df_eventos["fecha"].dt.date >= primer_dia) &
        (df_eventos["fecha"].dt.date <= ultimo_dia)
    ].copy()

    df_filtrado["impacto"] = df_filtrado["evento_nombre"].apply(
        lambda x: obtener_impacto_evento(x, sector_seleccionado, df_impactos)
    )

    df_filtrado = df_filtrado[df_filtrado["impacto"] >= 1]

    if categorias_permitidas:
        df_filtrado = df_filtrado[df_filtrado["categoria"].isin(categorias_permitidas)]
    else:
        st.warning("⚠️ Selecciona al menos una categoría de eventos para mostrar.")
        df_filtrado = pd.DataFrame()

    df_filtrado = df_filtrado[df_filtrado["impacto"] >= impacto_minimo]
    df_filtrado = df_filtrado.sort_values(["fecha"]).reset_index(drop=True)

    if df_filtrado.empty:
        st.info(f"📭 No hay eventos en {calendar.month_name[mes_seleccionado]} {anio_seleccionado} que coincidan con los criterios seleccionados.")
    else:
        semanas = obtener_semanas_del_mes(anio_seleccionado, mes_seleccionado)

        if "semana_actual" not in st.session_state:
            st.session_state.semana_actual = 0

        if st.session_state.semana_actual >= len(semanas):
            st.session_state.semana_actual = 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📅 Total Eventos", len(df_filtrado))
        with col2:
            eventos_economicos = len(df_filtrado[df_filtrado["categoria"] == "Evento Económico"])
            st.metric("📊 Económicos", eventos_economicos)
        with col3:
            eventos_magnificent = len(df_filtrado[df_filtrado["categoria"] == "Magnificent 7"])
            st.metric("💎 Magnificent 7", eventos_magnificent)
        with col4:
            eventos_muy_alto = len(df_filtrado[df_filtrado["impacto"] == 4])
            st.metric("🔴 Impacto 4", eventos_muy_alto)

        st.markdown("---")

        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

        with col_nav1:
            if st.button(
                "⬅️ Semana Anterior",
                disabled=st.session_state.semana_actual == 0,
                use_container_width=True
            ):
                st.session_state.semana_actual -= 1
                st.rerun()

        with col_nav2:
            inicio_semana, fin_semana = semanas[st.session_state.semana_actual]
            st.markdown(f"### 📆 Semana {st.session_state.semana_actual + 1} de {len(semanas)}")
            st.markdown(f"**{inicio_semana.strftime('%d/%m/%Y')} - {fin_semana.strftime('%d/%m/%Y')}**")

        with col_nav3:
            if st.button(
                "Semana Siguiente ➡️",
                disabled=st.session_state.semana_actual == len(semanas) - 1,
                use_container_width=True
            ):
                st.session_state.semana_actual += 1
                st.rerun()

        st.markdown("---")

        inicio_semana, fin_semana = semanas[st.session_state.semana_actual]
        df_semana = df_filtrado[
            (df_filtrado["fecha"].dt.date >= inicio_semana) &
            (df_filtrado["fecha"].dt.date <= fin_semana)
        ]

        if df_semana.empty:
            st.info("📭 No hay eventos en esta semana.")
        else:
            fechas_unicas = sorted(df_semana["fecha"].dt.date.unique())

            for fecha in fechas_unicas:
                eventos_dia = df_semana[
                    df_semana["fecha"].dt.date == fecha
                ].sort_values("impacto", ascending=False)

                fecha_str = pd.to_datetime(fecha).strftime("%A, %d de %B de %Y")
                st.markdown(f"### 📅 {fecha_str}")

                for _, row in eventos_dia.iterrows():
                    impacto = int(row["impacto"])

                    if impacto == 4:
                        icono = "🔴"
                        badge = "Muy Alto"
                    elif impacto == 3:
                        icono = "🟠"
                        badge = "Alto"
                    elif impacto == 2:
                        icono = "🟡"
                        badge = "Medio"
                    else:
                        icono = "🟢"
                        badge = "Bajo"

                    if row["categoria"] == "Magnificent 7":
                        cat_icon = "💎"
                    elif row["categoria"] == "Dow Jones 30":
                        cat_icon = "🏛️"
                    elif row["categoria"] == "Top 3 Sector":
                        cat_icon = "🏆"
                    elif row["categoria"] == "Noticia Externa":
                        cat_icon = "🌐"
                    else:
                        cat_icon = "📊"

                    col1, col2 = st.columns([1, 4])

                    with col1:
                        st.markdown(f"<small>{icono} **{badge}** ({impacto}/4)</small>", unsafe_allow_html=True)
                        st.markdown(f"<small>{cat_icon} {row['categoria']}</small>", unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"**{row['evento_nombre']}**")

                        info_parts = []

                        if row.get("ticker"):
                            info_parts.append(f"📌 `{row['ticker']}`")

                        if row.get("pais"):
                            info_parts.append(f"🌍 {row['pais']}")

                        if row.get("descripcion"):
                            descripcion = str(row["descripcion"])
                            desc_corta = descripcion[:100] + "..." if len(descripcion) > 100 else descripcion
                            info_parts.append(f"📝 {desc_corta}")

                        if info_parts:
                            st.markdown(f"<small>{' | '.join(info_parts)}</small>", unsafe_allow_html=True)

                        st.markdown(f"<small>💥 Impacto en {sector_seleccionado}: {impacto}/4</small>", unsafe_allow_html=True)

                    st.markdown("---")
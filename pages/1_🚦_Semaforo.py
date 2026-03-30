import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
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
    h1 {
        color: #FF4B4B;
    }

    .calendario-dia {
        position: relative;
        cursor: pointer;
    }

    .calendario-dia .tooltip-content {
        visibility: hidden;
        width: 260px;
        background-color: #333;
        color: #fff;
        text-align: left;
        border-radius: 8px;
        padding: 10px;
        position: absolute;
        z-index: 1000;
        bottom: 110%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.85em;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }

    .calendario-dia .tooltip-content::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }

    .calendario-dia:hover .tooltip-content {
        visibility: visible;
        opacity: 1;
    }

    .tooltip-evento {
        padding: 3px 0;
        border-bottom: 1px solid #555;
    }

    .tooltip-evento:last-child {
        border-bottom: none;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# FUNCIONES DE CARGA
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

            fecha_raw = row.get("Fecha")
            fecha = pd.to_datetime(fecha_raw, errors="coerce")

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


def generar_calendario_semaforo(anio, mes, df_eventos_mes):
    cal = calendar.monthcalendar(anio, mes)
    dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

    cols_header = st.columns(7)
    for i, dia in enumerate(dias_semana):
        with cols_header[i]:
            st.markdown(f"**{dia}**")

    for semana in cal:
        cols_semana = st.columns(7)
        for i, dia in enumerate(semana):
            with cols_semana[i]:
                if dia == 0:
                    st.markdown(
                        """
                        <div style='background-color: transparent; padding: 15px; border-radius: 8px; text-align: center; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    fecha_dia = datetime(anio, mes, dia).date()
                    eventos_dia = df_eventos_mes[df_eventos_mes["fecha"].dt.date == fecha_dia]

                    if eventos_dia.empty:
                        st.markdown(
                            f"""
                            <div style='background-color: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
                                <div style='font-size: 1.2em; font-weight: bold; color: #666;'>{dia}</div>
                                <div style='font-size: 0.8em; color: #999; margin-top: 5px;'>Sin eventos</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        impacto_max = int(eventos_dia["impacto"].max())
                        num_eventos = len(eventos_dia)

                        if impacto_max == 4:
                            bg_color = "#FF4444"
                            text_color = "white"
                            emoji = "🔴"
                        elif impacto_max == 3:
                            bg_color = "#FF8C00"
                            text_color = "white"
                            emoji = "🟠"
                        elif impacto_max == 2:
                            bg_color = "#FFD700"
                            text_color = "#333"
                            emoji = "🟡"
                        else:
                            bg_color = "#4CAF50"
                            text_color = "white"
                            emoji = "🟢"

                        tooltip_html = "<div class='tooltip-content'>"
                        tooltip_html += f"<strong>📅 {dia} de {calendar.month_name[mes]}</strong><br/><br/>"

                        eventos_ordenados = eventos_dia.sort_values("impacto", ascending=False)

                        for _, evento in eventos_ordenados.iterrows():
                            impacto_evento = int(evento["impacto"])
                            emoji_impacto = "🔴" if impacto_evento == 4 else "🟠" if impacto_evento == 3 else "🟡" if impacto_evento == 2 else "🟢"

                            nombre_evento = evento["evento_nombre"]
                            if len(nombre_evento) > 40:
                                nombre_evento = nombre_evento[:37] + "..."

                            tooltip_html += f"<div class='tooltip-evento'>{emoji_impacto} {nombre_evento}</div>"

                        tooltip_html += "</div>"

                        st.markdown(
                            f"""
                            <div class='calendario-dia' style='background-color: {bg_color}; padding: 15px; border-radius: 8px; text-align: center; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative;'>
                                <div style='font-size: 1.3em; font-weight: bold; color: {text_color};'>{dia}</div>
                                <div style='font-size: 0.85em; color: {text_color}; margin-top: 5px;'>{emoji} {num_eventos} evento{"s" if num_eventos > 1 else ""}</div>
                                <div style='font-size: 0.8em; color: {text_color};'>Impacto: {impacto_max}/4</div>
                                {tooltip_html}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )


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
        st.rerun()


# ==========================================
# PAGE
# ==========================================
st.title("🚦 Semáforo de Eventos")
st.markdown("Visualiza eventos por mes según el impacto para el sector seleccionado.")

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

    st.markdown("### 📅 Seleccionar Períodos")

    col1, col2 = st.columns(2)

    with col1:
        mes_inicio = mes_seleccionado
        anio_inicio = anio_seleccionado
        anio_fin = anio_seleccionado + 2

        meses_opciones = []
        for anio in range(anio_inicio, anio_fin + 1):
            mes_start = mes_inicio if anio == anio_inicio else 1
            for mes in range(mes_start, 13):
                meses_opciones.append((anio, mes))

        meses_seleccionados = st.multiselect(
            "Selecciona uno o más meses",
            meses_opciones,
            default=[(anio_seleccionado, mes_seleccionado)],
            format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}"
        )

    with col2:
        if meses_seleccionados:
            st.info(f"📊 **{len(meses_seleccionados)} mes(es) seleccionado(s)**")

    st.markdown("---")

    if not meses_seleccionados:
        st.warning("⚠️ Selecciona al menos un mes para mostrar")
    else:
        for idx, (anio_mes, mes_mes) in enumerate(meses_seleccionados):
            primer_dia_mes = datetime(anio_mes, mes_mes, 1).date()
            ultimo_dia_mes = datetime(anio_mes, mes_mes, calendar.monthrange(anio_mes, mes_mes)[1]).date()

            st.markdown(f"## 📅 {calendar.month_name[mes_mes]} {anio_mes}")

            df_semaforo = df_eventos[
                (df_eventos["fecha"].notna()) &
                (df_eventos["fecha"].dt.date >= primer_dia_mes) &
                (df_eventos["fecha"].dt.date <= ultimo_dia_mes)
            ].copy()

            df_semaforo["impacto"] = df_semaforo["evento_nombre"].apply(
                lambda x: obtener_impacto_evento(x, sector_seleccionado, df_impactos)
            )

            df_semaforo = df_semaforo[df_semaforo["impacto"] >= 1]

            if categorias_permitidas:
                df_semaforo = df_semaforo[df_semaforo["categoria"].isin(categorias_permitidas)]

            df_semaforo = df_semaforo[df_semaforo["impacto"] >= impacto_minimo]

            generar_calendario_semaforo(anio_mes, mes_mes, df_semaforo)

            if idx < len(meses_seleccionados) - 1:
                st.markdown("---")
                st.markdown("")

        st.markdown("---")
        st.markdown("### 📖 Leyenda")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown("🟢 **Bajo (1/4)**")
        with col2:
            st.markdown("🟡 **Medio (2/4)**")
        with col3:
            st.markdown("🟠 **Alto (3/4)**")
        with col4:
            st.markdown("🔴 **Muy Alto (4/4)**")
        with col5:
            st.markdown("⚪ **Sin eventos**")
import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, time, date
import calendar
import os

# ==========================================
# CONFIGURACIÓN
# ==========================================
# Intentar obtener de secrets de Streamlit Cloud primero, luego de variables de entorno
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Economic Events Calendar",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# ESTILOS CSS
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
    
    /* Estilos para tooltip */
    .calendario-dia {
        position: relative;
        cursor: pointer;
    }
    
    .calendario-dia .tooltip-content {
        visibility: hidden;
        width: 250px;
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
# FUNCIONES DE BASE DE DATOS
# ==========================================

@st.cache_data(ttl=300)
def obtener_sectores_disponibles():
    """Obtiene lista de sectores únicos desde impacto_sectores"""
    try:
        response = supabase.table('impacto_sectores').select('sector').execute()
        sectores = list(set([item['sector'] for item in response.data]))
        return sorted(sectores)
    except Exception as e:
        st.error(f"Error al obtener sectores: {str(e)}")
        return ["General"]

@st.cache_data(ttl=300)
def obtener_eventos_con_impacto():
    """Obtiene TODOS los eventos (económicos + earnings + noticias externas) con sus impactos"""
    try:
        # Obtener tabla de impactos
        impactos_response = supabase.table('impacto_sectores').select('*').execute()
        
        # Obtener TODOS los eventos únicos (económicos Y earnings Y noticias externas)
        eventos_response = supabase.table('eventos_unicos').select('*').execute()
        
        if not eventos_response.data:
            return pd.DataFrame(), pd.DataFrame()
        
        df_eventos = pd.DataFrame(eventos_response.data)
        df_impactos = pd.DataFrame(impactos_response.data)
        
        # Convertir fechas
        df_eventos['fecha'] = pd.to_datetime(df_eventos['fecha'], errors='coerce')
        
        return df_eventos, df_impactos
    except Exception as e:
        st.error(f"Error al obtener eventos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def obtener_impacto_evento(evento_nombre, sector, df_impactos):
    """Obtiene el impacto de un evento en un sector específico"""
    try:
        resultado = df_impactos[
            (df_impactos['evento_tipo'] == evento_nombre) & 
            (df_impactos['sector'] == sector)
        ]
        if not resultado.empty:
            return resultado.iloc[0]['impacto_score']
        return 0
    except:
        return 0

def actualizar_fecha_manual(evento_id, fecha):
    """Actualiza manualmente la fecha de un evento (solo día, sin hora)"""
    try:
        # Crear datetime a las 00:00:00
        fecha_datetime = datetime.combine(fecha, time(0, 0, 0))
        
        data = {
            "fecha": fecha_datetime.isoformat(),
            "ultima_actualizacion": datetime.now().isoformat()
        }
        supabase.table('eventos_unicos').update(data).eq('id', evento_id).execute()
        return True, "✅ Fecha actualizada exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def vaciar_fecha_evento(evento_id):
    """Vacía la fecha de un evento (pone NULL)"""
    try:
        data = {
            "fecha": None,
            "ultima_actualizacion": datetime.now().isoformat()
        }
        supabase.table('eventos_unicos').update(data).eq('id', evento_id).execute()
        return True, "✅ Fecha removida exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def eliminar_evento(evento_id, evento_nombre):
    """Elimina un evento y todos sus impactos asociados"""
    try:
        # 1. Eliminar impactos asociados en impacto_sectores
        supabase.table('impacto_sectores').delete().eq('evento_tipo', evento_nombre).execute()
        
        # 2. Eliminar el evento en eventos_unicos
        supabase.table('eventos_unicos').delete().eq('id', evento_id).execute()
        
        return True, "✅ Noticia eliminada exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def crear_noticia_externa(titulo, sectores_seleccionados, impacto, descripcion, fecha):
    """Crea una nueva noticia externa en eventos_unicos y sus impactos en impacto_sectores"""
    try:
        # Crear datetime a las 00:00:00
        fecha_datetime = datetime.combine(fecha, time(0, 0, 0))
        
        # 1. Crear el evento en eventos_unicos
        evento_data = {
            "evento_nombre": titulo,
            "categoria": "Noticia Externa",
            "tipo": "economico",
            "fecha": fecha_datetime.isoformat(),
            "descripcion": descripcion if descripcion else None,
            "ultima_actualizacion": datetime.now().isoformat()
        }
        
        response_evento = supabase.table('eventos_unicos').insert(evento_data).execute()
        
        if not response_evento.data:
            return False, "❌ Error al crear el evento"
        
        # 2. Crear los impactos para cada sector seleccionado en impacto_sectores
        for sector in sectores_seleccionados:
            impacto_data = {
                "evento_tipo": titulo,
                "sector": sector,
                "impacto_score": impacto
            }
            supabase.table('impacto_sectores').insert(impacto_data).execute()
        
        return True, f"✅ Noticia externa creada exitosamente con impacto en {len(sectores_seleccionados)} sector(es)"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def generar_calendario_semaforo(anio, mes, df_eventos_mes):
    """Genera el calendario con colores usando columnas de Streamlit - CON TOOLTIPS"""
    
    # Obtener información del mes
    cal = calendar.monthcalendar(anio, mes)
    dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    
    # Headers (días de la semana)
    cols_header = st.columns(7)
    for i, dia in enumerate(dias_semana):
        with cols_header[i]:
            st.markdown(f"**{dia}**")
    
    # Días del mes
    for semana in cal:
        cols_semana = st.columns(7)
        for i, dia in enumerate(semana):
            with cols_semana[i]:
                if dia == 0:
                    # Día vacío
                    st.markdown(
                        """
                        <div style='background-color: transparent; padding: 15px; border-radius: 8px; text-align: center; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    # Buscar eventos de este día
                    fecha_dia = datetime(anio, mes, dia).date()
                    eventos_dia = df_eventos_mes[df_eventos_mes['fecha'].dt.date == fecha_dia]
                    
                    if eventos_dia.empty:
                        # Sin eventos
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
                        # Con eventos - obtener impacto máximo
                        impacto_max = int(eventos_dia['impacto'].max())
                        num_eventos = len(eventos_dia)
                        
                        # Colores según impacto
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
                        
                        # Crear contenido del tooltip con lista de eventos
                        tooltip_html = "<div class='tooltip-content'>"
                        tooltip_html += f"<strong>📅 {dia} de {calendar.month_name[mes]}</strong><br/><br/>"
                        
                        # Ordenar eventos por impacto (mayor a menor)
                        eventos_ordenados = eventos_dia.sort_values('impacto', ascending=False)
                        
                        for idx, evento in eventos_ordenados.iterrows():
                            impacto_evento = int(evento['impacto'])
                            emoji_impacto = "🔴" if impacto_evento == 4 else "🟠" if impacto_evento == 3 else "🟡" if impacto_evento == 2 else "🟢"
                            
                            # Truncar nombre si es muy largo
                            nombre_evento = evento['evento_nombre']
                            if len(nombre_evento) > 40:
                                nombre_evento = nombre_evento[:37] + "..."
                            
                            tooltip_html += f"<div class='tooltip-evento'>{emoji_impacto} {nombre_evento}</div>"
                        
                        tooltip_html += "</div>"
                        
                        # Renderizar día con tooltip
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

def obtener_semanas_del_mes(anio, mes):
    """Obtiene las semanas de un mes dado"""
    primer_dia = datetime(anio, mes, 1).date()
    ultimo_dia = datetime(anio, mes, calendar.monthrange(anio, mes)[1]).date()
    
    semanas = []
    fecha_actual = primer_dia
    
    while fecha_actual <= ultimo_dia:
        # Inicio de semana (lunes)
        inicio_semana = fecha_actual - timedelta(days=fecha_actual.weekday())
        # Fin de semana (domingo)
        fin_semana = inicio_semana + timedelta(days=6)
        
        # Ajustar si la semana empieza antes del mes
        if inicio_semana < primer_dia:
            inicio_semana = primer_dia
        
        # Ajustar si la semana termina después del mes
        if fin_semana > ultimo_dia:
            fin_semana = ultimo_dia
        
        semanas.append((inicio_semana, fin_semana))
        
        # Avanzar a la siguiente semana
        fecha_actual = fin_semana + timedelta(days=1)
    
    return semanas

# ==========================================
# SIDEBAR - FILTROS
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
    
    # Selector de mes y año
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
            range(2025, 2028),
            index=0
        )
    
    # Calcular primer y último día del mes
    primer_dia = datetime(anio_seleccionado, mes_seleccionado, 1).date()
    ultimo_dia = datetime(anio_seleccionado, mes_seleccionado, calendar.monthrange(anio_seleccionado, mes_seleccionado)[1]).date()
    
    st.info(f"📆 {primer_dia.strftime('%d/%m/%Y')} - {ultimo_dia.strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.subheader("🔍 Tipo de Eventos")
    
    # Filtros por categoría
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
# PÁGINA PRINCIPAL
# ==========================================
st.title("📊 Economic Events Calendar")
st.markdown(f"**Sector:** `{sector_seleccionado}` | **Período:** {calendar.month_name[mes_seleccionado]} {anio_seleccionado}")

# Obtener datos
df_eventos, df_impactos = obtener_eventos_con_impacto()

if df_eventos.empty:
    st.warning("⚠️ No hay eventos disponibles en la base de datos")
else:
    # Preparar categorías permitidas
    categorias_permitidas = []
    if mostrar_economicos:
        categorias_permitidas.append('Evento Económico')
    if mostrar_magnificent7:
        categorias_permitidas.append('Magnificent 7')
    if mostrar_dow_jones:
        categorias_permitidas.append('Dow Jones 30')
    if mostrar_top3_sector:
        categorias_permitidas.append('Top 3 Sector')
    if mostrar_noticias_externas:
        categorias_permitidas.append('Noticia Externa')
    
    # Crear tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚦 Semáforo", 
        "📅 Calendario", 
        "🌐 Noticias Externas", 
        "✏️ Asignar Fechas",
        "🗄️ Noticias Expiradas"
    ])
    
    # TAB 1: SEMÁFORO
    with tab1:
        st.subheader(f"🚦 Vista de Semáforo")
        st.info("💡 Pasa el mouse sobre los días para ver las noticias")
        
        st.markdown("### 📅 Seleccionar Períodos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            mes_inicio = mes_seleccionado
            anio_inicio = anio_seleccionado
            anio_fin = anio_seleccionado + 2
            
            meses_opciones = []
            for anio in range(anio_inicio, anio_fin + 1):
                mes_start = mes_inicio if anio == anio_inicio else 1
                mes_end = 12
                
                for mes in range(mes_start, mes_end + 1):
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
                    (df_eventos['fecha'].notna()) &
                    (df_eventos['fecha'].dt.date >= primer_dia_mes) &
                    (df_eventos['fecha'].dt.date <= ultimo_dia_mes)
                ].copy()
                
                df_semaforo['impacto'] = df_semaforo['evento_nombre'].apply(
                    lambda x: obtener_impacto_evento(x, sector_seleccionado, df_impactos)
                )
                
                df_semaforo = df_semaforo[df_semaforo['impacto'] >= 1]
                
                if categorias_permitidas:
                    df_semaforo = df_semaforo[df_semaforo['categoria'].isin(categorias_permitidas)]
                
                df_semaforo = df_semaforo[df_semaforo['impacto'] >= impacto_minimo]
                
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
    
    # TAB 2: CALENDARIO
    with tab2:
        st.subheader("📅 Eventos por Semana")
        
        df_filtrado = df_eventos[
            (df_eventos['fecha'].notna()) &
            (df_eventos['fecha'].dt.date >= primer_dia) &
            (df_eventos['fecha'].dt.date <= ultimo_dia)
        ].copy()
        
        df_filtrado['impacto'] = df_filtrado['evento_nombre'].apply(
            lambda x: obtener_impacto_evento(x, sector_seleccionado, df_impactos)
        )
        
        df_filtrado = df_filtrado[df_filtrado['impacto'] >= 1]
        
        if categorias_permitidas:
            df_filtrado = df_filtrado[df_filtrado['categoria'].isin(categorias_permitidas)]
        else:
            st.warning("⚠️ Selecciona al menos una categoría de eventos para mostrar")
            df_filtrado = pd.DataFrame()
        
        df_filtrado = df_filtrado[df_filtrado['impacto'] >= impacto_minimo]
        df_filtrado = df_filtrado.sort_values(['fecha']).reset_index(drop=True)
        
        if df_filtrado.empty:
            st.info(f"📭 No hay eventos en {calendar.month_name[mes_seleccionado]} {anio_seleccionado} que coincidan con los criterios seleccionados")
        else:
            semanas = obtener_semanas_del_mes(anio_seleccionado, mes_seleccionado)
            
            if 'semana_actual' not in st.session_state:
                st.session_state.semana_actual = 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📅 Total Eventos", len(df_filtrado))
            with col2:
                eventos_economicos = len(df_filtrado[df_filtrado['categoria'] == 'Evento Económico'])
                st.metric("📊 Económicos", eventos_economicos)
            with col3:
                eventos_magnificent = len(df_filtrado[df_filtrado['categoria'] == 'Magnificent 7'])
                st.metric("💎 Magnificent 7", eventos_magnificent)
            with col4:
                eventos_muy_alto = len(df_filtrado[df_filtrado['impacto'] == 4])
                st.metric("🔴 Impacto 4", eventos_muy_alto)
            
            st.markdown("---")
            
            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            
            with col_nav1:
                if st.button("⬅️ Semana Anterior", disabled=st.session_state.semana_actual == 0, use_container_width=True):
                    st.session_state.semana_actual -= 1
                    st.rerun()
            
            with col_nav2:
                inicio_semana, fin_semana = semanas[st.session_state.semana_actual]
                st.markdown(f"### 📆 Semana {st.session_state.semana_actual + 1} de {len(semanas)}")
                st.markdown(f"**{inicio_semana.strftime('%d/%m/%Y')} - {fin_semana.strftime('%d/%m/%Y')}**")
            
            with col_nav3:
                if st.button("Semana Siguiente ➡️", disabled=st.session_state.semana_actual == len(semanas) - 1, use_container_width=True):
                    st.session_state.semana_actual += 1
                    st.rerun()
            
            st.markdown("---")
            
            inicio_semana, fin_semana = semanas[st.session_state.semana_actual]
            df_semana = df_filtrado[
                (df_filtrado['fecha'].dt.date >= inicio_semana) &
                (df_filtrado['fecha'].dt.date <= fin_semana)
            ]
            
            if df_semana.empty:
                st.info("📭 No hay eventos en esta semana")
            else:
                fechas_unicas = sorted(df_semana['fecha'].dt.date.unique())
                
                for fecha in fechas_unicas:
                    eventos_dia = df_semana[df_semana['fecha'].dt.date == fecha].sort_values('impacto', ascending=False)
                    
                    fecha_str = pd.to_datetime(fecha).strftime('%A, %d de %B de %Y')
                    st.markdown(f"### 📅 {fecha_str}")
                    
                    for idx, row in eventos_dia.iterrows():
                        impacto = int(row['impacto'])
                        
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
                        
                        if row['categoria'] == 'Magnificent 7':
                            cat_icon = "💎"
                        elif row['categoria'] == 'Dow Jones 30':
                            cat_icon = "🏛️"
                        elif row['categoria'] == 'Top 3 Sector':
                            cat_icon = "🏆"
                        elif row['categoria'] == 'Noticia Externa':
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
                            if row.get('ticker'):
                                info_parts.append(f"📌 `{row['ticker']}`")
                            if row.get('pais'):
                                info_parts.append(f"🌍 {row['pais']}")
                            if row.get('descripcion'):
                                desc_corta = row['descripcion'][:100] + "..." if len(row['descripcion']) > 100 else row['descripcion']
                                info_parts.append(f"📝 {desc_corta}")
                            
                            if info_parts:
                                st.markdown(f"<small>{' | '.join(info_parts)}</small>", unsafe_allow_html=True)
                            
                            st.markdown(f"<small>💥 Impacto en {sector_seleccionado}: {impacto}/4</small>", unsafe_allow_html=True)
                        
                        st.markdown("---")
    
    # TAB 3: NOTICIAS EXTERNAS
    with tab3:
        st.subheader("🌐 Agregar Noticia Externa")
        st.info("📌 Crea eventos personalizados con impacto en uno o varios sectores.")
        
        with st.form("form_noticia_externa"):
            titulo = st.text_input("📰 Título de la Noticia *", placeholder="Ej: Cambio en regulación bancaria")
            
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
        
        df_noticias_externas = df_eventos[df_eventos['categoria'] == 'Noticia Externa'].copy()
        
        if df_noticias_externas.empty:
            st.info("📭 No hay noticias externas registradas")
        else:
            df_noticias_externas = df_noticias_externas.sort_values('fecha', ascending=False)
            
            for idx, noticia in df_noticias_externas.iterrows():
                sectores_afectados = df_impactos[df_impactos['evento_tipo'] == noticia['evento_nombre']]['sector'].tolist()
                impacto_noticia = df_impactos[df_impactos['evento_tipo'] == noticia['evento_nombre']]['impacto_score'].iloc[0] if not df_impactos[df_impactos['evento_tipo'] == noticia['evento_nombre']].empty else 0
                
                with st.expander(f"🌐 {noticia['evento_nombre']} - {noticia['fecha'].strftime('%d/%m/%Y')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**📅 Fecha:** {noticia['fecha'].strftime('%d de %B de %Y')}")
                        st.markdown(f"**📊 Impacto:** {'⭐' * int(impacto_noticia)} {int(impacto_noticia)}/4")
                    
                    with col2:
                        st.markdown(f"**🎯 Sectores:** {len(sectores_afectados)}")
                        st.markdown(f"_{', '.join(sectores_afectados[:3])}{'...' if len(sectores_afectados) > 3 else ''}_")
                    
                    if noticia.get('descripcion'):
                        st.markdown(f"**📝 Descripción:** {noticia['descripcion']}")
    
    # TAB 4: ASIGNAR FECHAS
    with tab4:
        st.subheader("✏️ Asignar Fechas Manualmente")
        st.info("📌 Usa esta sección para agregar fechas a eventos que aún no las tienen.")
        
        df_sin_fecha = df_eventos[df_eventos['fecha'].isna()].sort_values('evento_nombre')
        
        if df_sin_fecha.empty:
            st.success("✅ ¡Todos los eventos tienen fecha asignada!")
        else:
            st.warning(f"⏳ **{len(df_sin_fecha)} eventos sin fecha**")
            
            cat_filtro = st.selectbox(
                "Filtrar por categoría:",
                ["Todos"] + sorted(df_sin_fecha['categoria'].unique().tolist())
            )
            
            if cat_filtro != "Todos":
                df_sin_fecha = df_sin_fecha[df_sin_fecha['categoria'] == cat_filtro]
            
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
                    if evento_seleccionado.get('pais'):
                        st.markdown(f"**País:** {evento_seleccionado['pais']}")
                    if evento_seleccionado.get('ticker'):
                        st.markdown(f"**Ticker:** {evento_seleccionado['ticker']}")
                
                with col2:
                    st.markdown("### 📅 Asignar Fecha")
                    with st.form("form_fecha"):
                        fecha_nueva = st.date_input("📅 Fecha", value=datetime.now().date())
                        
                        st.info("ℹ️ La hora se establecerá automáticamente a las 00:00")
                        
                        if st.form_submit_button("💾 Guardar Fecha", use_container_width=True):
                            exito, mensaje = actualizar_fecha_manual(evento_seleccionado['id'], fecha_nueva)
                            
                            if exito:
                                st.success(mensaje)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(mensaje)
    
    # TAB 5: NOTICIAS EXPIRADAS
    with tab5:
        st.subheader("🗄️ Gestión de Noticias con Fecha")
        
        col_toggle1, col_toggle2 = st.columns(2)
        
        with col_toggle1:
            mostrar_todas = st.checkbox("📋 Mostrar TODAS las noticias con fecha", value=False)
        
        with col_toggle2:
            if mostrar_todas:
                st.info("✅ Mostrando todas las noticias")
            else:
                st.info("⏰ Mostrando solo expiradas")
        
        st.markdown("---")
        
        fecha_hoy = date.today()
        
        if mostrar_todas:
            df_noticias = df_eventos[df_eventos['fecha'].notna()].copy()
        else:
            df_noticias = df_eventos[
                (df_eventos['fecha'].notna()) &
                (df_eventos['fecha'].dt.date < fecha_hoy)
            ].copy()
        
        if df_noticias.empty:
            if mostrar_todas:
                st.info("📭 No hay noticias con fecha asignada")
            else:
                st.success("✅ ¡No hay noticias expiradas!")
        else:
            if mostrar_todas:
                st.info(f"📋 **{len(df_noticias)} noticias con fecha encontradas**")
            else:
                st.warning(f"⏰ **{len(df_noticias)} noticias expiradas encontradas**")
            
            categorias_disponibles_filtro = sorted(df_noticias['categoria'].unique().tolist())
            
            cat_filtro_exp = st.selectbox(
                "Filtrar por categoría:",
                ["Todos"] + categorias_disponibles_filtro,
                key="cat_noticias"
            )
            
            if cat_filtro_exp != "Todos":
                df_noticias = df_noticias[df_noticias['categoria'] == cat_filtro_exp]
            
            if df_noticias.empty:
                st.info(f"✅ No hay noticias de categoría '{cat_filtro_exp}'")
            else:
                df_noticias = df_noticias.sort_values('fecha', ascending=False)
                
                st.markdown("---")
                
                for idx, evento in df_noticias.iterrows():
                    esta_expirada = evento['fecha'].date() < fecha_hoy
                    dias_diferencia = abs((fecha_hoy - evento['fecha'].date()).days)
                    
                    impactos_evento = df_impactos[df_impactos['evento_tipo'] == evento['evento_nombre']]['impacto_score']
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
                            
                            if evento.get('descripcion'):
                                st.markdown(f"**📝 Descripción:** {evento['descripcion']}")
                            
                            if evento.get('ticker'):
                                st.markdown(f"**📌 Ticker:** `{evento['ticker']}`")
                            
                            if evento.get('pais'):
                                st.markdown(f"**🌍 País:** {evento['pais']}")
                            
                            if impacto_promedio > 0:
                                st.markdown(f"**📊 Impacto Promedio:** {'⭐' * int(impacto_promedio)} {impacto_promedio:.1f}/4")
                        
                        with col2:
                            st.markdown("### 🛠️ Acciones")
                            
                            if evento['categoria'] == 'Noticia Externa':
                                st.info("🌐 Noticia Externa: Se eliminará completamente")
                                
                                if st.button(f"🗑️ Eliminar Noticia", key=f"del_{evento['id']}", use_container_width=True):
                                    exito, mensaje = eliminar_evento(evento['id'], evento['evento_nombre'])
                                    if exito:
                                        st.success(mensaje)
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(mensaje)
                            else:
                                st.info("📅 Evento recurrente: Se removerá la fecha")
                                
                                if st.button(f"🗑️ Remover Fecha", key=f"del_{evento['id']}", use_container_width=True):
                                    exito, mensaje = vaciar_fecha_evento(evento['id'])
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
                                
                                nueva_fecha = st.date_input(
                                    "Selecciona nueva fecha",
                                    value=evento['fecha'].date() if evento['fecha'].date() >= fecha_hoy else fecha_minima,
                                    min_value=fecha_minima,
                                    key=f"fecha_{evento['id']}"
                                )
                                
                                if st.form_submit_button("✅ Actualizar Fecha", use_container_width=True):
                                    exito, mensaje = actualizar_fecha_manual(evento['id'], nueva_fecha)
                                    
                                    if exito:
                                        st.success(mensaje)
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(mensaje)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.85rem;'>"
    "📊 Economic Events Calendar | Powered by Streamlit & Supabase"
    "</div>",
    unsafe_allow_html=True
)

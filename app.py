import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from ingest import load_all_data, clean_and_diagnose, transform_data, calculate_stability_metrics

# Configuración de página con estética moderna
st.set_page_config(
    page_title="Stability Dashboard | Store Availability",
    page_icon="🛡️",
    layout="wide"
)

# Estilos CSS básicos (limpios)
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def get_processed_data():
    """Pipeline completo con cache para evitar repasar los 201 archivos en cada interacción"""
    df = load_all_data("data/raw")
    df = clean_and_diagnose(df)
    df = transform_data(df)
    metrics, df_final = calculate_stability_metrics(df)
    return df_final, metrics

# Cargar datos
df, metrics_global = get_processed_data()

# --- SIDEBAR (Filtros y Configuración) ---
st.sidebar.header("⚙️ Configuración")

# Gestión de API Key
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", help="Obtén tu llave en https://aistudio.google.com/")

dates = sorted(df['date'].unique())
selected_date = st.sidebar.selectbox("Seleccionar Fecha", ["Todas las fechas"] + list(dates))

# Filtrado de datos
if selected_date != "Todas las fechas":
    df_display = df[df['date'] == selected_date].reset_index(drop=True)
    # Recalcular métricas específicas para la fecha seleccionada
    metrics_display, _ = calculate_stability_metrics(df_display)
else:
    df_display = df
    metrics_display = metrics_global

# --- TÍTULO ---
st.title("Panel de Estabilidad y Resiliencia")
st.markdown(f"**Dataset:** {len(df_display):,} registros analizados cada 10 segundos")

# --- KPIs ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Eventos de Caída (>1%)", metrics_display['num_events'])
with col2:
    st.metric("Recuperación Promedio", f"{metrics_display['avg_recovery_sec']/60:.1f} min")
with col3:
    st.metric("Caída Relativa Media", f"{metrics_display['avg_relative_drop_pct']:.2f}%")
with col4:
    st.metric("Volatilidad (StdDev)", f"{metrics_display['vol_global']:,.0f}")

st.divider()

# --- GRÁFICO PRINCIPAL ---
st.subheader("Comportamiento del Sistema y Detección de Incidentes")
fig = go.Figure()

# Línea de tendencia
fig.add_trace(go.Scatter(
    x=df_display['timestamp'], 
    y=df_display['visible_stores'],
    mode='lines',
    name='Tiendas Visibles',
    line=dict(color='#1f77b4', width=2)
))

# Marcar caídas en rojo
drops = df_display[df_display['is_drop']]
if not drops.empty:
    fig.add_trace(go.Scatter(
        x=drops['timestamp'], 
        y=drops['visible_stores'],
        mode='markers',
        name='Incidente Detectado',
        marker=dict(color='#d62728', size=8, symbol='x')
    ))

fig.update_layout(
    height=500,
    margin=dict(l=20, r=20, t=40, b=20),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True)

# --- ANÁLISIS POR HORA ---
st.subheader("Análisis de Volatilidad por Hora")
col_a, col_b = st.columns(2)

with col_a:
    # Incidentes por hora
    hourly_incidents = df_display[df_display['is_drop']].groupby('hour').size().reset_index(name='count')
    fig_hour = px.bar(hourly_incidents, x='hour', y='count', 
                      title="Frecuencia de Incidentes por Hora",
                      labels={'hour': 'Hora del Día', 'count': 'Número de Caídas'},
                      color_discrete_sequence=['#ff7f0e'])
    st.plotly_chart(fig_hour, use_container_width=True)

with col_b:
    # Volatilidad por hora (StdDev)
    hourly_vol = df_display.groupby('hour')['delta'].std().reset_index(name='std')
    fig_vol = px.line(hourly_vol, x='hour', y='std', 
                      title="Volatilidad del Sistema por Hora",
                      labels={'hour': 'Hora del Día', 'std': 'Inestabilidad (Delta StdDev)'},
                      markers=True)
    st.plotly_chart(fig_vol, use_container_width=True)

st.success("Datos actualizados y listos para análisis.")

# --- PASO 5 & 6: CHATBOT INTELIGENTE ---
st.divider()
st.subheader("Asistente de Análisis (AI Powered)")

def data_analyst_logic(query, df, metrics):
    """Prepara un contexto enriquecido con estadísticas calculadas por Pandas para la AI"""
    try:
        # 1. Cálculos de distribución temporal
        # Obtenemos los top 3 momentos críticos por hora
        hourly_summary = df[df['is_drop']].groupby('hour').size().sort_values(ascending=False).head(3).to_dict()
        # Distribución por día de la semana
        daily_summary = df[df['is_drop']].groupby('day_name').size().to_dict()
        
        # 2. Hechos deterministas adicionales según la pregunta
        query = query.lower()
        specific_fact = ""
        if "peor" in query or "cuándo" in query or "momento" in query:
            peor_dia = df[df['is_drop']].groupby('date').size().idxmax()
            conteo = df[df['is_drop']].groupby('date').size().max()
            specific_fact = f"DATO CRÍTICO: El peor día fue {peor_dia} con {conteo} caídas."

        # 3. Construcción del Contexto Maestro
        context = f"""
        INFORME TÉCNICO DE ESTABILIDAD:
        - Total registros: {len(df):,}
        - Eventos de caída detectados: {metrics['num_events']}
        - Volatilidad del sistema (StdDev): {metrics['vol_global']:.2f}
        - Resiliencia (Tiempo promedio de recuperación): {metrics['avg_recovery_sec']:.1f} segundos.
        - {specific_fact}
        
        PATRONES HORARIOS (Horas con más incidentes): {hourly_summary if hourly_summary else "Sin incidentes."}
        PATRONES SEMANALES (Distribución por día): {daily_summary if daily_summary else "Sin incidentes."}
        """
        return context
    except Exception as e:
        return f"Error procesando datos: {str(e)}"

def ask_gemini(question, context, key):
    """Analista con múltiples fallbacks para máxima confiabilidad"""
    if not key:
        return f"⚠️ API Key no configurada. (Datos técnicos: {context})"
    
    try:
        client = genai.Client(api_key=key)
        
        # Confirmado por diagnóstico: gemini-flash-latest es el que funciona para esta llave
        candidate_models = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-pro-latest"]
        
        full_prompt = f"""
        Actúa como un SRE Senior. 
        CONTEXTO REAL: {context}
        PREGUNTA: {question}
        Instrucciones: Explica el dato del CONTEXTO muy brevemente (3 frases). No alucines números.
        """
        
        last_error = ""
        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt
                )
                if response:
                    return response.text
            except Exception as e:
                last_error = str(e)
                continue # Probar el siguiente modelo
        
        # Si llegamos aquí, Gemini falló todos sus modelos
        return f"🤖 [AI temporalmente fuera de servicio]: {context}. (Error: {last_error[:50]}...)"
        
    except Exception as e:
        return f"❌ Error crítico de integración: {context}"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ej: ¿Cómo está la resiliencia del sistema?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Obtener hechos crudos con Pandas
    factual_context = data_analyst_logic(prompt, df_display, metrics_display)
    
    # 2. Convertir en lenguaje natural con Gemini
    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            ai_response = ask_gemini(prompt, factual_context, gemini_key)
            st.markdown(ai_response)
            
    st.session_state.messages.append({"role": "assistant", "content": ai_response})

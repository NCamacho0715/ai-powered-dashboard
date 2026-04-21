# AI-Powered Dashboard: Monitoreo de Estabilidad del Sistema

Este proyecto analiza la estabilidad técnica de un sistema de tiendas basado en series temporales agregadas, utilizando métricas de volatilidad y resiliencia, con un asistente inteligente integrado.

## Progreso del Proyecto

### PASO 1: Ingesta de Datos
**Objetivo:** Consolidar información dispersa (201 CSVs) en un formato de serie temporal largo.
*   **Filas finales:** 67,141 registros únicos.

### PASO 2: Limpieza y Transformación
**Objetivo:** Enriquecimiento temporal (horas, días) y cálculo de variaciones (`delta`).

### PASO 3: Análisis de Estabilidad (Métricas Senior)
**Objetivo:** Medir la salud del sistema a través de su capacidad de recuperación.
*   **Eventos de Caída:** Umbral relativo (>1%) para normalizar el impacto.
*   **Resiliencia:** Cálculo de *Recovery Time* tras incidentes.

### PASO 4: Dashboard Interactivo (Streamlit)
**Objetivo:** Visualizar KPIs de salud y series temporales con detección de incidentes.
*   Gráficos dinámicos de volatilidad horaria y marcadores de fallos.

### PASO 5 & 6: Chatbot Híbrido (AI Powered)
**Objetivo:** Interfaz de lenguaje natural que no alucina.
*   **Cerebro Matemático:** Lógica en Pandas para cálculos exactos.
*   **Voz de AI:** Integración con **Google Gemini (2.0 Flash)** para interpretación experta.
*   **Modo Resiliente:** El chat funciona incluso si la AI falla, usando resultados deterministas.

---

## Cómo Ejecutar
1. Instalar dependencias: `pip install pandas streamlit plotly google-genai`
2. Ejecutar: `python -m streamlit run app.py`
3. Ingresa tu **Gemini API Key** en la barra lateral para activar el asistente.

*Proyecto finalizado para prueba técnica - Enfoque Pragmático*

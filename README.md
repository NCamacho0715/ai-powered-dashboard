# AI-Powered Dashboard: Monitoreo de Disponibilidad de Tiendas

Este proyecto es una solución rápida y funcional para visualizar eventos de disponibilidad (online/offline) de tiendas, procesando múltiples fuentes de datos y ofreciendo un análisis asistido por Inteligencia Artificial.

## Progreso del Proyecto

### PASO 1: Ingesta de Datos
**Objetivo:** Consolidar información dispersa en un solo conjunto de datos manejable.

*   **Fuentes:** Se procesaron **201 archivos CSV** ubicados en `data/raw`.
*   **Desafío Técnico:** Los archivos originales venían en formato "ancho" (cada timestamp era una columna). Se implementó una lógica de transformación (**unpivot/melt**) para convertir los datos a formato "largo", donde cada fila representa un momento único en el tiempo.
*   **Resultados de Calidad:**
    *   **Filas procesadas:** 67,141 registros únicos.
    *   **Limpieza:** Se detectaron y eliminaron 1,987 registros duplicados causados por el solapamiento de tiempo entre archivos.
    *   **Rango Temporal:** Los datos cubren del **1 de febrero al 11 de febrero de 2026**.
    *   **Integridad:** 0 valores nulos y 100% de éxito en el procesamiento de fechas.

### PASO 2: Limpieza y Transformación
**Objetivo:** Enriquecer los datos para facilitar el análisis temporal y de disponibilidad.

*   **Enriquecimiento Temporal:** Se extrajeron dimensiones de fecha, hora y nombre del día para permitir análisis por franjas horarias (ej: ¿Hay más caídas en la madrugada?).
*   **Lógica de Disponibilidad:**
    *   Se calculó el `delta` (variación técnica) entre cada medición de 10 segundos.
    *   **Normalización de Estados:** Se categorizó cada registro como `Stable/Online` (conteo estable o en aumento) o `Offline Event` (conteo en descenso).
*   **Insights Detectados:**
    *   Se identificaron **28,280 momentos de inestabilidad** (caídas en el número de tiendas visibles).
    *   Esto permite calcular el "Uptime" técnico no solo como "está prendido o no", sino como la frecuencia de fluctuaciones.

---

*Estado actual: Datos listos y enriquecidos. Próximo paso: Cálculo de Métricas Clave.*
# 📘 Guía Maestra: Entendiendo el Dashboard de Estabilidad

Esta guía explica cómo funciona tu proyecto de principio a fin, diseñada para que puedas explicarlo en tu prueba técnica como un experto, sin lenguaje innecesariamente complicado.

---

## 1. El Problema (¿Qué estamos resolviendo?)
Tenemos **201 archivos CSV**, cada uno con una fila que dice cuántas tiendas están "online" en un momento dado. El objetivo no es solo saber si las tiendas están prendidas, sino qué tan **estable** es el sistema y cuánto tarda en recuperarse cuando algo falla.

---

## 2. El Flujo de los Datos (Paso a Paso)

### Paso A: Recolección y Unión (`ingest.py`)
1.  **Unión Masiva:** El script abre los 201 archivos uno por uno.
2.  **Transposición (Melt):** Los datos originales vienen en formato "ancho" (timestamps como columnas). El código los voltea para que sea una lista larga hacia abajo (Formato de Serie Temporal).
3.  **Limpieza:** Se eliminan filas duplicadas (mismo tiempo) y se ordenan cronológicamente.

### Paso B: Creación de Inteligencia
Aquí convertimos datos crudos en métricas útiles:
*   **Delta:** El código compara cada fila con la anterior. Si antes había 10,000 tiendas y ahora hay 9,900, el delta es `-100`.
*   **Identificación de Caídas:** Si el sistema pierde más del **1%** de sus tiendas en 10 segundos, el código marca esto automáticamente como un **"Incidente"**.
*   **Tiempo de Recuperación:** Esta es la métrica más "Senior". El código mide cuánto tiempo pasa desde que hay una caída hasta que el sistema vuelve al nivel de tiendas que tenía justo antes de caer.

---

## 3. El Dashboard (`app.py`)
Es la cara del proyecto. Se divide en 3 secciones:
1.  **KPIs (Indicadores Clave):** Muestran el resumen global (Volatilidad, # de Caídas, Tiempo medio de recuperación).
2.  **Gráfico de Serie Temporal:** Una línea azul que muestra el total de tiendas. Si aparece una **X roja**, significa que el código detectó automáticamente un incidente grave en ese punto exacto.
3.  **Análisis por Hora:** Ayuda a identificar patrones. ¿Se cae más el sistema a las 3:00 PM? El gráfico de barras te lo dice.

---

## 4. El Chatbot (El Analista de AI)
Esta es la parte más avanzada. Funciona con **Lógica Híbrida**:
1.  **El Usuario pregunta:** *"¿Cuánto tarda en recuperarse el sistema?"*
2.  **Paso de Pandas:** El código NO le pregunta a la AI cuánto tarda. El código hace el cálculo matemático exacto usando los datos.
3.  **Paso de AI (Gemini):** El código le envía el resultado matemático a Gemini y le dice: *"La respuesta exacta es 166 segundos, ahora explícaselo al usuario como un experto"*.
4.  **Resultado:** Obtienes una respuesta fluida, profesional y, lo más importante, **sin mentiras ni alucinaciones**.

---

## 5. El "Failover" (A prueba de errores)
Si por alguna razón la AI de Google falla (por internet o límites de la cuenta), el chatbot tiene un **respaldo**. Detecta el error y te muestra los datos matemáticos puros, asegurando que el usuario nunca se quede sin respuesta.

---

## 6. Diccionario Rápido para la Entrevista
*   **Volatilidad:** Qué tanto "brinca" el número de tiendas. Mucho brinco = inestabilidad.
*   **Resiliencia:** Qué tan rápido el sistema "rebota" después de un golpe.
*   **Serie Temporal Largo (Long Format):** Es la mejor forma de organizar datos para analítica moderna.

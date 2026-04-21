"""
PASO 1: Ingesta de datos
Cada CSV tiene formato 'wide': timestamps como columnas, valores en la única fila de datos.
Convertimos a formato 'long': una fila por observación (timestamp + valor).
"""

import pandas as pd
import glob
import os
import re

DATA_FOLDER = "data/raw"


def parse_timestamp(ts_str: str) -> pd.Timestamp:
    """
    Convierte el timestamp del formato del CSV al tipo datetime de pandas.
    Ejemplo: 'Sun Feb 01 2026 06:59:40 GMT-0500 (hora estándar de Colombia)'
    """
    # Extraemos solo la parte relevante antes del timezone offset
    # Resultado esperado: 'Sun Feb 01 2026 06:59:40'
    match = re.match(r"(\w+ \w+ \d+ \d+ \d+:\d+:\d+)", ts_str)
    if match:
        return pd.to_datetime(match.group(1), format="%a %b %d %Y %H:%M:%S")
    return pd.NaT


def load_single_csv(filepath: str) -> pd.DataFrame:
    """
    Lee un archivo CSV en formato wide y lo convierte a formato long.
    Retorna un DataFrame con columnas: ['timestamp', 'visible_stores', 'source_file']
    """
    df = pd.read_csv(filepath, header=0)

    # Las primeras 4 columnas son metadatos fijos, el resto son timestamps
    timestamp_cols = df.columns[4:]

    # Extraemos la fila de datos (índice 0, que es la única fila de valores)
    data_row = df.iloc[0]

    # Construimos el DataFrame long: una fila por timestamp
    records = []
    for col in timestamp_cols:
        value = data_row[col]
        records.append({
            "timestamp": col,                     # texto crudo del timestamp
            "visible_stores": value,              # valor numérico (puede ser str)
            "source_file": os.path.basename(filepath)
        })

    return pd.DataFrame(records)


def load_all_data(folder: str) -> pd.DataFrame:
    """
    Carga y unifica todos los CSVs de la carpeta en un solo DataFrame.
    """
    all_files = sorted(glob.glob(os.path.join(folder, "*.csv")))

    if not all_files:
        raise FileNotFoundError(f"No se encontraron archivos .csv en: {folder}")

    print(f"[INFO] Archivos encontrados: {len(all_files)}")

    dfs = []
    errors = []

    for f in all_files:
        try:
            dfs.append(load_single_csv(f))
        except Exception as e:
            errors.append((os.path.basename(f), str(e)))

    if errors:
        print(f"[WARN] Archivos con error ({len(errors)}):")
        for name, err in errors:
            print(f"   - {name}: {err}")

    # Concatenar todo
    df = pd.concat(dfs, ignore_index=True)
    print(f"[OK] Filas totales (antes de limpiar): {len(df):,}")

    return df


def clean_and_diagnose(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte tipos de datos y muestra diagnóstico de calidad.
    """
    print("\n--- DIAGNÓSTICO INICIAL ---")
    print(f"Shape: {df.shape}")
    print(f"Columnas: {list(df.columns)}")
    print(f"\nTipos de datos (antes):\n{df.dtypes}")

    # Convertir timestamp (texto -> datetime)
    df["timestamp"] = df["timestamp"].apply(parse_timestamp)

    # Convertir visible_stores a numérico (puede haber strings vacíos o nulls)
    df["visible_stores"] = pd.to_numeric(df["visible_stores"], errors="coerce")

    # Eliminar duplicados por timestamp
    antes = len(df)
    df = df.drop_duplicates(subset=["timestamp"])
    duplicados = antes - len(df)

    # Ordenar por tiempo
    df = df.sort_values("timestamp").reset_index(drop=True)

    print(f"\n--- CALIDAD DE DATOS ---")
    print(f"Timestamps inválidos (NaT): {df['timestamp'].isna().sum()}")
    print(f"Valores nulos en visible_stores: {df['visible_stores'].isna().sum()}")
    print(f"Filas duplicadas eliminadas: {duplicados}")
    print(f"Filas finales: {len(df):,}")
    print(f"\nRango temporal:")
    print(f"  Desde: {df['timestamp'].min()}")
    print(f"  Hasta: {df['timestamp'].max()}")
    print(f"\nEstadísticas de visible_stores:")
    print(df["visible_stores"].describe())

    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    PASO 2: Limpieza y transformación.
    Crea columnas útiles para análisis y detecta eventos de disponibilidad.
    """
    print("\n--- TRANSFORMACIÓN DE DATOS ---")
    
    # 1. Enriquecer con dimensiones de tiempo
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    df['day_name'] = df['timestamp'].dt.day_name()
    
    # 2. Calcular la variación (delta)
    # Importante: Como los archivos están ordenados por tiempo, diff() detecta caídas reales
    df['delta'] = df['visible_stores'].diff().fillna(0)
    
    # 3. Normalizar estado: Una caída en el conteo se considera un evento Offline
    df['status'] = df['delta'].apply(lambda x: 'Offline Event' if x < 0 else 'Stable/Online')
    
    print(f"Columnas añadidas: ['date', 'hour', 'day_name', 'delta', 'status']")
    print(f"Resumen de estados:\n{df['status'].value_counts()}")
    
    return df


    return df


def calculate_stability_metrics(df: pd.DataFrame) -> tuple:
    """
    PASO 3 REDISEÑADO: Estabilidad del Sistema.
    Calcula volatilidad, detecta caídas significativas (>1%) y mide tiempos de recuperación.
    """
    import numpy as np
    print("\n--- ANALIZANDO ESTABILIDAD DEL SISTEMA ---")
    
    if df.empty:
        return {}, df

    # 1. VOLATILIDAD
    # Medida como la desviación estándar de los cambios (delta)
    vol_global = df['delta'].std()
    
    # 2. DETECCIÓN DE EVENTOS DE CAÍDA (Relativa > 1%)
    # Calculamos qué porcentaje del valor anterior representa el cambio actual
    df['relative_delta'] = (df['delta'] / df['visible_stores'].shift(1)).fillna(0)
    
    # Definimos caída como un descenso mayor al 1% del valor total previo
    THRESHOLD = -0.01 
    df['is_drop'] = df['relative_delta'] < THRESHOLD
    
    drop_events = df[df['is_drop']].copy()
    num_drops = len(drop_events)
    
    # 3. RECOVERY TIME (Tiempo en volver al nivel pre-caída)
    recovery_times = []
    
    # Iteramos por los eventos de caída para calcular su resiliencia
    # Nota: Usamos una búsqueda hacia adelante limitada para evitar lentitud
    for idx in drop_events.index:
        if idx == 0: continue
        
        val_pre = df.loc[idx - 1, 'visible_stores']
        timestamp_start = df.loc[idx, 'timestamp']
        
        # Buscamos en el futuro (máximo 1000 registros para no congelar)
        future_data = df.loc[idx+1 : idx+1000]
        recovery_record = future_data[future_data['visible_stores'] >= val_pre].head(1)
        
        if not recovery_record.empty:
            duration = (recovery_record['timestamp'].iloc[0] - timestamp_start).total_seconds()
            recovery_times.append(duration)
    
    avg_recovery = np.mean(recovery_times) if recovery_times else 0
    max_recovery = np.max(recovery_times) if recovery_times else 0
    
    metrics = {
        "vol_global": vol_global,
        "num_events": num_drops,
        "avg_recovery_sec": avg_recovery,
        "max_recovery_sec": max_recovery,
        "avg_relative_drop_pct": (drop_events['relative_delta'].mean() * 100) if not drop_events.empty else 0
    }
    
    print(f"Volatilidad Global (StdDev): {metrics['vol_global']:.2f}")
    print(f"Eventos de Caída Detectados (>1%): {metrics['num_events']}")
    print(f"Caída Relativa Promedio: {metrics['avg_relative_drop_pct']:.2f}%")
    print(f"Tiempo Promedio de Recuperación: {metrics['avg_recovery_sec']:.2f} segundos")
    print(f"Tiempo Máximo de Recuperación: {metrics['max_recovery_sec']:.2f} segundos")
    
    return metrics, df


# --- EJECUCIÓN DIRECTA ---
if __name__ == "__main__":
    df_raw = load_all_data(DATA_FOLDER)
    df_cleaned = clean_and_diagnose(df_raw)
    df_final = transform_data(df_cleaned)
    
    # Aplicar nuevas métricas
    metrics, df_final = calculate_stability_metrics(df_final)

    print("\n[OK] Validación: Ejemplo de evento de caída y recuperación:")
    if metrics['num_events'] > 0:
        print(df_final[df_final['is_drop']][['timestamp', 'visible_stores', 'relative_delta', 'is_drop']].head(3))

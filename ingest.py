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


# --- EJECUCIÓN DIRECTA (solo para prueba en consola) ---
if __name__ == "__main__":
    df_raw = load_all_data(DATA_FOLDER)
    df_cleaned = clean_and_diagnose(df_raw)
    df_final = transform_data(df_cleaned)

    print("\n[OK] Pipeline de transformación completo. Muestra de eventos Offline:")
    print(df_final[df_final['status'] == 'Offline Event'].head())

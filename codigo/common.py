"""Constantes compartidas por los scripts del pipeline.

Centraliza aqui los nombres de columna y rutas base para que ningun script tenga
que repetir listas de columnas ni rutas absolutas (criterio de calidad del TFM:
"no debe haber rutas absolutas", "las funciones deben estar separadas y
reutilizables").
"""

from __future__ import annotations

from pathlib import Path

# Raiz del proyecto, calculada de forma relativa a este fichero (no absoluta),
# para que los scripts funcionen igual en cualquier maquina/carpeta.
BASE_DIR = Path(__file__).resolve().parents[1]

# Las 5 variables de comportamiento que sabemos que estan en minutos (suman ~1440
# min/dia cuando el dataset es diario real, o ~60 min/hora cuando es horario real).
ACTIVITY_COLUMNS = ["Ruminate", "Eat", "Graze", "Rest", "Walk"]

# Steps no es una duracion en minutos, es un conteo, pero se trata con la misma
# logica de escalado (ver hallazgos_resolucion_temporal.md).
STEPS_COLUMN = "Steps"

NUMERIC_COLUMNS = ACTIVITY_COLUMNS + [STEPS_COLUMN]

# Metadatos / variables auxiliares: NO deben usarse como entrada de PCA ni de
# clustering, solo para interpretar o cruzar resultados.
FEATURE_EXCLUDE_COLUMNS = [
    "dataset",
    "system",
    "cow_id",
    "window_start",
    "resolution",
    "scale_type",
    "n_records",
    "n_missing",
    "anomaly_count",
    "anomaly_rate",
]

RESULTADOS_DIR = BASE_DIR / "resultados"
DATOS_PROCESADOS_DIR = BASE_DIR / "datos" / "procesados"
FEATURES_DIR = DATOS_PROCESADOS_DIR / "features"

"""Extrae features semanales para las dos ramas de analisis:

  Rama A (horario intensivo): Celso horario + Ruibal horario, nativos, sin
  mezclar con Valdillera.

  Rama B (diario intensivo vs extensivo): Celso diario (nativo), Ruibal diario
  (generado por codigo/generar_diarios.py) y Valdillera diario equivalente
  (generado por codigo/generar_diarios.py, escalado x24).

Cada fila de features lleva metadatos "resolution" y "scale_type" ademas de
"dataset"/"system", para poder trazar de donde viene cada dato sin tener que
adivinarlo por el nombre.

Ejecutar desde la raiz del proyecto, DESPUES de codigo/generar_diarios.py:
    python codigo/extraer_features_ramas.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import BASE_DIR, FEATURES_DIR
from extraccion_metricas import extract_features
from preprocesado_base import clean_dataset, load_dataset

WINDOW = "weekly"

RAMA_A_SOURCES = [
    dict(
        path=BASE_DIR / "Procesados" / "Celso novo" / "04_Vacas_etiquetadas_horario.xlsx",
        dataset_name="celso_horario",
        system="intensivo",
        resolution="horario",
        scale_type="nativo",
    ),
    dict(
        path=BASE_DIR / "Procesados" / "Ruibal Riomayor" / "05_Datos_horarios_etiquetados_celo.csv",
        dataset_name="ruibal_horario",
        system="intensivo",
        resolution="horario",
        scale_type="nativo",
    ),
]

RAMA_B_SOURCES = [
    dict(
        path=BASE_DIR / "Procesados" / "Celso novo" / "05_original_variables.csv",
        dataset_name="celso_diario",
        system="intensivo",
        resolution="diario",
        scale_type="nativo",
    ),
    dict(
        path=BASE_DIR / "datos" / "procesados" / "ruibal_diario" / "ruibal_diario.csv",
        dataset_name="ruibal_diario",
        system="intensivo",
        resolution="diario",
        scale_type="agregado_desde_horario",
    ),
    dict(
        path=BASE_DIR / "datos" / "procesados" / "valdillera_diario_equivalente" / "valdillera_diario_equivalente.csv",
        dataset_name="valdillera_diario_equivalente",
        system="extensivo",
        resolution="diario",
        scale_type="escalado_x24_desde_media_horaria",
    ),
]


def _extract_for_source(spec: dict) -> pd.DataFrame:
    raw_df = load_dataset(spec["path"])
    clean_df, _ = clean_dataset(raw_df)
    features = extract_features(
        clean_df,
        window=WINDOW,
        dataset_name=spec["dataset_name"],
        system_label=spec["system"],
        resolution=spec["resolution"],
        scale_type=spec["scale_type"],
    )
    print(
        f"  {spec['dataset_name']:32s} filas={features.shape[0]:6d}  vacas={features['cow_id'].nunique():4d}  "
        f"resolution={spec['resolution']:8s} scale_type={spec['scale_type']}"
    )
    return features


def main() -> None:
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Rama A: horario intensivo (Celso horario + Ruibal horario) ===")
    rama_a = pd.concat([_extract_for_source(s) for s in RAMA_A_SOURCES], ignore_index=True)
    rama_a_path = FEATURES_DIR / "rama_a_horario_intensivo_weekly_features.csv"
    rama_a.to_csv(rama_a_path, index=False)
    print(f"Guardado: {rama_a_path} ({rama_a.shape[0]} filas, {rama_a.shape[1]} columnas)")

    print()
    print("=== Rama B: diario intensivo vs extensivo (Celso diario + Ruibal diario + Valdillera diario x24) ===")
    rama_b_parts = [_extract_for_source(s) for s in RAMA_B_SOURCES]
    rama_b = pd.concat(rama_b_parts, ignore_index=True)

    # Valdillera: no hay solape temporal entre el CSV de eventos (2021-2024) y el
    # periodo de actividad (dic-2025/ene-2026), asi que anomaly_count/anomaly_rate
    # NO deben interpretarse como "confirmado sin anomalias". Se dejan a NaN de
    # forma explicita en vez de heredar un 0 o un "Sin etiqueta" que aparentaria
    # informacion que no existe (ver datos/procesados/valdillera_diario_equivalente/*.json).
    valdillera_mask = rama_b["dataset"] == "valdillera_diario_equivalente"
    rama_b.loc[valdillera_mask, "anomaly_count"] = np.nan
    rama_b.loc[valdillera_mask, "anomaly_rate"] = np.nan

    rama_b_path = FEATURES_DIR / "rama_b_diario_sistemas_weekly_features.csv"
    rama_b.to_csv(rama_b_path, index=False)
    print(f"Guardado: {rama_b_path} ({rama_b.shape[0]} filas, {rama_b.shape[1]} columnas)")

    print()
    print("=== Resumen por dataset ===")
    combined = pd.concat([rama_a, rama_b], ignore_index=True)
    summary = combined.groupby(["dataset", "system", "resolution", "scale_type"]).size()
    print(summary.to_string())


if __name__ == "__main__":
    main()

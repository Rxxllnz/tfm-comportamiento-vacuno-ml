"""Genera las versiones diarias necesarias para comparar sistemas intensivos y
extensivos en la misma resolucion temporal:

  - Ruibal diario: agregado (suma) desde Ruibal horario, por vaca y dia.
  - Valdillera diario equivalente: Valdillera bruto (que es una media por hora
    agregada a nivel diario, ver auditoria_resolucion.py) escalado x24 para
    quedar en la misma escala (minutos/dia) que el resto.

Ejecutar desde la raiz del proyecto:
    python codigo/generar_diarios.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ACTIVITY_COLUMNS, BASE_DIR, DATOS_PROCESADOS_DIR, NUMERIC_COLUMNS
from preprocesado_base import CANONICAL_TIME_COLUMN, clean_dataset, load_dataset

RUIBAL_RAW_PATH = BASE_DIR / "Procesados" / "Ruibal Riomayor" / "05_Datos_horarios_etiquetados_celo.csv"
VALDILLERA_RAW_PATH = (
    BASE_DIR
    / "datos"
    / "entrada"
    / "valdillera"
    / "00zz_Datos_valdillera_bruto_media_horario_2025-01-01_2026-01-01_20260701.csv"
)
VALDILLERA_EVENTS_PATH = BASE_DIR / "datos" / "entrada" / "valdillera" / "Valdillera_Agropecuaria_events.csv"

RUIBAL_OUT_DIR = DATOS_PROCESADOS_DIR / "ruibal_diario"
VALDILLERA_OUT_DIR = DATOS_PROCESADOS_DIR / "valdillera_diario_equivalente"

# Prioridad para colapsar varias etiquetas del mismo dia en una sola (mas severa primero).
LABEL_PRIORITY = ["Heat/Estrus", "Other"]  # cualquier otro valor no "Sin etiqueta" cae en "Other-like"
NORMAL_LABELS = {"Sin etiqueta", "No anomaly", "No Anomaly", "None", ""}


def _daily_label(labels: pd.Series) -> str:
    non_normal = [str(v) for v in labels if str(v) not in NORMAL_LABELS]
    if not non_normal:
        return "Sin etiqueta"
    # Si hay mas de un tipo distinto ese dia, se queda con el mas frecuente;
    # empate -> el primero por orden alfabetico para que sea determinista.
    counts = pd.Series(non_normal).value_counts()
    top = counts[counts == counts.max()].index.tolist()
    return sorted(top)[0]


def aggregate_hourly_to_daily(
    df: pd.DataFrame, dataset_name: str, source_dataset_name: str
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Agrega un dataset horario (1 fila = 1 hora) a un dataset diario (1 fila =
    1 vaca-dia), sumando las variables de actividad y Steps, y colapsando
    Anomaly_Label al valor no-normal mas frecuente de ese dia (o 'Sin etiqueta')."""
    work = df.dropna(subset=[CANONICAL_TIME_COLUMN]).copy()
    work["Date"] = work[CANONICAL_TIME_COLUMN].dt.floor("D")

    present_numeric = [c for c in NUMERIC_COLUMNS if c in work.columns]
    agg_dict = {c: (c, "sum") for c in present_numeric}

    daily = work.groupby(["Cow_id", "Date"]).agg(n_horas_origen=(CANONICAL_TIME_COLUMN, "count"), **agg_dict)
    daily = daily.reset_index()

    if "Anomaly_Label" in work.columns:
        label_daily = (
            work.groupby(["Cow_id", "Date"])["Anomaly_Label"]
            .apply(_daily_label)
            .reset_index()
            .rename(columns={"Anomaly_Label": "Anomaly_Label"})
        )
        anomaly_hours = (
            work.assign(_is_anomaly=~work["Anomaly_Label"].astype(str).isin(NORMAL_LABELS))
            .groupby(["Cow_id", "Date"])["_is_anomaly"]
            .sum()
            .reset_index()
            .rename(columns={"_is_anomaly": "anomaly_hours"})
        )
        daily = daily.merge(label_daily, on=["Cow_id", "Date"], how="left")
        daily = daily.merge(anomaly_hours, on=["Cow_id", "Date"], how="left")

    daily = daily.rename(columns={"Date": CANONICAL_TIME_COLUMN})

    sum5 = daily[[c for c in ACTIVITY_COLUMNS if c in daily.columns]].sum(axis=1)
    summary = {
        "dataset": dataset_name,
        "rows": int(daily.shape[0]),
        "cow_count": int(daily["Cow_id"].nunique()),
        "n_horas_origen_median": float(daily["n_horas_origen"].median()),
        "suma_5_variables_mean": float(sum5.mean()),
        "suma_5_variables_median": float(sum5.median()),
        "generado_desde": source_dataset_name,
        "metodo": "suma de registros horarios agrupados por Cow_id y dia calendario",
    }
    return daily, summary


def build_valdillera_daily_equivalent(
    raw_df: pd.DataFrame, events_path: Path, factor: int = 24
) -> tuple[pd.DataFrame, dict[str, object]]:
    """A partir del CSV bruto de Valdillera (1 fila = 1 vaca-dia, variables en
    minutos MEDIOS POR HORA, ver auditoria_resolucion.py), construye la version
    diaria equivalente multiplicando por `factor` las variables de actividad y
    Steps (decision explicita del autor del TFM: Steps tambien se escala x24
    igual que el resto, dado que no hay forma de confirmar su escala real de
    forma independiente, ver hallazgos_resolucion_temporal.md)."""
    work = raw_df.dropna(subset=[CANONICAL_TIME_COLUMN]).copy()
    work[CANONICAL_TIME_COLUMN] = work[CANONICAL_TIME_COLUMN].dt.floor("D")

    scaled_cols = [c for c in NUMERIC_COLUMNS if c in work.columns]
    for col in scaled_cols:
        work[col] = pd.to_numeric(work[col], errors="coerce") * factor

    # Anomaly_Label a partir del CSV de eventos (HEAT/ANOMALY), si hay solape temporal.
    events = pd.read_csv(events_path)
    events = events.rename(columns={"official_tag": "Cow_id", "date": "event_date", "event": "event_type"})
    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce").dt.floor("D")
    events["event_type"] = events["event_type"].astype(str).str.strip().str.upper()
    events = events.dropna(subset=["event_date"])

    activity_min = work[CANONICAL_TIME_COLUMN].min()
    activity_max = work[CANONICAL_TIME_COLUMN].max()
    events_in_range = events[(events["event_date"] >= activity_min) & (events["event_date"] <= activity_max)]
    n_events_overlap = int(len(events_in_range))

    def _label_for(cow_id, date) -> str:
        matches = events_in_range[(events_in_range["Cow_id"] == cow_id) & (events_in_range["event_date"] == date)]
        if matches.empty:
            return "Sin etiqueta"
        types = set(matches["event_type"])
        if "ANOMALY" in types:
            return "ANOMALY"
        if "HEAT" in types:
            return "HEAT"
        return "Sin etiqueta"

    if n_events_overlap > 0:
        work["Anomaly_Label"] = [
            _label_for(cow, date) for cow, date in zip(work["Cow_id"], work[CANONICAL_TIME_COLUMN])
        ]
    else:
        # Sin solape temporal entre el fichero de eventos y el periodo de actividad:
        # no se rellena con 0 disfrazado de "confirmado sin anomalias", se deja
        # explicitamente sin informacion (NaN) para no generar una falsa certeza.
        work["Anomaly_Label"] = np.nan

    sum5 = work[[c for c in ACTIVITY_COLUMNS if c in work.columns]].sum(axis=1)
    summary = {
        "dataset": "valdillera_diario_equivalente",
        "rows": int(work.shape[0]),
        "cow_count": int(work["Cow_id"].nunique()),
        "factor_escala_aplicado": factor,
        "columnas_escaladas": scaled_cols,
        "suma_5_variables_mean_tras_escalado": float(sum5.mean()),
        "suma_5_variables_median_tras_escalado": float(sum5.median()),
        "eventos_totales_en_fichero": int(len(events)),
        "eventos_dentro_del_periodo_de_actividad": n_events_overlap,
        "rango_eventos": [str(events["event_date"].min()), str(events["event_date"].max())] if len(events) else None,
        "rango_actividad": [str(activity_min), str(activity_max)],
        "nota_anomaly_label": (
            "Sin solape temporal entre eventos y actividad: Anomaly_Label queda a NaN, no a 0/Sin etiqueta, "
            "para no aparentar una confirmacion de 'sin anomalias' que no existe."
            if n_events_overlap == 0
            else "Anomaly_Label derivado de eventos HEAT/ANOMALY que caen dentro del periodo de actividad."
        ),
    }
    return work, summary


def main() -> None:
    # --- Ruibal diario ---
    ruibal_raw = load_dataset(RUIBAL_RAW_PATH)
    ruibal_clean, _ = clean_dataset(ruibal_raw)
    ruibal_daily, ruibal_summary = aggregate_hourly_to_daily(ruibal_clean, "ruibal_diario", "ruibal_horario")

    RUIBAL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    ruibal_out_csv = RUIBAL_OUT_DIR / "ruibal_diario.csv"
    ruibal_daily.to_csv(ruibal_out_csv, index=False)
    with (RUIBAL_OUT_DIR / "ruibal_diario_report.json").open("w", encoding="utf-8") as f:
        json.dump(ruibal_summary, f, ensure_ascii=False, indent=2, default=str)

    # --- Valdillera diario equivalente ---
    valdillera_raw = load_dataset(VALDILLERA_RAW_PATH)
    valdillera_clean, _ = clean_dataset(valdillera_raw)
    valdillera_daily, valdillera_summary = build_valdillera_daily_equivalent(valdillera_clean, VALDILLERA_EVENTS_PATH)

    VALDILLERA_OUT_DIR.mkdir(parents=True, exist_ok=True)
    valdillera_out_csv = VALDILLERA_OUT_DIR / "valdillera_diario_equivalente.csv"
    valdillera_daily.to_csv(valdillera_out_csv, index=False)
    with (VALDILLERA_OUT_DIR / "valdillera_diario_equivalente_report.json").open("w", encoding="utf-8") as f:
        json.dump(valdillera_summary, f, ensure_ascii=False, indent=2, default=str)

    print("=== Ruibal diario ===")
    print(json.dumps(ruibal_summary, ensure_ascii=False, indent=2, default=str))
    print(f"Guardado en: {ruibal_out_csv}")
    print()
    print("=== Valdillera diario equivalente ===")
    print(json.dumps(valdillera_summary, ensure_ascii=False, indent=2, default=str))
    print(f"Guardado en: {valdillera_out_csv}")


if __name__ == "__main__":
    main()

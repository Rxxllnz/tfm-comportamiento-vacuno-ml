from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from preprocesado_base import CANONICAL_TIME_COLUMN, clean_dataset, load_dataset


ACTIVITY_COLUMNS = ["Ruminate", "Eat", "Graze", "Rest", "Walk", "Steps"]


def _window_floor(series: pd.Series, window: str) -> pd.Series:
    if window == "daily":
        return series.dt.floor("D")
    if window == "weekly":
        return series.dt.to_period("W").dt.start_time
    if window == "monthly":
        return series.dt.to_period("M").dt.start_time
    raise ValueError(f"Ventana no soportada: {window}")


def _numeric_summary(group: pd.DataFrame, columns: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for column in columns:
        values = pd.to_numeric(group[column], errors="coerce")
        result[f"{column.lower()}_mean"] = float(values.mean())
        result[f"{column.lower()}_std"] = float(values.std())
        result[f"{column.lower()}_min"] = float(values.min())
        result[f"{column.lower()}_max"] = float(values.max())
        result[f"{column.lower()}_median"] = float(values.median())
        result[f"{column.lower()}_p10"] = float(values.quantile(0.10))
        result[f"{column.lower()}_p90"] = float(values.quantile(0.90))

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        result[f"{column.lower()}_iqr"] = float(iqr)

        mean_value = values.mean()
        std_value = values.std()
        if pd.notna(mean_value) and mean_value != 0:
            result[f"{column.lower()}_cv"] = float(std_value / mean_value)
        else:
            result[f"{column.lower()}_cv"] = np.nan
    return result


def _ratio_summary(group: pd.DataFrame) -> dict[str, float]:
    present = [col for col in ["Ruminate", "Eat", "Graze", "Rest", "Walk"] if col in group.columns]
    if not present:
        return {}

    sums = group[present].apply(pd.to_numeric, errors="coerce").sum()
    total = float(sums.sum())
    if total <= 0:
        return {f"ratio_{col.lower()}": np.nan for col in present}

    return {f"ratio_{col.lower()}": float(sums[col] / total) for col in present}


def _anomaly_summary(group: pd.DataFrame) -> dict[str, float]:
    if "Anomaly_Label" not in group.columns:
        return {}

    labels = group["Anomaly_Label"].fillna("Sin etiqueta").astype(str).str.strip()
    is_anomaly = (~labels.isin(["Sin etiqueta", "No anomaly", "No Anomaly", "None", ""]))
    anomaly_count = int(is_anomaly.sum())
    total = int(len(labels))

    return {
        "anomaly_count": anomaly_count,
        "anomaly_rate": float(anomaly_count / total) if total > 0 else np.nan,
    }


def extract_features(
    df: pd.DataFrame,
    window: str,
    dataset_name: str,
    system_label: str,
    resolution: str = "unknown",
    scale_type: str = "unknown",
) -> pd.DataFrame:
    if "Cow_id" not in df.columns:
        raise ValueError("La columna Cow_id es obligatoria para extraer metricas.")
    if CANONICAL_TIME_COLUMN not in df.columns:
        raise ValueError(f"La columna {CANONICAL_TIME_COLUMN} es obligatoria para extraer metricas.")

    work_df = df.copy()
    work_df = work_df.dropna(subset=[CANONICAL_TIME_COLUMN])
    work_df["window_start"] = _window_floor(work_df[CANONICAL_TIME_COLUMN], window)

    present_numeric = [column for column in ACTIVITY_COLUMNS if column in work_df.columns]
    grouped = work_df.groupby(["Cow_id", "window_start"], dropna=False)

    rows: list[dict[str, object]] = []
    for (cow_id, window_start), group in grouped:
        row: dict[str, object] = {
            "dataset": dataset_name,
            "system": system_label,
            "resolution": resolution,
            "scale_type": scale_type,
            "cow_id": cow_id,
            "window_start": window_start,
            "n_records": int(group.shape[0]),
            "n_missing": int(group.isna().sum().sum()),
        }
        row.update(_numeric_summary(group, present_numeric))
        row.update(_ratio_summary(group))
        row.update(_anomaly_summary(group))
        rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraccion de metricas para comparacion intensivo vs extensivo")
    parser.add_argument("input_path", type=Path, help="Ruta del dataset de entrada")
    parser.add_argument("output_path", type=Path, help="Ruta de salida CSV con features")
    parser.add_argument("--window", choices=["daily", "weekly", "monthly"], default="weekly")
    parser.add_argument("--dataset-name", default="dataset")
    parser.add_argument("--system", default="unknown", help="Etiqueta del sistema: intensivo o extensivo")
    parser.add_argument(
        "--resolution", default="unknown", help="Resolucion temporal nativa de origen: horario o diario"
    )
    parser.add_argument(
        "--scale-type",
        default="unknown",
        help="nativo | agregado_desde_horario | escalado_x24_desde_media_horaria",
    )
    args = parser.parse_args()

    raw_df = load_dataset(args.input_path)
    clean_df, _ = clean_dataset(raw_df)
    features_df = extract_features(
        clean_df, args.window, args.dataset_name, args.system, args.resolution, args.scale_type
    )

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(args.output_path, index=False)

    print(f"Features guardadas en: {args.output_path}")
    print(f"Filas: {features_df.shape[0]} | Columnas: {features_df.shape[1]}")
    print(features_df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


CANONICAL_TIME_COLUMN = "Timestamp"


def load_dataset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}")

    df.columns = [column.strip().replace("\n", " ") for column in df.columns]
    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()

    if "Date" in renamed.columns:
        renamed = renamed.rename(columns={"Date": CANONICAL_TIME_COLUMN})
    elif "Time" in renamed.columns:
        renamed = renamed.rename(columns={"Time": CANONICAL_TIME_COLUMN})

    if "Anomaly_Label" in renamed.columns:
        renamed["Anomaly_Label"] = (
            renamed["Anomaly_Label"]
            .fillna("Sin etiqueta")
            .astype(str)
            .str.strip()
        )

    if "Description" in renamed.columns:
        renamed["Description"] = renamed["Description"].fillna("").astype(str).str.strip()

    if CANONICAL_TIME_COLUMN in renamed.columns:
        renamed[CANONICAL_TIME_COLUMN] = (
            pd.to_datetime(renamed[CANONICAL_TIME_COLUMN], errors="coerce", utc=True)
            .dt.tz_convert(None)
        )

    return renamed


def infer_frequency(df: pd.DataFrame) -> str:
    if CANONICAL_TIME_COLUMN not in df.columns:
        return "unknown"

    time_values = df[CANONICAL_TIME_COLUMN].dropna().sort_values().drop_duplicates()
    if len(time_values) < 2:
        return "unknown"

    deltas = time_values.diff().dropna()
    median_delta = deltas.median()

    if median_delta >= pd.Timedelta(hours=12):
        return "daily"
    return "hourly"


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    cleaned = standardize_columns(df)

    if {"Cow_id", CANONICAL_TIME_COLUMN}.issubset(cleaned.columns):
        cleaned = cleaned.sort_values(["Cow_id", CANONICAL_TIME_COLUMN])

    cleaned = cleaned.drop_duplicates().reset_index(drop=True)

    time_column = CANONICAL_TIME_COLUMN if CANONICAL_TIME_COLUMN in cleaned.columns else None
    summary: dict[str, object] = {
        "rows": int(cleaned.shape[0]),
        "columns": int(cleaned.shape[1]),
        "cow_count": int(cleaned["Cow_id"].nunique()) if "Cow_id" in cleaned.columns else None,
        "missing_values": int(cleaned.isna().sum().sum()),
        "frequency": infer_frequency(cleaned),
    }

    if time_column is not None:
        summary["start"] = cleaned[time_column].min()
        summary["end"] = cleaned[time_column].max()

    if "Anomaly_Label" in cleaned.columns:
        label_counts = cleaned["Anomaly_Label"].value_counts(dropna=False)
        summary["top_labels"] = label_counts.head(5).to_dict()

    return cleaned, summary


def build_output_paths(input_path: Path, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    cleaned_path = output_dir / f"{stem}_cleaned.csv"
    report_path = output_dir / f"{stem}_report.json"
    return cleaned_path, report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocesado base para datos de ganado vacuno")
    parser.add_argument("input_path", type=Path, help="Ruta del fichero de entrada (.csv, .xlsx, .xls)")
    parser.add_argument("output_dir", type=Path, help="Carpeta donde guardar la salida limpia")
    args = parser.parse_args()

    df = load_dataset(args.input_path)
    cleaned_df, summary = clean_dataset(df)
    cleaned_path, report_path = build_output_paths(args.input_path, args.output_dir)

    cleaned_df.to_csv(cleaned_path, index=False)

    with report_path.open("w", encoding="utf-8") as report_file:
        json.dump(summary, report_file, ensure_ascii=False, indent=2, default=str)

    print(f"Guardado: {cleaned_path}")
    print(f"Informe: {report_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
REFERENCES = [
    BASE_DIR / "Procesados" / "Celso novo" / "05_original_variables.csv",
    BASE_DIR / "Procesados" / "Celso novo" / "04_Vacas_etiquetadas_horario.xlsx",
    BASE_DIR / "Procesados" / "Ruibal Riomayor" / "05_Datos_horarios_etiquetados_celo.csv",
]


def load_dataset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}")

    df.columns = [column.strip() for column in df.columns]
    return df


def summarize_dataset(df: pd.DataFrame) -> dict[str, object]:
    time_column = "Date" if "Date" in df.columns else "Time" if "Time" in df.columns else None
    cow_count = int(df["Cow_id"].nunique()) if "Cow_id" in df.columns else None

    summary: dict[str, object] = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "cow_count": cow_count,
        "missing_values": int(df.isna().sum().sum()),
    }

    if time_column is not None:
        dates = pd.to_datetime(df[time_column], errors="coerce")
        summary["start"] = dates.min()
        summary["end"] = dates.max()

    if "Anomaly_Label" in df.columns:
        labels = df["Anomaly_Label"].dropna().astype(str).value_counts().head(5)
        summary["top_labels"] = labels.to_dict()

    return summary


def main() -> None:
    for path in REFERENCES:
        if not path.exists():
            print(f"Falta el fichero: {path}")
            continue

        df = load_dataset(path)
        summary = summarize_dataset(df)

        print("=" * 80)
        print(f"Fichero: {path.name}")
        print(f"Ruta: {path}")
        print(f"Columnas: {list(df.columns)}")
        for key, value in summary.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
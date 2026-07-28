from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    system: str
    path: Path


DATASETS = [
    DatasetSpec(
        name="celso_diario",
        system="intensivo",
        path=BASE_DIR / "Procesados" / "Celso novo" / "05_original_variables.csv",
    ),
    DatasetSpec(
        name="celso_horario",
        system="intensivo",
        path=BASE_DIR / "Procesados" / "Celso novo" / "04_Vacas_etiquetadas_horario.xlsx",
    ),
    DatasetSpec(
        name="ruibal_horario",
        system="intensivo",
        path=BASE_DIR / "Procesados" / "Ruibal Riomayor" / "05_Datos_horarios_etiquetados_celo.csv",
    ),
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


def summarize_dataset(df: pd.DataFrame, system: str, name: str) -> pd.DataFrame:
    time_column = "Date" if "Date" in df.columns else "Time" if "Time" in df.columns else None
    label_column = "Anomaly_Label" if "Anomaly_Label" in df.columns else None

    summary = {
        "dataset": name,
        "system": system,
        "rows": df.shape[0],
        "columns": df.shape[1],
        "cow_count": df["Cow_id"].nunique() if "Cow_id" in df.columns else pd.NA,
        "missing_values": int(df.isna().sum().sum()),
    }

    if time_column is not None:
        time_values = pd.to_datetime(df[time_column], errors="coerce")
        summary["start"] = time_values.min()
        summary["end"] = time_values.max()

    if label_column is not None:
        labels = df[label_column].fillna("Sin etiqueta").astype(str).value_counts()
        summary["top_label"] = labels.index[0] if not labels.empty else pd.NA
        summary["top_label_count"] = int(labels.iloc[0]) if not labels.empty else pd.NA
        summary["anomaly_rows"] = int(df[label_column].notna().sum())

    numeric_cols = [col for col in ["Ruminate", "Eat", "Graze", "Rest", "Walk", "Steps"] if col in df.columns]
    for column in numeric_cols:
        summary[f"mean_{column.lower()}"] = float(pd.to_numeric(df[column], errors="coerce").mean())

    return pd.DataFrame([summary])


def build_comparison_table() -> pd.DataFrame:
    summaries = []
    for spec in DATASETS:
        if not spec.path.exists():
            print(f"Falta el fichero: {spec.path}")
            continue
        df = load_dataset(spec.path)
        summaries.append(summarize_dataset(df, spec.system, spec.name))

    if not summaries:
        return pd.DataFrame()

    return pd.concat(summaries, ignore_index=True)


def plot_system_means(comparison_table: pd.DataFrame, output_dir: Path) -> None:
    numeric_columns = [column for column in comparison_table.columns if column.startswith("mean_")]
    if not numeric_columns:
        return

    system_means = comparison_table.groupby("system")[numeric_columns].mean(numeric_only=True)
    ax = system_means.T.plot(kind="bar", figsize=(12, 6))
    ax.set_title("Media de variables por sistema")
    ax.set_ylabel("Valor medio")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_path = output_dir / "medias_por_sistema.png"
    plt.savefig(figure_path, dpi=150)
    plt.show()
    print(f"Grafica guardada en: {figure_path}")


def main() -> None:
    comparison_table = build_comparison_table()
    if comparison_table.empty:
        print("No hay datos disponibles para comparar.")
        return

    output_dir = BASE_DIR / "resultados" / "comparacion"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "comparacion_sistemas.csv"
    comparison_table.to_csv(csv_path, index=False)
    print(f"Tabla guardada en: {csv_path}")
    print(comparison_table.to_string(index=False))

    plot_system_means(comparison_table, output_dir)


if __name__ == "__main__":
    main()
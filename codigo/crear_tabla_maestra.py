from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
FEATURES_DIR = BASE_DIR / "datos" / "procesados" / "features"
DEFAULT_OUTPUT = FEATURES_DIR / "master_features.csv"
DEFAULT_REPORT = BASE_DIR / "resultados" / "master_features_report.json"
REQUIRED_COLUMNS = ["dataset", "system", "cow_id", "window_start"]


def discover_feature_files(features_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in features_dir.glob("*_weekly_features.csv")
        if path.name != "master_features.csv"
    )


def load_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [column.strip() for column in df.columns]
    return df


def build_master_table(feature_files: list[Path]) -> tuple[pd.DataFrame, dict[str, object]]:
    tables: list[pd.DataFrame] = []
    report_files: list[dict[str, object]] = []

    for path in feature_files:
        df = load_features(path)
        missing_required = [column for column in REQUIRED_COLUMNS if column not in df.columns]
        if missing_required:
            raise ValueError(f"El fichero {path.name} no contiene las columnas requeridas: {missing_required}")

        df["window_start"] = pd.to_datetime(df["window_start"], errors="coerce")
        df = df.sort_values(REQUIRED_COLUMNS).reset_index(drop=True)

        report_files.append(
            {
                "file": path.name,
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
                "dataset": df["dataset"].iloc[0] if not df.empty else None,
                "system": df["system"].iloc[0] if not df.empty else None,
            }
        )
        tables.append(df)

    if not tables:
        empty_report = {
            "feature_files": [],
            "rows": 0,
            "columns": 0,
            "datasets": [],
            "systems": [],
        }
        return pd.DataFrame(), empty_report

    master = pd.concat(tables, ignore_index=True, sort=False)
    master = master.drop_duplicates(subset=REQUIRED_COLUMNS, keep="first").reset_index(drop=True)

    report = {
        "feature_files": report_files,
        "rows": int(master.shape[0]),
        "columns": int(master.shape[1]),
        "datasets": sorted(master["dataset"].dropna().astype(str).unique().tolist()),
        "systems": sorted(master["system"].dropna().astype(str).unique().tolist()),
        "cow_count": int(master["cow_id"].nunique()) if "cow_id" in master.columns else None,
        "window_start_min": str(master["window_start"].min()) if not master.empty else None,
        "window_start_max": str(master["window_start"].max()) if not master.empty else None,
        "missing_values": int(master.isna().sum().sum()),
    }
    return master, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Consolida las features semanales en una tabla maestra")
    parser.add_argument("--features-dir", type=Path, default=FEATURES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    feature_files = discover_feature_files(args.features_dir)
    master, report = build_master_table(feature_files)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    master.to_csv(args.output, index=False)
    with args.report.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2, default=str)

    print(f"Tabla maestra guardada en: {args.output}")
    print(f"Informe guardado en: {args.report}")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
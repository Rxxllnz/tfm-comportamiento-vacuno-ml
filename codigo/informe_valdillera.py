from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = BASE_DIR / "datos" / "entrada" / "valdillera"
OUTPUT_DIR = BASE_DIR / "resultados" / "valdillera"

ACTIVITY_FILE = INPUT_DIR / "00zz_Datos_valdillera_bruto_media_horario_2025-01-01_2026-01-01_20260701.csv"
EVENTS_FILE = INPUT_DIR / "Valdillera_Agropecuaria_events.csv"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    activity = pd.read_csv(ACTIVITY_FILE)
    events = pd.read_csv(EVENTS_FILE)
    return activity, events


def _timestamp_to_str(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def build_report(activity: pd.DataFrame, events: pd.DataFrame) -> dict[str, Any]:
    activity_time = pd.to_datetime(activity["Time"], utc=True, errors="coerce")
    event_time = pd.to_datetime(events["date"], errors="coerce")

    common_cows = sorted(set(activity["Cow_id"]).intersection(set(events["official_tag"])))
    activity_start = activity_time.min()
    activity_end = activity_time.max()
    events_start = event_time.min()
    events_end = event_time.max()
    temporal_overlap = bool(
        pd.notna(activity_start)
        and pd.notna(activity_end)
        and pd.notna(events_start)
        and pd.notna(events_end)
        and max(activity_start.tz_localize(None), events_start)
        <= min(activity_end.tz_localize(None), events_end)
    )

    return {
        "activity": {
            "rows": int(activity.shape[0]),
            "columns": int(activity.shape[1]),
            "cow_count": int(activity["Cow_id"].nunique()),
            "start": _timestamp_to_str(activity_time.min()),
            "end": _timestamp_to_str(activity_time.max()),
            "missing_values": int(activity.isna().sum().sum()),
        },
        "events": {
            "rows": int(events.shape[0]),
            "columns": int(events.shape[1]),
            "cow_count": int(events["official_tag"].nunique()),
            "start": _timestamp_to_str(event_time.min()),
            "end": _timestamp_to_str(event_time.max()),
            "event_counts": events["event"].value_counts(dropna=False).to_dict(),
        },
        "overlap": {
            "common_cows": int(len(common_cows)),
            "sample_common_cows": common_cows[:10],
            "temporal_overlap": temporal_overlap,
        },
    }


def build_cow_summary(activity: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    events_copy = events.copy()
    events_copy["date"] = pd.to_datetime(events_copy["date"], errors="coerce")

    summary = (
        events_copy.groupby("official_tag")
        .agg(
            event_total=("event", "count"),
            anomaly_events=("event", lambda series: int((series == "ANOMALY").sum())),
            heat_events=("event", lambda series: int((series == "HEAT").sum())),
            birth_events=("event", lambda series: int((series == "BIRTH").sum())),
            first_event_date=("date", "min"),
            last_event_date=("date", "max"),
        )
        .reset_index()
        .rename(columns={"official_tag": "cow_id"})
    )

    summary["has_activity"] = summary["cow_id"].isin(activity["Cow_id"])
    return summary.sort_values(["event_total", "cow_id"], ascending=[False, True])


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    activity, events = load_data()
    report = build_report(activity, events)
    cow_summary = build_cow_summary(activity, events)

    report_path = OUTPUT_DIR / "informe_integracion_valdillera.json"
    cow_summary_path = OUTPUT_DIR / "resumen_eventos_por_vaca.csv"
    markdown_path = OUTPUT_DIR / "informe_integracion_valdillera.md"

    with report_path.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2, default=str)

    cow_summary.to_csv(cow_summary_path, index=False)

    activity_report: dict[str, Any] = report["activity"]
    events_report: dict[str, Any] = report["events"]
    overlap_report: dict[str, Any] = report["overlap"]

    markdown = f"""# Informe de integracion de Valdillera

## Actividad

- Filas: {activity_report['rows']}
- Columnas: {activity_report['columns']}
- Vacas: {activity_report['cow_count']}
- Inicio: {activity_report['start']}
- Fin: {activity_report['end']}
- Faltantes: {activity_report['missing_values']}

## Eventos

- Filas: {events_report['rows']}
- Columnas: {events_report['columns']}
- Vacas: {events_report['cow_count']}
- Inicio: {events_report['start']}
- Fin: {events_report['end']}
- Distribucion de eventos: {events_report['event_counts']}

## Solape

- Vacas comunes entre actividad y eventos: {overlap_report['common_cows']}
- Ejemplo de vacas comunes: {overlap_report['sample_common_cows']}
- Solape temporal entre actividad y eventos: {overlap_report['temporal_overlap']}

La coincidencia de identificadores de vaca no implica que los eventos puedan utilizarse para
validar el periodo de actividad. En la version actual de los datos no existe solape temporal,
por lo que las etiquetas de evento no se incorporan como entrada a los modelos ni se interpretan
como confirmacion de ausencia de anomalias.

## Salidas generadas

- {report_path.name}
- {cow_summary_path.name}
"""

    markdown_path.write_text(markdown, encoding="utf-8")

    print(f"Informe JSON: {report_path}")
    print(f"Resumen por vaca: {cow_summary_path}")
    print(f"Markdown: {markdown_path}")


if __name__ == "__main__":
    main()
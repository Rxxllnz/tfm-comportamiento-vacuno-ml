"""Auditoria de resolucion temporal de los datasets de entrada.

Para cada dataset de origen:
  - detecta columna de fecha/hora, columna de vaca y columnas de actividad,
  - calcula cuantos registros hay por vaca y dia,
  - calcula la suma diaria de las variables de actividad (por vaca y dia),
  - clasifica el dataset como "horario", "diario" o "diario_escala_horaria"
    segun esos dos indicadores,
  - genera un informe en Markdown con los resultados.

Ademas, verifica que Celso diario coincide con la suma diaria de Celso horario
comparando por vaca y dia las seis variables principales.

Ejecutar desde la raiz del proyecto:
    python codigo/auditoria_resolucion.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ACTIVITY_COLUMNS, BASE_DIR, NUMERIC_COLUMNS, RESULTADOS_DIR
from preprocesado_base import CANONICAL_TIME_COLUMN, clean_dataset, load_dataset

RAW_SOURCES = {
    "celso_diario": BASE_DIR / "Procesados" / "Celso novo" / "05_original_variables.csv",
    "celso_horario": BASE_DIR / "Procesados" / "Celso novo" / "04_Vacas_etiquetadas_horario.xlsx",
    "ruibal_horario": BASE_DIR / "Procesados" / "Ruibal Riomayor" / "05_Datos_horarios_etiquetados_celo.csv",
    "valdillera_bruto": BASE_DIR
    / "datos"
    / "entrada"
    / "valdillera"
    / "00zz_Datos_valdillera_bruto_media_horario_2025-01-01_2026-01-01_20260701.csv",
}

# Umbrales de clasificacion. Los datos reales no dan exactamente 1440 o 60
# (hay huecos, vacas con menos horas registradas, etc.), asi que se usan bandas.
DAILY_SCALE_MIN, DAILY_SCALE_MAX = 800, 1440  # minutos/dia si es diario real
HOURLY_SCALE_MIN, HOURLY_SCALE_MAX = 20, 60  # minutos/hora si es diario en escala horaria


def _daily_grouping(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["__date"] = work[CANONICAL_TIME_COLUMN].dt.date
    present = [c for c in ACTIVITY_COLUMNS if c in work.columns]
    agg_kwargs = {f"suma_{c.lower()}": (c, "sum") for c in present}
    if "Steps" in work.columns:
        agg_kwargs["suma_steps"] = ("Steps", "sum")
    grouped = work.groupby(["Cow_id", "__date"]).agg(
        n_registros=(CANONICAL_TIME_COLUMN, "count"),
        **agg_kwargs,
    )
    grouped["suma_5_variables"] = grouped[[f"suma_{c.lower()}" for c in present]].sum(axis=1)
    return grouped.reset_index()


def classify_dataset(daily: pd.DataFrame) -> tuple[str, dict[str, float]]:
    median_records = float(daily["n_registros"].median())
    mean_sum = float(daily["suma_5_variables"].mean())
    median_sum = float(daily["suma_5_variables"].median())

    if median_records >= 12:
        classification = "horario"
    elif DAILY_SCALE_MIN <= median_sum <= DAILY_SCALE_MAX:
        classification = "diario"
    elif HOURLY_SCALE_MIN <= median_sum <= HOURLY_SCALE_MAX:
        classification = "diario_escala_horaria"
    else:
        classification = "no_determinado"

    stats = {
        "median_registros_por_vaca_dia": median_records,
        "mean_suma_5_variables": mean_sum,
        "median_suma_5_variables": median_sum,
    }
    return classification, stats


def audit_all_sources() -> dict[str, dict]:
    results: dict[str, dict] = {}
    for name, path in RAW_SOURCES.items():
        raw_df = load_dataset(path)
        clean_df, clean_summary = clean_dataset(raw_df)
        clean_df = clean_df.dropna(subset=[CANONICAL_TIME_COLUMN])

        daily = _daily_grouping(clean_df)
        classification, stats = classify_dataset(daily)

        results[name] = {
            "path": str(path.relative_to(BASE_DIR)),
            "rows": clean_summary["rows"],
            "cow_count": clean_summary["cow_count"],
            "frecuencia_inferida": clean_summary["frequency"],
            "classification": classification,
            **stats,
        }
        results[name]["_daily_table"] = daily
    return results


def verify_celso(results: dict[str, dict]) -> dict:
    """Compara Celso diario nativo contra Celso horario agregado a diario, por
    vaca y dia, para las seis variables principales."""
    diario_daily = results["celso_diario"]["_daily_table"].copy()
    horario_daily = results["celso_horario"]["_daily_table"].copy()

    merged = diario_daily.merge(
        horario_daily, on=["Cow_id", "__date"], how="inner", suffixes=("_diario", "_horario_agregado")
    )

    comparison_rows = []
    for col in NUMERIC_COLUMNS:
        col_a = f"suma_{col.lower()}_diario"
        col_b = f"suma_{col.lower()}_horario_agregado"
        if col_a not in merged.columns or col_b not in merged.columns:
            continue
        diff = (merged[col_a] - merged[col_b]).abs()
        comparison_rows.append(
            {
                "variable": col,
                "diferencia_media": float(diff.mean()),
                "diferencia_maxima": float(diff.max()),
                "diferencia_mediana": float(diff.median()),
                "n_dias_comparados": int(len(merged)),
            }
        )

    return {
        "n_dias_comparados": int(len(merged)),
        "n_dias_solo_en_diario": int(len(diario_daily) - len(merged)),
        "n_dias_solo_en_horario_agregado": int(len(horario_daily) - len(merged)),
        "comparacion_por_variable": comparison_rows,
    }


def write_markdown_report(results: dict[str, dict], celso_check: dict, output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Auditoria de resolucion temporal de los datasets de origen")
    lines.append("")
    lines.append(
        "Generado automaticamente por `codigo/auditoria_resolucion.py`. Clasifica cada "
        "dataset de origen como `horario` (varios registros/vaca/dia, tipicamente ~24), "
        "`diario` (1 registro/vaca/dia, suma de las 5 variables de actividad cercana a "
        "1440 min/dia) o `diario_escala_horaria` (1 registro/vaca/dia, pero la suma de las "
        "5 variables de actividad ronda 60, es decir, es una media por hora y no un total "
        "diario)."
    )
    lines.append("")
    lines.append("| Dataset | Fichero | Filas | Vacas | Registros/vaca/dia (mediana) | "
                  "Suma 5 vars (media) | Clasificacion |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for name, info in results.items():
        lines.append(
            f"| `{name}` | `{info['path']}` | {info['rows']:,} | {info['cow_count']} | "
            f"{info['median_registros_por_vaca_dia']:.2f} | {info['mean_suma_5_variables']:.2f} | "
            f"**{info['classification']}** |"
        )
    lines.append("")

    lines.append("## Interpretacion por dataset")
    lines.append("")
    for name, info in results.items():
        lines.append(f"### `{name}`")
        if info["classification"] == "horario":
            lines.append(
                f"- Mediana de {info['median_registros_por_vaca_dia']:.1f} registros por vaca y dia "
                f"(coherente con ~24 lecturas horarias). Suma diaria de las 5 variables "
                f"~{info['mean_suma_5_variables']:.0f} min, cercana a 1440. **Es horario real.**"
            )
        elif info["classification"] == "diario":
            lines.append(
                f"- 1 registro por vaca y dia, suma de las 5 variables ~{info['mean_suma_5_variables']:.0f} "
                "min, cercana a 1440. **Es diario real** (ya viene agregado a nivel de dia)."
            )
        elif info["classification"] == "diario_escala_horaria":
            lines.append(
                f"- 1 registro por vaca y dia, pero la suma de las 5 variables es "
                f"~{info['mean_suma_5_variables']:.1f}, cercana a 60 (minutos en una hora), no a 1440. "
                "**No es horario real**: es una media por hora agregada a nivel diario. Para obtener "
                "un equivalente diario en minutos/dia comparable con el resto hay que multiplicar "
                "las variables de actividad por 24 (ver `hallazgos_resolucion_temporal.md`)."
            )
        else:
            lines.append("- No se pudo determinar la clasificacion automaticamente con los umbrales actuales.")
        lines.append("")

    lines.append("## Verificacion de Celso: diario nativo vs horario agregado a diario")
    lines.append("")
    lines.append(
        f"Pares vaca-dia comparables (misma vaca y fecha presentes en ambos datasets): "
        f"{celso_check['n_dias_comparados']:,}. "
        f"Pares vaca-dia solo en el diario nativo: {celso_check['n_dias_solo_en_diario']:,}. "
        f"Pares vaca-dia solo en el horario agregado: {celso_check['n_dias_solo_en_horario_agregado']:,}. "
        "Esta diferencia no debe interpretarse como dias naturales faltantes: los dos ficheros "
        "incluyen coberturas distintas de animales y periodos. La comparacion de valores se realiza "
        "exclusivamente sobre la interseccion de identificador de vaca y fecha."
    )
    lines.append("")
    lines.append("| Variable | Diferencia media (unidad original) | Diferencia mediana (unidad original) | Diferencia maxima (unidad original) |")
    lines.append("|---|---:|---:|---:|")
    for row in celso_check["comparacion_por_variable"]:
        lines.append(
            f"| {row['variable']} | {row['diferencia_media']:.2f} | {row['diferencia_mediana']:.2f} | "
            f"{row['diferencia_maxima']:.2f} |"
        )
    lines.append("")

    max_diffs = [row["diferencia_maxima"] for row in celso_check["comparacion_por_variable"]]
    mean_diffs = [row["diferencia_media"] for row in celso_check["comparacion_por_variable"]]
    if max_diffs and max(max_diffs) <= 5 and max(mean_diffs) <= 1:
        lines.append(
            "**Conclusion:** las diferencias son despreciables (medias <= 1 unidad y maximos <= 5 unidades "
            "por variable y dia, en la unidad original de cada variable). Celso diario es coherente con la "
            "agregacion de Celso horario: las variables de actividad quedan expresadas en minutos/dia "
            "y Steps en conteos/dia, lo que confirma que Celso "
            "diario es un diario real y no requiere ningun reescalado."
        )
    else:
        lines.append(
            f"**Conclusion:** hay diferencias no despreciables entre Celso diario y la agregacion de Celso "
            f"horario (diferencia media maxima observada: {max(mean_diffs):.2f}; diferencia maxima "
            f"observada: {max(max_diffs):.2f}, en la unidad original de cada variable). Revisar antes de asumir que ambos son directamente "
            "intercambiables."
        )
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    results = audit_all_sources()
    celso_check = verify_celso(results)

    output_dir = RESULTADOS_DIR / "auditoria"
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON con los numeros (sin las tablas diarias completas, serian muy grandes)
    json_payload = {
        name: {k: v for k, v in info.items() if k != "_daily_table"} for name, info in results.items()
    }
    json_payload["verificacion_celso"] = celso_check
    with (output_dir / "auditoria_resolucion.json").open("w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, indent=2, default=str)

    write_markdown_report(results, celso_check, output_dir / "informe_auditoria_resolucion.md")

    print("=== Resumen de clasificacion ===")
    for name, info in results.items():
        print(
            f"{name:20s} registros/vaca/dia(mediana)={info['median_registros_por_vaca_dia']:6.2f}  "
            f"suma_5_vars(media)={info['mean_suma_5_variables']:8.2f}  -> {info['classification']}"
        )
    print()
    print(f"Informe guardado en: {output_dir / 'informe_auditoria_resolucion.md'}")
    print(f"JSON guardado en: {output_dir / 'auditoria_resolucion.json'}")


if __name__ == "__main__":
    main()

"""Consolida los resultados de pca_ramas.py y clustering_ramas.py en un informe
Markdown por rama, guardado dentro de su propia carpeta de resultados.

Ejecutar desde la raiz del proyecto, DESPUES de pca_ramas.py y clustering_ramas.py:
    python codigo/generar_informes_ramas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import RESULTADOS_DIR
from pca_ramas import RAMAS


def _fmt_contingency(table: dict) -> str:
    df = pd.DataFrame(table).fillna(0).astype(int)
    return df.to_markdown()


def build_report(rama_key: str, config: dict, pca_summary: dict, clustering_summary: dict) -> str:
    lines = [f"# Informe de analisis — {config['titulo']}", ""]
    lines.append(
        "Este informe se genera automaticamente a partir de `codigo/pca_ramas.py` y "
        "`codigo/clustering_ramas.py`, y documenta el analisis de componentes principales (PCA) y "
        "clustering realizado sobre las features semanales de esta rama. La fase de reduccion "
        "dimensional avanzada (t-SNE, UMAP) y clustering comparativo que amplia estos resultados se "
        "documenta por separado en `reduccion_avanzada/informe_reduccion_avanzada_"
        f"{rama_key}.md`."
    )
    lines.append("")
    lines.append(f"Numero de filas de features analizadas: {pca_summary['n_filas']:,}.")
    lines.append("")

    lines.append("## Analisis de componentes principales (PCA)")
    lines.append("")
    for kind in ["absolutas", "ratios"]:
        if kind not in pca_summary:
            continue
        info = pca_summary[kind]
        lines.append(f"### Variables {kind} ({info['n_features']} variables de entrada)")
        lines.append(
            f"Varianza explicada: PC1={info['explained_variance_ratio'][0]:.1%}, "
            f"PC2={info['explained_variance_ratio'][1]:.1%}, acumulada={info['explained_variance_cumulative']:.1%}."
        )
        top_pc1 = sorted(info["top5_loadings_pc1"].items(), key=lambda kv: abs(kv[1]), reverse=True)
        lines.append("Variables con mayor peso en PC1: " + ", ".join(f"`{k}` ({v:+.2f})" for k, v in top_pc1) + ".")
        lines.append(
            f"eta² (`system`, PC1) = {info['eta_cuadrado_system_PC1']:.3f}; "
            f"eta² (`dataset`, PC1) = {info['eta_cuadrado_dataset_PC1']:.3f} "
            "(proporcion de la varianza de PC1 atribuible a cada agrupacion)."
        )
        lines.append("")
        lines.append(f"![PCA {kind} por dataset](pca_{rama_key}_{kind}_por_dataset.png)")
        lines.append("")
        lines.append(f"![PCA {kind} por system](pca_{rama_key}_{kind}_por_system.png)")
        lines.append("")

    lines.append("## Clustering")
    lines.append("")
    for kind in ["absolutas", "ratios"]:
        if kind not in clustering_summary:
            continue
        info = clustering_summary[kind]
        lines.append(f"### Variables {kind}")
        lines.append(
            f"Configuracion con mayor silhouette score: **{info['mejor_algoritmo']}**, k={info['mejor_k']}."
        )
        lines.append(
            f"silhouette={info['silhouette']:.3f} (valores mas altos indican clusters mejor separados), "
            f"Davies-Bouldin={info['davies_bouldin']:.3f} (valores mas bajos indican mejor separacion), "
            f"Calinski-Harabasz={info['calinski_harabasz']:.1f} (valores mas altos indican mejor separacion)."
        )
        lines.append(
            "Pureza media por vaca (fraccion de semanas de una misma vaca asignadas a su cluster "
            f"dominante): {info['pureza_media_por_vaca']:.1%}."
        )
        lines.append("")
        lines.append("Distribucion de clusters por `dataset`:")
        lines.append("")
        lines.append(_fmt_contingency(info["contingencia_dataset"]))
        lines.append("")
        lines.append("Distribucion de clusters por `system`:")
        lines.append("")
        lines.append(_fmt_contingency(info["contingencia_system"]))
        lines.append("")
        lines.append(f"![Clustering {kind} en espacio PCA](clustering_{rama_key}_{kind}_scatter_pca.png)")
        lines.append("")
        lines.append(
            "Metricas completas para todas las combinaciones de algoritmo y k evaluadas: "
            f"`clustering_{rama_key}_{kind}_metricas.csv`."
        )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    with (RESULTADOS_DIR / "pca_resumen.json").open(encoding="utf-8") as f:
        pca_all = {item["rama"]: item for item in json.load(f)}
    with (RESULTADOS_DIR / "clustering_resumen.json").open(encoding="utf-8") as f:
        clustering_all = {item["rama"]: item for item in json.load(f)}

    for key, cfg in RAMAS.items():
        report = build_report(key, cfg, pca_all[key], clustering_all[key])
        out_path = cfg["output_dir"] / f"informe_{key}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"Informe guardado: {out_path}")


if __name__ == "__main__":
    main()

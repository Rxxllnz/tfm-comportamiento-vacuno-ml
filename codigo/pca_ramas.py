"""PCA para las dos ramas de analisis.

Para cada rama (A: horario intensivo, B: diario intensivo vs extensivo) y cada
conjunto de variables (absolutas vs solo ratios):
  - imputa (mediana) y escala (estandar) las features,
  - ajusta un PCA a 2 componentes,
  - guarda varianza explicada, loadings de PC1/PC2, y proyeccion con metadatos,
  - genera scatter coloreado por dataset, por system y (si el numero de vacas
    es manejable) por cow_id,
  - calcula, para PC1 y PC2, que fraccion de la varianza explica cada variable
    de agrupacion (system, dataset) mediante eta-cuadrado (SS-between/SS-total),
    para dar una interpretacion cuantitativa de que esta separando el PCA en
    lugar de una lectura solo visual del scatter.

Ejecutar desde la raiz del proyecto, DESPUES de codigo/extraer_features_ramas.py:
    python codigo/pca_ramas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FEATURE_EXCLUDE_COLUMNS, FEATURES_DIR, RESULTADOS_DIR

MAX_COWS_FOR_COLOR_PLOT = 150

RAMAS = {
    "rama_a_horario_intensivo": dict(
        features_path=FEATURES_DIR / "rama_a_horario_intensivo_weekly_features.csv",
        output_dir=RESULTADOS_DIR / "analisis_horario_intensivo",
        titulo="Rama A: horario intensivo (Celso horario + Ruibal horario)",
    ),
    "rama_b_diario_sistemas": dict(
        features_path=FEATURES_DIR / "rama_b_diario_sistemas_weekly_features.csv",
        output_dir=RESULTADOS_DIR / "analisis_diario_sistemas",
        titulo="Rama B: diario intensivo vs extensivo (Celso diario + Ruibal diario + Valdillera x24)",
    ),
}


def _feature_columns(df: pd.DataFrame, kind: str) -> list[str]:
    candidates = [c for c in df.columns if c not in FEATURE_EXCLUDE_COLUMNS]
    if kind == "ratios":
        return [c for c in candidates if c.startswith("ratio_")]
    if kind == "absolutas":
        return [c for c in candidates if not c.startswith("ratio_")]
    raise ValueError(f"kind no soportado: {kind}")


def _eta_squared(pc_values: np.ndarray, groups: pd.Series) -> float:
    """Fraccion de la varianza total de pc_values explicada por la pertenencia a
    'groups' (SS-between / SS-total). 0 = el grupo no explica nada, 1 = el grupo
    lo explica todo."""
    grand_mean = pc_values.mean()
    ss_total = float(((pc_values - grand_mean) ** 2).sum())
    if ss_total == 0:
        return float("nan")
    ss_between = 0.0
    for _, idx in groups.groupby(groups).groups.items():
        group_values = pc_values[groups.index.get_indexer(idx)]
        ss_between += len(group_values) * (group_values.mean() - grand_mean) ** 2
    return float(ss_between / ss_total)


def run_pca(df: pd.DataFrame, feature_cols: list[str]) -> tuple[PCA, np.ndarray, pd.DataFrame]:
    matrix = df[feature_cols].apply(pd.to_numeric, errors="coerce")
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    imputed = imputer.fit_transform(matrix)
    scaled = scaler.fit_transform(imputed)

    pca = PCA(n_components=2, random_state=42)
    components = pca.fit_transform(scaled)

    loadings = pd.DataFrame(
        pca.components_.T, index=feature_cols, columns=["PC1_loading", "PC2_loading"]
    )
    loadings["abs_PC1"] = loadings["PC1_loading"].abs()
    loadings["abs_PC2"] = loadings["PC2_loading"].abs()

    return pca, components, loadings


def make_scatter(pca_df: pd.DataFrame, color_col: str, title: str, out_path: Path, categorical_cmap: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    if categorical_cmap:
        codes = pd.Categorical(pca_df[color_col]).codes
        scatter = ax.scatter(pca_df["PC1"], pca_df["PC2"], c=codes, cmap="tab20", s=14, alpha=0.65)
    else:
        for value, group in pca_df.groupby(color_col):
            ax.scatter(group["PC1"], group["PC2"], s=14, alpha=0.6, label=str(value))
        ax.legend(fontsize=8, title=color_col)
    ax.set_title(title)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def analyze_rama(rama_key: str, config: dict) -> dict:
    output_dir = config["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(config["features_path"])
    df["window_start"] = pd.to_datetime(df["window_start"])

    rama_summary: dict[str, object] = {
        "rama": rama_key,
        "titulo": config["titulo"],
        "n_filas": int(len(df)),
        "n_systems": int(df["system"].nunique()),
        "system_unico": str(df["system"].iloc[0]) if df["system"].nunique() == 1 else None,
    }

    for kind in ["absolutas", "ratios"]:
        feature_cols = _feature_columns(df, kind)
        if not feature_cols:
            continue

        pca, components, loadings = run_pca(df, feature_cols)
        pca_df = pd.DataFrame(components, columns=["PC1", "PC2"], index=df.index)
        pca_df = pd.concat([df[["dataset", "system", "resolution", "scale_type", "cow_id", "window_start"]], pca_df], axis=1)

        prefix = f"pca_{rama_key}_{kind}"
        pca_df.to_csv(output_dir / f"{prefix}_proyeccion.csv", index=False)
        loadings.sort_values("abs_PC1", ascending=False).to_csv(output_dir / f"{prefix}_loadings.csv")

        make_scatter(pca_df, "dataset", f"{config['titulo']} — PCA ({kind}) por dataset", output_dir / f"{prefix}_por_dataset.png")
        make_scatter(pca_df, "system", f"{config['titulo']} — PCA ({kind}) por system", output_dir / f"{prefix}_por_system.png")

        n_cows = df["cow_id"].nunique()
        if n_cows <= MAX_COWS_FOR_COLOR_PLOT:
            make_scatter(
                pca_df, "cow_id", f"{config['titulo']} — PCA ({kind}) por cow_id",
                output_dir / f"{prefix}_por_cow_id.png", categorical_cmap=True,
            )

        eta_system_pc1 = _eta_squared(pca_df["PC1"].to_numpy(), df["system"])
        eta_system_pc2 = _eta_squared(pca_df["PC2"].to_numpy(), df["system"])
        eta_dataset_pc1 = _eta_squared(pca_df["PC1"].to_numpy(), df["dataset"])
        eta_dataset_pc2 = _eta_squared(pca_df["PC2"].to_numpy(), df["dataset"])

        rama_summary[kind] = {
            "n_features": len(feature_cols),
            "explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
            "explained_variance_cumulative": float(pca.explained_variance_ratio_.sum()),
            "top5_loadings_pc1": loadings.sort_values("abs_PC1", ascending=False).head(5)["PC1_loading"].to_dict(),
            "top5_loadings_pc2": loadings.sort_values("abs_PC2", ascending=False).head(5)["PC2_loading"].to_dict(),
            "eta_cuadrado_system_PC1": eta_system_pc1,
            "eta_cuadrado_system_PC2": eta_system_pc2,
            "eta_cuadrado_dataset_PC1": eta_dataset_pc1,
            "eta_cuadrado_dataset_PC2": eta_dataset_pc2,
        }

        print(
            f"[{rama_key}/{kind}] var.explicada={pca.explained_variance_ratio_.sum():.3f}  "
            f"eta2(system,PC1)={eta_system_pc1:.3f}  eta2(dataset,PC1)={eta_dataset_pc1:.3f}"
        )

    return rama_summary


def write_markdown_summary(all_summaries: list[dict], output_path: Path) -> None:
    lines = ["# Resumen de PCA por rama", ""]
    lines.append(
        "Este documento resume el analisis de componentes principales (PCA) de cada rama, con una "
        "medida cuantitativa (eta cuadrado) de que agrupacion — sistema productivo o dataset de "
        "origen — explica una mayor proporcion de la varianza del primer componente."
    )
    lines.append("")
    for summary in all_summaries:
        lines.append(f"## {summary['titulo']}")
        lines.append("")
        for kind in ["absolutas", "ratios"]:
            if kind not in summary:
                continue
            info = summary[kind]
            lines.append(f"### Variables {kind}")
            lines.append(
                f"Varianza explicada: PC1={info['explained_variance_ratio'][0]:.3f}, "
                f"PC2={info['explained_variance_ratio'][1]:.3f}, "
                f"acumulada={info['explained_variance_cumulative']:.3f} "
                f"(sobre {info['n_features']} variables de entrada)."
            )
            lines.append(
                f"eta² de `system` sobre PC1={info['eta_cuadrado_system_PC1']:.3f}, "
                f"sobre PC2={info['eta_cuadrado_system_PC2']:.3f} "
                "(proporcion de la varianza de ese componente asociada al sistema productivo)."
            )
            lines.append(
                f"eta² de `dataset` sobre PC1={info['eta_cuadrado_dataset_PC1']:.3f}, "
                f"sobre PC2={info['eta_cuadrado_dataset_PC2']:.3f} "
                "(proporcion de la varianza asociada al dataset de origen, que combina granja, "
                "resolucion temporal y escala)."
            )
            n_systems = summary["n_systems"]
            if n_systems < 2:
                interpretacion = (
                    f"`system` es constante en esta rama (unico valor: '{summary['system_unico']}'), por lo "
                    "que su eta² resulta trivialmente nulo y no es comparable con el de `dataset`. "
                    f"El eta² de `dataset` sobre PC1 ({info['eta_cuadrado_dataset_PC1']:.3f}) es "
                    + (
                        "bajo, lo que indica un solapamiento considerable entre las dos granjas intensivas "
                        "en este espacio de variables: la variabilidad individual/semanal predomina sobre "
                        "la variabilidad entre granjas."
                        if info["eta_cuadrado_dataset_PC1"] < 0.15
                        else "moderado o alto, lo que indica diferencias sistematicas entre las granjas "
                        "intensivas mas alla de la variabilidad individual."
                    )
                )
            elif info["eta_cuadrado_dataset_PC1"] > info["eta_cuadrado_system_PC1"] + 0.1:
                interpretacion = (
                    "PC1 esta mas asociado al **dataset de origen** que al sistema productivo: parte de "
                    "la separacion observada podria deberse a diferencias de granja, resolucion o escala, "
                    "y no exclusivamente a la distincion intensivo/extensivo. Se recomienda cautela al "
                    "atribuir la separacion al sistema productivo."
                )
            elif info["eta_cuadrado_system_PC1"] > info["eta_cuadrado_dataset_PC1"] + 0.1:
                interpretacion = (
                    "PC1 esta mas asociado al **sistema productivo** (intensivo/extensivo) que al dataset "
                    "individual: la separacion observada no se explica unicamente por diferencias entre "
                    "granjas concretas."
                )
            else:
                interpretacion = (
                    "Los valores de eta² de `system` y `dataset` son similares en PC1: este analisis no "
                    "permite distinguir si la separacion se debe al sistema productivo o a diferencias "
                    "especificas de cada granja o dataset, dado que ambas variables estan parcialmente "
                    "confundidas (el dataset determina el sistema)."
                )
            lines.append(f"**Interpretacion:** {interpretacion}")
            lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    summaries = [analyze_rama(key, cfg) for key, cfg in RAMAS.items()]

    json_out = RESULTADOS_DIR / "pca_resumen.json"
    with json_out.open("w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2, default=str)

    write_markdown_summary(summaries, RESULTADOS_DIR / "pca_resumen.md")
    print(f"\nResumen JSON: {json_out}")
    print(f"Resumen Markdown: {RESULTADOS_DIR / 'pca_resumen.md'}")


if __name__ == "__main__":
    main()

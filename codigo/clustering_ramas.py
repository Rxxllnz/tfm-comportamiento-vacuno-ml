"""Clustering para las dos ramas de analisis.

Para cada rama y cada conjunto de variables (absolutas / ratios):
  - imputa y escala igual que en pca_ramas.py (mismo preprocesado, para que los
    resultados de PCA y clustering sean comparables),
  - prueba KMeans, AgglomerativeClustering y GaussianMixture para k=2..6,
  - evalua cada combinacion con silhouette, Davies-Bouldin y Calinski-Harabasz,
  - se queda con la combinacion (algoritmo, k) de mayor silhouette como
    "recomendada" y genera su tabla de contingencia frente a dataset/system,
  - guarda un scatter en el espacio PCA(2D) coloreado por el cluster recomendado.

Ejecutar desde la raiz del proyecto, DESPUES de pca_ramas.py (reutiliza la
misma logica de features, no sus ficheros):
    python codigo/clustering_ramas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FEATURE_EXCLUDE_COLUMNS, FEATURES_DIR, RESULTADOS_DIR
from pca_ramas import RAMAS, _feature_columns

K_RANGE = [2, 3, 4, 5, 6]

ALGORITHMS = {
    "kmeans": lambda k: KMeans(n_clusters=k, random_state=42, n_init=10),
    "agglomerative": lambda k: AgglomerativeClustering(n_clusters=k),
    "gmm": lambda k: GaussianMixture(n_components=k, random_state=42),
}


def _prepare_matrix(df: pd.DataFrame, feature_cols: list[str]):
    matrix = df[feature_cols].apply(pd.to_numeric, errors="coerce")
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    return scaler.fit_transform(imputer.fit_transform(matrix))


def evaluate_clustering(scaled: "np.ndarray") -> pd.DataFrame:
    rows = []
    for algo_name, factory in ALGORITHMS.items():
        for k in K_RANGE:
            model = factory(k)
            labels = model.fit_predict(scaled)
            if len(set(labels)) < 2:
                continue
            rows.append(
                {
                    "algoritmo": algo_name,
                    "k": k,
                    "silhouette": float(silhouette_score(scaled, labels)),
                    "davies_bouldin": float(davies_bouldin_score(scaled, labels)),
                    "calinski_harabasz": float(calinski_harabasz_score(scaled, labels)),
                }
            )
    return pd.DataFrame(rows)


def fit_best(scaled, metrics: pd.DataFrame):
    best_row = metrics.sort_values("silhouette", ascending=False).iloc[0]
    model = ALGORITHMS[best_row["algoritmo"]](int(best_row["k"]))
    labels = model.fit_predict(scaled)
    return best_row, labels


def analyze_rama_clustering(rama_key: str, config: dict, output_dir: Path) -> dict:
    df = pd.read_csv(config["features_path"])
    rama_result: dict[str, object] = {"rama": rama_key}

    for kind in ["absolutas", "ratios"]:
        feature_cols = _feature_columns(df, kind)
        if not feature_cols:
            continue
        scaled = _prepare_matrix(df, feature_cols)

        metrics = evaluate_clustering(scaled)
        prefix = f"clustering_{rama_key}_{kind}"
        metrics.to_csv(output_dir / f"{prefix}_metricas.csv", index=False)

        if metrics.empty:
            continue

        best_row, labels = fit_best(scaled, metrics)
        df_labels = df[["dataset", "system", "cow_id"]].copy()
        df_labels["cluster"] = labels

        contingency_dataset = pd.crosstab(df_labels["cluster"], df_labels["dataset"])
        contingency_system = pd.crosstab(df_labels["cluster"], df_labels["system"])
        contingency_dataset.to_csv(output_dir / f"{prefix}_contingencia_dataset.csv")
        contingency_system.to_csv(output_dir / f"{prefix}_contingencia_system.csv")

        cow_purity = (
            df_labels.groupby("cow_id")["cluster"]
            .agg(lambda s: s.value_counts(normalize=True).max())
            .rename("pureza_cluster_dominante")
        )

        # scatter en espacio PCA 2D coloreado por el cluster recomendado
        pca = PCA(n_components=2, random_state=42)
        components = pca.fit_transform(scaled)
        fig, ax = plt.subplots(figsize=(8, 6))
        scatter = ax.scatter(components[:, 0], components[:, 1], c=labels, cmap="tab10", s=14, alpha=0.65)
        legend1 = ax.legend(*scatter.legend_elements(), title="cluster", fontsize=8)
        ax.add_artist(legend1)
        ax.set_title(
            f"{config['titulo']} — clustering ({kind}): {best_row['algoritmo']} k={int(best_row['k'])}"
        )
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        plt.tight_layout()
        plt.savefig(output_dir / f"{prefix}_scatter_pca.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

        rama_result[kind] = {
            "mejor_algoritmo": best_row["algoritmo"],
            "mejor_k": int(best_row["k"]),
            "silhouette": float(best_row["silhouette"]),
            "davies_bouldin": float(best_row["davies_bouldin"]),
            "calinski_harabasz": float(best_row["calinski_harabasz"]),
            "pureza_media_por_vaca": float(cow_purity.mean()),
            "contingencia_dataset": contingency_dataset.to_dict(),
            "contingencia_system": contingency_system.to_dict(),
        }
        print(
            f"[{rama_key}/{kind}] mejor: {best_row['algoritmo']} k={int(best_row['k'])} "
            f"silhouette={best_row['silhouette']:.3f} DB={best_row['davies_bouldin']:.3f} "
            f"CH={best_row['calinski_harabasz']:.1f} | pureza media por vaca={cow_purity.mean():.3f}"
        )

    return rama_result


def main() -> None:
    all_results = []
    for key, cfg in RAMAS.items():
        cfg["output_dir"].mkdir(parents=True, exist_ok=True)
        all_results.append(analyze_rama_clustering(key, cfg, cfg["output_dir"]))

    out_json = RESULTADOS_DIR / "clustering_resumen.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResumen guardado en: {out_json}")


if __name__ == "__main__":
    main()

"""Fase de reduccion dimensional avanzada y clustering comparativo.

Amplia pca_ramas.py / clustering_ramas.py con tecnicas no lineales (t-SNE, UMAP)
y con DBSCAN, siguiendo la recomendacion del tutor. IMPORTANTE (alcance):
t-SNE y UMAP se usan aqui como tecnicas de VISUALIZACION no lineal para explorar
la estructura de los datos, no como prueba definitiva de separacion entre
sistemas: las proyecciones no lineales distorsionan distancias globales y son
sensibles a sus hiperparametros, por eso se prueban varios y se documentan side
by side en vez de enseñar solo la que "mejor se ve". La tecnica con loadings
interpretables (que variable pesa cuanto) sigue siendo PCA.

Ninguna tecnica se entrena usando la etiqueta `system`: PCA/t-SNE/UMAP y el
clustering son todos no supervisados. `system`/`dataset`/`cow_id` solo se usan
DESPUES, para colorear e interpretar, nunca como entrada.

Trabaja sobre 3 conjuntos de variables por rama:
  a) absolutas_completas: todas las variables *_mean/_std/... (incluye steps)
  b) ratios: solo ratio_*
  c) absolutas_sin_steps: como (a) pero sin steps_*

Y sobre 3 espacios para el clustering: el espacio original escalado, la
proyeccion PCA(2D) y la proyeccion UMAP(2D) (si umap-learn esta instalado).

Uso (puede tardar varios minutos por ejecucion completa; t-SNE es lento):
    python codigo/reduccion_clustering_avanzado.py --rama all --kind all
    python codigo/reduccion_clustering_avanzado.py --rama rama_a_horario_intensivo --kind ratios
    python codigo/reduccion_clustering_avanzado.py --mode report   # solo consolida el informe Markdown
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.manifold import TSNE
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

try:
    import umap

    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FEATURE_EXCLUDE_COLUMNS, FEATURES_DIR, RESULTADOS_DIR

warnings.filterwarnings("ignore", category=UserWarning)

RANDOM_STATE = 42
TSNE_PERPLEXITIES = [5, 10, 30, 50]
TSNE_MAIN_PERPLEXITY = 30
UMAP_N_NEIGHBORS = [10, 15, 30, 50]
UMAP_MIN_DIST = [0.0, 0.1, 0.5]
UMAP_MAIN_PARAMS = {"n_neighbors": 15, "min_dist": 0.1}
CLUSTER_K_RANGE = [2, 3, 4, 5, 6]
DBSCAN_MIN_SAMPLES = [5, 10]
DBSCAN_ECDF_PERCENTILES = [50, 75, 90]
MAX_COWS_FOR_COLOR_PLOT = 150

# Un resultado de DBSCAN se considera degenerado (no apto como resultado principal,
# solo exploratorio) cuando produce demasiados microclusters o demasiado ruido.
DBSCAN_MAX_CLUSTERS_INTERPRETABLE = 10
DBSCAN_MAX_NOISE_FRACTION_INTERPRETABLE = 0.15

KINDS = ["absolutas_completas", "ratios", "absolutas_sin_steps"]

RAMAS = {
    "rama_a_horario_intensivo": dict(
        features_path=FEATURES_DIR / "rama_a_horario_intensivo_weekly_features.csv",
        output_dir=RESULTADOS_DIR / "analisis_horario_intensivo" / "reduccion_avanzada",
        titulo="Rama A: horario intensivo (Celso horario + Ruibal horario)",
    ),
    "rama_b_diario_sistemas": dict(
        features_path=FEATURES_DIR / "rama_b_diario_sistemas_weekly_features.csv",
        output_dir=RESULTADOS_DIR / "analisis_diario_sistemas" / "reduccion_avanzada",
        titulo="Rama B: diario intensivo vs extensivo (Celso diario + Ruibal diario + Valdillera x24)",
    ),
}


# ---------------------------------------------------------------------------
# Preparacion de datos
# ---------------------------------------------------------------------------


def feature_columns(df: pd.DataFrame, kind: str) -> list[str]:
    candidates = [c for c in df.columns if c not in FEATURE_EXCLUDE_COLUMNS]
    if kind == "absolutas_completas":
        return [c for c in candidates if not c.startswith("ratio_")]
    if kind == "ratios":
        return [c for c in candidates if c.startswith("ratio_")]
    if kind == "absolutas_sin_steps":
        return [c for c in candidates if not c.startswith("ratio_") and not c.startswith("steps_")]
    raise ValueError(f"kind no soportado: {kind}")


def prepare_matrix(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Imputa (mediana) y escala (estandar) las columnas indicadas. No usa
    `system`/`dataset`/`cow_id` para nada: son metadatos, ya excluidos en `cols`."""
    matrix = df[cols].apply(pd.to_numeric, errors="coerce")
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    return scaler.fit_transform(imputer.fit_transform(matrix))


# ---------------------------------------------------------------------------
# Reduccion dimensional
# ---------------------------------------------------------------------------


def run_pca(X: np.ndarray) -> tuple[np.ndarray, PCA]:
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    return pca.fit_transform(X), pca


def run_tsne_grid(X: np.ndarray, perplexities: list[int]) -> dict[int, dict[str, object]]:
    results = {}
    for perplexity in perplexities:
        if perplexity >= X.shape[0]:
            continue  # perplexity debe ser menor que n_muestras
        tsne = TSNE(
            n_components=2,
            perplexity=perplexity,
            learning_rate="auto",
            init="pca",
            random_state=RANDOM_STATE,
        )
        embedding = tsne.fit_transform(X)
        results[perplexity] = {"embedding": embedding, "kl_divergence": float(tsne.kl_divergence_)}
    return results


def run_umap_grid(
    X: np.ndarray, n_neighbors_list: list[int], min_dist_list: list[float]
) -> dict[tuple[int, float], dict[str, object]]:
    if not UMAP_AVAILABLE:
        return {}
    results = {}
    for n_neighbors in n_neighbors_list:
        if n_neighbors >= X.shape[0]:
            continue
        for min_dist in min_dist_list:
            reducer = umap.UMAP(
                n_neighbors=n_neighbors,
                min_dist=min_dist,
                n_components=2,
                random_state=RANDOM_STATE,
            )
            embedding = reducer.fit_transform(X)
            results[(n_neighbors, min_dist)] = {"embedding": embedding}
    return results


# ---------------------------------------------------------------------------
# Visualizacion
# ---------------------------------------------------------------------------


def make_scatter(coords: np.ndarray, color_values: pd.Series, title: str, out_path: Path, categorical_cmap: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    if categorical_cmap:
        codes = pd.Categorical(color_values).codes
        ax.scatter(coords[:, 0], coords[:, 1], c=codes, cmap="tab20", s=12, alpha=0.65)
    else:
        for value in sorted(color_values.unique(), key=str):
            mask = (color_values == value).to_numpy()
            ax.scatter(coords[mask, 0], coords[mask, 1], s=12, alpha=0.6, label=str(value))
        ax.legend(fontsize=8)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("dim 1")
    ax.set_ylabel("dim 2")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def make_grid_scatter(
    grid_results: dict, coord_key: str, panel_title_fn, color_values: pd.Series, suptitle: str, out_path: Path, ncols: int
) -> None:
    keys = list(grid_results.keys())
    if not keys:
        return
    nrows = int(np.ceil(len(keys) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.6 * nrows), squeeze=False)
    codes = pd.Categorical(color_values).codes
    categories = pd.Categorical(color_values).categories
    for idx, key in enumerate(keys):
        ax = axes[idx // ncols][idx % ncols]
        coords = grid_results[key][coord_key]
        scatter = ax.scatter(coords[:, 0], coords[:, 1], c=codes, cmap="tab10", s=8, alpha=0.6)
        ax.set_title(panel_title_fn(key), fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    for idx in range(len(keys), nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")
    handles = [
        plt.Line2D([0], [0], marker="o", linestyle="", color=plt.cm.tab10(i / max(len(categories) - 1, 1)))
        for i in range(len(categories))
    ]
    fig.legend(handles, list(categories), loc="lower center", ncol=len(categories), fontsize=8, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(suptitle, fontsize=11)
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def _eval_metrics(X: np.ndarray, labels: np.ndarray) -> dict[str, float] | None:
    if len(set(labels)) < 2:
        return None
    return {
        "silhouette": float(silhouette_score(X, labels)),
        "davies_bouldin": float(davies_bouldin_score(X, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
    }


def evaluate_clustering(X: np.ndarray) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Prueba KMeans/Agglomerative/GMM (k=2..6) y DBSCAN (grid de eps via
    percentiles de la distancia al k-esimo vecino, dos valores de min_samples).
    Devuelve la tabla de metricas y un diccionario {clave: labels} para poder
    recuperar la asignacion de la mejor combinacion sin reajustar."""
    rows = []
    labels_store: dict[str, np.ndarray] = {}

    factories = {
        "kmeans": lambda k: KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10),
        "agglomerative": lambda k: AgglomerativeClustering(n_clusters=k),
        "gmm": lambda k: GaussianMixture(n_components=k, random_state=RANDOM_STATE),
    }
    for algo_name, factory in factories.items():
        for k in CLUSTER_K_RANGE:
            if k >= X.shape[0]:
                continue
            labels = factory(k).fit_predict(X)
            key = f"{algo_name}|k={k}"
            labels_store[key] = labels
            metrics = _eval_metrics(X, labels)
            rows.append(
                {
                    "algoritmo": algo_name,
                    "parametros": f"k={k}",
                    "n_clusters": len(set(labels)),
                    "n_noise": 0,
                    **(metrics or {"silhouette": np.nan, "davies_bouldin": np.nan, "calinski_harabasz": np.nan}),
                }
            )

    # DBSCAN: eps derivado de percentiles de la distancia al k-esimo vecino (heuristica
    # de codo estandar), min_samples en dos valores.
    for min_samples in DBSCAN_MIN_SAMPLES:
        if min_samples >= X.shape[0]:
            continue
        nn = NearestNeighbors(n_neighbors=min_samples).fit(X)
        distances, _ = nn.kneighbors(X)
        kth_dist = distances[:, -1]
        seen_eps = set()
        for pct in DBSCAN_ECDF_PERCENTILES:
            eps = float(np.percentile(kth_dist, pct))
            eps_rounded = round(eps, 4)
            if eps <= 0 or eps_rounded in seen_eps:
                continue
            seen_eps.add(eps_rounded)
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
            key = f"dbscan|eps={eps:.3f}_min_samples={min_samples}_p{pct}"
            labels_store[key] = labels

            noise_mask = labels == -1
            n_noise = int(noise_mask.sum())
            core_labels = labels[~noise_mask]
            n_clusters = len(set(core_labels))
            if n_clusters >= 2 and (~noise_mask).sum() >= 2:
                metrics = _eval_metrics(X[~noise_mask], core_labels)
            else:
                metrics = None
            rows.append(
                {
                    "algoritmo": "dbscan",
                    "parametros": f"eps={eps:.3f}, min_samples={min_samples} (p{pct})",
                    "n_clusters": n_clusters,
                    "n_noise": n_noise,
                    **(metrics or {"silhouette": np.nan, "davies_bouldin": np.nan, "calinski_harabasz": np.nan}),
                }
            )

    metrics_df = pd.DataFrame(rows)
    return metrics_df, labels_store


def best_clustering(metrics_df: pd.DataFrame, labels_store: dict[str, np.ndarray]) -> tuple[pd.Series, np.ndarray] | None:
    valid = metrics_df.dropna(subset=["silhouette"])
    if valid.empty:
        return None
    best_row = valid.sort_values("silhouette", ascending=False).iloc[0]
    if best_row["algoritmo"] == "dbscan":
        eps_str = best_row["parametros"].split(",")[0].split("=")[1]
        min_samples_str = best_row["parametros"].split("min_samples=")[1].split(" ")[0]
        pct_str = best_row["parametros"].split("(p")[1].rstrip(")")
        key = f"dbscan|eps={float(eps_str):.3f}_min_samples={min_samples_str}_p{pct_str}"
    else:
        key = f"{best_row['algoritmo']}|{best_row['parametros']}"
    return best_row, labels_store[key]


# ---------------------------------------------------------------------------
# Orquestacion por (rama, kind)
# ---------------------------------------------------------------------------


def analyze_slice(rama_key: str, config: dict, kind: str) -> dict:
    output_dir = config["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(config["features_path"])

    cols = feature_columns(df, kind)
    X = prepare_matrix(df, cols)
    n_cows = df["cow_id"].nunique()
    color_cow = n_cows <= MAX_COWS_FOR_COLOR_PLOT

    prefix = f"{kind}"
    slice_summary: dict[str, object] = {
        "rama": rama_key,
        "kind": kind,
        "n_filas": int(len(df)),
        "n_variables": len(cols),
        "n_cows": int(n_cows),
        "umap_disponible": UMAP_AVAILABLE,
    }

    # --- PCA ---
    pca_coords, pca_obj = run_pca(X)
    make_scatter(pca_coords, df["dataset"], f"{config['titulo']} — PCA ({kind}) por dataset", output_dir / f"{prefix}_pca_por_dataset.png")
    make_scatter(pca_coords, df["system"], f"{config['titulo']} — PCA ({kind}) por system", output_dir / f"{prefix}_pca_por_system.png")
    if color_cow:
        make_scatter(pca_coords, df["cow_id"].astype(str), f"{config['titulo']} — PCA ({kind}) por cow_id", output_dir / f"{prefix}_pca_por_cow_id.png", categorical_cmap=True)
    loadings = pd.DataFrame(pca_obj.components_.T, index=cols, columns=["PC1_loading", "PC2_loading"])
    loadings.assign(abs_PC1=loadings["PC1_loading"].abs()).sort_values("abs_PC1", ascending=False).to_csv(
        output_dir / f"{prefix}_pca_loadings.csv"
    )
    slice_summary["pca"] = {
        "explained_variance_ratio": [float(v) for v in pca_obj.explained_variance_ratio_],
        "top5_loadings_pc1": loadings.assign(a=loadings["PC1_loading"].abs()).sort_values("a", ascending=False).head(5)["PC1_loading"].to_dict(),
    }

    # --- t-SNE ---
    tsne_grid = run_tsne_grid(X, TSNE_PERPLEXITIES)
    make_grid_scatter(
        tsne_grid, "embedding", lambda p: f"perplexity={p} (KL={tsne_grid[p]['kl_divergence']:.2f})",
        df["system"], f"{config['titulo']} — t-SNE ({kind}) por perplexity, coloreado por system",
        output_dir / f"{prefix}_tsne_grid_por_system.png", ncols=2,
    )
    main_perplexity = TSNE_MAIN_PERPLEXITY if TSNE_MAIN_PERPLEXITY in tsne_grid else max(tsne_grid.keys())
    tsne_main_coords = tsne_grid[main_perplexity]["embedding"]
    make_scatter(tsne_main_coords, df["dataset"], f"{config['titulo']} — t-SNE ({kind}, perplexity={main_perplexity}) por dataset", output_dir / f"{prefix}_tsne_por_dataset.png")
    make_scatter(tsne_main_coords, df["system"], f"{config['titulo']} — t-SNE ({kind}, perplexity={main_perplexity}) por system", output_dir / f"{prefix}_tsne_por_system.png")
    if color_cow:
        make_scatter(tsne_main_coords, df["cow_id"].astype(str), f"{config['titulo']} — t-SNE ({kind}, perplexity={main_perplexity}) por cow_id", output_dir / f"{prefix}_tsne_por_cow_id.png", categorical_cmap=True)
    slice_summary["tsne"] = {
        "perplexities_probadas": list(tsne_grid.keys()),
        "kl_divergence_por_perplexity": {p: v["kl_divergence"] for p, v in tsne_grid.items()},
        "perplexity_usada_en_graficas_principales": main_perplexity,
    }

    # --- UMAP ---
    umap_grid = run_umap_grid(X, UMAP_N_NEIGHBORS, UMAP_MIN_DIST)
    umap_main_coords = None
    if umap_grid:
        make_grid_scatter(
            umap_grid, "embedding", lambda key: f"n_neighbors={key[0]}, min_dist={key[1]}",
            df["system"], f"{config['titulo']} — UMAP ({kind}) por combinacion, coloreado por system",
            output_dir / f"{prefix}_umap_grid_por_system.png", ncols=3,
        )
        main_key = (UMAP_MAIN_PARAMS["n_neighbors"], UMAP_MAIN_PARAMS["min_dist"])
        if main_key not in umap_grid:
            main_key = list(umap_grid.keys())[0]
        umap_main_coords = umap_grid[main_key]["embedding"]
        make_scatter(umap_main_coords, df["dataset"], f"{config['titulo']} — UMAP ({kind}, n_neighbors={main_key[0]}, min_dist={main_key[1]}) por dataset", output_dir / f"{prefix}_umap_por_dataset.png")
        make_scatter(umap_main_coords, df["system"], f"{config['titulo']} — UMAP ({kind}, n_neighbors={main_key[0]}, min_dist={main_key[1]}) por system", output_dir / f"{prefix}_umap_por_system.png")
        if color_cow:
            make_scatter(umap_main_coords, df["cow_id"].astype(str), f"{config['titulo']} — UMAP ({kind}) por cow_id", output_dir / f"{prefix}_umap_por_cow_id.png", categorical_cmap=True)
        slice_summary["umap"] = {"combinaciones_probadas": [list(k) for k in umap_grid.keys()], "combinacion_usada_en_graficas_principales": list(main_key)}
    else:
        slice_summary["umap"] = {"nota": "umap-learn no esta instalado en el entorno de ejecucion; instalar con 'pip install umap-learn' y volver a ejecutar para obtener esta parte."}

    # --- Clustering sobre 3 espacios ---
    spaces = {"original_escalado": X, "pca": pca_coords}
    if umap_main_coords is not None:
        spaces["umap"] = umap_main_coords

    clustering_summary = {}
    for space_name, space_X in spaces.items():
        metrics_df, labels_store = evaluate_clustering(space_X)
        metrics_path = output_dir / f"{prefix}_clustering_{space_name}_metricas.csv"
        metrics_df.to_csv(metrics_path, index=False)

        best = best_clustering(metrics_df, labels_store)
        if best is None:
            clustering_summary[space_name] = {"nota": "ninguna combinacion produjo >=2 clusters validos"}
            continue
        best_row, labels = best

        df_labels = df[["dataset", "system", "cow_id"]].copy()
        df_labels["cluster"] = labels
        ct_dataset = pd.crosstab(df_labels["cluster"], df_labels["dataset"])
        ct_system = pd.crosstab(df_labels["cluster"], df_labels["system"])
        ct_dataset.to_csv(output_dir / f"{prefix}_clustering_{space_name}_contingencia_dataset.csv")
        ct_system.to_csv(output_dir / f"{prefix}_clustering_{space_name}_contingencia_system.csv")

        def _dominant(s: pd.Series) -> pd.Series:
            counts = s.value_counts(normalize=True)
            return pd.Series({"cluster_dominante": counts.idxmax(), "pureza": counts.max(), "n_semanas": len(s)})

        per_cow = df_labels.groupby("cow_id")["cluster"].apply(_dominant).unstack()
        per_cow.to_csv(output_dir / f"{prefix}_clustering_{space_name}_por_vaca.csv")
        cow_purity = per_cow["pureza"].mean()

        # visualizar siempre sobre PCA(2D) para que las 3 espacios sean comparables visualmente
        fig, ax = plt.subplots(figsize=(8, 6))
        plot_labels = labels
        codes = plot_labels
        scatter = ax.scatter(pca_coords[:, 0], pca_coords[:, 1], c=codes, cmap="tab10", s=12, alpha=0.65)
        legend1 = ax.legend(*scatter.legend_elements(), title="cluster", fontsize=8)
        ax.add_artist(legend1)
        ax.set_title(
            f"{config['titulo']} — clustering en espacio '{space_name}' ({kind}): "
            f"{best_row['algoritmo']} {best_row['parametros']} (proyectado en PCA 2D)", fontsize=9,
        )
        plt.tight_layout()
        plt.savefig(output_dir / f"{prefix}_clustering_{space_name}_scatter.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

        clustering_summary[space_name] = {
            "mejor_algoritmo": best_row["algoritmo"],
            "mejores_parametros": best_row["parametros"],
            "n_clusters": int(best_row["n_clusters"]),
            "n_noise": int(best_row["n_noise"]),
            "silhouette": float(best_row["silhouette"]),
            "davies_bouldin": float(best_row["davies_bouldin"]),
            "calinski_harabasz": float(best_row["calinski_harabasz"]),
            "pureza_media_por_vaca": float(cow_purity),
            "contingencia_dataset": ct_dataset.to_dict(),
            "contingencia_system": ct_system.to_dict(),
        }

    slice_summary["clustering"] = clustering_summary

    print(
        f"[{rama_key}/{kind}] filas={len(df)} vars={len(cols)} | "
        f"PCA var.expl={sum(slice_summary['pca']['explained_variance_ratio']):.3f} | "
        f"UMAP={'si' if umap_grid else 'no'} | "
        + " | ".join(
            f"{sp}: sil={info.get('silhouette', float('nan')):.3f}" if "silhouette" in info else f"{sp}: sin resultado"
            for sp, info in clustering_summary.items()
        )
    )

    partial_path = output_dir / f"_partial_{kind}.json"
    with partial_path.open("w", encoding="utf-8") as f:
        json.dump(slice_summary, f, ensure_ascii=False, indent=2, default=str)

    return slice_summary


# ---------------------------------------------------------------------------
# Informe Markdown consolidado
# ---------------------------------------------------------------------------


def _is_degenerate_dbscan(cinfo: dict, n_filas: int) -> bool:
    if cinfo.get("mejor_algoritmo") != "dbscan":
        return False
    n_clusters = cinfo.get("n_clusters", 0)
    n_noise = cinfo.get("n_noise", 0)
    noise_fraction = n_noise / n_filas if n_filas else 0
    return n_clusters > DBSCAN_MAX_CLUSTERS_INTERPRETABLE or noise_fraction > DBSCAN_MAX_NOISE_FRACTION_INTERPRETABLE


def _relation_heuristic(contingency: dict, label: str) -> tuple[str, float]:
    """Heuristica de correspondencia cluster-metadato a partir de una tabla de
    contingencia (cluster x metadato). Devuelve una frase descriptiva y la
    proporcion minima observada (usada como indicador cuantitativo de fuerza de
    la relacion). No se usa para entrenar nada, solo para interpretar a posteriori."""
    counts = pd.DataFrame(contingency).fillna(0)
    if counts.shape[1] <= 1:
        return (f"no evaluable: la particion analizada contiene un unico valor de `{label}`.", float("nan"))
    props = counts.div(counts.sum(axis=0), axis=1)
    max_props = props.max(axis=0)
    if (max_props > 0.85).all():
        return (f"correspondencia fuerte con `{label}` (>85% de cada categoria concentrado en un unico cluster).", float(max_props.min()))
    if (max_props > 0.65).all():
        return (
            f"correspondencia moderada con `{label}` (entre {max_props.min():.0%} y {max_props.max():.0%} "
            "de cada categoria en un unico cluster, con solape no despreciable).",
            float(max_props.min()),
        )
    return (f"sin correspondencia clara con `{label}` (particion distribuida entre clusters sin un patron dominante).", float(max_props.min()))


def _base_variable_names(loadings: dict) -> list[str]:
    """Extrae el nombre de variable de comportamiento (sin el sufijo estadistico
    _mean/_std/...) a partir de las columnas con mayor loading, preservando el
    orden de aparicion."""
    suffixes = ["_mean", "_std", "_min", "_max", "_median", "_p10", "_p90", "_iqr", "_cv"]
    seen: list[str] = []
    for col in loadings:
        base = col
        for suf in suffixes:
            if col.endswith(suf):
                base = col[: -len(suf)]
                break
        base = base.replace("ratio_", "")
        if base not in seen:
            seen.append(base)
    return seen


def _interpret_pca_loadings(pca_info: dict, kind: str) -> str:
    top = sorted(pca_info["top5_loadings_pc1"].items(), key=lambda kv: abs(kv[1]), reverse=True)
    base_vars = _base_variable_names(dict(top))
    variables_txt = ", ".join(f"`{v}`" for v in base_vars)
    signo = "positivo" if top[0][1] > 0 else "negativo"
    return (
        f"El primer componente principal esta dominado por estadisticos de las variables de "
        f"comportamiento {variables_txt}, con el mayor peso ({top[0][1]:+.2f}, signo {signo}) en "
        f"`{top[0][0]}`. Esto indica que la direccion de mayor varianza en el conjunto de "
        f"variables `{kind}` esta asociada principalmente a diferencias en el tiempo/intensidad "
        f"de estos comportamientos entre registros, mas que a las demas variables incluidas en el "
        "analisis, que contribuyen en menor medida a PC1."
    )


def write_report(rama_key: str, config: dict) -> None:
    output_dir = config["output_dir"]
    partials = {}
    for kind in KINDS:
        path = output_dir / f"_partial_{kind}.json"
        if not path.exists():
            print(f"Aviso: no se encontro {path}; ejecutar antes 'python codigo/reduccion_clustering_avanzado.py --rama {rama_key} --kind {kind}'.")
            continue
        with path.open(encoding="utf-8") as f:
            partials[kind] = json.load(f)

    if not partials:
        return

    any_umap = any(partials[k].get("umap_disponible") for k in partials)

    lines = [f"# Reduccion dimensional avanzada y clustering comparativo — {config['titulo']}", ""]
    lines.append(
        "Este informe se genera automaticamente a partir de `codigo/reduccion_clustering_avanzado.py` "
        "y documenta la fase de reduccion dimensional no lineal (t-SNE, UMAP) y clustering comparativo "
        "que amplia el analisis de componentes principales (PCA) descrito en "
        f"`informe_{rama_key}.md`."
    )
    lines.append("")
    lines.append(
        "**Alcance metodologico.** PCA, t-SNE y UMAP se aplican de forma no supervisada: en ningun "
        "caso se utiliza la etiqueta `system` (ni `dataset` ni `cow_id`) como variable de entrada. "
        "Estos metadatos se emplean unicamente a posteriori, para colorear las proyecciones e "
        "interpretar los resultados. PCA se mantiene como tecnica de referencia por ser la unica que "
        "ofrece loadings directamente interpretables; t-SNE y UMAP se presentan como visualizaciones "
        "complementarias de la estructura local de los datos, no como evidencia definitiva de "
        "separacion entre sistemas de produccion: ambas tecnicas distorsionan las distancias "
        "globales y su resultado depende de los hiperparametros elegidos, por lo que se documentan "
        "varias configuraciones en lugar de una unica proyeccion seleccionada a posteriori."
    )
    lines.append("")
    lines.append(
        "Tecnicas de reduccion evaluadas: PCA; t-SNE con perplexity "
        f"{TSNE_PERPLEXITIES} (learning_rate='auto', random_state fijo); UMAP con n_neighbors "
        f"{UMAP_N_NEIGHBORS} y min_dist {UMAP_MIN_DIST} (random_state fijo)"
        + ("." if any_umap else "; **no disponible en esta ejecucion** (ver seccion de limitaciones).")
    )
    lines.append(
        "Tecnicas de clustering evaluadas: K-Means, Agglomerative Clustering y Gaussian Mixture "
        f"(k=2..6), y DBSCAN (eps derivado de los percentiles {DBSCAN_ECDF_PERCENTILES} de la "
        f"distancia al k-esimo vecino, min_samples {DBSCAN_MIN_SAMPLES}), sobre tres espacios: "
        "variables originales estandarizadas, proyeccion PCA (2D) y proyeccion UMAP (2D)."
    )
    lines.append("")
    lines.append(
        "**Criterio de presentacion de resultados.** Por cada conjunto de variables se distingue "
        "entre el resultado principal — clustering sobre la proyeccion PCA, por ser el espacio "
        "interpretable mediante loadings — y resultados exploratorios — clustering sobre el espacio "
        "original de alta dimension y sobre la proyeccion UMAP. Dentro de los resultados "
        "exploratorios, las configuraciones de DBSCAN que producen mas de "
        f"{DBSCAN_MAX_CLUSTERS_INTERPRETABLE} microclusters o mas de un "
        f"{DBSCAN_MAX_NOISE_FRACTION_INTERPRETABLE:.0%} de puntos marcados como ruido se reportan "
        "como exploratorias y se excluyen como candidatas a resultado principal, con independencia "
        "de su silhouette score."
    )
    lines.append("")

    for kind in KINDS:
        if kind not in partials:
            continue
        info = partials[kind]
        etiqueta_kind = "analisis de sensibilidad (ratios)" if kind == "ratios" else "conjunto de variables"
        lines.append(f"## {kind} — {info['n_variables']} variables, {info['n_filas']} filas ({etiqueta_kind})")
        lines.append("")

        lines.append("### Componentes principales (PCA)")
        pca_info = info["pca"]
        lines.append(
            f"Varianza explicada: PC1={pca_info['explained_variance_ratio'][0]:.1%}, "
            f"PC2={pca_info['explained_variance_ratio'][1]:.1%}."
        )
        lines.append("")
        lines.append(_interpret_pca_loadings(pca_info, kind))
        lines.append("")
        top = sorted(pca_info["top5_loadings_pc1"].items(), key=lambda kv: abs(kv[1]), reverse=True)
        lines.append("Variables con mayor peso en PC1: " + ", ".join(f"`{k}` ({v:+.2f})" for k, v in top) + ".")
        lines.append("")
        lines.append(f"![PCA por dataset]({kind}_pca_por_dataset.png)")
        lines.append("")
        lines.append(f"![PCA por system]({kind}_pca_por_system.png)")
        lines.append("")

        lines.append("### t-SNE (visualizacion complementaria)")
        tsne_info = info["tsne"]
        lines.append(
            f"Perplexities evaluadas: {tsne_info['perplexities_probadas']}. Divergencia KL final por "
            f"perplexity: {', '.join(f'{p}={kl:.2f}' for p, kl in tsne_info['kl_divergence_por_perplexity'].items())}. "
            "Un valor de KL mas bajo indica un mejor ajuste de esa proyeccion concreta a las distancias "
            "locales originales, pero no es comparable de forma absoluta entre perplexities distintas ni "
            "constituye una medida de calidad de clustering."
        )
        lines.append(f"Grafica comparativa de las {len(tsne_info['perplexities_probadas'])} perplexities: `{kind}_tsne_grid_por_system.png`.")
        lines.append(f"Grafica principal (perplexity={tsne_info['perplexity_usada_en_graficas_principales']}): `{kind}_tsne_por_dataset.png`, `{kind}_tsne_por_system.png`.")
        lines.append("")

        lines.append("### UMAP (visualizacion complementaria)")
        umap_info = info["umap"]
        if "nota" in umap_info:
            lines.append(umap_info["nota"])
        else:
            lines.append(f"Combinaciones evaluadas (n_neighbors, min_dist): {umap_info['combinaciones_probadas']}.")
            lines.append(f"Grafica comparativa de las {len(umap_info['combinaciones_probadas'])} combinaciones: `{kind}_umap_grid_por_system.png`.")
            main_combo = tuple(umap_info["combinacion_usada_en_graficas_principales"])
            lines.append(f"Grafica principal (n_neighbors={main_combo[0]}, min_dist={main_combo[1]}): `{kind}_umap_por_dataset.png`, `{kind}_umap_por_system.png`.")
        lines.append("")

        # --- Resultado principal: clustering en espacio PCA ---
        lines.append("### Resultado principal: clustering sobre la proyeccion PCA")
        lines.append("")
        pca_cluster = info["clustering"].get("pca")
        if pca_cluster is None or "nota" in pca_cluster:
            lines.append("No se obtuvo una particion valida (menos de dos clusters) en este espacio.")
        else:
            lines.append(
                f"Mejor configuracion segun silhouette: **{pca_cluster['mejor_algoritmo']}** "
                f"({pca_cluster['mejores_parametros']}). silhouette={pca_cluster['silhouette']:.3f}, "
                f"Davies-Bouldin={pca_cluster['davies_bouldin']:.3f}, "
                f"Calinski-Harabasz={pca_cluster['calinski_harabasz']:.1f}, "
                f"n_clusters={pca_cluster['n_clusters']}, pureza media por vaca={pca_cluster['pureza_media_por_vaca']:.1%}."
            )
            rel_system, _ = _relation_heuristic(pca_cluster["contingencia_system"], "system")
            rel_dataset, _ = _relation_heuristic(pca_cluster["contingencia_dataset"], "dataset")
            lines.append(f"Relacion con `system`: {rel_system}")
            lines.append(f"Relacion con `dataset`: {rel_dataset}")
            lines.append(f"Figura: `{kind}_clustering_pca_scatter.png`. Asignacion por vaca: `{kind}_clustering_pca_por_vaca.csv`.")
        lines.append("")

        # --- Resultados exploratorios: espacio original y UMAP ---
        lines.append("### Resultados exploratorios: espacio original de variables y proyeccion UMAP")
        lines.append("")
        lines.append(
            "| Espacio | Algoritmo | Parametros | n_clusters | n_noise | silhouette | Davies-Bouldin | "
            "Calinski-Harabasz | Pureza media/vaca | Observacion |"
        )
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---|")
        for space_name in ["original_escalado", "umap"]:
            cinfo = info["clustering"].get(space_name)
            if cinfo is None:
                lines.append(f"| {space_name} | - | sin resultados (UMAP no disponible en esta ejecucion) | - | - | - | - | - | - | - |")
                continue
            if "nota" in cinfo:
                lines.append(f"| {space_name} | - | {cinfo['nota']} | - | - | - | - | - | - | - |")
                continue
            observacion = ""
            if _is_degenerate_dbscan(cinfo, info["n_filas"]):
                observacion = (
                    "excluido como resultado principal: DBSCAN genera un numero elevado de microclusters "
                    "o una fraccion de ruido por encima del umbral de interpretabilidad; se reporta unicamente "
                    "con fines exploratorios."
                )
            lines.append(
                f"| {space_name} | {cinfo['mejor_algoritmo']} | {cinfo['mejores_parametros']} | "
                f"{cinfo['n_clusters']} | {cinfo['n_noise']} | {cinfo['silhouette']:.3f} | "
                f"{cinfo['davies_bouldin']:.3f} | {cinfo['calinski_harabasz']:.1f} | "
                f"{cinfo['pureza_media_por_vaca']:.1%} | {observacion} |"
            )
        lines.append("")
        lines.append(
            "Las metricas completas para todas las combinaciones de algoritmo/parametros evaluadas en "
            f"cada espacio se encuentran en `{kind}_clustering_<espacio>_metricas.csv`."
        )
        lines.append("")

    lines.append("## Limitaciones de interpretacion")
    lines.append("")
    lines.append(
        "- t-SNE y UMAP no preservan distancias globales entre grupos; la distancia visual entre "
        "clusters en estas proyecciones no debe interpretarse como una medida de disimilitud."
    )
    lines.append(
        "- El resultado de t-SNE y UMAP depende de la semilla aleatoria y de los hiperparametros "
        "empleados; el barrido de valores utilizado es representativo pero no exhaustivo."
    )
    lines.append(
        "- El parametro `eps` de DBSCAN se deriva de percentiles de la distancia al k-esimo vecino "
        "(heuristica de codo) y no de una busqueda exhaustiva; las configuraciones con muy pocos puntos "
        "no clasificados como ruido se descartan de la evaluacion de silhouette/Davies-Bouldin/"
        "Calinski-Harabasz."
    )
    lines.append(
        "- La pureza por vaca puede resultar elevada como consecuencia de la autocorrelacion temporal "
        "entre semanas consecutivas de una misma vaca, y no necesariamente refleja un patron "
        "biologico independiente de esa autocorrelacion; no se ha aplicado ninguna correccion por "
        "esta dependencia."
    )
    if not any_umap:
        lines.append(
            "- **UMAP no se ejecuto en esta version del informe** por no encontrarse instalada la "
            "libreria `umap-learn` en el entorno de ejecucion utilizado. La dependencia esta declarada "
            "en `requirements.txt`; al instalarla y volver a ejecutar "
            "`codigo/reduccion_clustering_avanzado.py`, la seccion de UMAP se completa automaticamente "
            "sin necesidad de modificar el codigo."
        )
    lines.append("")

    out_path = output_dir / f"informe_reduccion_avanzada_{rama_key}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Informe guardado: {out_path}")


# ---------------------------------------------------------------------------
# Resumen global de configuraciones interpretables (ambas ramas)
# ---------------------------------------------------------------------------


def write_global_summary() -> None:
    rows = []
    loadings_sections = []

    for rama_key, config in RAMAS.items():
        output_dir = config["output_dir"]
        for kind in KINDS:
            path = output_dir / f"_partial_{kind}.json"
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as f:
                info = json.load(f)

            pca_cluster = info["clustering"].get("pca")
            if pca_cluster is None or "nota" in pca_cluster:
                continue

            rel_system, prop_system = _relation_heuristic(pca_cluster["contingencia_system"], "system")
            rel_dataset, prop_dataset = _relation_heuristic(pca_cluster["contingencia_dataset"], "dataset")

            if "no evaluable" in rel_system:
                interpretacion = "sistema constante en esta rama; la particion no puede contrastarse frente a system."
            elif prop_system > 0.85:
                interpretacion = "particion consistente con el sistema de produccion (intensivo/extensivo)."
            elif prop_system > 0.65:
                interpretacion = "particion parcialmente consistente con el sistema de produccion, con solape entre clusters."
            else:
                interpretacion = "particion no atribuible de forma clara al sistema de produccion."

            rows.append(
                {
                    "rama": rama_key,
                    "tipo_variables": kind,
                    "espacio": "PCA (2D)",
                    "algoritmo": f"{pca_cluster['mejor_algoritmo']} ({pca_cluster['mejores_parametros']})",
                    "n_clusters": pca_cluster["n_clusters"],
                    "silhouette": round(pca_cluster["silhouette"], 3),
                    "davies_bouldin": round(pca_cluster["davies_bouldin"], 3),
                    "calinski_harabasz": round(pca_cluster["calinski_harabasz"], 1),
                    "relacion_con_system": rel_system,
                    "relacion_con_dataset": rel_dataset,
                    "interpretacion_breve": interpretacion,
                }
            )

            loadings_sections.append(
                f"### {config['titulo']} — {kind}\n\n" + _interpret_pca_loadings(info["pca"], kind) + "\n"
            )

    if not rows:
        print("Aviso: no hay resultados PCA disponibles para construir el resumen global.")
        return

    summary_df = pd.DataFrame(rows)
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(RESULTADOS_DIR / "resumen_configuraciones_interpretables.csv", index=False)

    lines = [
        "# Resumen de resultados principales — reduccion dimensional y clustering",
        "",
        "Este documento consolida, para ambas ramas de analisis y los tres conjuntos de variables "
        "evaluados, la configuracion de clustering considerada como resultado principal: la mejor "
        "particion (segun silhouette score) obtenida sobre la proyeccion PCA de dos componentes. "
        "Se elige la proyeccion PCA como espacio de referencia por ser interpretable mediante "
        "loadings; los resultados obtenidos sobre el espacio original de variables y sobre la "
        "proyeccion UMAP se documentan como exploratorios en los informes de cada rama "
        "(`informe_reduccion_avanzada_<rama>.md`) y no se incluyen en esta tabla.",
        "",
        "## Tabla resumen",
        "",
    ]
    try:
        lines.append(summary_df.to_markdown(index=False))
    except ImportError:
        lines.append(summary_df.to_csv(index=False))
    lines.append("")
    lines.append(
        "Nota metodologica: la columna `tipo_variables=ratios` corresponde a un analisis de "
        "sensibilidad respecto a las variables absolutas, no a un resultado principal independiente: "
        "al excluir la escala absoluta de las variables, evalua si la separacion observada se "
        "mantiene cuando solo se consideran proporciones de tiempo entre comportamientos."
    )
    lines.append("")

    lines.append("## Interpretacion de los loadings principales de PCA")
    lines.append("")
    lines.append(
        "Se resume a continuacion que variables originales impulsan el primer componente principal "
        "en cada conjunto de variables, con especial atencion a la Rama B (comparacion intensivo vs. "
        "extensivo), donde este componente esta asociado a la separacion entre Valdillera y las "
        "granjas intensivas."
    )
    lines.append("")
    lines.extend(loadings_sections)

    lines.append("## Limitaciones generales")
    lines.append("")
    lines.append(
        "- Los resultados de la Rama B se basan en una unica explotacion extensiva (Valdillera); la "
        "correspondencia observada entre clusters y `system` no debe generalizarse a otras "
        "explotaciones extensivas sin datos adicionales, dado que dataset y system estan parcialmente "
        "confundidos en esta rama (un unico dataset representa el sistema extensivo)."
    )
    lines.append(
        "- t-SNE y UMAP se documentan en los informes por rama como visualizaciones complementarias; "
        "ninguna configuracion de estas dos tecnicas se incluye en esta tabla de resultados principales."
    )
    lines.append("")

    out_path = RESULTADOS_DIR / "resumen_resultados_principales.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Resumen global guardado en: {out_path}")
    print(f"Tabla CSV guardada en: {RESULTADOS_DIR / 'resumen_configuraciones_interpretables.csv'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Reduccion dimensional avanzada (PCA/t-SNE/UMAP) y clustering comparativo")
    parser.add_argument("--rama", choices=list(RAMAS.keys()) + ["all"], default="all")
    parser.add_argument("--kind", choices=KINDS + ["all"], default="all")
    parser.add_argument("--mode", choices=["run", "report"], default="run", help="'run' calcula, 'report' solo consolida el Markdown a partir de los JSON parciales ya generados")
    args = parser.parse_args()

    rama_keys = list(RAMAS.keys()) if args.rama == "all" else [args.rama]
    kind_list = KINDS if args.kind == "all" else [args.kind]

    if args.mode == "run":
        if not UMAP_AVAILABLE:
            print("Aviso: umap-learn no esta instalado en este entorno; se omite UMAP para las porciones calculadas en esta ejecucion.")
        for rama_key in rama_keys:
            config = RAMAS[rama_key]
            for kind in kind_list:
                analyze_slice(rama_key, config, kind)

    for rama_key in rama_keys:
        write_report(rama_key, RAMAS[rama_key])

    if args.rama == "all":
        write_global_summary()


if __name__ == "__main__":
    main()

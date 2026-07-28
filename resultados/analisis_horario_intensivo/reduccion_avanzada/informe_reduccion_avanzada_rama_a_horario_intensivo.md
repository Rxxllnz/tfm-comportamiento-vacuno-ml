# Reduccion dimensional avanzada y clustering comparativo — Rama A: horario intensivo (Celso horario + Ruibal horario)

Este informe se genera automaticamente a partir de `codigo/reduccion_clustering_avanzado.py` y documenta la fase de reduccion dimensional no lineal (t-SNE, UMAP) y clustering comparativo que amplia el analisis de componentes principales (PCA) descrito en `informe_rama_a_horario_intensivo.md`.

**Alcance metodologico.** PCA, t-SNE y UMAP se aplican de forma no supervisada: en ningun caso se utiliza la etiqueta `system` (ni `dataset` ni `cow_id`) como variable de entrada. Estos metadatos se emplean unicamente a posteriori, para colorear las proyecciones e interpretar los resultados. PCA se mantiene como tecnica de referencia por ser la unica que ofrece loadings directamente interpretables; t-SNE y UMAP se presentan como visualizaciones complementarias de la estructura local de los datos, no como evidencia definitiva de separacion entre sistemas de produccion: ambas tecnicas distorsionan las distancias globales y su resultado depende de los hiperparametros elegidos, por lo que se documentan varias configuraciones en lugar de una unica proyeccion seleccionada a posteriori.

Tecnicas de reduccion evaluadas: PCA; t-SNE con perplexity [5, 10, 30, 50] (learning_rate='auto', random_state fijo); UMAP con n_neighbors [10, 15, 30, 50] y min_dist [0.0, 0.1, 0.5] (random_state fijo).
Tecnicas de clustering evaluadas: K-Means, Agglomerative Clustering y Gaussian Mixture (k=2..6), y DBSCAN (eps derivado de los percentiles [50, 75, 90] de la distancia al k-esimo vecino, min_samples [5, 10]), sobre tres espacios: variables originales estandarizadas, proyeccion PCA (2D) y proyeccion UMAP (2D).

**Criterio de presentacion de resultados.** Por cada conjunto de variables se distingue entre el resultado principal — clustering sobre la proyeccion PCA, por ser el espacio interpretable mediante loadings — y resultados exploratorios — clustering sobre el espacio original de alta dimension y sobre la proyeccion UMAP. Dentro de los resultados exploratorios, las configuraciones de DBSCAN que producen mas de 10 microclusters o mas de un 15% de puntos marcados como ruido se reportan como exploratorias y se excluyen como candidatas a resultado principal, con independencia de su silhouette score.

## absolutas_completas — 54 variables, 7402 filas (conjunto de variables)

### Componentes principales (PCA)
Varianza explicada: PC1=19.5%, PC2=18.7%.

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `steps`, `ruminate`, `walk`, con el mayor peso (+0.25, signo positivo) en `steps_mean`. Esto indica que la direccion de mayor varianza en el conjunto de variables `absolutas_completas` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

Variables con mayor peso en PC1: `steps_mean` (+0.25), `ruminate_mean` (-0.25), `steps_p90` (+0.25), `ruminate_median` (-0.24), `walk_mean` (+0.24).

![PCA por dataset](absolutas_completas_pca_por_dataset.png)

![PCA por system](absolutas_completas_pca_por_system.png)

### t-SNE (visualizacion complementaria)
Perplexities evaluadas: [5, 10, 30, 50]. Divergencia KL final por perplexity: 5=1.97, 10=2.04, 30=2.00, 50=1.91. Un valor de KL mas bajo indica un mejor ajuste de esa proyeccion concreta a las distancias locales originales, pero no es comparable de forma absoluta entre perplexities distintas ni constituye una medida de calidad de clustering.
Grafica comparativa de las 4 perplexities: `absolutas_completas_tsne_grid_por_system.png`.
Grafica principal (perplexity=30): `absolutas_completas_tsne_por_dataset.png`, `absolutas_completas_tsne_por_system.png`.

### UMAP (visualizacion complementaria)
Combinaciones evaluadas (n_neighbors, min_dist): [[10, 0.0], [10, 0.1], [10, 0.5], [15, 0.0], [15, 0.1], [15, 0.5], [30, 0.0], [30, 0.1], [30, 0.5], [50, 0.0], [50, 0.1], [50, 0.5]].
Grafica comparativa de las 12 combinaciones: `absolutas_completas_umap_grid_por_system.png`.
Grafica principal (n_neighbors=15, min_dist=0.1): `absolutas_completas_umap_por_dataset.png`, `absolutas_completas_umap_por_system.png`.

### Resultado principal: clustering sobre la proyeccion PCA

Mejor configuracion segun silhouette: **gmm** (k=2). silhouette=0.487, Davies-Bouldin=1.128, Calinski-Harabasz=2787.1, n_clusters=2, pureza media por vaca=89.7%.
Relacion con `system`: no evaluable: la particion analizada contiene un unico valor de `system`.
Relacion con `dataset`: correspondencia moderada con `dataset` (entre 84% y 91% de cada categoria en un unico cluster, con solape no despreciable).
Figura: `absolutas_completas_clustering_pca_scatter.png`. Asignacion por vaca: `absolutas_completas_clustering_pca_por_vaca.csv`.

### Resultados exploratorios: espacio original de variables y proyeccion UMAP

| Espacio | Algoritmo | Parametros | n_clusters | n_noise | silhouette | Davies-Bouldin | Calinski-Harabasz | Pureza media/vaca | Observacion |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| original_escalado | gmm | k=2 | 2 | 0 | 0.310 | 2.384 | 705.7 | 89.0% |  |
| umap | dbscan | eps=0.086, min_samples=5 (p50) | 336 | 2255 | 0.434 | 0.583 | 9310.1 | 38.8% | excluido como resultado principal: DBSCAN genera un numero elevado de microclusters o una fraccion de ruido por encima del umbral de interpretabilidad; se reporta unicamente con fines exploratorios. |

Las metricas completas para todas las combinaciones de algoritmo/parametros evaluadas en cada espacio se encuentran en `absolutas_completas_clustering_<espacio>_metricas.csv`.

## ratios — 5 variables, 7402 filas (analisis de sensibilidad (ratios))

### Componentes principales (PCA)
Varianza explicada: PC1=38.6%, PC2=30.3%.

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `rest`, `ruminate`, `eat`, `graze`, `walk`, con el mayor peso (+0.64, signo positivo) en `ratio_rest`. Esto indica que la direccion de mayor varianza en el conjunto de variables `ratios` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

Variables con mayor peso en PC1: `ratio_rest` (+0.64), `ratio_ruminate` (-0.57), `ratio_eat` (-0.46), `ratio_graze` (+0.19), `ratio_walk` (+0.08).

![PCA por dataset](ratios_pca_por_dataset.png)

![PCA por system](ratios_pca_por_system.png)

### t-SNE (visualizacion complementaria)
Perplexities evaluadas: [5, 10, 30, 50]. Divergencia KL final por perplexity: 5=1.42, 10=1.44, 30=1.43, 50=1.38. Un valor de KL mas bajo indica un mejor ajuste de esa proyeccion concreta a las distancias locales originales, pero no es comparable de forma absoluta entre perplexities distintas ni constituye una medida de calidad de clustering.
Grafica comparativa de las 4 perplexities: `ratios_tsne_grid_por_system.png`.
Grafica principal (perplexity=30): `ratios_tsne_por_dataset.png`, `ratios_tsne_por_system.png`.

### UMAP (visualizacion complementaria)
Combinaciones evaluadas (n_neighbors, min_dist): [[10, 0.0], [10, 0.1], [10, 0.5], [15, 0.0], [15, 0.1], [15, 0.5], [30, 0.0], [30, 0.1], [30, 0.5], [50, 0.0], [50, 0.1], [50, 0.5]].
Grafica comparativa de las 12 combinaciones: `ratios_umap_grid_por_system.png`.
Grafica principal (n_neighbors=15, min_dist=0.1): `ratios_umap_por_dataset.png`, `ratios_umap_por_system.png`.

### Resultado principal: clustering sobre la proyeccion PCA

Mejor configuracion segun silhouette: **gmm** (k=3). silhouette=0.373, Davies-Bouldin=0.920, Calinski-Harabasz=3859.4, n_clusters=3, pureza media por vaca=79.9%.
Relacion con `system`: no evaluable: la particion analizada contiene un unico valor de `system`.
Relacion con `dataset`: sin correspondencia clara con `dataset` (particion distribuida entre clusters sin un patron dominante).
Figura: `ratios_clustering_pca_scatter.png`. Asignacion por vaca: `ratios_clustering_pca_por_vaca.csv`.

### Resultados exploratorios: espacio original de variables y proyeccion UMAP

| Espacio | Algoritmo | Parametros | n_clusters | n_noise | silhouette | Davies-Bouldin | Calinski-Harabasz | Pureza media/vaca | Observacion |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| original_escalado | dbscan | eps=0.701, min_samples=10 (p90) | 3 | 369 | 0.316 | 0.527 | 287.7 | 93.6% |  |
| umap | dbscan | eps=0.103, min_samples=5 (p50) | 375 | 2294 | 0.483 | 0.560 | 14076.6 | 34.6% | excluido como resultado principal: DBSCAN genera un numero elevado de microclusters o una fraccion de ruido por encima del umbral de interpretabilidad; se reporta unicamente con fines exploratorios. |

Las metricas completas para todas las combinaciones de algoritmo/parametros evaluadas en cada espacio se encuentran en `ratios_clustering_<espacio>_metricas.csv`.

## absolutas_sin_steps — 45 variables, 7402 filas (conjunto de variables)

### Componentes principales (PCA)
Varianza explicada: PC1=22.3%, PC2=19.3%.

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `rest`, `ruminate`, con el mayor peso (+0.28, signo positivo) en `rest_mean`. Esto indica que la direccion de mayor varianza en el conjunto de variables `absolutas_sin_steps` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

Variables con mayor peso en PC1: `rest_mean` (+0.28), `rest_median` (+0.27), `rest_p90` (+0.26), `ruminate_mean` (-0.24), `ruminate_median` (-0.23).

![PCA por dataset](absolutas_sin_steps_pca_por_dataset.png)

![PCA por system](absolutas_sin_steps_pca_por_system.png)

### t-SNE (visualizacion complementaria)
Perplexities evaluadas: [5, 10, 30, 50]. Divergencia KL final por perplexity: 5=2.03, 10=2.10, 30=2.05, 50=1.95. Un valor de KL mas bajo indica un mejor ajuste de esa proyeccion concreta a las distancias locales originales, pero no es comparable de forma absoluta entre perplexities distintas ni constituye una medida de calidad de clustering.
Grafica comparativa de las 4 perplexities: `absolutas_sin_steps_tsne_grid_por_system.png`.
Grafica principal (perplexity=30): `absolutas_sin_steps_tsne_por_dataset.png`, `absolutas_sin_steps_tsne_por_system.png`.

### UMAP (visualizacion complementaria)
Combinaciones evaluadas (n_neighbors, min_dist): [[10, 0.0], [10, 0.1], [10, 0.5], [15, 0.0], [15, 0.1], [15, 0.5], [30, 0.0], [30, 0.1], [30, 0.5], [50, 0.0], [50, 0.1], [50, 0.5]].
Grafica comparativa de las 12 combinaciones: `absolutas_sin_steps_umap_grid_por_system.png`.
Grafica principal (n_neighbors=15, min_dist=0.1): `absolutas_sin_steps_umap_por_dataset.png`, `absolutas_sin_steps_umap_por_system.png`.

### Resultado principal: clustering sobre la proyeccion PCA

Mejor configuracion segun silhouette: **gmm** (k=3). silhouette=0.379, Davies-Bouldin=0.983, Calinski-Harabasz=3201.6, n_clusters=3, pureza media por vaca=82.4%.
Relacion con `system`: no evaluable: la particion analizada contiene un unico valor de `system`.
Relacion con `dataset`: sin correspondencia clara con `dataset` (particion distribuida entre clusters sin un patron dominante).
Figura: `absolutas_sin_steps_clustering_pca_scatter.png`. Asignacion por vaca: `absolutas_sin_steps_clustering_pca_por_vaca.csv`.

### Resultados exploratorios: espacio original de variables y proyeccion UMAP

| Espacio | Algoritmo | Parametros | n_clusters | n_noise | silhouette | Davies-Bouldin | Calinski-Harabasz | Pureza media/vaca | Observacion |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| original_escalado | dbscan | eps=3.955, min_samples=10 (p90) | 2 | 359 | 0.479 | 0.637 | 93.3 | 93.6% |  |
| umap | kmeans | k=3 | 3 | 0 | 0.412 | 0.850 | 6302.0 | 78.8% |  |

Las metricas completas para todas las combinaciones de algoritmo/parametros evaluadas en cada espacio se encuentran en `absolutas_sin_steps_clustering_<espacio>_metricas.csv`.

## Limitaciones de interpretacion

- t-SNE y UMAP no preservan distancias globales entre grupos; la distancia visual entre clusters en estas proyecciones no debe interpretarse como una medida de disimilitud.
- El resultado de t-SNE y UMAP depende de la semilla aleatoria y de los hiperparametros empleados; el barrido de valores utilizado es representativo pero no exhaustivo.
- El parametro `eps` de DBSCAN se deriva de percentiles de la distancia al k-esimo vecino (heuristica de codo) y no de una busqueda exhaustiva; las configuraciones con muy pocos puntos no clasificados como ruido se descartan de la evaluacion de silhouette/Davies-Bouldin/Calinski-Harabasz.
- La pureza por vaca puede resultar elevada como consecuencia de la autocorrelacion temporal entre semanas consecutivas de una misma vaca, y no necesariamente refleja un patron biologico independiente de esa autocorrelacion; no se ha aplicado ninguna correccion por esta dependencia.

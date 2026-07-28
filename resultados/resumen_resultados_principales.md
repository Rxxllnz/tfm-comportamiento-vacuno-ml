# Resumen de resultados principales — reduccion dimensional y clustering

Este documento consolida, para ambas ramas de analisis y los tres conjuntos de variables evaluados, la configuracion de clustering considerada como resultado principal: la mejor particion (segun silhouette score) obtenida sobre la proyeccion PCA de dos componentes. Se elige la proyeccion PCA como espacio de referencia por ser interpretable mediante loadings; los resultados obtenidos sobre el espacio original de variables y sobre la proyeccion UMAP se documentan como exploratorios en los informes de cada rama (`informe_reduccion_avanzada_<rama>.md`) y no se incluyen en esta tabla.

## Tabla resumen

| rama                     | tipo_variables      | espacio   | algoritmo           |   n_clusters |   silhouette |   davies_bouldin |   calinski_harabasz | relacion_con_system                                                                                                         | relacion_con_dataset                                                                                                         | interpretacion_breve                                                                        |
|:-------------------------|:--------------------|:----------|:--------------------|-------------:|-------------:|-----------------:|--------------------:|:----------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------|
| rama_a_horario_intensivo | absolutas_completas | PCA (2D)  | gmm (k=2)           |            2 |        0.487 |            1.128 |              2787.1 | no evaluable: la particion analizada contiene un unico valor de `system`.                                                   | correspondencia moderada con `dataset` (entre 84% y 91% de cada categoria en un unico cluster, con solape no despreciable).  | sistema constante en esta rama; la particion no puede contrastarse frente a system.         |
| rama_a_horario_intensivo | ratios              | PCA (2D)  | gmm (k=3)           |            3 |        0.373 |            0.92  |              3859.4 | no evaluable: la particion analizada contiene un unico valor de `system`.                                                   | sin correspondencia clara con `dataset` (particion distribuida entre clusters sin un patron dominante).                      | sistema constante en esta rama; la particion no puede contrastarse frente a system.         |
| rama_a_horario_intensivo | absolutas_sin_steps | PCA (2D)  | gmm (k=3)           |            3 |        0.379 |            0.983 |              3201.6 | no evaluable: la particion analizada contiene un unico valor de `system`.                                                   | sin correspondencia clara con `dataset` (particion distribuida entre clusters sin un patron dominante).                      | sistema constante en esta rama; la particion no puede contrastarse frente a system.         |
| rama_b_diario_sistemas   | absolutas_completas | PCA (2D)  | gmm (k=2)           |            2 |        0.515 |            1.016 |              2417.5 | correspondencia fuerte con `system` (>85% de cada categoria concentrado en un unico cluster).                               | correspondencia fuerte con `dataset` (>85% de cada categoria concentrado en un unico cluster).                               | particion consistente con el sistema de produccion (intensivo/extensivo).                   |
| rama_b_diario_sistemas   | ratios              | PCA (2D)  | kmeans (k=2)        |            2 |        0.44  |            1.013 |              2094.4 | correspondencia fuerte con `system` (>85% de cada categoria concentrado en un unico cluster).                               | sin correspondencia clara con `dataset` (particion distribuida entre clusters sin un patron dominante).                      | particion consistente con el sistema de produccion (intensivo/extensivo).                   |
| rama_b_diario_sistemas   | absolutas_sin_steps | PCA (2D)  | agglomerative (k=2) |            2 |        0.602 |            0.622 |              2190.3 | correspondencia moderada con `system` (entre 79% y 100% de cada categoria en un unico cluster, con solape no despreciable). | correspondencia moderada con `dataset` (entre 79% y 100% de cada categoria en un unico cluster, con solape no despreciable). | particion parcialmente consistente con el sistema de produccion, con solape entre clusters. |

Nota metodologica: la columna `tipo_variables=ratios` corresponde a un analisis de sensibilidad respecto a las variables absolutas, no a un resultado principal independiente: al excluir la escala absoluta de las variables, evalua si la separacion observada se mantiene cuando solo se consideran proporciones de tiempo entre comportamientos.

## Interpretacion de los loadings principales de PCA

Se resume a continuacion que variables originales impulsan el primer componente principal en cada conjunto de variables, con especial atencion a la Rama B (comparacion intensivo vs. extensivo), donde este componente esta asociado a la separacion entre Valdillera y las granjas intensivas.

### Rama A: horario intensivo (Celso horario + Ruibal horario) — absolutas_completas

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `steps`, `ruminate`, `walk`, con el mayor peso (+0.25, signo positivo) en `steps_mean`. Esto indica que la direccion de mayor varianza en el conjunto de variables `absolutas_completas` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

### Rama A: horario intensivo (Celso horario + Ruibal horario) — ratios

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `rest`, `ruminate`, `eat`, `graze`, `walk`, con el mayor peso (+0.64, signo positivo) en `ratio_rest`. Esto indica que la direccion de mayor varianza en el conjunto de variables `ratios` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

### Rama A: horario intensivo (Celso horario + Ruibal horario) — absolutas_sin_steps

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `rest`, `ruminate`, con el mayor peso (+0.28, signo positivo) en `rest_mean`. Esto indica que la direccion de mayor varianza en el conjunto de variables `absolutas_sin_steps` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

### Rama B: diario intensivo vs extensivo (Celso diario + Ruibal diario + Valdillera x24) — absolutas_completas

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `walk`, `steps`, con el mayor peso (+0.21, signo positivo) en `walk_mean`. Esto indica que la direccion de mayor varianza en el conjunto de variables `absolutas_completas` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

### Rama B: diario intensivo vs extensivo (Celso diario + Ruibal diario + Valdillera x24) — ratios

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `graze`, `eat`, `walk`, `ruminate`, `rest`, con el mayor peso (+0.58, signo positivo) en `ratio_graze`. Esto indica que la direccion de mayor varianza en el conjunto de variables `ratios` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

### Rama B: diario intensivo vs extensivo (Celso diario + Ruibal diario + Valdillera x24) — absolutas_sin_steps

El primer componente principal esta dominado por estadisticos de las variables de comportamiento `graze`, con el mayor peso (+0.23, signo positivo) en `graze_max`. Esto indica que la direccion de mayor varianza en el conjunto de variables `absolutas_sin_steps` esta asociada principalmente a diferencias en el tiempo/intensidad de estos comportamientos entre registros, mas que a las demas variables incluidas en el analisis, que contribuyen en menor medida a PC1.

## Limitaciones generales

- Los resultados de la Rama B se basan en una unica explotacion extensiva (Valdillera); la correspondencia observada entre clusters y `system` no debe generalizarse a otras explotaciones extensivas sin datos adicionales, dado que dataset y system estan parcialmente confundidos en esta rama (un unico dataset representa el sistema extensivo).
- t-SNE y UMAP se documentan en los informes por rama como visualizaciones complementarias; ninguna configuracion de estas dos tecnicas se incluye en esta tabla de resultados principales.

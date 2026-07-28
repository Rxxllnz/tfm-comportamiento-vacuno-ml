# Análisis comparativo del comportamiento del ganado vacuno en sistemas intensivos y extensivos mediante técnicas de aprendizaje automático

Repositorio del Trabajo Fin de Máster dedicado al análisis comparativo de patrones de actividad del ganado vacuno a partir de datos registrados mediante collares de monitorización. El estudio utiliza técnicas de reducción dimensional y agrupamiento no supervisado para explorar diferencias entre explotaciones intensivas y extensivas.

## 1. Objetivo

El proyecto desarrolla un flujo reproducible para:

1. integrar datos de actividad procedentes de distintas explotaciones;
2. auditar y homogeneizar su resolución temporal;
3. extraer características semanales por animal;
4. aplicar PCA, t-SNE y UMAP;
5. evaluar K-Means, Agglomerative Clustering, Gaussian Mixture Models y DBSCAN;
6. interpretar a posteriori la relación de los grupos obtenidos con la explotación, el sistema productivo y el animal.

El enfoque principal es **no supervisado**. Las columnas `system`, `dataset`, `cow_id`, `window_start`, `resolution`, `scale_type`, `n_records`, `n_missing`, `anomaly_count` y `anomaly_rate` se conservan como metadatos o variables auxiliares, pero no se utilizan como entrada de PCA ni de los algoritmos de clustering.

## 2. Estructura del repositorio

```text
Procesados/                         Datos originales de Celso y Ruibal
codigo/                             Scripts Python del pipeline
  common.py                         Constantes y rutas compartidas
  preprocesado_base.py              Limpieza y normalización de un fichero
  auditoria_resolucion.py           Auditoría de escala y verificación de Celso
  generar_diarios.py                Ruibal diario y Valdillera diario equivalente
  extraer_features_ramas.py         Features semanales de las ramas A y B
  pca_ramas.py                      PCA base por rama
  clustering_ramas.py               Clustering base por rama
  generar_informes_ramas.py         Informes base en Markdown
  reduccion_clustering_avanzado.py  PCA, t-SNE, UMAP y clustering comparativo
  informe_valdillera.py             Informe auxiliar de actividad y eventos
  extraccion_metricas.py            Funciones de extracción de características
  crear_tabla_maestra.py            Consolidación histórica de features
  exploracion_referencias.py        Inspección auxiliar de ficheros de origen
  comparacion_sistemas.py           Comparación exploratoria legacy

datos/
  entrada/valdillera/               Actividad y eventos originales de Valdillera
  procesados/                       Intermedios, diarios generados y features

Procesados/                         Copias limpias de los ficheros originales de Celso y Ruibal
documentos/                         Artículos de referencia.
experimentos/                       Notebooks de la fase exploratoria
resultados/                         Informes, tablas, JSON y figuras
requirements.txt                    Dependencias Python
.gitignore                          Exclusiones para control de versiones
```

### 2.1. Componentes finales

Los resultados utilizados para las conclusiones se generan mediante:

- `codigo/auditoria_resolucion.py`
- `codigo/generar_diarios.py`
- `codigo/extraer_features_ramas.py`
- `codigo/pca_ramas.py`
- `codigo/clustering_ramas.py`
- `codigo/generar_informes_ramas.py`
- `codigo/reduccion_clustering_avanzado.py`

Los scripts `preprocesado_base.py`, `informe_valdillera.py` y `extraccion_metricas.py` son utilidades de apoyo. `crear_tabla_maestra.py` conserva la tabla maestra de la fase inicial, pero las conclusiones finales se basan en las tablas específicas de las ramas A y B.

### 2.2. Componentes exploratorios o legacy

Los siguientes elementos se conservan como registro de la evolución del trabajo, pero no deben utilizarse como base de las conclusiones finales:

- `codigo/comparacion_sistemas.py`
- `experimentos/exploracion_inicial.ipynb`
- `experimentos/semana2_eda_pca.ipynb`
- `experimentos/comparacion_sistemas.ipynb`
- `resultados/legacy/hallazgos_semana2.md`
- `resultados/legacy/comparacion/`
- `resultados/legacy/eda/`
- `datos/procesados/features/master_features.csv` y los CSV individuales anteriores a las ramas
- `resultados/master_features_report.json`

La fase exploratoria combinó datos antes de corregir la escala de Valdillera. Sus resultados se mantienen únicamente con fines históricos.

## 3. Datos de origen

| Explotación | Sistema | Fichero | Resolución verificada |
|---|---|---|---|
| Celso | Intensivo | `Procesados/Celso novo/05_original_variables.csv` | Diaria nativa |
| Celso | Intensivo | `Procesados/Celso novo/04_Vacas_etiquetadas_horario.xlsx` | Horaria nativa |
| Ruibal | Intensivo | `Procesados/Ruibal Riomayor/05_Datos_horarios_etiquetados_celo.csv` | Horaria nativa |
| Valdillera | Extensivo | `datos/entrada/valdillera/00zz_Datos_valdillera_bruto_media_horario_2025-01-01_2026-01-01_20260701.csv` | Una fila por vaca y día, en escala de media horaria |

El fichero `datos/entrada/valdillera/Valdillera_Agropecuaria_events.csv` contiene eventos `HEAT`, `ANOMALY` y `BIRTH`. Los eventos disponibles abarcan 2021-05-13–2024-09-22, mientras que la actividad de Valdillera abarca 2025-12-01–2026-01-01. Por tanto, no existe solape temporal entre ambas fuentes.

Los datos originales se incluyen en este paquete para permitir la reproducción académica. Antes de publicar el repositorio de forma abierta debe comprobarse que existe autorización para redistribuir los datos suministrados por terceros.

## 4. Auditoría de resolución temporal

La auditoría automática se basa en dos indicadores por vaca y día:

- número de registros;
- suma de las cinco variables de actividad: `Ruminate`, `Eat`, `Graze`, `Rest` y `Walk`.

Los resultados principales son:

- Celso horario y Ruibal horario presentan aproximadamente 24 registros por vaca y día;
- Celso diario presenta una fila por vaca y día y una suma próxima a 1440 minutos;
- Valdillera presenta una fila por vaca y día, pero la suma de las actividades es aproximadamente 59,5, compatible con minutos medios por hora;
- Celso diario coincide con la agregación diaria de Celso horario en los 3755 pares vaca-día comparables. Las diferencias son nulas en la unidad original de las seis variables comprobadas: cinco duraciones y `Steps`.

Informes:

- `resultados/auditoria/informe_auditoria_resolucion.md`
- `resultados/auditoria/auditoria_resolucion.json`
- `resultados/hallazgos_resolucion_temporal.md`

## 5. Corrección de Valdillera

Valdillera no contiene lecturas horarias individuales. El fichero presenta una única fila por vaca y día y valores de actividad en escala de media horaria. Para situarlo en el mismo orden de magnitud que los diarios de Celso y Ruibal se genera `datos/procesados/valdillera_diario_equivalente/valdillera_diario_equivalente.csv`, multiplicando por 24 las cinco variables de actividad.

**La transformación no recupera datos horarios.** Únicamente convierte la escala de media horaria en una magnitud diaria equivalente.

`Steps` también se multiplica por 24, aunque su unidad original no ha podido confirmarse independientemente. Por este motivo se incluye un análisis de sensibilidad con todas las variables `steps_*` excluidas.

Dado que los eventos no solapan temporalmente con la actividad, `anomaly_count` y `anomaly_rate` se mantienen como valores faltantes para Valdillera y se excluyen de los modelos.

## 6. Generación de Ruibal diario

Ruibal no dispone de un fichero diario nativo. `codigo/generar_diarios.py` suma sus registros horarios por `Cow_id` y día calendario para producir:

```text
datos/procesados/ruibal_diario/ruibal_diario.csv
```

La suma media de las cinco actividades es aproximadamente 1415,9 minutos por día, coherente con la escala de Celso diario y Valdillera diario equivalente.

## 7. Ramas de análisis

### Rama A: horario intensivo

Incluye Celso horario y Ruibal horario. No incluye Valdillera, porque no se dispone de datos horarios reales de la explotación extensiva. Esta rama estudia la estructura interna, la variabilidad individual y las diferencias entre las dos explotaciones intensivas.

Features:

```text
datos/procesados/features/rama_a_horario_intensivo_weekly_features.csv
```

Resultados:

```text
resultados/analisis_horario_intensivo/
```

### Rama B: diario intensivo frente a extensivo

Incluye Celso diario, Ruibal diario generado y Valdillera diario equivalente. Es la rama principal para la comparación entre sistemas productivos.

Features:

```text
datos/procesados/features/rama_b_diario_sistemas_weekly_features.csv
```

Resultados:

```text
resultados/analisis_diario_sistemas/
```

## 8. Características y modelos

Las series se dividen en ventanas semanales. Para cada actividad se calculan media, desviación típica, mínimo, máximo, mediana, percentiles 10 y 90, rango intercuartílico y coeficiente de variación. También se calculan cinco ratios de comportamiento.

Se evalúan tres conjuntos de variables:

1. `absolutas_completas`: 54 variables, incluidos los estadísticos de `Steps`;
2. `ratios`: cinco proporciones de comportamiento;
3. `absolutas_sin_steps`: 45 variables, sin estadísticos de `Steps`.

Reducción dimensional:

- PCA como técnica principal, porque permite interpretar los loadings;
- t-SNE y UMAP como visualizaciones complementarias no lineales.

Clustering:

- K-Means;
- Agglomerative Clustering;
- Gaussian Mixture Models;
- DBSCAN.

Métricas internas:

- silhouette score;
- índice de Davies-Bouldin;
- índice de Calinski-Harabasz.

Las tablas de contingencia frente a `system`, `dataset` y `cow_id` se calculan después del ajuste y se utilizan únicamente para interpretar las particiones obtenidas.

## 9. Instalación

Se recomienda Python 3.10 o posterior. En PowerShell, desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Dependencias directas:

- pandas y NumPy;
- Matplotlib;
- openpyxl;
- scikit-learn;
- tabulate;
- umap-learn.

La ejecución actual incluye resultados UMAP. Si `umap-learn` no está disponible en otro entorno, el script avanzado omite esa fase e informa de ello sin interrumpir PCA, t-SNE ni el resto del clustering.

## 10. Ejecución desde cero

Todos los comandos siguientes deben ejecutarse desde la raíz del repositorio.

### 10.1. Comprobar los cinco ficheros imprescindibles

PowerShell:

```powershell
Test-Path ".\Procesados\Celso novo\05_original_variables.csv"
Test-Path ".\Procesados\Celso novo\04_Vacas_etiquetadas_horario.xlsx"
Test-Path ".\Procesados\Ruibal Riomayor\05_Datos_horarios_etiquetados_celo.csv"
Test-Path ".\datos\entrada\valdillera\00zz_Datos_valdillera_bruto_media_horario_2025-01-01_2026-01-01_20260701.csv"
Test-Path ".\datos\entrada\valdillera\Valdillera_Agropecuaria_events.csv"
```

Los cinco comandos deben devolver `True`.

### 10.2. Generar copias limpias intermedias

```powershell
python .\codigo\preprocesado_base.py ".\Procesados\Celso novo\05_original_variables.csv" ".\datos\procesados\celso_diario"
python .\codigo\preprocesado_base.py ".\Procesados\Celso novo\04_Vacas_etiquetadas_horario.xlsx" ".\datos\procesados\celso_horario"
python .\codigo\preprocesado_base.py ".\Procesados\Ruibal Riomayor\05_Datos_horarios_etiquetados_celo.csv" ".\datos\procesados\ruibal_horario"
python .\codigo\preprocesado_base.py ".\datos\entrada\valdillera\00zz_Datos_valdillera_bruto_media_horario_2025-01-01_2026-01-01_20260701.csv" ".\datos\procesados\valdillera_diario_raw"
```

Estas copias permiten inspeccionar la limpieza de cada fuente. Los scripts principales de auditoría y extracción leen los ficheros originales mediante rutas relativas, por lo que las copias limpias son salidas documentales intermedias y no una dependencia oculta del análisis final.

### 10.3. Auditoría y generación de diarios

```powershell
python .\codigo\auditoria_resolucion.py
python .\codigo\generar_diarios.py
python .\codigo\informe_valdillera.py
```

### 10.4. Extracción de features por rama

```powershell
python .\codigo\extraer_features_ramas.py
```

### 10.5. PCA, clustering base e informes

```powershell
python .\codigo\pca_ramas.py
python .\codigo\clustering_ramas.py
python .\codigo\generar_informes_ramas.py
```

### 10.6. Reducción y clustering avanzados

Ejecución completa:

```powershell
python .\codigo\reduccion_clustering_avanzado.py --rama all --kind all
python .\codigo\reduccion_clustering_avanzado.py --rama all --mode report
```

La primera orden recalcula PCA, t-SNE, UMAP y clustering en las seis combinaciones de rama y conjunto de variables. Puede tardar varios minutos. La segunda consolida los informes y el resumen global a partir de los JSON parciales generados.

Ejecución por partes:

```powershell
python .\codigo\reduccion_clustering_avanzado.py --rama rama_a_horario_intensivo --kind absolutas_completas
python .\codigo\reduccion_clustering_avanzado.py --rama rama_a_horario_intensivo --kind ratios
python .\codigo\reduccion_clustering_avanzado.py --rama rama_a_horario_intensivo --kind absolutas_sin_steps
python .\codigo\reduccion_clustering_avanzado.py --rama rama_b_diario_sistemas --kind absolutas_completas
python .\codigo\reduccion_clustering_avanzado.py --rama rama_b_diario_sistemas --kind ratios
python .\codigo\reduccion_clustering_avanzado.py --rama rama_b_diario_sistemas --kind absolutas_sin_steps
python .\codigo\reduccion_clustering_avanzado.py --rama all --mode report
```

### 10.7. Recalcular solo los análisis finales desde las features incluidas

Cuando las dos tablas de features por rama ya existen, no es necesario repetir la lectura de los datos originales:

```powershell
python .\codigo\pca_ramas.py
python .\codigo\clustering_ramas.py
python .\codigo\generar_informes_ramas.py
python .\codigo\reduccion_clustering_avanzado.py --rama all --kind all
python .\codigo\reduccion_clustering_avanzado.py --rama all --mode report
```

### 10.8. Salidas principales esperadas

```text
resultados/auditoria/informe_auditoria_resolucion.md
resultados/pca_resumen.json
resultados/pca_resumen.md
resultados/clustering_resumen.json
resultados/analisis_horario_intensivo/informe_rama_a_horario_intensivo.md
resultados/analisis_diario_sistemas/informe_rama_b_diario_sistemas.md
resultados/analisis_horario_intensivo/reduccion_avanzada/informe_reduccion_avanzada_rama_a_horario_intensivo.md
resultados/analisis_diario_sistemas/reduccion_avanzada/informe_reduccion_avanzada_rama_b_diario_sistemas.md
resultados/resumen_resultados_principales.md
resultados/resumen_configuraciones_interpretables.csv
```

## 11. Resultados verificados

### 11.1. PCA base

| Rama | Variables | Varianza PC1+PC2 | eta²(`system`, PC1) | eta²(`dataset`, PC1) |
|---|---|---:|---:|---:|
| A, horario intensivo | Absolutas | 0,382 | 0,000 | 0,007 |
| A, horario intensivo | Ratios | 0,689 | 0,000 | 0,029 |
| B, diario por sistemas | Absolutas | 0,498 | 0,549 | 0,563 |
| B, diario por sistemas | Ratios | 0,743 | 0,483 | 0,524 |

En la Rama A, `system` es constante porque ambas explotaciones son intensivas. En la Rama B existe una asociación importante de PC1 tanto con el sistema como con el dataset. La similitud entre ambas eta² impide atribuir la separación exclusivamente al sistema productivo.

### 11.2. Clustering base en el espacio original estandarizado

| Rama | Variables | Mejor algoritmo | Silhouette | Davies-Bouldin | Calinski-Harabasz |
|---|---|---|---:|---:|---:|
| A | Absolutas | GMM, k=2 | 0,310 | 2,384 | 705,7 |
| A | Ratios | GMM, k=2 | 0,297 | 1,888 | 1258,0 |
| B | Absolutas | Agglomerative, k=2 | 0,439 | 1,180 | 879,1 |
| B | Ratios | Agglomerative, k=2 | 0,540 | 0,736 | 1178,8 |

La Rama B presenta una estructura más definida que la Rama A. En el clustering base con variables absolutas, 278 de las 310 ventanas de Valdillera se asignan a un cluster que contiene una sola ventana intensiva.

### 11.3. Clustering principal sobre PCA

Se considera principal el clustering sobre PCA de dos componentes, porque permite relacionar la partición con loadings interpretables. El resumen completo está en `resultados/resumen_resultados_principales.md`.

Resultados destacados de la Rama B:

- absolutas completas, PCA + GMM (`k=2`): silhouette 0,515; más del 85 % de cada sistema se concentra en su cluster mayoritario;
- ratios, PCA + K-Means (`k=2`): silhouette 0,440; más del 85 % de cada sistema se concentra en su cluster mayoritario;
- absolutas sin `Steps`, PCA + Agglomerative (`k=2`): silhouette **0,602**, Davies-Bouldin 0,622 y Calinski-Harabasz 2190,3.

La configuración sin `Steps` es el mejor resultado interpretable de la Rama B. El cluster asociado mayoritariamente al sistema extensivo contiene 245 de las 310 ventanas de Valdillera y solo seis ventanas intensivas. El cluster mayoritariamente intensivo contiene 3398 de las 3404 ventanas intensivas. Esto muestra que la estructura observada se mantiene sin depender de la variable cuya escala presenta mayor incertidumbre.

### 11.4. Variables que impulsan PC1

- Rama B, absolutas completas: predominan `walk_*` y `steps_*`;
- Rama B, ratios: predominan `ratio_graze`, `ratio_eat` y `ratio_walk`;
- Rama B, absolutas sin `Steps`: predominan los estadísticos de `graze`, especialmente `graze_max`.

Los signos de los loadings dependen de la orientación arbitraria de cada componente. La interpretación debe centrarse en la magnitud relativa y en la combinación de variables, no en considerar un signo positivo como biológicamente favorable o desfavorable.

### 11.5. Resultados exploratorios

- t-SNE y UMAP se utilizan como visualizaciones complementarias;
- el clustering sobre el espacio original de alta dimensión y sobre UMAP se mantiene como análisis exploratorio;
- las configuraciones DBSCAN que generan más de diez clusters o más de un 15 % de ruido se excluyen como candidatas a resultado principal, aunque su silhouette sea elevada.

## 12. Interpretación y alcance

Los análisis no supervisados encuentran una estructura diferenciada entre las ventanas diarias de Valdillera y las de Celso y Ruibal. Sin embargo, no se ha entrenado un clasificador supervisado y las métricas de clustering no equivalen a una accuracy de clasificación.

Además, Valdillera es la única explotación extensiva. Por tanto, el resultado demuestra una separación entre **la explotación extensiva disponible y las dos explotaciones intensivas analizadas**, pero no permite concluir que el mismo patrón vaya a generalizarse a cualquier granja extensiva.

## 13. Limitaciones

- una única explotación extensiva;
- confusión parcial entre `dataset` y `system`;
- Valdillera diario equivalente se obtiene mediante una hipótesis de escala ×24;
- unidad de `Steps` en Valdillera no confirmada independientemente;
- ausencia de datos horarios reales de Valdillera;
- eventos de Valdillera sin solape con el periodo de actividad;
- Ruibal diario generado desde datos horarios y no proporcionado como diario nativo;
- autocorrelación entre ventanas consecutivas del mismo animal;
- sensibilidad de t-SNE, UMAP y DBSCAN a los hiperparámetros.

## 14. Trabajos futuros

1. incorporar más explotaciones extensivas;
2. obtener los registros históricos de eventos que solapen con la actividad de Valdillera;
3. validar la unidad de `Steps` con documentación del proveedor;
4. añadir características temporales, circadianas, de transición o complejidad;
5. evaluar clasificación supervisada como extensión exploratoria, con validación agrupada por animal y, cuando sea posible, por explotación;
6. realizar validación externa sobre granjas no utilizadas durante el desarrollo.

La clasificación supervisada no constituye una fase pendiente necesaria para que el pipeline no supervisado actual sea válido; se plantea como posible ampliación y requeriría datos adicionales para evaluar generalización entre explotaciones.

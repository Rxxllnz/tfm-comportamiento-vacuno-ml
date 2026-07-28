# Auditoría y corrección de la resolución temporal de los datasets

## 1. Resumen

Se identificó que el pipeline inicial combinaba, bajo la etiqueta común de "features
semanales", datos de tres escalas temporales distintas sin homogeneizar. La Tabla 1 resume
la resolución real de cada dataset de origen, determinada mediante auditoría automática
(`codigo/auditoria_resolucion.py`) a partir de dos indicadores objetivos: número de registros
por vaca y día, y suma diaria de las cinco variables de actividad (rumia, alimentación,
pastoreo, reposo y desplazamiento).

**Tabla 1.** Resolución temporal real frente a la resolución indicada por el nombre del fichero.

| Dataset | Nombre del fichero de origen | Resolución declarada | Resolución verificada | Evidencia |
|---|---|---|---|---|
| Celso diario | `05_original_variables.csv` | diaria | diaria (confirmada) | 1 fila/vaca/día; suma de las 5 variables ≈1415 min/día |
| Celso horario | `04_Vacas_etiquetadas_horario.xlsx` | horaria | horaria (confirmada) | ~24 filas/vaca/día; suma ≈1412 min/día |
| Ruibal horario | `05_Datos_horarios_etiquetados_celo.csv` | horaria | horaria (confirmada) | ~24 filas/vaca/día; suma ≈1416 min/día |
| Valdillera | `00zz_..._bruto_media_horario_...csv` | horaria ("bruto_media_horario") | **diaria, en escala de media horaria** | 1 fila/vaca/día; suma de las 5 variables ≈59.5 (≈60, minutos en una hora) |

El nombre del fichero de origen de Valdillera ("bruto_**media**_horario") es consistente con
esta conclusión: no se trata de lecturas horarias individuales, sino de una media horaria ya
agregada a un valor por vaca y día. El error metodológico del pipeline inicial no residía en
el cálculo, sino en la interpretación de la unidad de medida: dicha media (rango 0–60) se
trataba como directamente comparable con el total diario (rango 0–1440) del resto de granjas,
y adicionalmente el dataset quedaba excluido de la agrupación por resolución al filtrarse por
coincidencia de texto (`dataset.str.contains("horario")`).

## 2. Justificación metodológica

La inclusión de Valdillera sin corregir en el mismo análisis de PCA/clustering que Celso
diario y Ruibal diario introduciría un factor de confusión: cualquier separación observada
entre sistema intensivo y extensivo podría deberse a que los valores de Valdillera son
aproximadamente 24 veces menores que los del resto, y no a un patrón de comportamiento
distinto. Es decir, una diferencia de escala de medición podría confundirse con una diferencia
de sistema productivo, que constituye la pregunta de investigación central del TFM.

## 3. Corrección aplicada

1. **Auditoría automática** (`codigo/auditoria_resolucion.py`). Clasifica cada dataset de
   origen como horario, diario o diario en escala horaria a partir de los dos indicadores
   descritos en la sección 1, sin depender del nombre del fichero. Informe completo:
   `resultados/auditoria/informe_auditoria_resolucion.md`.

2. **Verificación de Celso.** Se comparó Celso diario nativo frente a Celso horario agregado a
   nivel diario, por vaca y día, para las seis variables (rumia, alimentación, pastoreo,
   reposo, desplazamiento y pasos). Se obtuvo una diferencia media de 0.00 en la unidad original de cada una de las seis
   variables sobre 3.755 pares vaca-día comparables, lo que confirma que Celso diario corresponde
   exactamente a la agregación de Celso horario y no requiere ningún reescalado.

3. **Generación de Ruibal diario** (`codigo/generar_diarios.py`). Al no existir un fichero
   diario nativo para esta granja, se generó por agregación (suma) de Ruibal horario, agrupado
   por vaca y día calendario. La suma media resultante de las cinco variables de actividad es
   ≈1415.9 min/día, consistente con Celso. Resultado almacenado en
   `datos/procesados/ruibal_diario/ruibal_diario.csv`.

4. **Corrección de Valdillera: generación del dataset diario equivalente.** Dado que las
   variables de actividad de Valdillera están expresadas en minutos medios por hora (suma
   ≈59.5 sobre un máximo de 60), se generó una versión escalada multiplicando por 24 las cinco
   variables de actividad y la variable Steps. Tras el escalado, la suma media de las cinco
   variables pasa de 59.5 a ≈1427.4 min/día, quedando en el mismo orden de magnitud que Celso
   (≈1415) y Ruibal (≈1416). Resultado almacenado en
   `datos/procesados/valdillera_diario_equivalente/valdillera_diario_equivalente.csv`.

   **Advertencia metodológica.** El dataset resultante se denomina "Valdillera diario
   equivalente" y no "Valdillera horario": la multiplicación por 24 no reconstruye lecturas
   horarias reales, únicamente convierte una media horaria agregada en una magnitud diaria
   comparable en escala con el resto de granjas. La transformación asume que la relación entre
   "minutos medios por hora" y "minutos totales del día" es lineal y constante a lo largo del
   día, supuesto que no puede verificarse directamente al no disponerse de las lecturas
   horarias originales.

   Respecto a la variable Steps, tras el escalado el valor medio de Valdillera es de ≈7259
   pasos/día, frente a ≈3048 (Celso) y ≈3521 (Ruibal). Un valor superior en el sistema
   extensivo es compatible con un mayor desplazamiento asociado al pastoreo, pero no existe
   forma de verificar esta hipótesis de manera independiente sin documentación técnica del
   proveedor del sensor; se documenta como una observación consistente con la corrección
   aplicada, no como una conclusión biológica confirmada.

5. **Tratamiento de `anomaly_count`/`anomaly_rate` en Valdillera.** Se evaluó la posibilidad de
   derivar estas variables a partir de `Valdillera_Agropecuaria_events.csv` (eventos de tipo
   HEAT/ANOMALY/BIRTH). Se constató que dicho fichero cubre el periodo 2021-05-13 a
   2024-09-22, mientras que los datos de actividad corresponden al periodo 2025-12-01 a
   2026-01-01: no existe solapamiento temporal entre ambas fuentes. En consecuencia,
   `anomaly_count` y `anomaly_rate` se establecen explícitamente como valores faltantes (NaN)
   para Valdillera en las features de la Rama B, en lugar de asignarles el valor cero. Esta
   decisión evita que la ausencia de datos de eventos se interprete como una confirmación de
   ausencia de anomalías. Ambas variables están excluidas como entrada de PCA y clustering
   (se consideran metadatos auxiliares), por lo que esta limitación no afecta a los resultados
   de reducción dimensional.

6. **Separación en dos ramas de análisis**, con el fin de no volver a combinar resoluciones
   temporales incompatibles:
   - **Rama A (horario intensivo):** Celso horario y Ruibal horario. No incluye Valdillera.
     Resultados en `resultados/analisis_horario_intensivo/`.
   - **Rama B (diario intensivo/extensivo):** Celso diario, Ruibal diario (generado) y
     Valdillera diario equivalente (×24). Resultados en `resultados/analisis_diario_sistemas/`.

## 4. Resultado tras la corrección

Los valores de esta sección corresponden al análisis base utilizado para verificar la corrección metodológica. La comparación avanzada y el mejor resultado interpretable final se documentan en `resultados/resumen_resultados_principales.md`.

Con las tres granjas expresadas en una escala común (minutos/día), el análisis de
componentes principales y el clustering de la Rama B muestran una separación asociada al
sistema productivo:

- PCA (variables absolutas): eta² (`system`, PC1) = 0.549 — el sistema productivo explica el
  55% de la varianza del primer componente principal.
- Clustering (Agglomerative, k=2, variables absolutas): silhouette = 0.439. La tabla de
  contingencia cluster×dataset asigna 278 de las 310 filas de Valdillera a un cluster
  compuesto en un 99.6% por registros de Valdillera (278 de 279 filas), frente a 3.403 filas
  de granjas intensivas concentradas mayoritariamente en el cluster restante. Detalle completo
  en `resultados/analisis_diario_sistemas/informe_rama_b_diario_sistemas.md`.

Esta interpretación no sería sostenible sobre los datos de Valdillera sin corregir: la
separación observada podría atribuirse trivialmente a que sus valores son del orden de 24
veces menores, sin relación con un patrón de comportamiento distinto.

**Advertencia metodológica adicional.** La Rama B incluye una única explotación extensiva
(Valdillera). En consecuencia, `dataset` y `system` están parcialmente confundidos: el
sistema extensivo está representado por un único dataset. La correspondencia observada entre
clusters y sistema productivo es consistente con la hipótesis de separación por sistema, pero
no permite descartar que responda, en todo o en parte, a características propias de esta
explotación en particular. Una conclusión generalizable a "sistemas extensivos" en sentido
amplio requeriría datos de más de una explotación extensiva.

## 5. Limitaciones documentadas

- La corrección de Valdillera (×24) asume una relación lineal y constante entre la media
  horaria agregada y el total diario; no se dispone de las lecturas horarias originales para
  verificar este supuesto de forma directa.
- El escalado de Steps en Valdillera es una decisión razonada pero no verificada de forma
  independiente (sección 3.4).
- El fichero de eventos de Valdillera no cubre el periodo de actividad analizado; un análisis
  de anomalías en esta granja requeriría un fichero de eventos correspondiente al periodo
  diciembre de 2025–enero de 2026.
- Ruibal diario es una agregación (suma) de Ruibal horario, no un dato diario nativo como
  Celso diario. Ambos son metodológicamente equivalentes tras la agregación, pero se
  distinguen en las features mediante el campo `scale_type` (`"agregado_desde_horario"` frente
  a `"nativo"`).
- Como se indica en la sección 4, la separación entre sistemas en la Rama B se apoya en una
  única explotación extensiva, lo que limita la generalización de la conclusión.

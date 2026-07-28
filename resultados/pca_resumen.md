# Resumen de PCA por rama

Este documento resume el analisis de componentes principales (PCA) de cada rama, con una medida cuantitativa (eta cuadrado) de que agrupacion — sistema productivo o dataset de origen — explica una mayor proporcion de la varianza del primer componente.

## Rama A: horario intensivo (Celso horario + Ruibal horario)

### Variables absolutas
Varianza explicada: PC1=0.195, PC2=0.187, acumulada=0.382 (sobre 54 variables de entrada).
eta² de `system` sobre PC1=0.000, sobre PC2=0.000 (proporcion de la varianza de ese componente asociada al sistema productivo).
eta² de `dataset` sobre PC1=0.007, sobre PC2=0.032 (proporcion de la varianza asociada al dataset de origen, que combina granja, resolucion temporal y escala).
**Interpretacion:** `system` es constante en esta rama (unico valor: 'intensivo'), por lo que su eta² resulta trivialmente nulo y no es comparable con el de `dataset`. El eta² de `dataset` sobre PC1 (0.007) es bajo, lo que indica un solapamiento considerable entre las dos granjas intensivas en este espacio de variables: la variabilidad individual/semanal predomina sobre la variabilidad entre granjas.

### Variables ratios
Varianza explicada: PC1=0.386, PC2=0.303, acumulada=0.689 (sobre 5 variables de entrada).
eta² de `system` sobre PC1=0.000, sobre PC2=0.000 (proporcion de la varianza de ese componente asociada al sistema productivo).
eta² de `dataset` sobre PC1=0.029, sobre PC2=0.045 (proporcion de la varianza asociada al dataset de origen, que combina granja, resolucion temporal y escala).
**Interpretacion:** `system` es constante en esta rama (unico valor: 'intensivo'), por lo que su eta² resulta trivialmente nulo y no es comparable con el de `dataset`. El eta² de `dataset` sobre PC1 (0.029) es bajo, lo que indica un solapamiento considerable entre las dos granjas intensivas en este espacio de variables: la variabilidad individual/semanal predomina sobre la variabilidad entre granjas.

## Rama B: diario intensivo vs extensivo (Celso diario + Ruibal diario + Valdillera x24)

### Variables absolutas
Varianza explicada: PC1=0.319, PC2=0.178, acumulada=0.498 (sobre 54 variables de entrada).
eta² de `system` sobre PC1=0.549, sobre PC2=0.019 (proporcion de la varianza de ese componente asociada al sistema productivo).
eta² de `dataset` sobre PC1=0.563, sobre PC2=0.067 (proporcion de la varianza asociada al dataset de origen, que combina granja, resolucion temporal y escala).
**Interpretacion:** Los valores de eta² de `system` y `dataset` son similares en PC1: este analisis no permite distinguir si la separacion se debe al sistema productivo o a diferencias especificas de cada granja o dataset, dado que ambas variables estan parcialmente confundidas (el dataset determina el sistema).

### Variables ratios
Varianza explicada: PC1=0.440, PC2=0.303, acumulada=0.743 (sobre 5 variables de entrada).
eta² de `system` sobre PC1=0.483, sobre PC2=0.068 (proporcion de la varianza de ese componente asociada al sistema productivo).
eta² de `dataset` sobre PC1=0.524, sobre PC2=0.106 (proporcion de la varianza asociada al dataset de origen, que combina granja, resolucion temporal y escala).
**Interpretacion:** Los valores de eta² de `system` y `dataset` son similares en PC1: este analisis no permite distinguir si la separacion se debe al sistema productivo o a diferencias especificas de cada granja o dataset, dado que ambas variables estan parcialmente confundidas (el dataset determina el sistema).

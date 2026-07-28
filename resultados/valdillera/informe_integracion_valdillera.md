# Informe de integracion de Valdillera

## Actividad

- Filas: 1674
- Columnas: 8
- Vacas: 62
- Inicio: 2025-12-01 00:00:00+00:00
- Fin: 2026-01-01 00:00:00+00:00
- Faltantes: 0

## Eventos

- Filas: 290
- Columnas: 4
- Vacas: 88
- Inicio: 2021-05-13 00:00:00
- Fin: 2024-09-22 00:00:00
- Distribucion de eventos: {'ANOMALY': 188, 'BIRTH': 95, 'HEAT': 7}

## Solape

- Vacas comunes entre actividad y eventos: 47
- Ejemplo de vacas comunes: ['ES000811746937', 'ES000813308428', 'ES000814089435', 'ES000815468623', 'ES010814027210', 'ES020810524951', 'ES020811311330', 'ES020812427128', 'ES020815468614', 'ES021009919114']
- Solape temporal entre actividad y eventos: False

La coincidencia de identificadores de vaca no implica que los eventos puedan utilizarse para
validar el periodo de actividad. En la version actual de los datos no existe solape temporal,
por lo que las etiquetas de evento no se incorporan como entrada a los modelos ni se interpretan
como confirmacion de ausencia de anomalias.

## Salidas generadas

- informe_integracion_valdillera.json
- resumen_eventos_por_vaca.csv

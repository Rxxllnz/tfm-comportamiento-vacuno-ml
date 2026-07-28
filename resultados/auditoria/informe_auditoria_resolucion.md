# Auditoria de resolucion temporal de los datasets de origen

Generado automaticamente por `codigo/auditoria_resolucion.py`. Clasifica cada dataset de origen como `horario` (varios registros/vaca/dia, tipicamente ~24), `diario` (1 registro/vaca/dia, suma de las 5 variables de actividad cercana a 1440 min/dia) o `diario_escala_horaria` (1 registro/vaca/dia, pero la suma de las 5 variables de actividad ronda 60, es decir, es una media por hora y no un total diario).

| Dataset | Fichero | Filas | Vacas | Registros/vaca/dia (mediana) | Suma 5 vars (media) | Clasificacion |
|---|---|---:|---:|---:|---:|---|
| `celso_diario` | `Procesados/Celso novo/05_original_variables.csv` | 3,755 | 16 | 1.00 | 1414.62 | **diario** |
| `celso_horario` | `Procesados/Celso novo/04_Vacas_etiquetadas_horario.xlsx` | 720,131 | 108 | 24.00 | 1412.31 | **horario** |
| `ruibal_horario` | `Procesados/Ruibal Riomayor/05_Datos_horarios_etiquetados_celo.csv` | 454,296 | 93 | 24.00 | 1415.91 | **horario** |
| `valdillera_bruto` | `datos/entrada/valdillera/00zz_Datos_valdillera_bruto_media_horario_2025-01-01_2026-01-01_20260701.csv` | 1,674 | 62 | 1.00 | 59.47 | **diario_escala_horaria** |

## Interpretacion por dataset

### `celso_diario`
- 1 registro por vaca y dia, suma de las 5 variables ~1415 min, cercana a 1440. **Es diario real** (ya viene agregado a nivel de dia).

### `celso_horario`
- Mediana de 24.0 registros por vaca y dia (coherente con ~24 lecturas horarias). Suma diaria de las 5 variables ~1412 min, cercana a 1440. **Es horario real.**

### `ruibal_horario`
- Mediana de 24.0 registros por vaca y dia (coherente con ~24 lecturas horarias). Suma diaria de las 5 variables ~1416 min, cercana a 1440. **Es horario real.**

### `valdillera_bruto`
- 1 registro por vaca y dia, pero la suma de las 5 variables es ~59.5, cercana a 60 (minutos en una hora), no a 1440. **No es horario real**: es una media por hora agregada a nivel diario. Para obtener un equivalente diario en minutos/dia comparable con el resto hay que multiplicar las variables de actividad por 24 (ver `hallazgos_resolucion_temporal.md`).

## Verificacion de Celso: diario nativo vs horario agregado a diario

Pares vaca-dia comparables (misma vaca y fecha presentes en ambos datasets): 3,755. Pares vaca-dia solo en el diario nativo: 0. Pares vaca-dia solo en el horario agregado: 26,250. Esta diferencia no debe interpretarse como dias naturales faltantes: los dos ficheros incluyen coberturas distintas de animales y periodos. La comparacion de valores se realiza exclusivamente sobre la interseccion de identificador de vaca y fecha.

| Variable | Diferencia media (unidad original) | Diferencia mediana (unidad original) | Diferencia maxima (unidad original) |
|---|---:|---:|---:|
| Ruminate | 0.00 | 0.00 | 0.00 |
| Eat | 0.00 | 0.00 | 0.00 |
| Graze | 0.00 | 0.00 | 0.00 |
| Rest | 0.00 | 0.00 | 0.00 |
| Walk | 0.00 | 0.00 | 0.00 |
| Steps | 0.00 | 0.00 | 0.00 |

**Conclusion:** las diferencias son despreciables (medias <= 1 unidad y maximos <= 5 unidades por variable y dia, en la unidad original de cada variable). Celso diario es coherente con la agregacion de Celso horario: las variables de actividad quedan expresadas en minutos/dia y `Steps` en conteos/dia, lo que confirma que Celso diario es un diario real y no requiere ningun reescalado.

# Análisis y correcciones — `limpieza_datos_etinverterxw.ipynb`

Este documento describe **los problemas detectados** en los datos del inversor XW
(`etinverterxw`) y **las soluciones implementadas en el notebook**: dónde están, por qué
se hicieron y cómo funcionan. No cubre otros notebooks ni otros temas.

---

## 0. Para qué sirven estos datos (contexto mínimo)

El inversor XW alimenta **solo dos** cálculos del proyecto, y ambos están hoy
bloqueados / en DEMO:

| Variables del inversor | Alimenta | Estado |
|---|---|---|
| `energyfrombattery`, `energytobattery` | **EB — Eficiencia de batería** (`Σ E_from / Σ E_to`) | Indicador diagnóstico |
| `gridinputenergy` (import), `gridoutputenergy` (export) | **KPI 07 — Autosuficiencia solar** | DEMO (blocker: *"etinverterxw export unconfirmed"*) |

Las cuatro variables son **contadores acumulados** de energía (crecen con el tiempo),
no medidas instantáneas. Esto es la raíz de casi todo lo que sigue.

---

## 1. Problemas detectados

### P1 — El export a red (`gridoutputenergy`) está congelado
En 4 meses el contador tiene **un solo valor** por entidad (desviación estándar = 0).
- **Significado posible:** el XW no mide inyección a red, FIWARE no actualiza el campo,
  o el sistema realmente no exporta (autoconsumo total).
- **Impacto:** KPI 07 no puede calcular el export → sigue en DEMO. Confirma el blocker del CONTEXT.

### P2 — La descarga de batería (`energyfrombattery`) está casi congelada
La descarga acumulada sube **0,25** en 4 meses, mientras la carga (`energytobattery`)
sube **~41–53**.
- **Significado posible:** la batería casi no descarga (modo respaldo / descarga inhibida),
  o el contador de descarga está roto.
- **Impacto:** EB calculado da **≈ 0,2–0,6 %**, físicamente imposible (Li-ion ronda 85–95 %).
  EB no es publicable como REAL.

### P3 — Valor centinela de desbordamiento (uint32) en `Inverter_XW:12`
Una lectura de `energyfrombattery`/`energytobattery` marca **4.294.967,5 ≈ 2³²−1**:
error de sensor/serialización, no un dato real.

### P4 — Los contadores acumulados se resampleaban por **media** (metodología incorrecta)
La versión previa hacía `.agg('mean')` sobre los contadores. **Promediar un contador
acumulado no tiene sentido físico.** EB y KPI 07 necesitan **energía por intervalo =
diferencia del contador entre extremos**, no su promedio.

### P5 — Muestreo muy irregular y cobertura horaria ~47 %
Cadencia mediana ~20 min, pero con huecos de hasta **8,5 días**; solo **~47 %** de las
horas del rango tienen dato. Sumar energía sobre periodos con huecos sesga el resultado
si no se marca cuáles intervalos son de baja confianza.

---

## 2. Soluciones implementadas (dónde, por qué, cómo)

Las correcciones de **código** son **P4** y **P5**; **P3** ya estaba mitigada. **P1, P2,
P6 y P7** requieren validación con operación/negocio y **no** se resuelven en el notebook
(ver sección 4).

| Problema | Dónde (bloque del notebook) | Solución |
|---|---|---|
| P3 | **Bloque 4.2** — Validación de rangos físicos | Filtro de rango que descarta el centinela |
| P4 | **Bloque 5.1 + 5.2** — Resample | `last` + `diff` en lugar de `mean` |
| P5 | **Bloque 5.1 + 5.2** — Resample | Columnas `n_muestras`, `gap_h`, `calidad` |

### Solución a P3 — filtro de centinela · `Bloque 4.2`
```python
RANGES = {
    'energyfrombattery': (0, 1_000_000),
    'energytobattery':   (0, 1_000_000),
    'gridinputenergy':   (0, 1_000_000),
    'gridoutputenergy':  (0, 1_000_000),
}
for col, (lo, hi) in RANGES.items():
    df[col] = df[col].where(df[col].between(lo, hi))
```
- **Por qué:** `4.294.967,5` supera cualquier valor físico real (los contadores reales van
  hasta ~52.000). Un tope de `1.000.000` lo deja fuera sin tocar datos válidos.
- **Cómo funciona:** `where(between(lo, hi))` convierte a `NaN` todo lo que cae fuera del
  rango; el `Bloque 4.3` (`dropna`) elimina esa fila antes del resample.

### Solución a P4 — energía por intervalo con `last` + `diff`
**`Bloque 5.1`** — se toma el valor del contador **al cierre de cada hora** (`last`), no el promedio:
```python
grp = df.set_index('time_index_colombia').groupby('entity_id', observed=True).resample(FREQ)
hourly = grp[num_cols].last()          # contador al final de la hora (NO 'mean')
hourly['n_muestras'] = grp.size()      # nº de lecturas crudas en la hora
hourly = hourly[hourly['n_muestras'] > 0]   # no se fabrican horas vacías
```
**`Bloque 5.2`** — se convierte el contador acumulado en **energía por hora** con la diferencia respecto a la hora anterior, por entidad:
```python
for c in num_cols:
    d = gb[c].diff()          # energía del intervalo = contador(t) - contador(t-1)
    d[d < 0] = np.nan         # un delta negativo sería un reset/atípico -> se anula
    df_h[c + '_delta'] = d
```
- **Por qué:** para un contador acumulado, la energía de un periodo es
  `valor_final − valor_inicial`. La suma de deltas horarios es telescópica: sumar
  `energyfrombattery_delta` sobre un día/mes da exactamente la energía de ese periodo.
  Así EB (`Σ from / Σ to`) y KPI 07 (`Σ import`, `Σ export`) se calculan correctamente
  aguas abajo simplemente **sumando las columnas `_delta`**.
- **Cómo funciona:** `diff()` dentro de cada `entity_id` resta el contador de la hora previa;
  los deltas negativos (resets/atípicos) se anulan a `NaN` para no contaminar las sumas.

### Solución a P5 — banderas de cobertura y calidad · `Bloque 5.1 + 5.2`
```python
GAP_MAX_H = 1   # horas contiguas = 'ok'; un salto mayor marca 'hueco'

df_h['gap_h'] = gb['time_index_colombia'].diff().dt.total_seconds() / 3600
df_h['calidad'] = np.where(df_h['gap_h'] <= GAP_MAX_H, 'ok', 'hueco')
df_h.loc[df_h['gap_h'].isna(), 'calidad'] = 'inicio'   # 1ª hora de cada entidad
```
- **Por qué:** un delta calculado tras un hueco de horas/días **acumula la energía de todo
  ese hueco en una sola hora**. La suma total sigue siendo correcta, pero ese punto no
  representa una hora real y no debe usarse para perfiles horarios ni para detectar picos.
- **Cómo funciona:**
  - `n_muestras` = cuántas lecturas crudas cayeron en la hora (cobertura real del dato).
  - `gap_h` = horas transcurridas desde la hora-con-dato anterior (`1` = contigua).
  - `calidad` = `ok` si el delta abarca una sola hora; `hueco` si atraviesa un vacío;
    `inicio` para la primera hora de cada entidad (sin delta, se descarta).
  - Regla de uso aguas abajo: para **sumas de energía** (EB, KPI 07) usar todo; para
    **perfiles horarios / picos** filtrar `calidad == 'ok'`.

---

## 3. Cómo leer el archivo `clean_etinverterxw.csv`

| Columna | Significado |
|---|---|
| `entity_id` | Inversor (`Inverter_XW:10/12/13`) |
| `time_index_colombia` | Hora (resolución horaria) |
| `energyfrombattery_delta` | Energía **descargada** de batería en esa hora |
| `energytobattery_delta` | Energía **cargada** a batería en esa hora |
| `gridinputenergy_delta` | Energía **importada** de la red en esa hora |
| `gridoutputenergy_delta` | Energía **exportada** a la red en esa hora |
| `n_muestras` | Lecturas crudas dentro de la hora (cobertura) |
| `gap_h` | Horas desde la hora-con-dato previa (`1` = contigua) |
| `calidad` | `ok` (hora contigua) · `hueco` (el delta abarca un vacío) |

**Qué confirman los datos ya con la metodología corregida** (suma de deltas, solo `calidad == 'ok'`):

| Entidad | EB = Σfrom/Σto | Σ export | Σ import | Lectura |
|---|---|---|---|---|
| XW:10 | 0,0019 | 0,000 | 1.178 | descarga y export congelados; import sano |
| XW:12 | 0,0049 | 0,000 | 1.230 | ídem |
| XW:13 | 0,0063 | 0,001 | 1.008 | ídem |

→ **EB ≈ 0** e **export = 0** no son errores de cálculo: son el estado real de los
contadores. Confirman P1 y P2 y justifican mantener EB y KPI 07 fuera de "REAL".

---

## 4. Lo que **no** se resolvió en código (depende de negocio/operación)

| Pendiente | Por qué no es código |
|---|---|
| **P1** ¿el XW exporta a red? | Requiere confirmar con operación si el export=0 es real o falla de telemetría |
| **P2** ¿la batería descarga? | Requiere confirmar el modo de operación de la batería con operación |
| **P6** mapeo `inverter → bloque` | Dato externo; sin él EB/KPI 07 no se atribuyen a un edificio |
| **P7** unidades (Wh vs kWh) | Debe confirmarse en la documentación del XW / FIWARE antes de reportar |

Mientras P1/P2 no se aclaren, **EB y KPI 07 deben permanecer en DEMO** (panel ámbar,
sufijo `⚠ Valor de referencia`), según la convención del CONTEXT.

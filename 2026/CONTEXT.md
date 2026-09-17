# e-Visor — Project Context

**Language:** context in English (token efficiency). All user-facing output must be in **Spanish**.

**Project:** Energy KPIs and dashboards for Ecocampus UPB (Medellín), ESG-aligned.
**Phase:** A2 — dashboard design + indicator calculation (infrastructure operational, no automation).
**Stack:** FIWARE (context broker) · Grafana (dashboards + alerts) · Landis meters (`etsmartmeter`, 16 meters) · Fronius inverter B11 (`etfroniusinverter`) · Enphase inverter B10 (`etenphaseinverter`) · Fronius sensor (`etfroniussensorcard`) · XW inverter (`etinverterxw`, grid export unconfirmed) · Battery inverter (`Inversor_Baterías`).
**Constraints:** hourly resolution · per block/building granularity · academic validity required.

## Design Rules

- Dashboards: simple, clear, public-facing. Vision: *"campus that speaks in every corner"*.
- KPIs: immediate per-building diagnostic for decision-makers.

## DEMO_MODE Convention

KPIs/indicators blocked by missing data are shown with plausible reference values. Rules:
- **Code:** tag every affected variable with `# DEMO_MODE: <reason> | ref=<value>`. Remove when real data arrives.
- **Grafana:** amber/orange panel tint + `⚠ Valor de referencia` suffix in title + tooltip stating what's missing.
- Goal: a stakeholder must never mistake a reference value for a real measured KPI.
- **Tariff:** every COP figure (IND-20, the summary energy card, KPI 01 cost, KPI 09 night cost/savings) uses one reference tariff, `TARIFA_REF_COP_KWH = 600` COP/kWh, defined identically in the notebook and `dashboard.py`. It is not the UPB bill and no public EPM tariff is used anywhere; replace it only with the actual invoice.

---

## Indicators (diagnostic, hourly, per block — source: Landis `etsmartmeter` unless noted)

Source of truth: `indicadores_y_kpis.json`. `PENDING` = no data yet; `dashboard.py` renders these as amber "Indicadores en integración" cards.

| ID | Name | Formula | Variables | Status |
|---|---|---|---|---|
| IND-01 | LF — Load Factor | `mean(P) / max(P)` | activepower | REAL |
| IND-02 | PAR — Peak-to-Average Ratio | `max(P) / mean(P)` | activepower | REAL |
| IND-03 | f₁ — Operational uniformity | `mean(P_op) / max(P_op)` · op=06:00–21:59 | activepower | REAL |
| IND-04 | f₂ — Load CV | `std(P_op) / mean(P_op)` | activepower | REAL |
| IND-05 | f₃ — Min-to-mean | `min(P_op) / mean(P_op)` | activepower | REAL |
| IND-06 | f₄ — Non-op load factor | `mean(P_non_op) / mean(P_op)` · non_op=22:00–05:59 | activepower | REAL |
| IND-07 | CO₂ emissions | `9.7018e-8 × Σ(E_day[Wh])` → tCO₂e · FE_2025=0.097018 tCO₂e/MWh (XM, 2026-01-30) ⚠ replace legacy 0.18 everywhere | Δactiveenergyimport | REAL |
| IND-08 | IGS — PV Yield Factor | `Σ(E_pv_day) / P_installed` → kWh/kWp · **per plant, never a fleet average** | energyproducedtoday · source: `etfroniusinverter` + `etenphaseinverter` | REAL (kWp: 52.65 / 45.4 inferred / 4.9) |
| IND-09 | TCP — Panel temp delta | `mean(T_panel) − mean(T_ambient)` over hours with `G > 200 W/m²` | paneltemperature · ambienttemperature · source: Fronius sensor | REAL (γ still missing for the efficiency-loss extension) |
| IND-10 | EB — Battery efficiency | `Σ(E_from_bat) / Σ(E_to_bat)` | energyfrombattery · energytobattery · source: `Inversor_Baterías` | PENDING |
| IND-11 | Energy savings | `1 − (E_current / E_base)` | Δactiveenergyimport | PENDING (needs ≥12-mo baseline) |
| IND-12 | VU — Voltage unbalance | `max(\|vₙ−v̄\|) / v̄ × 100` | v1, v2, v3 | REAL |
| IND-13 | FD — Diversity Factor | `Σ max(P_i) / max(Σ P_i)` · i = each of the 16 meters · campus-level, needs timestamp alignment | activepower | REAL |
| IND-15 | DDCE_h — Expected-consumption deviation (hourly) | `(E_obs − E_exp) / E_exp × 100` · E_exp = median of the same hour **and day-type** over the previous 4 weeks | Δactiveenergyimport | REAL |
| IND-16 | DDCE_d — Expected-consumption deviation (daily) | same formula on daily energy · feeds IND-19 | Δactiveenergyimport | REAL |
| IND-17 | PCT — Load percentiles (P90 / P95) | `quantile(P, 0.90)` and `quantile(P, 0.95)` per block-month · descriptive band, no threshold, no traffic light | activepower | REAL |
| IND-18 | PART — Share of submetered consumption | `E_block_month / E_submetered_month × 100` · denominator = the 16 meters, **never the campus** | Δactiveenergyimport | REAL |
| IND-19 | PERS — Deviation persistence | days with `DDCE_d > 0` within the last 7 · only full 7-day windows are exported | Δactiveenergyimport | REAL |
| IND-20 | VER — Reference economic value | `Σ(E_month[kWh]) × 600 COP/kWh` | Δactiveenergyimport + tariff parameter | **DEMO** (reference tariff, not the UPB bill) |
| IND-21 | CSE — Submetering coverage | `E_submetered_month / E_frontier_month × 100` | Δactiveenergyimport + `E_frontera_kwh` | PENDING (EPM frontier) |
| IND-22 | CORR_FS — Frontier vs submetering correlation | Pearson of the daily frontier series against the daily submetered series, per month · NaN below 10 paired days | Δactiveenergyimport + `E_frontera_kwh` | PENDING (EPM frontier) |

**Note:** HU (equivalent utilization hours) was dropped — it is not in the JSON spec nor computed by `dashboard.py`. Feeder chain: IND-01→KPI 08 · IND-06→KPI 09 · IND-07→KPI 05 · IND-11→KPI 04 · IND-12→KPI 10 · IND-16→IND-19.

**IND-15 to IND-22 — the rules that are easy to get wrong.**

- **Day-type is mandatory** in the DDCE grouper: `habil` / `sabado` / `domingo_festivo`, with Colombian holidays counted as Sunday (`FESTIVOS_COL_2026`, Emiliani shifts already applied). Without it a Monday is compared against Sundays and the indicator measures the calendar, not consumption. Base size is 4 weeks of the *same* day-type — 20 weekdays, 4 Saturdays, 4 Sundays — and below 3 observations no deviation is issued.
- **Only energy attributable to one hour enters DDCE.** The 48 h gap filter lets 22–25 h ingest cuts through (5 in 2026-H1): the first reading back carries the whole gap in one hour (+10 000 % hourly, −95 %/+150 % day pairs), and a 1e8 counter wrap becomes two negative diffs that `clip(0)` turns into two 0 kWh hours. DDCE requires previous reading at exactly 1 h, a non-decreasing counter, all meters of the block present, and 24 valid hours for a day. Other energy indicators still use the loose `E_hora_wh` (monthly totals are right; hour-of-day splits like KPI 09 are not).
- **Median, never mean,** for the expected value. A single spike inside the base would drag a mean upward and blind the indicator right after an anomaly, which is when it matters.
- **"Real time" is a promise the pipeline cannot keep.** There is no continuous ingest: IND-15 is computed for every loaded hour, and the output schema keeps only the date, so the dashboard shows the hourly distribution of the period, never a single 'current' hour.
- **Two denominators, never confused.** IND-18 divides by the 16 meters (submetered); IND-21 divides by the EPM frontier (campus). Any PART figure must be reported as "of measured consumption".
- **Correlation is not coverage.** A month can show r≈0.95 with low CSE if the unmetered load varies in proportion to the metered one. IND-22 is only ever reported next to IND-21 and its paired-day count.
- **IND-21/IND-22 are implemented and waiting,** not just declared. They read `frontera_epm.csv` (`fecha`, `E_frontera_kwh`); while the file is absent they emit PENDING exactly like IND-10/IND-11, and the moment it exists the PENDING rows disappear on their own with no code change.
- **Two shape decisions forced by the output schema** (`indicador · descripcion · bloque · fecha · mes · valor · unidad`, which must not gain columns): IND-17 is monthly per block rather than profiled by hour-of-day, and IND-19 exports only complete 7-day windows so the denominator is always 7.

---

## PV fleet — inventory, status and aggregation rule

Source of truth: `indicadores_y_kpis.json` → `plantas_fv` and `reglas_de_agregacion`.
Capacities come from `Reporte Maestro.xlsx` (sheet *Fichas técnicas SFV*).

| FIWARE id | System | Block | kWp | Own irradiance sensor | Status |
|---|---|---|---|---|---|
| `fronius_plant_52kWp` | SFV4_Terraza 11C-Sur | 11C | 52.65 | **yes** | OPERATING |
| `fronius_plant_45kW` | SFV21–SFV24 | 18 | 45.4 *(inferred)* | no | **NOT OPERATING** |
| `enphase_monitor` | SFV1_Terraza Juan Pablo II | 10 | 4.9 | no | OPERATING |

**Two capacities, never one.** Campus installed = 138.37 kWp · monitored = 102.95 kWp (74 %) · **operating = 57.55 kWp**. Every PV figure must say which of the three it divides by. Of the ~35 kWp without telemetry nothing can be asserted either way.

**Aggregation rule — a dead plant is treated in OPPOSITE ways depending on the question:**

- **Efficiency family (IGS, TCP, KPI 06)** — *how well does the equipment convert sunlight?* → **always per plant. A fleet-wide value is forbidden.** Averaging does not dilute the fault, it disguises it as a different one: healthy-plant PR is 76.1 %, combined-fleet PR is 41.6 %. That 41.6 % would send maintenance hunting for soiling or shading on a plant that works.
- **Impact family (IND-07 CO₂, KPI 07)** — *how much energy did the campus actually get?* → **always the whole fleet, dead plants included with their zero.** Dropping them would inflate self-sufficiency with energy that was never generated.

**KPI 06 scope.** Computable only for `fronius_plant_52kWp`, the only plant with a coplanar sensor. It cannot be extended to Enphase B10: azimuth 126° vs the sensor's 238–264° is a different plane of incidence. Only days with the full 06:00–18:00 daylight band are evaluated — one missing hour silently lowers RY and inflates PR.

**The 45 kW finding (2026-09).** Two of its four inverters produced nothing in 7 months; the other two stopped on **13–14 Feb 2026**. It delivered 701.3 kWh (1.8 % of Fronius generation) while holding 46 % of its installed capacity. Gap vs. the healthy plant's yield: **31,531 kWh · ≈ $18.9 M COP (reference tariff 600 COP/kWh) · 3.06 tCO₂e**. Telemetry proves the *reported* output is zero, **not** the cause: inverters off/disconnected and broken telemetry are both consistent with the data, and only a site visit to Block 18 separates them. Always present both hypotheses — claiming the loss as fact and being wrong costs credibility on everything else.

---

## KPIs — Master Table

11 KPIs. `DEMO` = shown with reference values (amber panel). `REAL` = calculated from live data. Groups: 1 Eficiencia energética (01, 02, 04) · 2 Gestión de demanda (03, 08, 09) · 3 Sostenibilidad + Generación renovable (05, 06, 07) · 4 Calidad del suministro (10, 11). All `E_day` = `Δactiveenergyimport` [Wh] from the Landis meters unless the row says otherwise. **`activeenergyimport` is a cumulative Wh counter, not period consumption** — `Δ` = consecutive `.diff()` per meter ordered by `time_index_colombia`, clipped at 0 to absorb counter resets. The raw CSVs also carry `activeenergyimportday`, but the cumulative counter is what the pipeline uses because it preserves hourly resolution.

| # | Name | Unit | Formula | Threshold | SDG | ESG axis | Stakeholder | Status | Blocker / ref value |
|---|---|---|---|---|---|---|---|---|---|
| 01 | Consumo/m² | kWh/m²·mo | `Σ(E_day÷1000) / Área_bloque` · área from `AREAS 2026.xlsx` | Propio: **media + 1σ** por bloque | 7,9 | Regen & resilience | Institutional leaders | REAL | — |
| 02 | Intensidad por usuario | kWh/user·mo | `Σ(E_day÷1000) / N_users` | Propio: **media + 1σ** sobre la serie de campus | 4,7,9 | Conscious leadership | Academic sector | **DEMO** | "Usuario activo" definition pending (students + FTE) · ref=3500 users |
| 03 | Pico de demanda | kW + timestamp | `max(P)` per period per block · log date, hour and block | Propio: **media + 1σ** por bloque | 7,9 | Conscious leadership | Leaders + business | REAL | — |
| 04 | Ahorro verificado | % | `[1 − Σ(E_act÷1000)/E_base_adj] × 100` · E_base_adj normalized by users+temp | — sin umbral: serie constante en DEMO (σ=0) | 7,9,13 | Regen & resilience | All groups | **DEMO** | No 12-mo baseline yet; awaiting EPM data for full-university consumption · ref=prior period×1.03 |
| 05 | Emisiones CO₂ | tCO₂e | See IND-07 | Propio: **media + 1σ** por bloque | 7,13,17 | Regen & resilience | Public + community | REAL | ⚠ Replace 0.18 legacy FE everywhere · check whether UPB Sostenibilidad already owns this KPI |
| 06 | Performance Ratio FV | % | `PR=(YF/RY)×100` · `YF=Σ(E_pv)/P_inst` · `RY=Σ(G×Δt)/1000` | Propio: **media − 1σ** por planta (más es mejor) | 7,9,13 | Regen & resilience | Academic + business | REAL | Only `fronius_plant_52kWp` (coplanar sensor) and only days with the full 06:00–18:00 band — see PV section |
| 07 | Autosuficiencia solar | % | `Σ(E_solar_self)/Σ(E_grid+E_solar_AC)×100` · if no export meter: `E_self≈energyproducedtoday` (proxy that **overestimates** SS — declare it each run) | Propio: **media − 1σ** sobre la serie de campus (más es mejor) | 7,13,17 | Regen & resilience | Students + alumni | REAL | `etinverterxw` export unconfirmed → proxy · whole fleet, dead plants with their zero · denominator = the 16 Landis meters (none on Block 11): *measured campus*, not the university |
| 08 | Load Factor | 0–1 | See IND-01 · denominator = max of the analysed period, NOT meter rating | Propio: **media − 1σ** por bloque (más es mejor) | 7,9 | Conscious leadership | Maintenance | REAL | — |
| 09 | Consumo no operacional | % | `[Σ(E_22h-06h÷1000)/Σ(E_total÷1000)]×100` (=f₄ by energy) · non-op=22:00–05:59 | Propio: **media + 1σ** por bloque | 7,9 | Regen & resilience | Maintenance | REAL | — |
| 10 | Desbalance de tensión | % | `[max(\|vₙ−v̄\|)/v̄]×100` | Fijo (directriz e-Visor): objetivo <2 % · alerta ≥3 % | 9 | Conscious leadership | Tech + labs | REAL | — |
| 11 | Factor de potencia | — | Direct: `totalpowerfactor` | Fijo (directriz e-Visor): objetivo ≥0.90 · alerta <0.85 | 9 | Conscious leadership | Finance + ops | REAL | On alert, cross-check with `reactivepower` |

**KPI 12 (THD-V) was dropped** — not in the JSON spec nor in `dashboard.py`. `relativethdvoltage` is still cleaned and kept in the dataset if it is ever reinstated.


**Threshold rule.** Only KPI 10 and KPI 11 carry fixed thresholds, set by e-Visor team directive; they are never recomputed from data. **Every other KPI derives its own** from the 12 months *preceding* the evaluated month (the month being judged is excluded from its own threshold): `alerta = media ± 1σ`, `objetivo = media` mejorada un 7 %, the sign chosen by the KPI's direction — `+1σ` when more is worse (01, 02, 03, 05, 09), `−1σ` when more is better (04, 06, 07, 08). Grouping is per block over its monthly series (per plant for KPI 06), except KPI 02 and KPI 07, which are campus-level. The 7 % improvement target is the only constant, and it comes from the project's own threshold protocol. No threshold value is written by hand.

Direction lives in exactly one place: the `higher_is_better` flag of `estado_icon()`, which `umbral_movil()` passes straight through. Do not reintroduce a second place that decides it.

Below `n_min = 4` months of base, no verdict is issued: the state is `SIN_BASE`. Every evaluated row carries `n_base`, `ventana_desde`, `ventana_hasta` and `base_completa` so the judgment can be reproduced. `umbral_movil(..., ventana_fija=('2026-01','2026-12'))` freezes the baseline instead of rolling it, for when the first full cycle closes.

---

## Coding Rules

**1. Think Before Coding** — state assumptions explicitly; surface tradeoffs; ask when unclear.
**2. Simplicity First** — minimum code that solves the problem; no speculative features or abstractions.
**3. Surgical Changes** — touch only what the request requires; match existing style; don't refactor unrelated code; remove only orphans your changes create.
**4. Goal-Driven Execution** — define verifiable success criteria before implementing; for multi-step tasks state a plan with verify steps.

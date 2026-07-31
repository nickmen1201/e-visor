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

---

## Indicators (diagnostic, hourly, per block — source: Landis `etsmartmeter` unless noted)

Source of truth: `ecocampus_kpis_indicadores.json` (v `Indicadores_y_KPI_26_1_3`). `PENDING` = no data yet; `dashboard.py` renders these as amber "Indicadores en integración" cards.

| ID | Name | Formula | Variables | Status |
|---|---|---|---|---|
| IND-01 | LF — Load Factor | `mean(P) / max(P)` | activepower | REAL |
| IND-02 | PAR — Peak-to-Average Ratio | `max(P) / mean(P)` | activepower | REAL |
| IND-03 | f₁ — Operational uniformity | `mean(P_op) / max(P_op)` · op=06:00–21:59 | activepower | REAL |
| IND-04 | f₂ — Load CV | `std(P_op) / mean(P_op)` | activepower | REAL |
| IND-05 | f₃ — Min-to-mean | `min(P_op) / mean(P_op)` | activepower | REAL |
| IND-06 | f₄ — Non-op load factor | `mean(P_non_op) / mean(P_op)` · non_op=22:00–05:59 | activepower | REAL |
| IND-07 | CO₂ emissions | `9.7018e-8 × Σ(E_day[Wh])` → tCO₂e · FE_2025=0.097018 tCO₂e/MWh (XM, 2026-01-30) ⚠ replace legacy 0.18 everywhere | Δactiveenergyimport | REAL |
| IND-08 | IGS — PV Yield Factor | `Σ(E_pv_day) / P_installed` → kWh/kWp | energyproducedtoday · source: Fronius B11 + Enphase B10 | PENDING (kWp unconfirmed) |
| IND-09 | TCP — Panel temp delta | `mean(T_panel) − mean(T_ambient)` · ~0.4%/°C efficiency loss over TC | paneltemperature · ambienttemperature · source: Fronius sensor | PENDING |
| IND-10 | EB — Battery efficiency | `Σ(E_from_bat) / Σ(E_to_bat)` | energyfrombattery · energytobattery · source: `Inversor_Baterías` | PENDING |
| IND-11 | Energy savings | `1 − (E_current / E_base)` | Δactiveenergyimport | PENDING (needs ≥12-mo baseline) |
| IND-12 | VU — Voltage unbalance | `max(|vₙ−v̄|) / v̄ × 100` · NEMA MG-1 | v1, v2, v3 | REAL |
| IND-13 | FD — Diversity Factor | `Σ max(P_i) / max(Σ P_i)` · i = each of the 16 meters · campus-level, needs timestamp alignment | activepower | REAL |

**Note:** HU (equivalent utilization hours) was dropped — it is not in the JSON spec nor computed by `dashboard.py`. Feeder chain: IND-01→KPI 08 · IND-06→KPI 09 · IND-07→KPI 05 · IND-11→KPI 04 · IND-12→KPI 10.

---

## KPIs — Master Table

11 KPIs. `DEMO` = shown with reference values (amber panel). `REAL` = calculated from live data. Groups: 1 Eficiencia energética (01, 02, 04) · 2 Gestión de demanda (03, 08, 09) · 3 Sostenibilidad + Generación renovable (05, 06, 07) · 4 Calidad del suministro (10, 11). All `E_day` = `Δactiveenergyimport` [Wh] from the Landis meters unless the row says otherwise. **`activeenergyimport` is a cumulative Wh counter, not period consumption** — `Δ` = consecutive `.diff()` per meter ordered by `time_index_colombia`, clipped at 0 to absorb counter resets. The raw CSVs also carry `activeenergyimportday`, but the cumulative counter is what the pipeline uses because it preserves hourly resolution.

| # | Name | Unit | Formula | Threshold | SDG | ESG axis | Stakeholder | Status | Blocker / ref value |
|---|---|---|---|---|---|---|---|---|---|
| 01 | Consumo/m² | kWh/m²·mo | `Σ(E_day÷1000) / Área_bloque` · área from `AREAS 2026.xlsx` | TBD · ref: 8–25 kWh/m²·mo, 124.4 kWh/m²·yr (UPME PGEE) | 7,9 | Regen & resilience | Institutional leaders | REAL | — |
| 02 | Intensidad por usuario | kWh/user·mo | `Σ(E_day÷1000) / N_users` | TBD after 12-mo cycle (NQA §6.4 functional unit) | 4,7,9 | Conscious leadership | Academic sector | **DEMO** | "Usuario activo" definition pending (students + FTE) · ref=3500 users |
| 03 | Pico de demanda | kW + timestamp | `max(P)` per period per block · log date, hour and block | TBD: monthly peak mean+1σ (yr 1) | 7,9 | Conscious leadership | Leaders + business | REAL | — |
| 04 | Ahorro verificado | % | `[1 − Σ(E_act÷1000)/E_base_adj] × 100` · E_base_adj normalized by users+temp (ISO 50001 Annex B) | ≥3% annual (Ley 2169/2021, UPME PGEE) | 7,9,13 | Regen & resilience | All groups | **DEMO** | No 12-mo baseline yet; awaiting EPM data for full-university consumption · ref=prior period×1.03 |
| 05 | Emisiones CO₂ | tCO₂e | See IND-07 | ≥3% annual reduction; long-term: carbon neutrality (Ley 2169/2021, GRI 302-1) | 7,13,17 | Regen & resilience | Public + community | REAL | ⚠ Replace 0.18 legacy FE everywhere · check whether UPB Sostenibilidad already owns this KPI |
| 06 | Performance Ratio FV | % | `PR=(YF/RY)×100` · `YF=Σ(E_pv)/P_inst` · `RY=Σ(G×Δt)/1000` | ≥75% target · <65% degradation alert (IEC 61724-1:2017; Kumar et al. 2019: 73–78% tropical) · EU 80% does not apply | 7,9,13 | Regen & resilience | Academic + business | **DEMO** | `solarirradiation` is W/m² (instantaneous) and Fronius time resolution is undefined; kWp unconfirmed — **do not compute until resolved** · ref=PR 73% |
| 07 | Autosuficiencia solar | % | `Σ(E_solar_self)/Σ(E_grid+E_solar_AC)×100` · if no export meter: `E_self≈energyproducedtoday` (conservative proxy, document it each run) | ≥15% guidance (GRI 302-1, Ley 2169/2021) | 7,13,17 | Regen & resilience | Students + alumni | **DEMO** | `etinverterxw` export unconfirmed; kWp unconfirmed · ref=SS 12% |
| 08 | Load Factor | 0–1 | See IND-01 · denominator = max of the analysed period, NOT meter rating | ≥0.65 guidance (Papadopoulos et al. 2016: mean 0.67, range 0.55–0.80) | 7,9 | Conscious leadership | Maintenance | REAL | — |
| 09 | Consumo no operacional | % | `[Σ(E_22h-06h÷1000)/Σ(E_total÷1000)]×100` (=f₄ by energy) · non-op=22:00–05:59 | TBD (yr 1) · qualitative ref: Papadopoulos et al. 2016 — high f₄ is the common pattern in campuses | 7,9 | Regen & resilience | Maintenance | REAL | Threshold pending — see literature note below |
| 10 | Desbalance de tensión | % | `[max(|vₙ−v̄|)/v̄]×100` NEMA MG-1 | <2% normal · **alert ≥3%** (e-Visor directive; ref. IEEE 1159:2019) | 9 | Conscious leadership | Tech + labs | REAL | — |
| 11 | Factor de potencia | — | Direct: `totalpowerfactor` | ≥0.9 normal · **alert <0.85** (e-Visor directive; CREG Res. 108/1997 requires ≥0.9) | 9 | Conscious leadership | Finance + ops | REAL | On alert, cross-check with `reactivepower` |

**KPI 12 (THD-V) was dropped** — not in the JSON spec nor in `dashboard.py`. `relativethdvoltage` is still cleaned and kept in the dataset if it is ever reinstated.

**KPI 09 literature (kept from earlier research, not yet adopted as threshold):** Tavakoli et al. 2023, *Sustainability* 15:4240 — UTS Sydney university building, nighttime baseload ~38% of peak; Gul & Patidar 2015, *EnB* 87:155 — Heriot-Watt academic building, ~33% of peak at night. Suggests alert >30% · target <20% · acceptable 20–30%, pending validation with Ecocampus data.

**TBD threshold protocol (KPI 01, 02, 03, 09):** collect 12 months → compute mean+σ per block and period type → alert=mean+1σ, target=mean−10% → validate with stakeholders (A2.4) → review annually.

---

## Coding Rules

**1. Think Before Coding** — state assumptions explicitly; surface tradeoffs; ask when unclear.
**2. Simplicity First** — minimum code that solves the problem; no speculative features or abstractions.
**3. Surgical Changes** — touch only what the request requires; match existing style; don't refactor unrelated code; remove only orphans your changes create.
**4. Goal-Driven Execution** — define verifiable success criteria before implementing; for multi-step tasks state a plan with verify steps.

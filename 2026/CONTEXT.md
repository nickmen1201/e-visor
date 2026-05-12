# e-Visor — Project Context

**Language:** context in English (token efficiency). All user-facing output must be in **Spanish**.

**Project:** Energy KPIs and dashboards for Ecocampus UPB (Medellín), ESG-aligned.
**Phase:** A2 — dashboard design + indicator calculation (infrastructure operational, no automation).
**Stack:** FIWARE (context broker) · Grafana (dashboards + alerts) · Landis meters (`etsmartmeter`) · Fronius inverter B11 (`etfroniusinverter`) · Enphase inverter B10 (`etenphaseinverter`) · Fronius sensor (`etfroniussensorcard`) · XW inverter (`etinverterxw`, grid export unconfirmed).
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

## Indicators (diagnostic, hourly, per block — source: Landis meters unless noted)

| ID | Name | Formula | Variables |
|---|---|---|---|
| LF | Load Factor | `mean(P) / max(P)` | activepower |
| PAR | Peak-to-Average Ratio | `max(P) / mean(P)` | activepower |
| f₁ | Operational uniformity | `mean(P_op) / max(P_op)` · op=06:00–21:59 | activepower |
| f₂ | Load CV | `std(P_op) / mean(P_op)` | activepower |
| f₃ | Min-to-mean | `min(P_op) / mean(P_op)` | activepower |
| f₄ | Non-op load factor | `mean(P_non_op) / mean(P_op)` · non_op=22:00–05:59 | activepower |
| HU | Equivalent utilization hours | `Σ(E_day[Wh]) / max(P[W])` → h · range [0,24] | activeenergyimport, activepower |
| CO₂ | Carbon emissions | `9.7018e-8 × Σ(E_day[Wh])` → tCO₂e · FE_2025=0.097018 tCO₂e/MWh (XM, 2026-01-30) ⚠ replace legacy 0.18 everywhere | activeenergyimport |
| IGS | PV Yield Factor `⚠DEMO` | `Σ(E_pv_day) / P_installed` | energyproducedtoday · solarradiation |
| TCP | Panel temp delta | `mean(T_panel) − mean(T_ambient)` | paneltemperature · ambienttemperature · source: Fronius sensor |
| EB | Battery efficiency | `Σ(E_from_bat) / Σ(E_to_bat)` | energyfrombattery · energytobattery |
| VU | Voltage unbalance | `mean(max(|vₙ−v̄|) / v̄) × 100` | v1, v2, v3 |

---

## KPIs — Master Table

`DEMO` = shown with reference values (amber panel). `REAL` = calculated from live data.

| # | Name | Unit | Formula | Threshold | SDG | ESG axis | Stakeholder | Status | Blocker / ref value |
|---|---|---|---|---|---|---|---|---|---|
| 01 | Consumo/m² | kWh/m² | `Σ(E_day÷1000) / Área_bloque` | TBD · ref: 8–25 kWh/m²·mo (UPME PGEE) | 7,9 | Regen & resilience | Institutional leaders | **DEMO** | Areas pending from Planeación Física UPB · ref=1200 m²/block |
| 02 | Intensidad por usuario | kWh/user·mo | `Σ(E_day÷1000) / N_users` | TBD after 12-mo cycle | 4,7,9 | Conscious leadership | Academic sector | **DEMO** | "Active user" definition pending (students + FTE) · ref=3500 users |
| 03 | Pico de demanda | kW + timestamp | `max(P)` per period per block | TBD: monthly peak mean+1σ (yr 1) | 7,9 | Conscious leadership | Leaders + business | REAL | — |
| 04 | Ahorro verificado | % | `[1 − Σ(E_act÷1000)/E_base_adj] × 100` · E_base_adj normalized by users+temp (ISO 50001 Annex B) | ≥3% annual (Ley 2169/2021, UPME PGEE) | 7,9,13 | Regen & resilience | All groups | **DEMO** | No 12-mo baseline yet · ref=prior period×1.03 |
| 05 | Emisiones CO₂ | tCO₂e | See CO₂ indicator above | ≥3% annual reduction; long-term: carbon neutrality (Ley 2169/2021) | 7,13,17 | Regen & resilience | Public + community | REAL | ⚠ Replace 0.18 legacy FE everywhere |
| 06 | Performance Ratio FV | % | `PR=(YF/RY)×100` · `YF=Σ(E_pv)/P_inst` · `RY=Σ(G×Δt)/1000` | ≥75% target · <65% degradation alert (IEC 61724-1:2017, tropical adj.) | 7,9,13 | Regen & resilience | Academic + business | **DEMO** | Fronius irradiance resolution unconfirmed; kWp unconfirmed · ref=PR 73% |
| 07 | Autosuficiencia solar | % | `Σ(E_solar_self)/Σ(E_grid+E_solar_AC)×100` · if no export meter: `E_self≈energyproducedtoday` | ≥15% guidance (GRI 302-1, Ley 2169/2021) | 7,13,17 | Regen & resilience | Students + alumni | **DEMO** | `etinverterxw` export unconfirmed; kWp unconfirmed · ref=SS 12% |
| 08 | Load Factor | 0–1 | See LF indicator | ≥0.65 guidance (Papadopoulos et al. 2016: mean 0.67) | 7,9 | Conscious leadership | Maintenance | REAL | — |
| 09 | Consumo no operacional | % | `[Σ(E_22h-07h÷1000)/Σ(E_total÷1000)]×100` (=f₄ by energy) | Alert >20% · target <10% · range 8–22% (Papadopoulos et al. 2016) | 7,9 | Regen & resilience | Maintenance | REAL | — |
| 10 | Desbalance de tensión | % | `[max(|vₙ−v̄|)/v̄]×100` NEMA MG-1 | <2% normal · alert ≥2% for ≥3h consecutive (IEEE 1159:2019, NTC 5001) | 9 | Conscious leadership | Tech + labs | REAL | — |
| 11 | Factor de potencia | — | Direct: `totalpowerfactor` | ≥0.9 · alert <0.9 for ≥3h (CREG 108/1997, NTC 5001) | 9 | Conscious leadership | Finance + ops | REAL | — |
| 12 | THD-V | % | Direct: `relativethdvoltage` · per-phase: `harmonicsv1/v2/v3` | <5% LV (≤1kV) · alert ≥5% sustained (IEEE 519:2022, NTC 5001) | 9 | Conscious leadership | Tech + labs | REAL | — |

**TBD threshold protocol (KPI 01, 02, 03):** collect 12 months → compute mean+σ per block and period type → alert=mean+1σ, target=mean−10% → validate with stakeholders (A2.4) → review annually.

---

## Coding Rules

**1. Think Before Coding** — state assumptions explicitly; surface tradeoffs; ask when unclear.
**2. Simplicity First** — minimum code that solves the problem; no speculative features or abstractions.
**3. Surgical Changes** — touch only what the request requires; match existing style; don't refactor unrelated code; remove only orphans your changes create.
**4. Goal-Driven Execution** — define verifiable success criteria before implementing; for multi-step tasks state a plan with verify steps.

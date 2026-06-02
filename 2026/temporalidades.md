# Temporalidades — Indicadores y KPIs del Ecocampus UPB

**Resolución de entrada:** siempre horaria (medidores Landis `etsmartmeter`).  
**Granularidad de cálculo:** período mínimo en que el indicador/KPI se computa.  
**Ventana de umbral:** período al que aplica el umbral o referencia normativa.  
**Visualización:** cómo se agrega para mostrarse en el dashboard.

---

## Indicadores diagnósticos

| ID | Nombre | Granularidad de cálculo | Ventana de umbral | Visualización en dashboard | Notas |
|---|---|---|---|---|---|
| **LF** | Factor de carga | Diaria · por medidor | Sin umbral fijo | Serie diaria + barra por bloque | `mean(P) / max(P)` curva completa |
| **PAR** | Peak-to-Average Ratio | Diaria · por medidor | Sin umbral fijo | Serie diaria + barra por bloque | Inverso de LF |
| **f₁** | Uniformidad diurna | Diaria · por medidor | Sin umbral fijo | Serie diaria + barra por bloque | Franja 06:00–21:59 |
| **f₂** | CV de carga | Diaria · por medidor | Sin umbral fijo | Serie diaria + barra por bloque | Franja 06:00–21:59 |
| **f₃** | Mínimo/promedio | Diaria · por medidor | Sin umbral fijo | Serie diaria + barra por bloque | Franja 06:00–21:59 |
| **f₄** | Carga no operacional | Diaria · por medidor | Sin umbral fijo | Serie diaria + heatmap semanal | Franja 22:00–05:59 |
| **HU** | Horas de utilización | Diaria · por medidor | [0, 24] h (físico) | Barra por bloque | `E_día / P_max` |
| **CO₂** | Emisiones de carbono | Diaria → acum. mensual · por medidor | Reducción ≥ 3 % anual (Ley 2169/2021) | Barra mensual + barra diaria | FE 2025 = 0.097018 tCO₂e/MWh |
| **IGS** | Rendimiento específico FV | Diaria · por sistema | Sin umbral fijo | — | ⚠ DEMO · requiere Fronius/Enphase |
| **TCP** | Delta temperatura panel | Horaria → diaria · por sensor | Sin umbral fijo | — | ⚠ DEMO · requiere sensor Fronius |
| **EB** | Eficiencia de batería | Diaria · por sistema | Sin umbral fijo | — | ⚠ DEMO · requiere datos inversor |
| **VU** | Desbalance de tensión | Horaria → media diaria · por medidor | < 2 % normal · alerta ≥ 2 % sostenida ≥ 3 h consecutivas | Barra por bloque + barra diaria | IEEE 1159:2019 · NTC 5001 |
| **THD-V** | Distorsión armónica total de voltaje | Horaria · por medidor | < 5 % LV (≤ 1 kV) · alerta ≥ 5 % sostenida (IEEE 519:2022 · NTC 5001) | Serie diaria + tira de calor | IEEE 519:2022 · NTC 5001 |

---

## KPIs estratégicos

| # | Nombre | Granularidad de cálculo | Ventana de umbral | Visualización en dashboard | Estado |
|---|---|---|---|---|---|
| **01** | Consumo por m² | Diaria · por bloque → acum. anual | **124.4 kWh/m²·año** | Barra por bloque (equiv. anual) | REAL |
| **02** | Intensidad por usuario | Diaria → mensual · por bloque | TBD tras ciclo de 12 meses | — | ⚠ DEMO · N_usuarios pendiente |
| **03** | Pico de demanda | Diaria · por medidor | TBD: μ+1σ mensual (año 1) | Barra por bloque con umbral dinámico | REAL |
| **04** | Ahorro verificado | Anual · por bloque | ≥ 3 % anual (Ley 2169/2021) | — | ⚠ DEMO · requiere línea base 12 meses |
| **05** | Emisiones CO₂ | Diaria → mensual · total campus | Reducción ≥ 3 % anual (Ley 2169/2021) | Barra mensual + barra diaria | REAL |
| **06** | Performance Ratio FV | Diaria · por sistema | ≥ 75 % objetivo · < 65 % alerta (IEC 61724-1) | — | ⚠ DEMO · requiere Fronius irradiancia |
| **07** | Autosuficiencia solar | Mensual · por campus | ≥ 15 % (GRI 302-1 · Ley 2169/2021) | — | ⚠ DEMO · requiere energyproducedtoday |
| **08** | Load Factor | Diaria · por medidor | ≥ 0.65 (Papadopoulos et al. 2016) | Barra por bloque (% días en cumplimiento) | REAL |
| **09** | Consumo no operacional | Diaria · por medidor | Objetivo < 20 % · Aceptable 20–30 % · Alerta > 30 % | Barra por bloque | REAL |
| **10** | Desbalance de tensión | Horaria · por medidor | < 2 % normal · alerta ≥ 2 % sostenida ≥ 3 h (IEEE 1159:2019 · NTC 5001) | Tira de calor diaria por medidor | REAL |
| **11** | Factor de potencia | Horaria · por medidor | ≥ 0.9 · alerta < 0.9 sostenida ≥ 3 h (CREG 108/1997 · NTC 5001) | Serie diaria + tira de calor | REAL |

---

## Resumen de ventanas de tiempo

| Ventana | Indicadores / KPIs |
|---|---|
| **Horaria** (detección de eventos) | VU · THD-V · KPI 10 · KPI 11 |
| **Diaria** (diagnóstico operativo) | LF · PAR · f₁ · f₂ · f₃ · f₄ · HU · CO₂ · KPI 03 · KPI 08 · KPI 09 |
| **Mensual** (reporte de gestión) | CO₂ (acum.) · KPI 05 · KPI 07 |
| **Anual** (cumplimiento ESG) | KPI 01 · KPI 04 · KPI 05 (meta) |

---

*Fuente normativa: UPME PGEE · Ley 2169/2021 · ISO 50001 · IEEE 519:2022 · IEEE 1159:2019 · NTC 5001 · CREG 108/1997 · IEC 61724-1:2017 · GRI 302-1*

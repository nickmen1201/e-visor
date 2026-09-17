# Temporalidades — Indicadores y KPIs del Ecocampus UPB

**Resolución de entrada:** siempre horaria (medidores Landis `etsmartmeter`).  
**Granularidad de cálculo:** período mínimo en que el indicador/KPI se computa.  
**Ventana de umbral:** período al que aplica el umbral. Solo los KPI 10 y 11 tienen umbral fijo (directriz e-Visor). Los demás KPIs usan **umbral propio**: `media ± 1σ` de los 12 meses previos al mes evaluado (mínimo 4 meses, si no `SIN_BASE`), con objetivo = media mejorada un 7 %. Los indicadores son diagnósticos y no llevan umbral. Detalle en `CONTEXT.md`.  
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
| **CO₂** | Emisiones de carbono | Diaria → acum. mensual · por medidor | Sin umbral fijo · el juicio lo emite KPI 05 | Barra mensual + barra diaria | FE 2025 = 0.097018 tCO₂e/MWh |
| **IGS** | Rendimiento específico FV | Diaria · por planta | Sin umbral fijo | Serie diaria por planta | Por planta, nunca promedio de flota · kWp 52,65 / 45,4 (inferido) / 4,9 |
| **TCP** | Delta temperatura panel | Horaria → diaria · por sensor | Sin umbral fijo | Serie diaria + media móvil 7 d | Solo horas con G > 200 W/m² · sensor Fronius B11 · falta γ para estimar la pérdida de eficiencia |
| **EB** | Eficiencia de batería | Diaria · por sistema | Sin umbral fijo | — | ⚠ PENDIENTE · requiere datos de `Inversor_Baterías` |
| **Ahorro** | Ahorro de energía | Mensual · por bloque | Sin umbral fijo | — | ⚠ PENDIENTE · requiere línea base ≥ 12 meses |
| **VU** | Desbalance de tensión | Horaria → media diaria · por medidor | Objetivo < 2 % · alerta ≥ 3 % (directriz e-Visor, compartida con KPI 10) | Barra por bloque + barra diaria | Referencia: IEEE 1159:2019 · NTC 5001 |
| **FD** | Factor de diversidad | Mensual · campus completo | Sin umbral fijo | Serie mensual de campus | Exige timestamps alineados entre los 16 medidores |
| **DDCE_H** | Desviación del consumo esperado (horaria) | Horaria · por bloque | Sin umbral fijo · base móvil de 4 semanas del mismo tipo de día | Distribución horaria por bloque (P5–P95, P25–P75, mediana) | Esperado = mediana, no promedio · mínimo 3 observaciones de base |
| **DDCE_D** | Desviación del consumo esperado (diaria) | Diaria · por bloque | Sin umbral fijo · base móvil de 4 semanas del mismo tipo de día | Barra diaria del bloque típico (mediana entre bloques) · el detalle nombra el bloque más alto y el más bajo | Alimenta a PERS |
| **PCT** | Percentiles de carga (P90 / P95) | Mensual · por bloque | Descriptivo: sin umbral ni semáforo | Barras P90 / P95 por bloque · B9 por submedidor | Mensual y no por hora del día: el esquema de salida no tiene esa dimensión |
| **PART** | Participación en el consumo submedido | Mensual · por bloque | Sin umbral fijo | Dona o barra apilada por bloque | Denominador = los 16 medidores, NO el campus completo |
| **PERS** | Persistencia de la desviación | Diaria · por bloque · ventana de 7 días | Sin umbral fijo | Mapa bloque × fecha (días de 7) · B9 por submedidor | Solo se publican ventanas completas (7 de 7 días evaluados) |
| **VER** | Valor económico de referencia | Mensual · por bloque | Sin umbral fijo | Tarjeta de valor + barra mensual | ⚠ DEMO · tarifa de referencia 600 COP/kWh, no la factura de la UPB |
| **CSE** | Cobertura de submedición | Mensual · campus completo | Sin umbral fijo | — | ⚠ PENDIENTE · requiere la frontera EPM (`frontera_epm.csv`) |
| **CORR_FS** | Correlación frontera – submedición | Mensual · campus completo | Sin umbral fijo · mínimo 10 días pareados | — | ⚠ PENDIENTE · requiere la frontera EPM · se reporta siempre junto a CSE |

---

## KPIs estratégicos

| # | Nombre | Granularidad de cálculo | Ventana de umbral | Visualización en dashboard | Estado |
|---|---|---|---|---|---|
| **01** | Consumo por m² | Diaria · por bloque → acum. anual | Propio: media + 1σ por bloque | Barra por bloque (equiv. anual) | REAL · el costo en COP usa la tarifa de referencia de 600 COP/kWh (DEMO) |
| **02** | Intensidad por usuario | Diaria → mensual · por bloque | Propio: media + 1σ · serie de campus | — | ⚠ DEMO · N_usuarios pendiente |
| **03** | Pico de demanda | Diaria · por medidor | Propio: media + 1σ por bloque | Barra por bloque con umbral dinámico | REAL |
| **04** | Ahorro verificado | Anual · por bloque | Sin umbral efectivo: la serie DEMO es constante (σ = 0) | — | ⚠ DEMO · requiere línea base 12 meses |
| **05** | Emisiones CO₂ | Diaria → mensual · total campus | Propio: media + 1σ | Barra mensual + barra diaria | REAL |
| **06** | Performance Ratio FV | Mensual · solo planta 52,65 kWp (días con franja 06:00–18:00 completa) | Propio: media − 1σ (más es mejor) | Línea mensual de PR con umbral móvil | REAL |
| **07** | Autosuficiencia solar | Mensual · por campus medido | Propio: media − 1σ · serie de campus (más es mejor) | Barra mensual | REAL · proxy que sobreestima (sin medición de exportación) |
| **08** | Load Factor | Diaria · por medidor | Propio: media − 1σ por bloque (más es mejor) | Barra del último mes por medidor con su umbral propio + tira de estado mensual · B9 por submedidor (SFA1, SFA2) | REAL |
| **09** | Consumo no operacional | Diaria · por medidor | Propio: media + 1σ por bloque | Barra por bloque | REAL |
| **10** | Desbalance de tensión | Horaria · por medidor | Fijo (directriz e-Visor): objetivo < 2 % · alerta ≥ 3 % | Tira de calor diaria por medidor | REAL |
| **11** | Factor de potencia | Horaria · por medidor | Fijo (directriz e-Visor): objetivo ≥ 0,90 · alerta < 0,85 | Serie diaria + tira de calor | REAL |

---

## Resumen de ventanas de tiempo

| Ventana | Indicadores / KPIs |
|---|---|
| **Horaria** (detección de eventos) | VU · DDCE_H · KPI 10 · KPI 11 |
| **Diaria** (diagnóstico operativo) | LF · PAR · f₁ · f₂ · f₃ · f₄ · CO₂ · DDCE_D · PERS · KPI 03 · KPI 08 · KPI 09 |
| **Mensual** (reporte de gestión) | CO₂ (acum.) · Ahorro · FD · PCT · PART · VER · CSE · CORR_FS · KPI 05 · KPI 07 |
| **Anual** (cumplimiento ESG) | KPI 01 · KPI 04 · KPI 05 (meta) |

---

*Referencias normativas y bibliográficas (contexto; los umbrales vienen de la regla propia o de la directriz e-Visor, no de estas normas): UPME PGEE · Ley 2169/2021 · ISO 50001 · IEEE 1159:2019 · NTC 5001 · CREG 108/1997 · IEC 61724-1:2017 · GRI 302-1*

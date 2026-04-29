# e-Visor — Referencia de Indicadores y KPIs

> **Proyecto:** e-Visor · Ecocampus UPB · Fase A2.3  
> **Marco:** ISO 50001 · ESG · Ley 2169 de 2021  
> **Granularidad temporal:** 1 hora por bloque (medidor)

---

## Tabla 1 — Indicadores energéticos y de sostenibilidad

| Indicador | Fórmula | Explicación | Variable(s) usada(s) | Archivo / Fuente |
|-----------|---------|-------------|----------------------|-----------------|
| **LF** — Load Factor (Factor de carga) | `LF = promedio(activepower) / máximo(activepower)` | Mide la uniformidad de la curva de carga. Valores cercanos a 1 indican estabilidad y buena utilización de la capacidad instalada. | `activepower` | Medidores Landis |
| **PAR** — Peak to Average Ratio | `PAR = máximo(activepower) / promedio(activepower)` | Indica cuántas veces la demanda pico supera la demanda promedio. Es el inverso del LF; valores altos señalan picos de consumo pronunciados. | `activepower` | Medidores Landis |
| **f₁** — Uniformidad de franja diurna | `f₁ = promedio(activepower_operación) / máximo(activepower_operación)` | Uniformidad del consumo dentro de la franja operacional (06:00–21:59). Análogo al LF pero restringido al horario de uso activo del campus. | `activepower` | Medidores Landis |
| **f₂** — Coeficiente de variación de carga (CV) | `f₂ = σ(activepower_operación) / promedio(activepower_operación)` | Mide la variabilidad relativa de la demanda dentro de la franja operacional. Valores altos indican curva de carga errática con cambios bruscos frecuentes; valores bajos indican consumo estable. | `activepower` | Medidores Landis |
| **f₃** — Relación mínimo–promedio | `f₃ = mínimo(activepower_operación) / promedio(activepower_operación)` | Estabilidad relativa del consumo respecto al promedio en la franja operacional. Detecta caídas de carga anómalas o subutilización de equipos en horas de operación. | `activepower` | Medidores Landis |
| **f₄** — Factor de carga no operacional | `f₄ = promedio(activepower_no_op) / promedio(activepower_op)` · no operación = 22:00–05:59 · operación = 06:00–21:59 | Razón entre la potencia promedio en franja no operacional y la potencia promedio en franja operacional. Revela consumo fuera de horario; valores altos indican equipos encendidos innecesariamente durante la noche. | `activepower` | Medidores Landis |
| **HU** — Horas de utilización | `HU [h] = Σ(activeenergyimportday [Wh]) / (1 000 × máximo(activepower [W]))` | Número de horas equivalentes al nivel de máxima potencia necesarias para acumular el consumo total del período. Conecta la dimensión de energía con la de potencia. | `activeenergyimportday`, `activepower` | Medidores Landis |
| **CO₂** — Emisiones de carbono | `CO₂ [tCO₂e] = 9,7018 × 10⁻⁸ × Σ(activeenergyimportday [Wh])` | Conversión del consumo eléctrico a toneladas de CO₂ equivalente mediante el factor de emisión del SIN colombiano (XM S.A. E.S.P., resultado preliminar 2025). Actualizar FE cada año con la publicación de XM. | `activeenergyimportday` | Medidores Landis |
| **IGS** — Yield Factor (Rendimiento específico FV) | `IGS = Σ(energyproducedtoday) / P_instalada [kWp]` | Energía producida normalizada por la potencia pico instalada. Permite comparar plantas de distinto tamaño e independiza el resultado de la irradiancia. | `energyproducedtoday`, `solarirradiation` | Fronius / Enphase + Sensor climático |
| **TCP** — Temperatura crítica de panel | `ΔT = promedio(paneltemperature) − promedio(ambienttemperature)` | Sobrecalentamiento de paneles respecto al ambiente. Se recomienda complementar con el efecto calculado sobre la reducción de eficiencia (pérdida orientadora: −0,4 %/°C sobre Tc) para hacerlo directamente accionable. | `paneltemperature`, `ambienttemperature` | Sensor Fronius |
| **EB** — Eficiencia de batería | `EB = Σ(energyfrombattery) / Σ(energytobattery)` | Eficiencia del ciclo carga–descarga del sistema de almacenamiento. Valores inferiores al 90 % pueden indicar degradación de celdas o pérdidas de conversión anómalas. | `energyfrombattery`, `energytobattery` | Inversor / Sistema de baterías |
| **Ahorro** — Ahorro energético verificado | `Ahorro (%) = [1 − (E_actual / E_base_ajustada)] × 100` · E_base_ajustada = consumo del período equivalente del año anterior, normalizado por ocupación y temperatura (ISO 50001, Anexo B) | Cuantifica la reducción de consumo respecto a una línea base ajustada por variables de influencia (ocupación, temperatura, m²). Requiere formalizar explícitamente el baseline; sin ajuste, el indicador puede ser manipulable o no comparable entre períodos. | `activeenergyimportday` | Medidores Landis |
| **Desbalance de tensión** | `DB (%) = [máx(|v₁−v̄|, |v₂−v̄|, |v₃−v̄|) / v̄] × 100` · `v̄ = (v₁ + v₂ + v₃) / 3` (Método NEMA MG-1) | Mide el desvío porcentual máximo entre cada fase y la tensión trifásica promedio. Valores altos indican mala calidad de la energía, pérdidas adicionales y riesgo para cargas trifásicas sensibles (motores, servidores, equipos de laboratorio). | `v1`, `v2`, `v3` | Medidores Landis |

---

## Tabla 2 — KPIs de gestión energética y sostenibilidad

### Grupo 1 — Eficiencia energética

| KPI | Unidad | Fórmula | Umbral de alerta | Variables | Fuente | Norma / Referencia | ODS |
|-----|--------|---------|-----------------|-----------|--------|--------------------|-----|
| **KPI 01** — Consumo por metro cuadrado | kWh/m²·mes | `IE_área = Σ(activeenergyimportday ÷ 1 000) / Área_bloque` | Referencia orientadora: 8–25 kWh/m²·mes (edificios educativos, UPME Guía PGEE). Umbral propio: a definir con el primer ciclo académico completo (≥ 12 meses). | `activeenergyimportday` [Wh], `Área_bloque` [m²] ⚠️ *Pendiente: obtener de Planeación Física UPB* | Medidores Landis | Guía NQA §6.4 · UPME Guía PGEE | 7, 9 |
| **KPI 02** — Intensidad energética por usuario | kWh/usuario·mes | `IE = Σ(activeenergyimportday ÷ 1 000) / N_usuarios_activos` | A definir con datos del primer ciclo académico completo. | `activeenergyimportday` [Wh], `N_usuarios_activos` ⚠️ *Pendiente: definir institucionalmente (matriculados + FTE)* | Medidores Landis + Sistemas académicos / RRHH | Guía NQA §6.4–6.5 | 4, 7, 9 |
| **KPI 04** — Ahorro energético verificado | % | `Ahorro (%) = [1 − Σ(E_actual ÷ 1 000) / E_base_ajustada] × 100` · E_base_ajustada = año anterior normalizado por ocupación y temperatura (ISO 50001, Anexo B) | ≥ 3 % de reducción anual frente a la línea base ajustada. | `activeenergyimportday` [Wh], `E_base_ajustada` (construir en el primer año) | Medidores Landis | Ley 2169/2021 · UPME Guía PGEE · ISO 50001 Anexo B | 7, 9, 13 |

### Grupo 2 — Gestión de demanda

| KPI | Unidad | Fórmula | Umbral de alerta | Variables | Fuente | Norma / Referencia | ODS |
|-----|--------|---------|-----------------|-----------|--------|--------------------|-----|
| **KPI 03** — Pico de demanda absoluto | kW (+ fecha y hora) | `D_pico = máximo(activepower)` en el período, por bloque. Registrar fecha, hora y bloque de ocurrencia. | A definir con el primer año: media mensual del pico + 1σ. Reducción del pico como objetivo de mejora continua. | `activepower` [kW] | Medidores Landis | CREG (cargo por demanda máxima) · Lineamientos e-Visor §5 | 7, 9 |
| **KPI 08** — Factor de carga (Load Factor) | Adimensional (0–1) | `LF = promedio(activepower) / máximo(activepower)` en el período, por bloque | LF ≥ 0,65. Referencia bibliográfica: media de 0,67 en campus universitarios (Papadopoulos et al., 2016; rango 0,55–0,80). | `activepower` [kW] | Medidores Landis | Papadopoulos et al. (2016) | 7, 9 |
| **KPI 09** — Índice de consumo nocturno (f₄) | % | `f₄ = [Σ(E_22h–07h ÷ 1 000) / Σ(E_total ÷ 1 000)] × 100` · Franja nocturna: 22:00–07:00 h | Alerta operativa: f₄ > 20 %. Objetivo de eficiencia: f₄ < 10 %. Rango en campus universitarios: 8–22 %. | `activeenergyimportday` [Wh] segmentado por `time_index_colombia` | Medidores Landis | Papadopoulos et al. (2016), ec. 7 | 7, 9 |

### Grupo 3 — Sostenibilidad y generación renovable

| KPI | Unidad | Fórmula | Umbral de alerta | Variables | Fuente | Norma / Referencia | ODS |
|-----|--------|---------|-----------------|-----------|--------|--------------------|-----|
| **KPI 05** — Emisiones de CO₂ (huella de carbono) | tCO₂e | `CO₂ = FE_año × Σ(activeenergyimportday ÷ 1 000)` · FE_2025 = 0,097018 tCO₂e/MWh (XM S.A. E.S.P., publicado 30 ene 2026). ⚠️ *Actualizar FE cada año.* | Meta operativa anual: ≥ 3 % de reducción frente al año anterior. Meta estratégica: carbono neutralidad (0 neto). | `activeenergyimportday` [Wh] | Medidores Landis | Ley 2169/2021 · XM S.A. E.S.P. · UPME Guía PGEE | 7, 13, 17 |
| **KPI 06** — Performance Ratio del sistema FV (PR) | % | `PR = (YF / RY) × 100` · `YF = Σ(energyproducedtoday) / P_instalada` [kWh/kWp] · `RY = Σ(solarirradiation × Δt) / 1 000` [h ref.] · Δt = 1 h (resolución horaria) | Objetivo: PR ≥ 75 %. Alerta de falla técnica: PR < 65 %. | `energyproducedtoday` [kWh] (Fronius Blq. 11 / Enphase Blq. 10), `solarirradiation` [W/m²] (Sensor Fronius), `P_instalada` [kWp] ⚠️ *Pendiente: confirmar potencia exacta bloques 10 y 11. No calcular hasta definir resolución de archivos Fronius.* | Fronius / Enphase + Sensor climático | IEC 61724-1:2017 §7.3 · Kumar et al. (2019) | 7, 9, 13 |
| **KPI 07** — Fracción de autosuficiencia solar (SS) | % | `SS = [Σ(E_solar_autoconsumida) / Σ(E_consumida_red ÷ 1 000 + E_solar_AC)] × 100` · Si no hay medidor de exportación: `E_solar_autoconsumida ≈ energyproducedtoday` (proxy conservador) | ≥ 15 % orientador. Revisar con la generación real del primer año de operación completa. | `energyproducedtoday` [kWh], `activeenergyimportday` [Wh] ⚠️ *Pendiente: verificar si inversor XW registra energía exportada a red.* | Fronius / Enphase + Medidores Landis | GRI 302-1 · Ley 2169/2021 | 7, 13, 17 |

### Grupo 4 — Calidad del suministro eléctrico

| KPI | Unidad | Fórmula | Umbral de alerta | Variables | Fuente | Norma / Referencia | ODS |
|-----|--------|---------|-----------------|-----------|--------|--------------------|-----|
| **KPI 10** — Desbalance de tensión | % | `DB = [máx(|v₁−v̄|, |v₂−v̄|, |v₃−v̄|) / v̄] × 100` · `v̄ = (v₁ + v₂ + v₃) / 3` (Método NEMA MG-1) | < 2 % condición normal. Alerta si ≥ 2 % durante **3 o más horas consecutivas** (evita falsas alarmas por transitorios). | `v1`, `v2`, `v3` [V] | Medidores Landis | IEEE 1159:2019 §4.4 · NTC 5001 | 9 |
| **KPI 11** — Factor de potencia total | Adimensional (0–1) | `FP = totalpowerfactor` (variable directa del medidor — no requiere cálculo adicional) | FP ≥ 0,9 condición normal. Alerta si FP < 0,9 durante **3 o más horas consecutivas**. En alerta, complementar con `reactivepower` [kVAr]. | `totalpowerfactor` | Medidores Landis | Resolución CREG 108/1997 · NTC 5001 | 9 |
| **KPI 12** — Distorsión armónica total de voltaje (THD-V) | % | `THD_V = relativethdvoltage` (variable directa del medidor — no requiere cálculo adicional). Para diagnóstico por fase: `harmonicsv1`, `harmonicsv2`, `harmonicsv3`. | THD-V < 5 % condición normal (sistemas BT ≤ 1 kV). Alerta si ≥ 5 % de forma sostenida. | `relativethdvoltage` [%] · diagnóstico: `harmonicsv1`, `harmonicsv2`, `harmonicsv3` [%] | Medidores Landis | IEEE 519:2022 §5 · NTC 5001 | 9 |

---

## Notas generales

- **Factor de emisión CO₂:** El valor correcto y vigente es **0,097018 tCO₂e/MWh** (XM S.A. E.S.P., publicado el 30 de enero de 2026 para el año 2025). El valor de 0,18 tCO₂/MWh que aparece en versiones anteriores del proyecto está desactualizado y debe reemplazarse en todos los sistemas.
- **Datos pendientes de fuentes externas:** KPI 01 y la intensidad de carbono (tCO₂e/m²) del indicador CO₂ requieren el `Área_bloque` de Planeación Física UPB. KPI 02 requiere `N_usuarios_activos` de sistemas académicos y RRHH. KPI 06 requiere confirmar la resolución temporal de los archivos Fronius antes de calcular.
- **Consistencia de f₄:** La definición de f₄ adoptada en los KPIs (fracción de energía consumida en horario nocturno, Papadopoulos et al., 2016, ec. 7) es conceptualmente distinta al f₄ de los indicadores (ratio de potencias promedio operacional/no operacional). La métrica de comparación semanal se recomienda formalizar como **Índice de Consistencia Semanal** en una etapa posterior.
- **Criterio de persistencia (KPI 10 y 11):** El umbral de 3 horas consecutivas es consistente con la evaluación de condiciones sostenidas que propone IEEE 1159:2019 y evita falsas alarmas por eventos transitorios (arranques de motores, conmutaciones breves).

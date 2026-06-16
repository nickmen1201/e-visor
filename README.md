# e-Visor — Dashboard Energético Ecocampus UPB

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![Pandas](https://img.shields.io/badge/Pandas-2.x-purple)
![Plotly](https://img.shields.io/badge/Plotly-5.x-lightgrey)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)

Sistema de indicadores y KPIs energéticos para el **Ecocampus UPB (Medellín)**. Transforma datos crudos de medidores IoT Landis en métricas estratégicas presentadas en un dashboard interactivo de Streamlit.

---

## Inicio Rápido

```powershell
pip install streamlit pandas numpy matplotlib plotly openpyxl
python -m streamlit run 2026/dashboard.py
```

El dashboard lee `2026/resultados_e-visor.xlsx` generado por el notebook de cálculo.

---

## Flujo del Proyecto

```
Archivos CSV (etsmartmeter_*.csv)
        ↓
limpieza_datos.ipynb  →  etsmartmeter_clean.csv
        ↓
notebook_evisor_calculo.ipynb  →  resultados_e-visor.xlsx
        ↓
dashboard.py  →  Dashboard Streamlit
```

### 1. Limpieza de datos

`2026/limpieza_datos.ipynb` carga los archivos CSV del medidor inteligente Landis, sanea la información y exporta `etsmartmeter_clean.csv` y `etsmartmeter_clean.parquet`.

### 2. Cálculo de indicadores y KPIs

`2026/notebook_evisor_calculo.ipynb` calcula todos los indicadores y KPIs y los exporta en formato largo a `2026/resultados_e-visor.xlsx` con dos hojas:

| Hoja | Contenido | Granularidad |
|---|---|---|
| `Indicadores` | IND-01 a IND-13 por bloque | Diaria / horaria / mensual |
| `KPIs` | KPI-01 a KPI-11 por bloque | Mensual |

### 3. Dashboard operativo

`2026/dashboard.py` expone los resultados en Streamlit con dos pestañas:

- **Indicadores** — LF, PAR, f₁, f₂, f₃, f₄, CO₂, desbalance de tensión
- **KPIs** — consumo/m², pico de demanda, emisiones CO₂, Load Factor, consumo no operacional, desbalance, factor de potencia

---

## Indicadores

| ID | Nombre | Granularidad | Estado |
|---|---|---|---|
| IND-01 | Load Factor (LF) | Diario | ✅ Activo |
| IND-02 | Peak-to-Average Ratio (PAR) | Diario | ✅ Activo |
| IND-03 | Uniformidad operacional (f₁) | Diario | ✅ Activo |
| IND-04 | Coeficiente de variación (f₂) | Diario | ✅ Activo |
| IND-05 | Relación mínimo-promedio (f₃) | Diario | ✅ Activo |
| IND-06 | Factor de carga no operacional (f₄) | Diario | ✅ Activo |
| IND-07 | Emisiones CO₂ | Mensual | ✅ Activo |
| IND-08 | Yield Factor FV (IGS) | — | ⏳ Pendiente datos FV |
| IND-09 | Temp. crítica de panel (TCP) | — | ⏳ Pendiente sensor Fronius |
| IND-10 | Eficiencia de batería (EB) | — | ⏳ Pendiente inversor baterías |
| IND-11 | Ahorro energético | — | ⏳ Pendiente línea base 12 meses |
| IND-12 | Desbalance de tensión (VU) | Horario | ✅ Activo |
| IND-13 | Factor de Diversidad (FD) | Mensual | ✅ Activo |

---

## KPIs

| # | Nombre | Unidad | Estado |
|---|---|---|---|
| KPI-01 | Consumo por m² | kWh/m² | ✅ Real |
| KPI-02 | Intensidad por usuario | kWh/usuario | ⚠️ DEMO — N_usuarios pendiente |
| KPI-03 | Pico de demanda | kW + timestamp | ✅ Real |
| KPI-04 | Ahorro energético verificado | % | ⚠️ DEMO — línea base pendiente |
| KPI-05 | Emisiones CO₂ | tCO₂e | ✅ Real |
| KPI-06 | Performance Ratio FV | % | ⚠️ DEMO — datos FV no disponibles |
| KPI-07 | Autosuficiencia solar | % | ⚠️ DEMO — datos FV no disponibles |
| KPI-08 | Load Factor | 0–1 | ✅ Real |
| KPI-09 | Consumo no operacional | % | ✅ Real |
| KPI-10 | Desbalance de tensión | % | ✅ Real |
| KPI-11 | Factor de potencia total | — | ✅ Real |

---

## Estructura del Proyecto

```
README.md
_config.yml                          ← configuración GitHub Pages
2026/
  CONTEXT.md                         ← contexto y reglas del proyecto
  ecocampus_kpis_indicadores.json    ← especificación de indicadores y KPIs
  AREAS 2026.xlsx                    ← áreas construidas por bloque (m²)
  dashboard.py                       ← dashboard Streamlit (dos pestañas)
  limpieza_datos.ipynb               ← saneamiento de datos crudos
  notebook_evisor_calculo.ipynb      ← cálculo de indicadores y KPIs
  etsmartmeter_*.csv                 ← datos crudos del medidor (6 archivos)
  etsmartmeter_clean.csv             ← salida de limpieza_datos.ipynb
  resultados_e-visor.xlsx            ← salida de notebook_evisor_calculo.ipynb
```

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Fuente de datos | Medidores Landis (`etsmartmeter`) vía FIWARE |
| Inversores FV | Fronius Bloque 11 · Enphase Bloque 10 |
| Procesamiento | Python 3.12 · Pandas 2.x · NumPy |
| Visualización | Streamlit · Plotly · Matplotlib |
| Almacenamiento | Excel (`.xlsx`) · CSV · Parquet |

---

## Contexto Académico

Proyecto e-Visor — **Universidad Pontificia Bolivariana, Sede Medellín**.  
Fase A2: diseño de dashboards y cálculo de indicadores (infraestructura IoT operacional).  
Alineado con ODS 7, 9 y 13 y la Ley 2169 de 2021 (Colombia).

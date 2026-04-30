# e-visor

![Python](https://img.shields.io/badge/Python-3776ab?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37726?style=flat-square&logo=jupyter&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557c?style=flat-square&logo=python&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)

E-visor es un proyecto de análisis y visualización energética para el **Ecocampus UPB**. Integra datos crudos del medidor inteligente, calcula indicadores y KPIs energéticos, y los expone en un dashboard interactivo de Streamlit.

## Inicio Rápido

```powershell
pip install streamlit pandas numpy matplotlib plotly jupyter openpyxl
python -m streamlit run 2026/dashboard.py
```

## Estado Actual

El proyecto tiene una cadena funcional notebook → CSV → dashboard. Conviven cuatro capas:

- `2026/limpieza_datos.ipynb`: preparación y saneamiento de los datos crudos del medidor.
- `2026/calculo_indicadores_kpis_2026.ipynb`: cálculo de indicadores y KPIs diarios.
- `2026/visualizaciones_evisor.ipynb`: espacio modular para probar nuevas formas de visualización de forma simple y rápida.
- `2026/dashboard.py`: implementación completa del dashboard en Streamlit, organizada en dos pestañas (Indicadores y KPIs).

### Indicadores en el dashboard

**11 indicadores** actualmente presentados en la pestaña Indicadores:

- LF, PAR, f₁, f₂, f₃, f₄, HU, CO₂, desbalance, FP, THD-V

### KPIs en el dashboard

**7 KPIs** actualmente presentados en la pestaña KPIs:

- KPI03, KPI05, KPI08, KPI09, KPI10, KPI11, KPI12

**Nota:** KPI01 (consumo por m²) y KPI07 (autosuficiencia solar) no se presentan porque requieren datos externos no disponibles (`Área_bloque` y `energyproducedtoday` respectivamente). Se calculan en los notebooks pero no persisten en CSV ni aparecen en el dashboard.

## Flujo Del Proyecto

### 1. Limpieza de datos

`2026/limpieza_datos.ipynb` carga los archivos xlsx del medidor, sanea la información y exporta `etsmartmeter_clean.csv` y `etsmartmeter_clean.parquet`.

### 2. Cálculo de indicadores y KPIs

`2026/calculo_indicadores_kpis_2026.ipynb` construye los agregados diarios:

- `2026/indicadores_diarios.csv` / `indicadores_diarios.xlsx`
- `2026/kpis_diarios.csv` / `kpis_diarios.xlsx`

La lógica prioriza la validez operativa: no se aplica eliminación de valores atípicos porque esos puntos pueden reflejar eventos reales relevantes para la gestión energética.

### 3. Visualización exploratoria

`2026/visualizaciones_evisor.ipynb` se usa como laboratorio de visualización modular. Su objetivo actual es probar nuevas representaciones de forma sencilla, reutilizando los CSV ya calculados y permitiendo iterar rápido sobre alternativas gráficas antes de decidir qué llevar al producto final.

### 4. Dashboard operativo

`2026/dashboard.py` contiene la implementación completa del dashboard en Streamlit. Organiza la vista en pestañas de Indicadores y KPIs, incluye widgets específicos para f4 y CO2, y compara valores recientes contra el mismo día de la semana anterior.


## Estructura Del Proyecto

```text
README.md
2026/
  CONTEXT.md
  evisor_indicadores_kpis.md
  dashboard.py
  limpieza_datos.ipynb
  calculo_indicadores_kpis_2026.ipynb
  visualizaciones_evisor.ipynb
  etsmartmeter_2026-03-12_17-47-37.xlsx        ← datos crudos del medidor (7 partes)
  etsmartmeter_2026-03-12_17-49-36_parte_2.xlsx
  etsmartmeter_2026-03-12_17-51-33_parte_3.xlsx
  etsmartmeter_2026-03-12_17-53-27_parte_4.xlsx
  etsmartmeter_2026-03-12_17-55-22_parte_5.xlsx
  etsmartmeter_2026-03-12_17-57-15_parte_6.xlsx
  etsmartmeter_2026-03-12_17-59-20_parte_7.xlsx
  etsmartmeter_clean.csv                        ← salida de limpieza_datos.ipynb
  etsmartmeter_clean.parquet
  indicadores_diarios.csv                       ← salida de calculo_indicadores_kpis_2026.ipynb
  indicadores_diarios.xlsx
  kpis_diarios.csv
  kpis_diarios.xlsx
```

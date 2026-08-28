import re
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_chart_n = [0]

def _chart(fig, **kwargs):
    _chart_n[0] += 1
    ucw = kwargs.pop('use_container_width', None)   # API deprecada → width=
    if ucw is not None:
        kwargs.setdefault('width', 'stretch' if ucw else 'content')
    st.plotly_chart(fig, key=f"c{_chart_n[0]}", **kwargs)

st.set_page_config(page_title="E-Visor · Ecocampus UPB", layout="wide",
                   initial_sidebar_state="expanded")

# ── Sistema de diseño ───────────────────────────────────────────────────────
# Paleta validada con dataviz/scripts/validate_palette.js (light + dark: PASS).
#
# STATUS (reservado — solo semáforo, nunca como color de serie):
C_TEAL   = '#157347'   # verde — positivo / cumple objetivo
C_AMBER  = '#B7791F'   # ámbar — advertencia (máx. distancia perceptual del verde/rojo)
C_RED    = '#B42318'   # rojo  — alerta
# CATEGÓRICO (identidad — orden fijo, nunca cíclico):
C_BLUE   = '#1F5CA8'   # azul medio (barras comparativas / serie 1)
C_PURPLE = '#7B3EA7'   # violeta   (líneas secundarias / serie 2)
C_GRAY   = '#8A97A6'   # gris azulado (referencia / media móvil)
C_BG     = '#F6F8FA'   # fondo principal

# Tokens de superficie y tinta (data-product claro)
INK      = '#0E1726'   # texto principal / números
INK2     = '#5A6675'   # texto secundario / ejes
MUTED    = '#8A97A6'   # texto terciario / captions
SURFACE  = '#FFFFFF'   # tarjetas
BORDER   = '#E6E9EF'   # bordes discretos
GRID     = '#EFF2F6'   # grillas recesivas
# Acento de marca UPB (magenta→violeta) — SOLO detalles, nunca dato
BRAND_A  = '#FF003D'
BRAND_B  = '#AD3DFF'

# ── Plantilla global de Plotly (todas las figuras heredan de aquí) ────────────
import plotly.io as pio

_FONT = 'IBM Plex Sans, -apple-system, Segoe UI, Helvetica, Arial, sans-serif'
_MONO = 'IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, monospace'

pio.templates['evisor'] = go.layout.Template(layout=dict(
    font=dict(family=_FONT, size=12, color=INK),
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    colorway=[C_BLUE, C_PURPLE, C_TEAL, C_AMBER, C_RED, C_GRAY],
    barcornerradius=4,
    title=dict(font=dict(family=_FONT, size=13, color=INK), x=0, xref='paper'),
    margin=dict(t=48, b=44, l=64, r=24),
    xaxis=dict(gridcolor=GRID, linecolor=BORDER, zerolinecolor=GRID,
               tickfont=dict(size=11, color=INK2),
               title=dict(font=dict(size=11.5, color=INK2))),
    yaxis=dict(gridcolor=GRID, linecolor=BORDER, zerolinecolor=GRID,
               tickfont=dict(size=11, color=INK2),
               title=dict(font=dict(size=11.5, color=INK2))),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                font=dict(size=11, color=INK2), bgcolor='rgba(0,0,0,0)'),
    colorscale=dict(sequential=[
        [0.0, '#EAF0F8'], [0.5, '#5A8AC6'], [1.0, C_BLUE]]),
    hoverlabel=dict(font=dict(family=_FONT, size=12), bgcolor=INK,
                    bordercolor=INK, font_color='#FFFFFF'),
))
pio.templates.default = 'evisor'

BASE = Path(__file__).parent

# ── Constantes ────────────────────────────────────────────────────────────────
HORA_OP_INI = 6
HORA_OP_FIN = 22

FACTOR_EMISION_CO2        = 9.7018e-8
ARBOLES_POR_TON_CO2       = 45
TON_CO2_POR_VUELO_MDE_BOG = 0.18
TON_CO2_POR_VEHICULO_ANO  = 4.6

AREAS_BLOQUE = {
    3:   4778.68,
    4:  10309.89,
    5:  10008.87,
    7:   4834.72,
    8:   3836.47,
    9:   7579.50,   # B9 total (SFA1 + SFA2)
    10: 11469.06,
    12:  2848.88,
    15:  7780.01,
    17:  7611.12,
    18: 35916.80,
    '9.1':      3789.75,   # SFA1 — usado solo en carga intermedia
    '9.2':      3789.75,   # SFA2 — usado solo en carga intermedia
    'Ecovilla': 0.0,       # área sin confirmar
}

# Mapeo entity_id → etiqueta de display
_ENTITY_TO_LABEL = {
    'SmartMeter_SM_B9':       'B9',
    'SmartMeter_SM_ECOVILLA': 'Ecovilla',
}

# Mapeo bloque (string) → entity_id canónico
_BLOQUE_TO_ENTITY = {
    '9.1':      'SmartMeter_SM_B9_SFA1',
    '9.2':      'SmartMeter_SM_B9_SFA2',
    'Ecovilla': 'SmartMeter_SM_ECOVILLA',
}

TARIFA_BASE_COP_KWH   = 859.19
TARIFA_INDCOM_COP_KWH = 1_031.03
HOGAR_KWH_MES         = 130

UMBRAL_FP_OBJ   = 0.90
UMBRAL_FP_ALERT = 0.85
UMBRAL_DB_OBJ   = 2.0   # JSON spec: objetivo < 2% normal (IEEE 1159:2019)
UMBRAL_DB_ALERT = 3.0   # JSON spec: alerta ≥ 3%

_DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

# ── CSS · Sistema de diseño (data-product, tema claro) ────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root{
  --ink:#0E1726; --ink2:#5A6675; --muted:#8A97A6;
  --surface:#FFFFFF; --app:#F6F8FA; --border:#E6E9EF; --border-strong:#D8DDE6;
  --ok:#157347; --warn:#B7791F; --bad:#B42318;
  --brand-a:#FF003D; --brand-b:#AD3DFF;
  --font:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}

html, body, [class*="css"]{ font-family:var(--font); }
h1,h2,h3,h4,h5,h6,p,li,td,th,label,input,textarea,select,
[data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stWidgetLabel"],
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3,
[data-testid="stCaptionContainer"] p{ font-family:var(--font) !important; }

[data-testid="stAppViewContainer"]{ background:var(--app); }
.block-container{ padding-top:2.4rem; padding-bottom:3rem; max-width:1180px; }

/* Sidebar — hairline de marca a la derecha */
[data-testid="stSidebar"]{ background:var(--surface); border-right:1px solid var(--border); }
[data-testid="stSidebar"]::after{
  content:""; position:absolute; top:0; right:0; width:2px; height:100%;
  background:linear-gradient(180deg,var(--brand-a) 0%,var(--brand-b) 100%);
}

/* Cifras SIEMPRE en mono tabular — sello del data-product */
[data-testid="stMetricValue"], .ev-value, .num,
[data-testid="stMetricDelta"]{ font-family:var(--mono) !important; font-feature-settings:"tnum" 1,"lnum" 1; }

/* Jerarquía tipográfica */
h1{ font-size:1.55rem !important; font-weight:600 !important; color:var(--ink) !important;
    letter-spacing:-0.02em !important; line-height:1.15 !important; }
h2{ font-size:.68rem !important; font-weight:600 !important; color:var(--ink2) !important;
    text-transform:uppercase !important; letter-spacing:0.13em !important;
    padding-bottom:8px !important; margin-top:2.6rem !important; margin-bottom:1rem !important;
    border-bottom:1px solid var(--border) !important; position:relative; }
h2::before{ content:""; position:absolute; left:0; bottom:-1px; width:34px; height:2px;
    background:linear-gradient(90deg,var(--brand-a),var(--brand-b)); }
h3{ font-size:.92rem !important; font-weight:600 !important; color:var(--ink) !important;
    letter-spacing:-0.01em !important; }

/* st.metric → tarjeta limpia */
div[data-testid="stMetric"], div[data-testid="metric-container"]{
  background:var(--surface); border:1px solid var(--border); border-radius:10px;
  padding:16px 18px; box-shadow:0 1px 2px rgba(16,23,38,.04); }
div[data-testid="stMetric"] label, div[data-testid="metric-container"] label{
  font-size:.66rem !important; font-weight:600 !important; color:var(--ink2) !important;
  text-transform:uppercase !important; letter-spacing:0.08em !important; }
[data-testid="stMetricValue"]{ font-size:1.5rem !important; font-weight:600 !important; color:var(--ink) !important; }

/* Header / topbar */
.ev-topbar{ display:flex; align-items:baseline; justify-content:space-between; gap:16px;
  margin:2px 0 2px 0; }
.ev-topbar .ev-sub{ font-size:.82rem; color:var(--ink2); }
.ev-rule{ height:2px; border:0; margin:14px 0 6px 0;
  background:linear-gradient(90deg,var(--brand-a) 0%,var(--brand-b) 42%,var(--border) 42%,var(--border) 100%); }

/* Grid de KPIs hero */
.ev-grid{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:8px 0 4px 0; }
.ev-kpi{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
  padding:16px 18px 14px 18px; box-shadow:0 1px 2px rgba(16,23,38,.04);
  transition:box-shadow .15s ease,transform .15s ease; }
.ev-kpi:hover{ box-shadow:0 6px 20px rgba(16,23,38,.08); transform:translateY(-1px); }
.ev-eyebrow{ font-size:.64rem; font-weight:600; color:var(--ink2); text-transform:uppercase;
  letter-spacing:0.1em; margin-bottom:8px; }
.ev-value{ font-size:1.85rem; font-weight:600; color:var(--ink); line-height:1; letter-spacing:-0.01em; }
.ev-unit{ font-family:var(--font); font-size:.82rem; font-weight:500; color:var(--muted); margin-left:4px; }
.ev-spark{ margin:10px 0 8px 0; height:30px; }
.ev-foot{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; font-size:.76rem; color:var(--ink2); }
.ev-delta{ font-family:var(--mono); font-feature-settings:"tnum" 1; }

/* Pills de estado (siempre punto + palabra, nunca color solo) */
.pill{ display:inline-flex; align-items:center; gap:5px; padding:2px 9px; border-radius:999px;
  font-size:.7rem; font-weight:600; line-height:1.5; letter-spacing:.01em; border:1px solid transparent; }
.pill::before{ content:""; width:6px; height:6px; border-radius:50%; background:currentColor; }
.pill-ok{ color:var(--ok);  background:rgba(21,115,71,.09);  border-color:rgba(21,115,71,.18); }
.pill-warn{ color:var(--warn); background:rgba(183,121,31,.10); border-color:rgba(183,121,31,.20); }
.pill-bad{ color:var(--bad);  background:rgba(180,35,24,.09);  border-color:rgba(180,35,24,.18); }
.pill-demo{ color:#6B48B0; background:rgba(122,62,167,.09); border-color:rgba(122,62,167,.18); }

.status-verde{ color:var(--ok); font-weight:600; }
.status-ambar{ color:var(--warn); font-weight:600; }
.status-rojo{ color:var(--bad); font-weight:600; }

/* Tabs — subrayado de marca en la activa */
button[data-baseweb="tab"]{ padding-left:2px !important; padding-right:2px !important; }
button[data-baseweb="tab"] p{ font-size:.72rem !important; font-weight:600 !important;
  text-transform:uppercase !important; letter-spacing:0.09em !important; color:var(--ink2) !important; }
button[data-baseweb="tab"][aria-selected="true"] p{ color:var(--ink) !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] div{
  background:linear-gradient(90deg,var(--brand-a),var(--brand-b)) !important; }
div[data-baseweb="tab-list"]{ gap:26px; border-bottom:1px solid var(--border); }

/* Bloques de contexto (info/callout) */
.ev-note{ border:1px solid var(--border); border-left:3px solid var(--warn);
  background:#FCFAF5; border-radius:10px; padding:14px 18px; margin-bottom:14px; }

hr{ border-color:var(--border) !important; margin:1.2rem 0 !important; }
[data-testid="stCaptionContainer"] p{ font-size:.73rem !important; color:var(--muted) !important; }
[data-testid="stDivider"]{ margin:.4rem 0 !important; }
</style>
""", unsafe_allow_html=True)


def _parse_bloque(b):
    if b is None or (isinstance(b, float) and b != b):
        return b
    s = str(b).strip()
    try:
        f = float(s)
        return int(f) if f == int(f) else s  # "9" → 9, "9.1" → "9.1"
    except ValueError:
        return s  # "Ecovilla", "CAMPUS_TOTAL"


def _entity_id_for(bloque):
    key = str(bloque)
    return _BLOQUE_TO_ENTITY.get(key, f'SmartMeter_SM_{bloque}')


def _bloque_label(entity_id):
    if entity_id in _ENTITY_TO_LABEL:
        return _ENTITY_TO_LABEL[entity_id]
    return entity_id.replace('SmartMeter_SM_', 'B')


def _bloque_de_medidor(entity_id):
    """Medidor del CSV crudo → bloque: 'SmartMeter_SM_B7_CTIC' → 'B7'.

    Los identificadores del CSV crudo (por medidor) y los del Excel (por bloque)
    viven en espacios distintos: un bloque puede tener varios medidores
    (B7 = CTIC + TAC, B8 = AA + CPA + LABS, B9 = SFA1 + SFA2).
    """
    if entity_id in _ENTITY_TO_LABEL:
        return _ENTITY_TO_LABEL[entity_id]
    return entity_id.replace('SmartMeter_SM_', '').split('_')[0]


# ═══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def cargar_datos():
    xl = pd.ExcelFile(BASE / 'resultados_e-visor.xlsx')

    ind_raw = xl.parse('Indicadores')
    ind_raw['valor_num'] = pd.to_numeric(ind_raw['valor'], errors='coerce')

    _IND_MAP = {
        'IND-01': 'LF', 'IND-02': 'PAR', 'IND-03': 'f1',
        'IND-04': 'f2_CV', 'IND-05': 'f3', 'IND-06': 'f4',
    }
    daily_raw = (ind_raw[ind_raw['indicador'].isin(_IND_MAP)]
                 [['indicador', 'bloque', 'fecha', 'valor_num']]
                 .dropna(subset=['bloque', 'fecha'])
                 .copy())
    daily_raw['fecha'] = pd.to_datetime(daily_raw['fecha'])
    ind = (daily_raw
           .pivot_table(index=['bloque', 'fecha'], columns='indicador',
                        values='valor_num', aggfunc='mean')
           .reset_index())
    ind.columns.name = None
    ind.rename(columns=_IND_MAP, inplace=True)
    ind['bloque'] = ind['bloque'].map(_parse_bloque)

    d12 = (ind_raw[ind_raw['indicador'] == 'IND-12']
           [['bloque', 'fecha', 'valor_num']]
           .dropna(subset=['bloque']).copy())
    d12['fecha']  = pd.to_datetime(d12['fecha'])
    d12['bloque'] = d12['bloque'].map(_parse_bloque)
    d12 = (d12.groupby(['bloque', 'fecha'])['valor_num']
              .mean().reset_index()
              .rename(columns={'valor_num': 'desbalance_pct'}))
    ind = pd.merge(ind, d12, on=['bloque', 'fecha'], how='outer')

    d07 = (ind_raw[ind_raw['indicador'] == 'IND-07']
           [['bloque', 'mes', 'valor_num']]
           .dropna(subset=['bloque']).copy()
           .rename(columns={'valor_num': 'co2_mes'}))
    d07['bloque'] = d07['bloque'].map(_parse_bloque)
    co2_rows = []
    for _, row in d07.iterrows():
        b, mes_str, co2 = row['bloque'], row['mes'], row['co2_mes']
        if pd.isna(co2):
            continue
        start = pd.Timestamp(f'{mes_str}-01')
        end   = start + pd.offsets.MonthEnd(0)
        mask  = (ind['bloque'] == b) & (ind['fecha'] >= start) & (ind['fecha'] <= end)
        dates = ind[mask]['fecha'].unique()
        if len(dates) == 0:
            continue
        cpd = co2 / len(dates)
        for d in dates:
            co2_rows.append({'bloque': b, 'fecha': d, 'CO2_tCO2e': cpd})
    if co2_rows:
        ind = pd.merge(ind, pd.DataFrame(co2_rows), on=['bloque', 'fecha'], how='left')
    else:
        ind['CO2_tCO2e'] = np.nan

    ind['entity_id']   = ind['bloque'].map(_entity_id_for)
    ind['fp_promedio'] = np.nan
    ind['fecha']       = pd.to_datetime(ind['fecha'])

    kpi_raw = xl.parse('KPIs')
    kpi_raw['valor_num']  = pd.to_numeric(kpi_raw['valor'], errors='coerce')
    kpi_raw['bloque_int'] = kpi_raw['bloque'].map(_parse_bloque)
    kpi_raw['fecha'] = (pd.to_datetime(kpi_raw['mes'], format='%Y-%m', errors='coerce')
                        + pd.offsets.MonthEnd(0))
    _KPI_MAP = {
        'KPI-01': 'KPI01_kwh_m2', 'KPI-03': 'KPI03_pico_kw',
        'KPI-05': 'KPI05_CO2_tCO2e', 'KPI-08': 'KPI08_LF',
        'KPI-09': 'KPI09_f4_pct', 'KPI-10': 'KPI10_desbalance_pct',
        'KPI-11': 'KPI11_fp',
    }
    # Solo KPIs con bloque numérico o string conocido (excluye CAMPUS_TOTAL, Bloques 10-11)
    kpi_long = (kpi_raw[kpi_raw['kpi'].isin(_KPI_MAP)]
                [['kpi', 'bloque_int', 'fecha', 'mes', 'valor_num']]
                .dropna(subset=['bloque_int']).copy()
                .rename(columns={'bloque_int': 'bloque'}))
    kpi = (kpi_long
           .pivot_table(index=['bloque', 'fecha', 'mes'],
                        columns='kpi', values='valor_num', aggfunc='mean')
           .reset_index())
    kpi.columns.name = None
    kpi.rename(columns=_KPI_MAP, inplace=True)
    kpi['entity_id'] = kpi['bloque'].map(_entity_id_for)
    kpi['area_m2']   = kpi['bloque'].map(AREAS_BLOQUE)
    kpi['e_wh']      = kpi['KPI01_kwh_m2'] * kpi['area_m2'] * 1000

    k03x = (kpi_raw[kpi_raw['kpi'] == 'KPI-03']
            [['bloque_int', 'fecha', 'fecha_pico', 'hora_pico']]
            .dropna(subset=['bloque_int'])
            .rename(columns={'bloque_int': 'bloque'}))
    kpi = pd.merge(kpi, k03x, on=['bloque', 'fecha'], how='left')

    # ── DEMO KPIs (bloque puede ser texto: 'CAMPUS_TOTAL', 'Bloques 10-11') ──
    _KPI_DEMO_IDS = ['KPI-02', 'KPI-04', 'KPI-06', 'KPI-07']
    kpi_demo = (kpi_raw[kpi_raw['kpi'].isin(_KPI_DEMO_IDS)]
                [['kpi', 'bloque', 'mes', 'valor_num', 'estado', 'unidad']]
                .copy())
    kpi_demo['fecha'] = (pd.to_datetime(kpi_demo['mes'], format='%Y-%m', errors='coerce')
                         + pd.offsets.MonthEnd(0))

    # ── IND-13 — Factor de Diversidad (campus) ────────────────────────────────
    ind13 = (ind_raw[ind_raw['indicador'] == 'IND-13']
             [['mes', 'valor_num']]
             .dropna(subset=['valor_num'])
             .copy())
    # fecha puede ser NaT; derivar del campo mes (formato 'YYYY-MM')
    ind13['fecha'] = (pd.to_datetime(ind13['mes'], format='%Y-%m', errors='coerce')
                      + pd.offsets.MonthEnd(0))

    try:
        raw = pd.read_csv(BASE / 'clean_etsmartmeter.csv',
                          parse_dates=['time_index_colombia'])
        raw['hora']  = raw['time_index_colombia'].dt.hour
        raw['fecha'] = pd.to_datetime(raw['time_index_colombia'].dt.date)
    except FileNotFoundError:
        raw = None

    # ── Combinar B9.1 (SFA1) + B9.2 (SFA2) → B9 ─────────────────────────────
    _b9_ind = ind['bloque'].isin(['9.1', '9.2'])
    if _b9_ind.any():
        _num = [c for c in ind.columns if c not in ('bloque', 'fecha', 'entity_id', 'fp_promedio')]
        _agg = {c: ('sum' if c == 'CO2_tCO2e' else 'mean') for c in _num}
        _b9 = ind[_b9_ind].groupby('fecha', as_index=False).agg(_agg)
        _b9['bloque']      = 9
        _b9['entity_id']   = 'SmartMeter_SM_B9'
        _b9['fp_promedio'] = np.nan
        ind = pd.concat([ind[~_b9_ind], _b9], ignore_index=True)

    _b9_kpi = kpi['bloque'].isin(['9.1', '9.2'])
    if _b9_kpi.any():
        _kn = [c for c in kpi.columns
               if c not in ('bloque', 'fecha', 'mes', 'entity_id', 'area_m2', 'fecha_pico', 'hora_pico')]
        _kagg = {c: ('sum' if c in ('e_wh', 'KPI05_CO2_tCO2e', 'KPI03_pico_kw') else 'mean')
                 for c in _kn}
        _b9k = kpi[_b9_kpi].groupby(['fecha', 'mes'], as_index=False).agg(_kagg)
        _b9k['bloque']    = 9
        _b9k['entity_id'] = 'SmartMeter_SM_B9'
        _b9k['area_m2']   = AREAS_BLOQUE[9]
        # El pico de B9 suma los dos submedidores; se registra la fecha/hora del
        # dominante de cada mes (el que aporta el mayor pico).
        _dom = (kpi[_b9_kpi].sort_values('KPI03_pico_kw')
                .drop_duplicates(subset=['fecha'], keep='last')
                [['fecha', 'fecha_pico', 'hora_pico']])
        _b9k = (_b9k.drop(columns=['fecha_pico', 'hora_pico'], errors='ignore')
                    .merge(_dom, on='fecha', how='left'))
        if 'e_wh' in _b9k.columns:
            _b9k['KPI01_kwh_m2'] = _b9k['e_wh'] / (_b9k['area_m2'] * 1000)
        kpi = pd.concat([kpi[~_b9_kpi], _b9k], ignore_index=True)

    if raw is not None:
        _b9_raw = raw['entity_id'].isin(['SmartMeter_SM_B9_SFA1', 'SmartMeter_SM_B9_SFA2'])
        if _b9_raw.any():
            _rw = (raw[_b9_raw]
                   .groupby('time_index_colombia', as_index=False)
                   .agg({'activepower': 'sum', 'hora': 'first', 'fecha': 'first'}))
            _rw['entity_id'] = 'SmartMeter_SM_B9'
            raw = pd.concat([raw[~_b9_raw], _rw], ignore_index=True)

    return ind, kpi, raw, kpi_demo, ind13


ind, kpi, raw, kpi_demo, ind13 = cargar_datos()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════



def _delta_semana(ind_df, col):
    serie = ind_df.groupby('fecha')[col].mean().sort_index()
    if serie.empty:
        return None, None, None
    fecha_hoy  = serie.index[-1]
    candidatos = serie[(serie.index.dayofweek == fecha_hoy.dayofweek) &
                       (serie.index < fecha_hoy)]
    if candidatos.empty:
        return None, None, None
    return (float(serie.iloc[-1]) - float(candidatos.iloc[-1]),
            float(candidatos.iloc[-1]), candidatos.index[-1])


def _semaforo(v, obj, alert, mayor_es_mejor=True):
    """Devuelve color hex según umbrales."""
    if mayor_es_mejor:
        return C_TEAL if v >= obj else (C_AMBER if v >= alert else C_RED)
    else:
        return C_TEAL if v <= obj else (C_AMBER if v <= alert else C_RED)


_MESES_ABR = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
              'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _fmt_fecha_hora(fecha, hora, largo=False):
    """'20 may · 14:00' — fecha y hora de ocurrencia (KPI-03 las exige)."""
    if pd.isna(fecha):
        return 's/d'
    f = pd.Timestamp(fecha)
    txt = f'{f.day} {_MESES_ABR[f.month - 1]}' + (f' {f.year}' if largo else '')
    return txt if pd.isna(hora) else f'{txt} · {int(hora):02d}:00'


# KPI-03 — umbral propio (media ± 1σ) sobre la serie mensual de picos de cada
# bloque, según ecocampus_kpis_indicadores.json → kpis[KPI-03].umbral.
UMBRAL_PICO_VENTANA   = 12   # meses de base como máximo (los más cercanos)
UMBRAL_PICO_MIN_MESES = 4    # con menos base no se emite semáforo


def _umbral_pico(serie, fecha_eval):
    """Objetivo y alerta de KPI-03 para un bloque, y tamaño de la base.

    `serie` son los picos mensuales del bloque en el período analizado. La base
    son los DEMÁS meses de ese período: el mes que se juzga no entra en su propio
    umbral, porque si entrara el máximo quedaría siempre por encima de su propia
    media y el semáforo no diría nada. Se toman como mucho los 12 meses más
    cercanos al evaluado. Con menos de 4 meses de base se devuelve (nan, nan, n)
    → estado «sin base».
    """
    base = serie.drop(index=fecha_eval, errors='ignore').dropna()
    if len(base) > UMBRAL_PICO_VENTANA:
        cercanos = np.argsort(np.abs((base.index - fecha_eval).values))
        base = base.iloc[sorted(cercanos[:UMBRAL_PICO_VENTANA])]
    if len(base) < UMBRAL_PICO_MIN_MESES:
        return np.nan, np.nan, len(base)
    mu = float(base.mean())
    return mu, mu + float(base.std(ddof=1)), len(base)


def _estado_from_color(c):
    """Traduce el color de semáforo a clave de estado ('ok'|'warn'|'bad')."""
    return 'ok' if c == C_TEAL else ('warn' if c == C_AMBER else 'bad')


def _pill(estado, texto=None):
    """Etiqueta de estado (punto + palabra) — nunca color solo."""
    _txt = texto or {'ok': 'cumple', 'warn': 'revisar',
                     'bad': 'alerta', 'demo': 'referencia'}.get(estado, estado)
    return f'<span class="pill pill-{estado}">{_txt}</span>'


def _sparkline_svg(vals, color=C_BLUE, w=160, h=30, pad=3):
    """Mini-tendencia como SVG inline (stroke no escalado, área con degradado)."""
    v = [float(x) for x in vals if x == x]
    if len(v) < 2:
        return ''
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1.0
    n = len(v)
    xs = [pad + i * (w - 2 * pad) / (n - 1) for i in range(n)]
    ys = [h - pad - (val - lo) / rng * (h - 2 * pad) for val in v]
    line = ' '.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
    area = f'{xs[0]:.1f},{h - pad:.1f} ' + line + f' {xs[-1]:.1f},{h - pad:.1f}'
    uid = f'sp{abs(hash((tuple(v), color))) % 999999}'
    return (
        f'<svg width="100%" height="{h}" viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
        f'<polygon points="{area}" fill="url(#{uid})"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>'
        f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.4" fill="{color}" '
        f'vector-effect="non-scaling-stroke"/></svg>'
    )


def _kpi_card(eyebrow, value, unit='', estado=None, spark=None, foot='', pill_txt=None):
    """Tarjeta KPI hero (HTML): etiqueta, número tabular, sparkline, pill + contexto."""
    body = [
        f'<div class="ev-eyebrow">{eyebrow}</div>',
        f'<div class="ev-value num">{value}'
        f'{f"<span class=ev-unit>{unit}</span>" if unit else ""}</div>',
        f'<div class="ev-spark">{spark or ""}</div>',
    ]
    foot_bits = []
    if estado:
        foot_bits.append(_pill(estado, pill_txt))
    if foot:
        foot_bits.append(f'<span class="ev-delta">{foot}</span>')
    body.append(f'<div class="ev-foot">{"".join(foot_bits)}</div>')
    return f'<div class="ev-kpi">{"".join(body)}</div>'


def _layout_base(fig, h=360):
    # Colores, fuente, grillas y leyenda vienen de la plantilla 'evisor'.
    fig.update_layout(height=h, margin=dict(t=48, b=44, l=64, r=24))
    fig.update_yaxes(rangemode='tozero')
    return fig


def barras_horizontales(serie, titulo, xlabel, color_fn=None,
                        ref_lines=None, h=None, colores=None,
                        fmt='{:.2f}', hover=None, customdata=None, margin_r=100):
    """Barras horizontales genéricas con colores por umbral.

    `colores` permite pasar el semáforo ya resuelto cuando el umbral no depende
    sólo del valor (KPI-03: cada bloque se juzga contra su propia historia).
    """
    labels  = [str(x) for x in serie.index]
    valores = serie.values
    if colores is None:
        colores = [color_fn(v) for v in valores] if color_fn else [C_TEAL] * len(valores)
    fig = go.Figure(go.Bar(
        x=valores, y=labels, orientation='h',
        marker_color=colores, marker_line_width=0,
        text=[fmt.format(v) for v in valores],
        textposition='outside', cliponaxis=False,
        customdata=customdata,
        hovertemplate=hover or '%{y}: %{x:.3f}<extra></extra>',
    ))
    if ref_lines:
        for val, color, label in ref_lines:
            fig.add_vline(x=val, line_color=color, line_dash='dot', line_width=1.5,
                          annotation_text=label, annotation_position='top right',
                          annotation_font_color=color, annotation_font_size=10)
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=12, color='#1B2A3B', family='IBM Plex Sans, Arial, sans-serif'), x=0),
        xaxis_title=xlabel,
        plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF',
        height=h or max(300, 38 * len(serie) + 110),
        margin=dict(t=48, b=44, l=100, r=margin_r),
        font=dict(family='IBM Plex Sans, Arial, sans-serif', size=12),
    )
    fig.update_xaxes(gridcolor='#EEF0F3', linecolor='#DDE2EA')
    fig.update_yaxes(gridcolor='#EEF0F3', linecolor='#DDE2EA')
    return fig


def serie_diaria(ind_df, col, titulo_y, titulo='Evolución diaria', h=320):
    serie = ind_df.groupby('fecha')[col].mean().sort_index()
    if serie.empty:
        return go.Figure()
    df_s = serie.rename('val').to_frame()
    df_s['es_finde'] = df_s.index.dayofweek >= 5
    df_s['ma7']      = df_s['val'].rolling(7, min_periods=1).mean()
    laboral = df_s[~df_s['es_finde']]
    finde   = df_s[df_s['es_finde']]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=laboral.index, y=laboral['val'], mode='lines+markers',
        name='Día hábil',
        line=dict(color=C_BLUE, width=2),
        marker=dict(color=C_BLUE, size=7, line=dict(color='#FFFFFF', width=1)),
        hovertemplate='%{x|%d %b}: %{y:.3f}<extra>Hábil</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=finde.index, y=finde['val'], mode='markers',
        name='Fin de semana',
        marker=dict(color=C_PURPLE, size=9, symbol='diamond',
                    line=dict(color='#FFFFFF', width=1)),
        hovertemplate='%{x|%d %b}: %{y:.3f}<extra>Fin de semana</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=df_s.index, y=df_s['ma7'], mode='lines',
        name='Media móvil 7d',
        line=dict(color=C_GRAY, width=2, dash='dot'), opacity=0.9,
        hovertemplate='%{x|%d %b}: %{y:.3f}<extra>MA7</extra>',
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13), x=0),
        xaxis_title='Fecha', yaxis_title=titulo_y,
    )
    return _layout_base(fig, h=h)


def comparativo_bloques(ind_df, col, titulo_x, titulo='Promedio por bloque (período)'):
    serie = (ind_df
             .assign(bloque=ind_df['entity_id'].map(_bloque_label))
             .groupby('bloque')[col].mean()
             .sort_values())
    if serie.empty:
        return go.Figure()
    fig = go.Figure(go.Bar(
        x=serie.values, y=serie.index.tolist(),
        orientation='h', marker_color=C_BLUE,
        text=[f'{v:.3f}' for v in serie.values], textposition='outside',
        hovertemplate='%{y}: %{x:.3f}<extra></extra>',
    ))
    fig.update_layout(title=dict(text=titulo, font=dict(size=13), x=0),
                      xaxis_title=titulo_x)
    return _layout_base(fig, h=max(240, 36 * len(serie) + 100))


def card_indicador(valor, num_lbl, num_val, den_lbl, den_val,
                   delta, ref_val, fecha_ref, fecha_hoy, unidad=''):
    ind_kw = dict(
        mode='number+delta' if delta is not None else 'number',
        value=round(float(valor), 3),
        number=dict(font=dict(size=56, color='#0D1B2A', family='IBM Plex Sans, Arial, sans-serif'),
                    valueformat='.3f', suffix=f' {unidad}' if unidad else ''),
        domain=dict(x=[0.05, 0.95], y=[0.45, 1.0]),
    )
    if delta is not None:
        ind_kw['delta'] = dict(
            reference=round(float(ref_val), 3), valueformat='.3f', relative=False,
            increasing=dict(color=C_AMBER), decreasing=dict(color=C_TEAL),
        )
    fig = go.Figure(go.Indicator(**ind_kw))
    if num_val is not None and den_val is not None:
        fig.add_annotation(
            x=0.5, y=0.32, xref='paper', yref='paper', showarrow=False,
            text=f'<b>{num_lbl}:</b> {num_val:.0f} W &nbsp;&nbsp; <b>{den_lbl}:</b> {den_val:.0f} W',
            font=dict(size=13, color='#5F5E5A'), align='center',
        )
    if delta is not None:
        flecha = '▲' if delta > 0 else '▼'
        col    = C_AMBER if delta > 0 else C_TEAL
        fig.add_annotation(
            x=0.5, y=0.12, xref='paper', yref='paper', showarrow=False,
            text=f'<span style="color:{col}">{flecha} {abs(delta):.3f}</span> vs {fecha_ref.strftime("%d %b")} (mismo día–semana anterior)',
            font=dict(size=12, color='#5F5E5A'), align='center',
        )
    else:
        fig.add_annotation(
            x=0.5, y=0.12, xref='paper', yref='paper', showarrow=False,
            text='Sin referencia de semana anterior',
            font=dict(size=12, color=C_GRAY),
        )
    fig.update_layout(
        title=dict(text=f'Último valor disponible — {fecha_hoy.strftime("%d %b %Y")}',
                   font=dict(size=12, color='#6B6965'), x=0.5, xanchor='center'),
        plot_bgcolor='white', paper_bgcolor='white',
        height=240, margin=dict(t=36, b=10, l=20, r=20),
    )
    return fig


def perfil_diurno_base(comp, titulo='Perfil diurno — evidencia del cálculo'):
    fig = go.Figure()
    if comp is None:
        fig.add_annotation(x=0.5, y=0.5, text='Datos crudos no disponibles',
                           xref='paper', yref='paper', showarrow=False,
                           font=dict(size=14, color=C_GRAY))
        return _layout_base(fig, h=300)
    p = comp['perfil']
    fig.add_trace(go.Scatter(
        x=p.index, y=p.values, mode='lines+markers',
        line=dict(color=C_TEAL, width=2.5),
        marker=dict(color=C_TEAL, size=6),
        showlegend=False,
        hovertemplate='%{x:02d}:00 → %{y:.0f} W<extra></extra>',
    ))
    fig.update_xaxes(title='Hora del día',
                     tickvals=list(range(6, 22, 2)),
                     ticktext=[f'{h:02d}:00' for h in range(6, 22, 2)])
    fig.update_yaxes(title='Potencia activa (W)')
    fig.update_layout(title=dict(text=titulo, font=dict(size=13), x=0))
    return _layout_base(fig, h=300)


def graficar_evidencia_f1(comp):
    fig = perfil_diurno_base(comp, 'f₁ — Perfil diurno: uniformidad operacional')
    if comp is None:
        return fig
    p = comp['perfil']
    fig.add_hline(y=comp['prom'], line=dict(color=C_AMBER, width=1.8, dash='dash'),
                  annotation_text=f'P̄ = {comp["prom"]:.0f} W (numerador)',
                  annotation_position='bottom right',
                  annotation_font_color=C_AMBER)
    fig.add_hline(y=comp['max'], line=dict(color=C_PURPLE, width=1.8, dash='dash'),
                  annotation_text=f'P_max = {comp["max"]:.0f} W (denominador)',
                  annotation_position='top right',
                  annotation_font_color=C_PURPLE)
    return fig


def graficar_evidencia_f2(comp):
    fig = perfil_diurno_base(comp, 'f₂ — Perfil diurno: coeficiente de variación')
    if comp is None:
        return fig
    p = comp['perfil']
    fig.add_hline(y=comp['prom'], line=dict(color=C_AMBER, width=1.8, dash='dash'),
                  annotation_text=f'P̄ = {comp["prom"]:.0f} W (denominador)',
                  annotation_position='bottom right', annotation_font_color=C_AMBER)
    fig.add_annotation(x=p.index[0], y=comp['prom'] + comp['std'],
                       text=f'σ = {comp["std"]:.0f} W (numerador)',
                       showarrow=False, xanchor='left', font=dict(size=11, color=C_BLUE))
    return fig


def graficar_evidencia_f3(comp):
    fig = perfil_diurno_base(comp, 'f₃ — Perfil diurno: relación mínimo–promedio')
    if comp is None:
        return fig
    p = comp['perfil']
    h_min = p.idxmin()
    fig.add_trace(go.Scatter(
        x=[h_min], y=[comp['min']], mode='markers',
        name=f'P_min = {comp["min"]:.0f} W (numerador)',
        marker=dict(color=C_RED, size=12, symbol='star'),
    ))
    fig.add_hline(y=comp['prom'], line=dict(color=C_AMBER, width=1.8, dash='dash'),
                  annotation_text=f'P̄ = {comp["prom"]:.0f} W (denominador)',
                  annotation_position='bottom right', annotation_font_color=C_AMBER)
    fig.update_layout(legend=dict(orientation='h', y=1.05, x=0, font=dict(size=10)))
    return fig


def calcular_componentes_diurnos(df):
    d = df.copy()
    d['hora']  = pd.to_datetime(d['time_index_colombia']).dt.hour
    mask_op    = (d['hora'] >= HORA_OP_INI) & (d['hora'] < HORA_OP_FIN)
    ap_op      = d[mask_op]['activepower'].dropna()
    perfil     = d[mask_op].groupby('hora')['activepower'].mean()
    if ap_op.empty:
        return None
    return {
        'perfil': perfil, 'prom': float(ap_op.mean()),
        'max':  float(ap_op.max()), 'min': float(ap_op.min()),
        'std':  float(ap_op.std()),
    }


def calcular_f4_diario(df):
    d = df[['time_index_colombia', 'activepower']].copy()
    d['hora']  = pd.to_datetime(d['time_index_colombia']).dt.hour
    d['fecha'] = pd.to_datetime(d['time_index_colombia']).dt.normalize()
    mask_op    = (d['hora'] >= HORA_OP_INI) & (d['hora'] < HORA_OP_FIN)
    p_op    = d[mask_op].groupby('fecha')['activepower'].mean().rename('p_op')
    p_no_op = d[~mask_op].groupby('fecha')['activepower'].mean().rename('p_no_op')
    res = pd.concat([p_op, p_no_op], axis=1)
    res['f4'] = res['p_no_op'] / res['p_op']
    return res.dropna(subset=['f4'])


def heatmap_semanal(df):
    d = df.copy()
    d['hora'] = pd.to_datetime(d['time_index_colombia']).dt.hour
    d['dia']  = pd.to_datetime(d['time_index_colombia']).dt.dayofweek
    matriz = (d.groupby(['dia', 'hora'])['activepower'].mean()
               .unstack('hora').reindex(index=range(7), columns=range(24)))
    fig = go.Figure(go.Heatmap(
        z=np.nan_to_num(matriz.values), x=list(range(24)), y=_DIAS_SEMANA,
        colorscale='YlOrBr',
        colorbar=dict(title=dict(text='W', side='right')),
        hoverongaps=False,
        hovertemplate='%{y} %{x:02d}:00 — %{z:.0f} W<extra></extra>',
    ))
    for x0, x1 in [(-0.5, 5.5), (21.5, 23.5)]:
        fig.add_shape(type='rect', xref='x', yref='y',
                      x0=x0, x1=x1, y0=-0.5, y1=6.5,
                      fillcolor='rgba(44,44,42,0.10)', line=dict(width=0), layer='above')
    fig.add_annotation(x=1.05, y=0.5, xref='paper', yref='paper', showarrow=False,
                       text='← No<br>operacional', xanchor='left',
                       font=dict(size=10, color='#5F5E5A'))
    fig.update_xaxes(title='Hora del día', tickvals=list(range(0, 24, 2)),
                     ticktext=[f'{h:02d}:00' for h in range(0, 24, 2)])
    fig.update_yaxes(autorange='reversed')
    fig.update_layout(title=dict(text='Perfil semanal de carga — evidencia f₄',
                                 font=dict(size=13), x=0),
                      plot_bgcolor='white', paper_bgcolor='white',
                      height=280, margin=dict(t=50, b=50, l=60, r=130))
    return fig


def tira_estado(kpi_df, col, titulo, color_fn, leyenda,
                estado_fn=None, fmt='{:.3f}'):
    """Heatmap calendario de estado (reemplaza la tira matplotlib).

    `estado_fn(entity_id, fecha, valor) -> color` sustituye a `color_fn` cuando
    el umbral depende del bloque y del mes, no sólo del valor (KPI-03). Si
    devuelve C_GRAY la celda se pinta como «sin base».
    """
    pivot  = kpi_df.pivot_table(index='entity_id', columns='fecha',
                                values=col, aggfunc='mean')
    fechas = pivot.columns.tolist()
    labels_y = [_bloque_label(e) for e in pivot.index]

    z      = pivot.values
    n_col  = len(fechas)
    n_row  = len(pivot)

    # Estado como código: 0=verde 1=ámbar 2=rojo 3=sin base · nan=sin dato
    _COD = {C_TEAL: 0.0, C_AMBER: 1.0, C_RED: 2.0, C_GRAY: 3.0}
    z_estado = np.full(z.shape, np.nan)
    for i in range(n_row):
        for j in range(n_col):
            v = z[i, j]
            if np.isnan(v):
                continue
            c = (estado_fn(pivot.index[i], fechas[j], v) if estado_fn
                 else color_fn(v))
            z_estado[i, j] = _COD.get(c, 2.0)

    _b = 1 / 6, 1 / 2, 5 / 6          # bordes entre las cuatro bandas
    colorscale = [
        [0.0,   C_TEAL],  [_b[0], C_TEAL],
        [_b[0], C_AMBER], [_b[1], C_AMBER],
        [_b[1], C_RED],   [_b[2], C_RED],
        [_b[2], C_GRAY],  [1.0,   C_GRAY],
    ]
    _NOM = {0.0: 'cumple', 1.0: 'revisar', 2.0: 'alerta', 3.0: 'sin base'}
    hover = [[
        (f'{_bloque_label(pivot.index[i])} · {fechas[j].strftime("%d %b %Y")}<br>'
         f'Valor: {fmt.format(z[i,j])}<br>'
         f'Estado: {_NOM.get(z_estado[i,j], "—")}')
        if not np.isnan(z[i, j]) else 'Sin dato'
        for j in range(n_col)
    ] for i in range(n_row)]

    fig = go.Figure(go.Heatmap(
        z=z_estado,
        x=[f.strftime('%d-%b') for f in fechas],
        y=labels_y,
        colorscale=colorscale,
        zmin=0, zmax=3,
        showscale=False,
        text=hover, hoverinfo='text',
        xgap=1.5, ygap=1.5,
    ))
    step = max(1, n_col // 12)
    tick_vals = [f.strftime('%d-%b') for f in fechas[::step]]
    fig.update_xaxes(tickvals=tick_vals, tickangle=-45, tickfont=dict(size=9))
    fig.update_layout(
        title=dict(text=f'{titulo} — estado por período', font=dict(size=13), x=0),
        plot_bgcolor='white', paper_bgcolor='white',
        height=max(200, 30 * n_row + 100),
        margin=dict(t=50, b=60, l=80, r=20),
        annotations=[dict(
            x=1.01, y=0.5, xref='paper', yref='paper', showarrow=False,
            text=leyenda, xanchor='left', yanchor='middle',
            font=dict(size=9, color='#5F5E5A'), align='left',
        )],
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    _logo_path = BASE / 'Logo-UPB-2022.svg'
    if _logo_path.exists():
        _svg = _logo_path.read_text(encoding='utf-8').replace(
            'x="0px" y="0px"', 'x="0px" y="0px" width="100%" height="auto"'
        )
        st.markdown(
            f'<div style="padding:20px 12px 8px 12px">{_svg}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div style="padding:4px 4px 2px 4px;font-size:1.05rem;font-weight:600;'
        'color:#0D1B2A;letter-spacing:-0.01em">E-Visor</div>'
        '<div style="padding:0 4px 12px 4px;font-size:0.75rem;color:#64748B;'
        'letter-spacing:0.02em">Ecocampus UPB · Medellín</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("### Filtros")

    fecha_min = ind['fecha'].min().date()
    fecha_max = ind['fecha'].max().date()
    c1, c2 = st.columns(2)
    fecha_ini = c1.date_input("Inicio", fecha_min, min_value=fecha_min, max_value=fecha_max)
    fecha_fin = c2.date_input("Fin",   fecha_max, min_value=fecha_min, max_value=fecha_max)

    medidores = ["Todos"] + sorted(ind['entity_id'].unique().tolist())
    seleccion = st.selectbox(
        "Bloque",
        medidores,
        format_func=lambda x: "Todos los bloques" if x == "Todos" else _bloque_label(x),
    )
    st.divider()
    st.caption("FE CO₂: 0.097018 tCO₂e/MWh (XM, 2026-01-30)")
    st.caption("Tarifa EPM NT1 ene-2026: $859 COP/kWh")


# ── Filtrado ──────────────────────────────────────────────────────────────────
inicio = pd.Timestamp(fecha_ini)
fin    = pd.Timestamp(fecha_fin)

ind_f      = ind[ind['fecha'].between(inicio, fin)].copy()
ind_fechas = ind_f.copy()
inicio_mes = inicio.strftime('%Y-%m')
fin_mes    = fin.strftime('%Y-%m')
kpi_f      = kpi[(kpi['mes'] >= inicio_mes) & (kpi['mes'] <= fin_mes)].copy()

kpi_demo_f = kpi_demo[(kpi_demo['mes'] >= inicio_mes) & (kpi_demo['mes'] <= fin_mes)].copy()
ind13_f    = ind13[(ind13['mes'] >= inicio_mes) & (ind13['mes'] <= fin_mes)].copy() if not ind13.empty else pd.DataFrame()

if seleccion != "Todos":
    ind_f = ind_f[ind_f['entity_id'] == seleccion]
    kpi_f = kpi_f[kpi_f['entity_id'] == seleccion]

raw_f = None
if raw is not None:
    raw_f = raw[raw['fecha'].between(inicio, fin)]
    if seleccion != "Todos":
        # El crudo va por medidor y la selección por bloque: se comparan
        # bloque contra bloque, no entity_id contra entity_id.
        _blq = _bloque_label(seleccion)
        raw_f = raw_f[raw_f['entity_id'].map(_bloque_de_medidor) == _blq]

if ind_f.empty:
    st.warning("Sin datos para el rango seleccionado.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# CABECERA
# ═══════════════════════════════════════════════════════════════════════════════
bloque_txt = ("Todos los bloques" if seleccion == "Todos"
              else f"Bloque {_bloque_label(seleccion)}")
periodo_dias = max(1, (fin - inicio).days + 1)

st.markdown(
    '<div class="ev-topbar">'
    '<h1>Monitoreo energético del Ecocampus</h1>'
    f'<div class="ev-sub"><b>{bloque_txt}</b> &nbsp;·&nbsp; '
    f'{inicio.strftime("%d %b %Y")} — {fin.strftime("%d %b %Y")} · {periodo_dias} días</div>'
    '</div>'
    '<hr class="ev-rule"/>',
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# RESUMEN EJECUTIVO (métricas rápidas)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Resumen ejecutivo")

# Cálculo de métricas de resumen
kpi01_f = (kpi_f.drop_duplicates(subset=['bloque', 'fecha'])
           [['bloque', 'fecha', 'KPI01_kwh_m2', 'e_wh', 'area_m2']]
           .dropna(subset=['KPI01_kwh_m2'])) if 'KPI01_kwh_m2' in kpi_f.columns else pd.DataFrame()

total_kwh_campus = kpi01_f['e_wh'].sum() / 1_000 if not kpi01_f.empty else None
co2_total        = float(ind_f['CO2_tCO2e'].sum()) if 'CO2_tCO2e' in ind_f.columns else None
lf_medio         = float(ind_f['LF'].mean()) if 'LF' in ind_f.columns else None
fp_medio         = float(kpi_f['KPI11_fp'].mean()) if 'KPI11_fp' in kpi_f.columns and not kpi_f['KPI11_fp'].dropna().empty else None
db_medio         = float(ind_f['desbalance_pct'].mean()) if 'desbalance_pct' in ind_f.columns and not ind_f['desbalance_pct'].dropna().empty else None
pico_max         = float(kpi_f['KPI03_pico_kw'].max()) if 'KPI03_pico_kw' in kpi_f.columns and not kpi_f['KPI03_pico_kw'].dropna().empty else None


def _svals(df, by, col, agg='mean'):
    if df is None or col not in df.columns:
        return []
    s = df.groupby(by)[col].agg(agg).sort_index().dropna()
    return s.tolist()

# Series de tendencia (sparklines)
_sp_co2 = _svals(ind_f, 'fecha', 'CO2_tCO2e', 'sum')
_sp_lf  = _svals(ind_f, 'fecha', 'LF', 'mean')
_sp_db  = _svals(ind_f, 'fecha', 'desbalance_pct', 'mean')
_sp_fp  = _svals(kpi_f, 'fecha', 'KPI11_fp', 'mean')
_sp_pk  = _svals(kpi_f, 'fecha', 'KPI03_pico_kw', 'max')
_sp_en  = _svals(raw_f, 'fecha', 'activepower', 'sum') if raw_f is not None else []

_cards = []

# Energía
if total_kwh_campus:
    _costo = total_kwh_campus * TARIFA_BASE_COP_KWH
    _cards.append(_kpi_card('Energía consumida', f'{total_kwh_campus:,.0f}', 'kWh',
                            spark=_sparkline_svg(_sp_en), foot=f'${_costo:,.0f} COP'))
else:
    _cards.append(_kpi_card('Energía consumida', '—'))

# CO₂
if co2_total is not None:
    _arb = int(co2_total * ARBOLES_POR_TON_CO2)
    _cards.append(_kpi_card('Emisiones CO₂', f'{co2_total:.2f}', 'tCO₂e',
                            spark=_sparkline_svg(_sp_co2), foot=f'≈ {_arb:,} árboles'))
else:
    _cards.append(_kpi_card('Emisiones CO₂', '—'))

# Load Factor
if lf_medio is not None:
    _e = _estado_from_color(_semaforo(lf_medio, 0.65, 0.50))
    _cards.append(_kpi_card('LF medio diario', f'{lf_medio:.2f}', '',
                            estado=_e, spark=_sparkline_svg(_sp_lf),
                            foot='media de LF diarios · obj ≥ 0.65'))
else:
    _cards.append(_kpi_card('LF medio diario', '—'))

# Pico de demanda
if pico_max is not None:
    # KPI-03 exige registrar bloque, fecha y hora del pico junto al valor.
    _r_pk    = kpi_f.loc[kpi_f['KPI03_pico_kw'].idxmax()]
    _foot_pk = (f"{_bloque_label(_r_pk['entity_id'])} · "
                f"{_fmt_fecha_hora(_r_pk.get('fecha_pico'), _r_pk.get('hora_pico'))}")
    _cards.append(_kpi_card('Pico de demanda', f'{pico_max:.1f}', 'kW',
                            spark=_sparkline_svg(_sp_pk), foot=_foot_pk))
else:
    _cards.append(_kpi_card('Pico de demanda', '—'))

# Factor de potencia
if fp_medio is not None:
    _e = _estado_from_color(_semaforo(fp_medio, UMBRAL_FP_OBJ, UMBRAL_FP_ALERT))
    _cards.append(_kpi_card('Factor de potencia', f'{fp_medio:.2f}', '',
                            estado=_e, spark=_sparkline_svg(_sp_fp), foot='obj ≥ 0.90'))
else:
    _cards.append(_kpi_card('Factor de potencia', '—'))

# Desbalance de tensión
if db_medio is not None:
    _e = _estado_from_color(_semaforo(db_medio, UMBRAL_DB_OBJ, UMBRAL_DB_ALERT, mayor_es_mejor=False))
    _cards.append(_kpi_card('Desbalance de tensión', f'{db_medio:.2f}', '%',
                            estado=_e, spark=_sparkline_svg(_sp_db), foot='obj < 2%'))
else:
    _cards.append(_kpi_card('Desbalance de tensión', '—'))

st.markdown(f'<div class="ev-grid">{"".join(_cards)}</div>', unsafe_allow_html=True)

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_ind, tab_kpi = st.tabs(["Indicadores", "KPIs"])


# ───────────────────────────────────────────────────────────────────────────────
# TAB 1 — INDICADORES
# ───────────────────────────────────────────────────────────────────────────────
with tab_ind:

    if raw_f is not None and not raw_f.empty:
        _raw_hoy = raw_f[raw_f['fecha'] == raw_f['fecha'].max()]
        _comp    = calcular_componentes_diurnos(_raw_hoy)
    else:
        _comp = None

    # ── LF — Load Factor ────────────────────────────────────────────────────
    st.markdown("## LF — Factor de carga (diario)")
    fig_lf_bar = barras_horizontales(
        ind_f.assign(bloque=ind_f['entity_id'].map(_bloque_label))
             .groupby('bloque')['LF'].mean().sort_values(),
        titulo='IND-01 — Media de los LF diarios por bloque',
        xlabel='Factor de carga diario (0–1)',
        color_fn=lambda v: _semaforo(v, 0.65, 0.50),
        ref_lines=[(0.65, C_TEAL, 'objetivo 0.65')],
    )
    _chart(fig_lf_bar, use_container_width=True)
    st.caption(
        "IND-01 usa la misma fórmula que el KPI 08 —LF = P̄ / P_máx— pero sobre una "
        "ventana distinta: aquí cada **día** tiene su propio máximo y el gráfico "
        "promedia esos LF diarios; el KPI 08 usa el máximo del **mes**. Como el "
        "máximo mensual es mayor o igual que el de cualquier día, el LF diario "
        "siempre da más alto que el mensual: los dos números no son comparables "
        "entre sí y ninguno es el LF del período completo."
    )
    _chart(serie_diaria(ind_f, 'LF', 'LF (adimensional)'), use_container_width=True)

    # ── PAR — Peak-to-Average Ratio ─────────────────────────────────────────
    st.markdown("## PAR — Peak-to-Average Ratio")
    fig_par_bar = barras_horizontales(
        ind_f.assign(bloque=ind_f['entity_id'].map(_bloque_label))
             .groupby('bloque')['PAR'].mean().sort_values(),
        titulo='PAR medio por bloque',
        xlabel='PAR (>1 = picos pronunciados)',
        color_fn=lambda v: _semaforo(v, 1.54, 2.0, mayor_es_mejor=False),
    )
    _chart(fig_par_bar, use_container_width=True)
    _chart(serie_diaria(ind_f, 'PAR', 'PAR (adimensional)'), use_container_width=True)

    # ── f₁ — Uniformidad diurna ─────────────────────────────────────────────
    st.markdown("## f₁ — Uniformidad de franja diurna")
    _d1, _r1, _fr1 = _delta_semana(ind_f, 'f1')
    _f1_valid = ind_f[ind_f['f1'].notna()]
    _fh1 = _f1_valid['fecha'].max() if not _f1_valid.empty else pd.NaT
    _v1  = _f1_valid[_f1_valid['fecha'] == _fh1]['f1'].mean() if not _f1_valid.empty else float('nan')

    if pd.notna(_v1) and pd.notna(_fh1):
        _chart(card_indicador(
            _v1, 'P̄ op.', _comp['prom'] if _comp else None,
            'P_max op.', _comp['max'] if _comp else None,
            _d1, _r1, _fr1, _fh1), use_container_width=True)
    _chart(serie_diaria(ind_f, 'f1', 'f₁ (adimensional)'), use_container_width=True)
    _chart(comparativo_bloques(ind_fechas, 'f1', 'f₁ (adimensional)'), use_container_width=True)

    # ── f₂ — CV de carga ────────────────────────────────────────────────────
    st.markdown("## f₂ — Coeficiente de variación de carga")
    _d2, _r2, _fr2 = _delta_semana(ind_f, 'f2_CV')
    _f2_valid = ind_f[ind_f['f2_CV'].notna()]
    _fh2 = _f2_valid['fecha'].max() if not _f2_valid.empty else pd.NaT
    _v2  = _f2_valid[_f2_valid['fecha'] == _fh2]['f2_CV'].mean() if not _f2_valid.empty else float('nan')

    if pd.notna(_v2) and pd.notna(_fh2):
        _chart(card_indicador(
            _v2, 'σ op.', _comp['std'] if _comp else None,
            'P̄ op.', _comp['prom'] if _comp else None,
            _d2, _r2, _fr2, _fh2), use_container_width=True)
    _chart(serie_diaria(ind_f, 'f2_CV', 'f₂ (adimensional)'), use_container_width=True)
    _chart(comparativo_bloques(ind_fechas, 'f2_CV', 'f₂ (adimensional)'), use_container_width=True)

    # ── f₃ — Mínimo–promedio ────────────────────────────────────────────────
    st.markdown("## f₃ — Relación mínimo–promedio")
    _d3, _r3, _fr3 = _delta_semana(ind_f, 'f3')
    _f3_valid = ind_f[ind_f['f3'].notna()]
    _fh3 = _f3_valid['fecha'].max() if not _f3_valid.empty else pd.NaT
    _v3  = _f3_valid[_f3_valid['fecha'] == _fh3]['f3'].mean() if not _f3_valid.empty else float('nan')

    if pd.notna(_v3) and pd.notna(_fh3):
        _chart(card_indicador(
            _v3, 'P_min op.', _comp['min'] if _comp else None,
            'P̄ op.', _comp['prom'] if _comp else None,
            _d3, _r3, _fr3, _fh3), use_container_width=True)
    _chart(serie_diaria(ind_f, 'f3', 'f₃ (adimensional)'), use_container_width=True)
    _chart(comparativo_bloques(ind_fechas, 'f3', 'f₃ (adimensional)'), use_container_width=True)

    # ── f₄ — Carga no operacional ────────────────────────────────────────────
    st.markdown("## f₄ — Factor de carga no operacional")
    if raw_f is not None and not raw_f.empty:
        f4_diario = calcular_f4_diario(raw_f)
    else:
        f4_diario = (ind_f.groupby('fecha')['f4'].mean()
                     .to_frame('f4').assign(p_op=np.nan, p_no_op=np.nan))
        st.caption("P̄ desagregada no disponible — clean_etsmartmeter.csv no encontrado.")

    if not f4_diario.empty:
        hoy_f4       = f4_diario.iloc[-1]
        fecha_hoy_f4 = f4_diario.index[-1]
        cand_f4      = f4_diario[(f4_diario.index.dayofweek == fecha_hoy_f4.dayofweek) &
                                 (f4_diario.index < fecha_hoy_f4)]
        f4_ref   = cand_f4.iloc[-1]['f4'] if not cand_f4.empty else None
        delta_f4 = float(hoy_f4['f4']) - float(f4_ref) if f4_ref is not None else None

        fig_f4_card = card_indicador(
            hoy_f4['f4'],
            'P̄ no-op', hoy_f4.get('p_no_op') if pd.notna(hoy_f4.get('p_no_op', np.nan)) else None,
            'P̄ op',    hoy_f4.get('p_op')    if pd.notna(hoy_f4.get('p_op',    np.nan)) else None,
            delta_f4, f4_ref,
            cand_f4.index[-1] if not cand_f4.empty else None,
            fecha_hoy_f4,
        )
        _chart(fig_f4_card, use_container_width=True)
        df_f4 = f4_diario.sort_index().copy()
        df_f4['es_finde'] = df_f4.index.dayofweek >= 5
        df_f4['ma7']      = df_f4['f4'].rolling(7, min_periods=1).mean()
        fig_f4_ev = go.Figure()
        fig_f4_ev.add_trace(go.Scatter(
            x=df_f4[~df_f4['es_finde']].index, y=df_f4[~df_f4['es_finde']]['f4'],
            mode='lines+markers', name='Día hábil',
            line=dict(color=C_TEAL, width=1.8), marker=dict(color=C_TEAL, size=5),
        ))
        fig_f4_ev.add_trace(go.Scatter(
            x=df_f4[df_f4['es_finde']].index, y=df_f4[df_f4['es_finde']]['f4'],
            mode='markers', name='Fin de semana',
            marker=dict(color=C_AMBER, size=8, symbol='diamond'),
        ))
        fig_f4_ev.add_trace(go.Scatter(
            x=df_f4.index, y=df_f4['ma7'], mode='lines', name='MA7',
            line=dict(color=C_GRAY, width=2.5, dash='dot'), opacity=0.8,
        ))
        fig_f4_ev.update_layout(title=dict(text='Evolución diaria f₄', font=dict(size=13), x=0),
                                xaxis_title='Fecha', yaxis_title='f₄')
        _chart(_layout_base(fig_f4_ev), use_container_width=True)

    if raw_f is not None and not raw_f.empty:
        _chart(heatmap_semanal(raw_f), use_container_width=True)
    _chart(comparativo_bloques(ind_fechas, 'f4', 'f₄ (adimensional)'),
                    use_container_width=True)

    # ── CO₂ — Emisiones ────────────────────────────────────────────────────────
    st.markdown("## CO₂ — Huella de carbono del Ecocampus")
    if 'CO2_tCO2e' in ind_f.columns and not ind_f['CO2_tCO2e'].dropna().empty:
        total_co2  = float(ind_f['CO2_tCO2e'].sum())
        arboles    = int(total_co2 * ARBOLES_POR_TON_CO2)
        vuelos     = total_co2 / TON_CO2_POR_VUELO_MDE_BOG
        vehiculos  = total_co2 / TON_CO2_POR_VEHICULO_ANO

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("CO₂ total", f"{total_co2:.3f} tCO₂e")
        col_m2.metric("Árboles equiv.", f"{arboles:,}")
        col_m3.metric("Vuelos MDE–BOG", f"{vuelos:.1f}")
        col_m4.metric("Vehículos/año", f"{vehiculos:.2f}")

        # Evolución mensual + diaria
        diario   = ind_f.groupby('fecha')['CO2_tCO2e'].sum().sort_index()
        mensual  = diario.resample('ME').sum()
        n        = len(mensual)
        col_mes  = [C_AMBER if i == n - 1 else C_TEAL for i in range(n)]

        fig_co2 = make_subplots(rows=2, cols=1, row_heights=[0.55, 0.45],
                                vertical_spacing=0.14,
                                subplot_titles=('Emisiones mensuales', 'Emisiones diarias'))
        fig_co2.add_trace(go.Bar(
            x=[f.strftime('%b %Y') for f in mensual.index], y=mensual.values,
            marker_color=col_mes,
            text=[f'{v:.3f} tCO₂e' for v in mensual.values], textposition='outside',
            showlegend=False,
        ), row=1, col=1)
        es_finde = diario.index.dayofweek >= 5
        fig_co2.add_trace(go.Bar(
            x=diario[~es_finde].index, y=diario[~es_finde].values,
            name='Día hábil', marker_color=C_TEAL,
        ), row=2, col=1)
        fig_co2.add_trace(go.Bar(
            x=diario[es_finde].index, y=diario[es_finde].values,
            name='Fin de semana', marker_color=C_AMBER,
        ), row=2, col=1)
        fig_co2.update_yaxes(title_text='tCO₂e/mes', gridcolor='#EEEEEE', row=1, col=1)
        fig_co2.update_yaxes(title_text='tCO₂e/día', gridcolor='#EEEEEE', row=2, col=1)
        fig_co2.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                              height=460, margin=dict(t=60, b=40, l=70, r=20),
                              barmode='overlay',
                              legend=dict(orientation='h', y=1.02, x=1, xanchor='right'))
        _chart(fig_co2, use_container_width=True)

        # CO₂ por bloque
        totales = (ind_f
                   .assign(bloque=ind_f['entity_id'].map(_bloque_label))
                   .groupby('bloque')['CO2_tCO2e'].sum().sort_values())
        fig_co2_bloq = go.Figure(go.Bar(
            x=totales.values, y=totales.index.tolist(), orientation='h',
            marker=dict(color=totales.values, colorscale='YlOrBr', showscale=True,
                        colorbar=dict(title='tCO₂e')),
            text=[f'{v:.3f}' for v in totales.values], textposition='outside',
            hovertemplate='%{y}: %{x:.4f} tCO₂e<extra></extra>',
        ))
        fig_co2_bloq.update_layout(title=dict(text='Emisiones CO₂ por bloque (tCO₂e totales)',
                                              font=dict(size=13), x=0),
                                   xaxis_title='tCO₂e',
                                   plot_bgcolor='white', paper_bgcolor='white',
                                   height=max(260, 36 * len(totales) + 100),
                                   margin=dict(t=50, b=40, l=80, r=100))
        fig_co2_bloq.update_xaxes(gridcolor='#EEEEEE')
        _chart(fig_co2_bloq, use_container_width=True)

    # ── Desbalance de tensión ────────────────────────────────────────────────
    st.markdown("## Desbalance de tensión")
    if 'desbalance_pct' in ind_f.columns and not ind_f['desbalance_pct'].dropna().empty:
        db_bloque = (ind_f
                     .assign(bloque=ind_f['entity_id'].map(_bloque_label))
                     .groupby('bloque')['desbalance_pct'].mean().sort_values())
        fig_db_bar = barras_horizontales(
            db_bloque, titulo='Desbalance medio por bloque', xlabel='%',
            color_fn=lambda v: _semaforo(v, UMBRAL_DB_OBJ, UMBRAL_DB_ALERT, mayor_es_mejor=False),
            ref_lines=[
                (UMBRAL_DB_OBJ,   C_TEAL, f'{UMBRAL_DB_OBJ:.0f}% objetivo'),
                (UMBRAL_DB_ALERT, C_RED,  f'{UMBRAL_DB_ALERT:.0f}% alerta'),
            ],
        )
        _chart(fig_db_bar, use_container_width=True)
        serie_db = ind_f.groupby('fecha')['desbalance_pct'].mean().sort_index()
        colores_db = [_semaforo(v, UMBRAL_DB_OBJ, UMBRAL_DB_ALERT, mayor_es_mejor=False)
                      for v in serie_db.values]
        fig_db_ev = go.Figure()
        fig_db_ev.add_hrect(y0=UMBRAL_DB_ALERT, y1=serie_db.max() * 1.2 or 4,
                            fillcolor=C_RED, opacity=0.05, line_width=0)
        fig_db_ev.add_hrect(y0=UMBRAL_DB_OBJ, y1=UMBRAL_DB_ALERT,
                            fillcolor=C_AMBER, opacity=0.07, line_width=0)
        fig_db_ev.add_trace(go.Bar(
            x=serie_db.index, y=serie_db.values, marker_color=colores_db,
            hovertemplate='%{x|%d %b}: %{y:.2f}%<extra></extra>',
        ))
        fig_db_ev.add_hline(y=UMBRAL_DB_OBJ,   line_color=C_TEAL, line_dash='dot',
                            annotation_text=f'objetivo {UMBRAL_DB_OBJ:.0f}%',
                            annotation_position='top right')
        fig_db_ev.add_hline(y=UMBRAL_DB_ALERT, line_color=C_RED, line_dash='dash',
                            annotation_text=f'alerta {UMBRAL_DB_ALERT:.0f}%',
                            annotation_position='top right')
        fig_db_ev.update_layout(title=dict(text='Evolución diaria — desbalance de tensión',
                                           font=dict(size=13), x=0),
                                showlegend=False, xaxis_title='Fecha', yaxis_title='%')
        _chart(_layout_base(fig_db_ev), use_container_width=True)

    # ── IND-13 — Factor de Diversidad del campus ────────────────────────────
    st.markdown("## FD — Factor de Diversidad del campus")
    if not ind13_f.empty:
        fd_vals = ind13_f.sort_values('fecha')
        fig_fd = go.Figure(go.Bar(
            x=[f.strftime('%b %Y') for f in fd_vals['fecha']],
            y=fd_vals['valor_num'].values,
            marker_color=C_TEAL,
            text=[f'{v:.3f}' for v in fd_vals['valor_num']],
            textposition='outside',
            hovertemplate='%{x}: FD = %{y:.3f}<extra></extra>',
        ))
        fig_fd.add_hline(y=1.0, line_color=C_GRAY, line_dash='dot',
                         annotation_text='FD = 1 (sin diversidad)', annotation_position='top left',
                         annotation_font_color=C_GRAY)
        fig_fd.update_layout(
            title=dict(text='IND-13 — Factor de Diversidad mensual del campus', font=dict(size=13), x=0),
            xaxis_title='Mes', yaxis_title='FD (adimensional)',
        )
        _chart(_layout_base(fig_fd, h=320), use_container_width=True)
        fd_mean = float(fd_vals['valor_num'].mean())
        st.caption(
            f"FD = Σ(pico individual de cada bloque) / pico simultáneo del campus. "
            f"FD > 1 indica diversidad temporal de picos — cuanto mayor, mejor la distribución. "
            f"Promedio período: **{fd_mean:.3f}**"
        )
    else:
        st.info("IND-13 (Factor de Diversidad) sin datos para el rango seleccionado.")

    # ── Indicadores en integración (PENDIENTE) ──────────────────────────────
    st.markdown("## Indicadores en integración")
    _PEND_INFO = [
        ('IND-08', 'IGS', 'Índice de generación solar (Yield Factor FV)',
         'Pendiente: registros de generación FV + capacidad instalada kWp (integración Fronius).'),
        ('IND-09', 'TCP', 'Temperatura de panel fotovoltaico',
         'Pendiente: configuración de sensor Fronius de temperatura de panel.'),
        ('IND-10', 'EB',  'Eficiencia de batería (Energy Balance)',
         'Pendiente: datos del inversor/batería no disponibles aún.'),
        ('IND-11', 'Ahorro', 'Ahorro energético verificado',
         'Pendiente: se requiere línea base de ≥ 12 meses de operación histórica.'),
    ]
    for ind_id, sigla, nombre, pendiente in _PEND_INFO:
        st.markdown(
            f'<div style="background:#FDFAF5;border-left:3px solid {C_AMBER};'
            f'border-radius:2px;padding:14px 18px;margin-bottom:16px">'
            f'<b style="color:#0D1B2A;font-family:IBM Plex Sans,sans-serif">{ind_id} · {sigla} — {nombre}</b><br>'
            f'<span style="color:#64748B;font-size:.85rem;font-family:IBM Plex Sans,sans-serif">{pendiente}</span><br>'
            f'<span style="color:{C_AMBER};font-weight:600;font-size:.80rem;font-family:IBM Plex Sans,sans-serif">Sin datos — pendiente de integración</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ───────────────────────────────────────────────────────────────────────────────
# TAB 2 — KPIs
# ───────────────────────────────────────────────────────────────────────────────
with tab_kpi:

    if kpi_f.empty:
        st.warning("Sin KPIs para el rango seleccionado.")
        st.stop()

    total_kwh_campus = None  # se calcula en KPI 01 y se reutiliza en KPI 09

    # ── KPI 01 — Consumo / m² ────────────────────────────────────────────────
    st.markdown("## KPI 01 — Consumo por metro cuadrado (kWh/m²)")
    kpi01_f = (kpi_f.drop_duplicates(subset=['bloque', 'fecha'])
               [['bloque', 'fecha', 'KPI01_kwh_m2', 'e_wh', 'area_m2']]
               .dropna(subset=['KPI01_kwh_m2'])) if 'KPI01_kwh_m2' in kpi_f.columns else pd.DataFrame()

    if not kpi01_f.empty:
        total_periodo = kpi01_f.groupby('bloque')['KPI01_kwh_m2'].sum().sort_values()
        vals_k1       = total_periodo.values
        mu_k1         = float(vals_k1.mean()) if len(vals_k1) > 0 else 0.0
        sigma_k1      = float(vals_k1.std())  if len(vals_k1) > 1 else 0.0
        umbral_alerta_k1   = mu_k1 + sigma_k1
        umbral_objetivo_k1 = mu_k1 * 0.93

        serie_k1 = pd.Series(vals_k1, index=[f'B{b}' for b in total_periodo.index])
        fig_k1 = barras_horizontales(
            serie_k1, titulo='KPI 01 — Intensidad energética por bloque',
            xlabel=f'kWh/m² · {periodo_dias} días',
            color_fn=lambda v: _semaforo(v, umbral_objetivo_k1, umbral_alerta_k1, mayor_es_mejor=False),
            ref_lines=[
                (umbral_objetivo_k1, C_TEAL, f'objetivo {umbral_objetivo_k1:.2f}'),
                (umbral_alerta_k1,   C_RED,  f'alerta {umbral_alerta_k1:.2f}'),
            ],
        )
        _chart(fig_k1, use_container_width=True)
        total_kwh_campus = kpi01_f['e_wh'].sum() / 1_000
        costo_cop      = total_kwh_campus * TARIFA_BASE_COP_KWH
        hogares_meses  = total_kwh_campus / HOGAR_KWH_MES
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Energía consumida", f"{total_kwh_campus:,.0f} kWh")
        cm2.metric("Costo estimado", f"${costo_cop:,.0f} COP",
                   help="Tarifa EPM NT1 ene-2026: $859.19 COP/kWh")
        cm3.metric("Hogares equivalentes", f"{hogares_meses:,.0f} mes-hogar",
                   help=f"Referencia: {HOGAR_KWH_MES} kWh/mes estrato 1–2")
        st.info(
            f"En {periodo_dias} días el campus consumió **{total_kwh_campus:,.0f} kWh** "
            f"≡ {hogares_meses:,.0f} hogares un mes. "
            f"Costo de referencia: **${costo_cop:,.0f} COP** "
            f"(EPM NT1 ene-2026 · $859 COP/kWh)."
        )
        st.caption(
            f"Umbrales dinámicos: objetivo = μ×0.93 = {umbral_objetivo_k1:.2f} kWh/m² · "
            f"alerta = μ+1σ = {umbral_alerta_k1:.2f} kWh/m². "
            f"Áreas: AREAS_2026.xlsx, Planeación Física UPB."
        )
    else:
        st.info("KPI 01 no disponible para el período seleccionado.")

    # ── KPI 03 — Pico de demanda ─────────────────────────────────────────────
    # La ficha pide max(activepower) SOBRE EL PERÍODO ANALIZADO, así que el valor
    # se calcula sobre la potencia horaria cruda y no sobre el pico mensual ya
    # agregado: con un filtro que no cubra meses enteros, el mensual devolvería un
    # pico ocurrido fuera del período. Y un bloque puede tener varios medidores
    # (B7 = CTIC+TAC, B8 = AA+CPA+LABS, B9 = SFA1+SFA2): su potencia es la suma en
    # el MISMO timestamp, no la suma de sus máximos, que ocurren en horas distintas.
    st.markdown("## KPI 03 — Pico de demanda absoluto")

    def _picos_mensuales_k3(df_crudo):
        """Pico mensual de cada bloque, sumando sus medidores en el mismo instante."""
        bp = (df_crudo.assign(bloque=df_crudo['entity_id'].map(_bloque_de_medidor))
              .groupby(['bloque', 'time_index_colombia'], as_index=False)['activepower'].sum())
        bp['kw']  = bp['activepower'] / 1000.0            # el medidor entrega W
        bp['mes'] = (bp['time_index_colombia'].dt.to_period('M')
                     .dt.to_timestamp(how='end').dt.normalize())
        return bp

    # `_k3_mens` es lo que se muestra (período filtrado); `_k3_base` es la serie
    # completa del bloque, con la que se arma el umbral: si dependiera del filtro,
    # el umbral de un mes ya cerrado cambiaría al mover las fechas y la evaluación
    # dejaría de ser reproducible.
    _k3_mens, _k3_base, _picos_k3, _k3_exacto = pd.DataFrame(), pd.DataFrame(), [], False
    if raw_f is not None and not raw_f.empty and 'activepower' in raw_f.columns:
        _bp = _picos_mensuales_k3(raw_f)
        _k3_mens = (_bp.groupby(['bloque', 'mes'], as_index=False)['kw'].max()
                    .rename(columns={'bloque': 'entity_id', 'mes': 'fecha',
                                     'kw': 'KPI03_pico_kw'}))
        _rw_todo = raw if seleccion == "Todos" else raw[
            raw['entity_id'].map(_bloque_de_medidor) == _bloque_label(seleccion)]
        _k3_base = (_picos_mensuales_k3(_rw_todo)
                    .groupby(['bloque', 'mes'], as_index=False)['kw'].max()
                    .rename(columns={'bloque': 'entity_id', 'mes': 'fecha',
                                     'kw': 'KPI03_pico_kw'}))
        _picos_k3 = [dict(bloque=_r['bloque'], pico=float(_r['kw']), mes=_r['mes'],
                          fecha=_r['time_index_colombia'], hora=_r['time_index_colombia'].hour)
                     for _, _r in _bp.loc[_bp.groupby('bloque')['kw'].idxmax()].iterrows()]
        _k3_exacto = True
    elif 'KPI03_pico_kw' in kpi_f.columns:
        # Sin CSV crudo: se cae al pico mensual ya calculado en el Excel.
        _mf = (kpi_f[['entity_id', 'fecha', 'KPI03_pico_kw', 'fecha_pico', 'hora_pico']]
               .dropna(subset=['KPI03_pico_kw']))
        _k3_mens = _mf[['entity_id', 'fecha', 'KPI03_pico_kw']].copy()
        _k3_mens['entity_id'] = _k3_mens['entity_id'].map(_bloque_label)
        _k3_base = (kpi[['entity_id', 'fecha', 'KPI03_pico_kw']]
                    .dropna(subset=['KPI03_pico_kw']).copy())
        _k3_base['entity_id'] = _k3_base['entity_id'].map(_bloque_label)
        _picos_k3 = [dict(bloque=_bloque_label(_r['entity_id']),
                          pico=float(_r['KPI03_pico_kw']), mes=_r['fecha'],
                          fecha=_r['fecha_pico'], hora=_r['hora_pico'])
                     for _, _r in _mf.loc[_mf.groupby('entity_id')['KPI03_pico_kw'].idxmax()].iterrows()]

    if not _picos_k3:
        st.info("KPI 03 no disponible para el período seleccionado.")
    else:
        # Serie mensual de picos de cada bloque: es la base con la que se
        # construye su umbral propio (el mes evaluado se excluye después).
        _hist_k3 = {e: g.set_index('fecha')['KPI03_pico_kw'].sort_index()
                    for e, g in _k3_base.groupby('entity_id')}
        _cache_k3 = {}

        def _umbral_k3(bloque, fecha):
            """Objetivo, alerta y nº de meses de base de un bloque en un mes."""
            clave = (bloque, fecha)
            if clave not in _cache_k3:
                _cache_k3[clave] = _umbral_pico(
                    _hist_k3.get(bloque, pd.Series(dtype=float)), fecha)
            return _cache_k3[clave]

        def _color_k3(bloque, fecha, valor):
            obj, alerta, _ = _umbral_k3(bloque, fecha)
            if not np.isfinite(obj):
                return C_GRAY                      # sin base histórica suficiente
            return _semaforo(valor, obj, alerta, mayor_es_mejor=False)

        for _f in _picos_k3:                       # umbral y estado de cada bloque
            _f['objetivo'], _f['alerta'], _f['n_base'] = _umbral_k3(_f['bloque'], _f['mes'])
            _f['color']  = _color_k3(_f['bloque'], _f['mes'], _f['pico'])
            _f['estado'] = ('sin base' if _f['color'] == C_GRAY else
                            {'ok': 'cumple', 'warn': 'revisar',
                             'bad': 'alerta'}[_estado_from_color(_f['color'])])
            _f['cuando']       = _fmt_fecha_hora(_f['fecha'], _f['hora'])
            _f['cuando_largo'] = _fmt_fecha_hora(_f['fecha'], _f['hora'], largo=True)
        k3 = pd.DataFrame(_picos_k3).sort_values('pico').reset_index(drop=True)

        # Ranking en kW: la magnitud es lo que factura. Cada bloque lleva su
        # propio umbral dibujado sobre su fila —objetivo (μ) y alerta (μ+1σ) de
        # su serie mensual—, porque el umbral del KPI-03 es por bloque y no
        # admite una línea única para todo el campus.
        serie_k3 = pd.Series(k3['pico'].values, index=k3['bloque'])
        fig_k3 = barras_horizontales(
            serie_k3, titulo='KPI 03 — Pico máximo por bloque y su umbral propio',
            xlabel=f'kW · {periodo_dias} días',
            colores=k3['color'].tolist(),
            margin_r=180,
            customdata=[[c, ('—' if not np.isfinite(o) else f'{o:,.1f} kW'),
                         ('—' if not np.isfinite(a) else f'{a:,.1f} kW'), e, int(n)]
                        for c, o, a, e, n in zip(k3['cuando'], k3['objetivo'],
                                                 k3['alerta'], k3['estado'], k3['n_base'])],
            hover=('<b>%{y}</b> — %{x:,.1f} kW<br>Ocurrió: %{customdata[0]}<br>'
                   'Objetivo (μ): %{customdata[1]} · Alerta (μ+1σ): %{customdata[2]}<br>'
                   'Estado: %{customdata[3]} · base: %{customdata[4]} meses<extra></extra>'),
        )
        fig_k3.data[0].text = None                  # la etiqueta va como anotación

        # Marcas de umbral por fila, con el código de color del resto del tablero.
        for _i, _f in k3.iterrows():
            for _v, _c in ((_f['objetivo'], C_TEAL), (_f['alerta'], C_RED)):
                if not np.isfinite(_v):
                    continue
                fig_k3.add_shape(type='line', xref='x', yref='y',
                                 x0=_v, x1=_v, y0=_i - 0.34, y1=_i + 0.34,
                                 line=dict(color=_c, width=2.4), layer='above')
        # Valor, fecha y hora al final de la barra (o de la marca, si sobresale),
        # de modo que la etiqueta nunca se monte sobre el umbral.
        _xmax_k3 = float(np.nanmax([k3['pico'].max(), k3['alerta'].max()]))
        for _i, _f in k3.iterrows():
            _x = max(_f['pico'], _f['alerta'] if np.isfinite(_f['alerta']) else 0)
            fig_k3.add_annotation(
                x=_x + _xmax_k3 * 0.012, y=_i, xref='x', yref='y',
                xanchor='left', yanchor='middle', showarrow=False, align='left',
                text=(f"<b>{_f['pico']:,.1f} kW</b>"
                      f"<span style=\"color:{MUTED}\"> · {_f['cuando']}"
                      f"{' · sin base' if _f['estado'] == 'sin base' else ''}</span>"),
                font=dict(size=11.5, color=INK),
            )
        for _c, _nom in ((C_TEAL, 'Objetivo (μ)'), (C_RED, 'Alerta (μ+1σ)')):
            fig_k3.add_trace(go.Scatter(
                x=[None], y=[None], mode='lines', name=_nom,
                line=dict(color=_c, width=2.4),
            ))
        fig_k3.update_xaxes(range=[0, _xmax_k3 * 1.03])
        fig_k3.update_layout(
            showlegend=True, margin=dict(t=64, b=44, l=100, r=180),
            legend=dict(orientation='h', yanchor='bottom', y=1.01,
                        xanchor='right', x=1, font=dict(size=11, color=INK2)),
        )
        _chart(fig_k3, use_container_width=True)

        _top = k3.iloc[-1]
        m1, m2, m3 = st.columns(3)
        m1.metric("Mayor pico de un bloque", f"{_top['pico']:,.1f} kW",
                  help="D_pico = máximo(activepower) del período, por bloque.")
        m2.metric("Bloque del pico", _top['bloque'],
                  delta=_top['cuando_largo'], delta_color="off",
                  help="Bloque, fecha y hora de ocurrencia exigidos por la ficha.")
        if np.isfinite(_top['objetivo']):
            m3.metric("Exceso sobre su objetivo", f"{_top['pico'] - _top['objetivo']:+,.1f} kW",
                      delta=f"objetivo {_top['objetivo']:,.1f} kW", delta_color="off",
                      help="Distancia hasta la media de picos mensuales del bloque.")
        else:
            m3.metric("Exceso sobre su objetivo", "—", help="Sin base histórica suficiente.")

        _n_alerta  = int((k3['estado'] == 'alerta').sum())
        _n_sinbase = int((k3['estado'] == 'sin base').sum())
        _txt = (f"El mayor pico del período fue **{_top['pico']:,.1f} kW** en "
                f"**{_top['bloque']}**, el {_top['cuando_largo']}. Ese valor —y no el "
                f"consumo total— es el que fija el cargo por demanda de la factura: "
                f"bajarlo se traduce en ahorro directo.")
        if _n_alerta:
            st.warning(_txt + f" **{_n_alerta} bloque(s)** superan su umbral de alerta.")
        else:
            st.info(_txt)

        # Tira de estado mensual: el umbral de cada bloque, mes a mes.
        _chart(tira_estado(
            _k3_mens, 'KPI03_pico_kw', 'KPI 03 — Pico de demanda', None,
            'verde ≤ μ\nnaranja ≤ μ+1σ\nrojo > μ+1σ\ngris sin base',
            estado_fn=_color_k3, fmt='{:,.1f} kW',
        ), use_container_width=True)

        st.caption(
            ("D_pico = máximo(activepower) sobre el período exacto seleccionado, por "
             "bloque, sumando en el mismo instante los medidores del bloque. "
             if _k3_exacto else
             "D_pico tomado del pico mensual precalculado (clean_etsmartmeter.csv no "
             "disponible): con un filtro que no cubra meses enteros el pico puede "
             "haber ocurrido fuera del período. ") +
            "activepower es la **media horaria** del medidor Landis, así que el pico "
            "instantáneo real es algo mayor que el reportado. "
            "Umbral propio: objetivo = μ y alerta = μ+1σ de la serie mensual de picos "
            "del bloque, sobre los demás meses con dato (máx. 12) — el mes que se juzga "
            "no entra en su propio umbral, y la base no depende del filtro de fechas para "
            f"que la evaluación sea reproducible; con menos de 4 meses de base no se emite "
            f"semáforo ({_n_sinbase} bloque(s) hoy). ODS 7 y 9."
        )

    # ── KPI 05 — Emisiones CO₂ acumuladas ────────────────────────────────────
    st.markdown("## KPI 05 — Emisiones CO₂ acumuladas vs. meta")
    actual_diario = kpi_f.groupby('fecha')['KPI05_CO2_tCO2e'].sum().sort_index()
    if not actual_diario.empty:
        actual_acum   = actual_diario.cumsum()
        mu_co2        = float(actual_diario.mean())
        sigma_co2     = float(actual_diario.std()) if len(actual_diario) > 1 else 0.0
        n_acum        = pd.Series(range(1, len(actual_diario) + 1), index=actual_diario.index, dtype=float)
        alerta_acum   = (mu_co2 + sigma_co2) * n_acum
        objetivo_acum = mu_co2 * 0.93 * n_acum

        fig_k5 = go.Figure()
        fig_k5.add_trace(go.Scatter(
            x=actual_acum.index.tolist() + actual_acum.index[::-1].tolist(),
            y=objetivo_acum.values.tolist() + alerta_acum.values[::-1].tolist(),
            fill='toself', fillcolor='rgba(239,159,39,0.08)',
            line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip',
        ))
        fig_k5.add_trace(go.Scatter(
            x=alerta_acum.index, y=alerta_acum.values, mode='lines',
            name='Alerta acum. (μ+1σ)',
            line=dict(color=C_RED, width=1.5, dash='dash'),
        ))
        fig_k5.add_trace(go.Scatter(
            x=objetivo_acum.index, y=objetivo_acum.values, mode='lines',
            name='Objetivo acum. (μ−7%)',
            line=dict(color=C_TEAL, width=1.5, dash='dot'),
        ))
        fig_k5.add_trace(go.Scatter(
            x=actual_acum.index, y=actual_acum.values, mode='lines+markers',
            name='Real acumulado',
            line=dict(color=C_AMBER, width=2.5),
            marker=dict(color=C_AMBER, size=5),
            hovertemplate='%{x|%d %b}: %{y:.4f} tCO₂e<extra></extra>',
        ))
        fig_k5.update_layout(title=dict(text='KPI 05 — Emisiones CO₂ acumuladas', font=dict(size=13), x=0),
                             xaxis_title='Fecha', yaxis_title='tCO₂e acumuladas')
        _chart(_layout_base(fig_k5, h=360), use_container_width=True)
        st.caption(
            f"μ diario = {mu_co2:.4f} tCO₂e · "
            f"alerta acum. = {alerta_acum.iloc[-1]:.3f} tCO₂e · "
            f"objetivo acum. = {objetivo_acum.iloc[-1]:.3f} tCO₂e."
        )

    # ── KPI 08 — Load Factor ─────────────────────────────────────────────────
    st.markdown("## KPI 08 — Load Factor (mensual)")
    lf_vals            = kpi_f['KPI08_LF'].dropna()
    mu_lf              = float(lf_vals.mean()) if len(lf_vals) > 0 else 0.65
    sigma_lf           = float(lf_vals.std())  if len(lf_vals) > 1 else 0.0
    umbral_alerta_lf   = max(0.0, mu_lf - sigma_lf)
    umbral_objetivo_lf = min(1.0, mu_lf * 1.07)

    lf_medio_k8 = kpi_f.groupby('entity_id')['KPI08_LF'].mean().sort_values()
    lf_medio_k8.index = [_bloque_label(e) for e in lf_medio_k8.index]

    _chart(barras_horizontales(
        lf_medio_k8, titulo='KPI 08 — Media de los LF mensuales por bloque',
        xlabel='Factor de carga mensual (0–1)',
        color_fn=lambda v: _semaforo(v, umbral_objetivo_lf, umbral_alerta_lf),
        ref_lines=[
            (umbral_objetivo_lf, C_TEAL, f'objetivo {umbral_objetivo_lf:.3f}'),
            (umbral_alerta_lf,   C_RED,  f'alerta {umbral_alerta_lf:.3f}'),
        ],
    ), use_container_width=True)
    st.caption(
        "LF mensual = P̄ del mes / P_máx del mes. No coincide con el IND-01 de la "
        "pestaña de indicadores, que promedia LF diarios: misma fórmula, ventana "
        "distinta (ver nota allí)."
    )
    _chart(tira_estado(
        kpi_f, 'KPI08_LF', 'KPI 08 — Load Factor',
        lambda v: _semaforo(v, umbral_objetivo_lf, umbral_alerta_lf),
        f'verde ≥ {umbral_objetivo_lf:.3f}\nnaranja ≥ {umbral_alerta_lf:.3f}\nrojo < {umbral_alerta_lf:.3f}',
    ), use_container_width=True)

    # ── KPI 09 — Consumo no operacional ──────────────────────────────────────
    st.markdown("## KPI 09 — Índice de consumo no operacional")
    f4_bloque_k9    = kpi_f.groupby('entity_id')['KPI09_f4_pct'].mean().sort_values(ascending=False)
    mu_k9           = float(f4_bloque_k9.mean()) if len(f4_bloque_k9) > 0 else 20.0
    sigma_k9        = float(f4_bloque_k9.std())  if len(f4_bloque_k9) > 1 else 0.0
    umbral_alerta_k9   = mu_k9 + sigma_k9
    umbral_objetivo_k9 = mu_k9 * 0.93
    f4_bloque_k9.index = [_bloque_label(e) for e in f4_bloque_k9.index]

    _chart(barras_horizontales(
        f4_bloque_k9, titulo='KPI 09 — Consumo no operacional por bloque',
        xlabel='% (22:00–06:00)',
        color_fn=lambda v: _semaforo(v, umbral_objetivo_k9, umbral_alerta_k9, mayor_es_mejor=False),
        ref_lines=[
            (umbral_objetivo_k9, C_TEAL, f'objetivo {umbral_objetivo_k9:.1f}%'),
            (umbral_alerta_k9,   C_RED,  f'alerta {umbral_alerta_k9:.1f}%'),
        ],
    ), use_container_width=True)
    if total_kwh_campus is not None and total_kwh_campus > 0:
        pct_noche  = float(f4_bloque_k9.mean()) / 100
        e_noche    = total_kwh_campus * pct_noche
        costo_noch = e_noche * TARIFA_BASE_COP_KWH
        pct_exceso = max(0.0, pct_noche - umbral_objetivo_k9 / 100)
        ahorro_kwh = total_kwh_campus * pct_exceso
        ahorro_cop = ahorro_kwh * TARIFA_BASE_COP_KWH

        cn1, cn2, cn3 = st.columns(3)
        cn1.metric("Energía nocturna", f"{e_noche:,.0f} kWh")
        cn2.metric("Costo nocturno", f"${costo_noch:,.0f} COP")
        if ahorro_cop > 0:
            cn3.metric("Ahorro potencial", f"${ahorro_cop:,.0f} COP",
                       delta=f"−{ahorro_kwh:,.0f} kWh", delta_color="inverse")
            st.warning(
                f"**{pct_noche*100:.1f}%** del consumo ocurre entre 22:00 y 06:00 "
                f"({e_noche:,.0f} kWh · ${costo_noch:,.0f} COP). "
                f"Reducir al objetivo ({umbral_objetivo_k9:.1f}%) ahorraría **${ahorro_cop:,.0f} COP**."
            )
        else:
            cn3.metric("Objetivo cumplido", "—")
            st.success(
                f"Consumo nocturno: **{pct_noche*100:.1f}%** — por debajo del objetivo "
                f"({umbral_objetivo_k9:.1f}%). Costo nocturno: **${costo_noch:,.0f} COP**."
            )

    _chart(tira_estado(
        kpi_f, 'KPI09_f4_pct', 'KPI 09 — Consumo no operacional',
        lambda v: _semaforo(v, umbral_objetivo_k9, umbral_alerta_k9, mayor_es_mejor=False),
        f'verde ≤ {umbral_objetivo_k9:.1f}%\nnaranja ≤ {umbral_alerta_k9:.1f}%\nrojo > {umbral_alerta_k9:.1f}%',
    ), use_container_width=True)

    # ── KPI 10 — Desbalance de tensión ───────────────────────────────────────
    st.markdown("## KPI 10 — Desbalance de tensión")
    _chart(tira_estado(
        kpi_f, 'KPI10_desbalance_pct', 'KPI 10 — Desbalance de tensión',
        lambda v: _semaforo(v, UMBRAL_DB_OBJ, UMBRAL_DB_ALERT, mayor_es_mejor=False),
        f'verde < {UMBRAL_DB_OBJ:.0f}%\nnaranja < {UMBRAL_DB_ALERT:.0f}%\nrojo ≥ {UMBRAL_DB_ALERT:.0f}%',
    ), use_container_width=True)

    # ── KPI 11 — Factor de potencia ─────────────────────────────────────────
    st.markdown("## KPI 11 — Factor de potencia total")
    serie_fp = kpi_f.groupby('fecha')['KPI11_fp'].mean().sort_index()
    if not serie_fp.empty:
        colores_fp = [_semaforo(v, UMBRAL_FP_OBJ, UMBRAL_FP_ALERT) for v in serie_fp.values]
        fig_k11 = go.Figure()
        fig_k11.add_hrect(y0=0, y1=UMBRAL_FP_ALERT, fillcolor=C_RED, opacity=0.06, line_width=0)
        fig_k11.add_hrect(y0=UMBRAL_FP_ALERT, y1=UMBRAL_FP_OBJ, fillcolor=C_AMBER, opacity=0.06, line_width=0)
        fig_k11.add_trace(go.Scatter(
            x=serie_fp.index, y=serie_fp.values, mode='lines+markers',
            line=dict(color=C_PURPLE, width=2),
            marker=dict(color=colores_fp, size=8, line=dict(color='white', width=1)),
            hovertemplate='%{x|%b %Y}: FP = %{y:.3f}<extra></extra>',
            showlegend=False,
        ))
        fig_k11.add_hline(y=UMBRAL_FP_OBJ, line_color=C_TEAL, line_dash='dot',
                          annotation_text=f'objetivo {UMBRAL_FP_OBJ}', annotation_position='top right',
                          annotation_font_color=C_TEAL)
        fig_k11.add_hline(y=UMBRAL_FP_ALERT, line_color=C_RED, line_dash='dash',
                          annotation_text=f'alerta {UMBRAL_FP_ALERT}', annotation_position='bottom right',
                          annotation_font_color=C_RED)
        ymin = min(UMBRAL_FP_ALERT * 0.95, serie_fp.min() * 0.98)
        fig_k11.update_yaxes(range=[ymin, 1.0])
        fig_k11.update_layout(title=dict(text='KPI 11 — Factor de potencia (mínimo mensual)',
                                         font=dict(size=13), x=0),
                              xaxis_title='Fecha', yaxis_title='FP')
        _chart(_layout_base(fig_k11, h=320), use_container_width=True)

    _chart(tira_estado(
        kpi_f, 'KPI11_fp', 'KPI 11 — Factor de potencia',
        lambda v: _semaforo(v, UMBRAL_FP_OBJ, UMBRAL_FP_ALERT),
        f'verde ≥ {UMBRAL_FP_OBJ}\nnaranja ≥ {UMBRAL_FP_ALERT}\nrojo < {UMBRAL_FP_ALERT}',
    ), use_container_width=True)

    # ── KPIs en integración / validación (DEMO) ──────────────────────────────
    st.markdown("## KPIs en integración / validación")
    st.info(
        "Los siguientes KPIs muestran **valores de referencia (DEMO)** porque sus fuentes de datos "
        "aún no están confirmadas. Se actualizarán automáticamente cuando se integren los datos reales."
    )

    # ── KPI 02 — Intensidad por usuario [DEMO] ──────────────────────────────
    st.markdown("## KPI 02 — Intensidad energética por usuario")
    st.warning(
        "**DEMO — Valor de referencia:** N° de usuarios (estudiantes + docentes + administrativos) "
        "sin confirmar. Referencia utilizada: 3 500 usuarios totales."
    )
    k02 = kpi_demo_f[kpi_demo_f['kpi'] == 'KPI-02'].copy()
    if not k02.empty and k02['valor_num'].dropna().shape[0] > 0:
        k02_mes = k02.groupby('mes')['valor_num'].mean().sort_index()
        fig_k02 = go.Figure(go.Bar(
            x=k02_mes.index, y=k02_mes.values,
            marker_color=C_AMBER,
            text=[f'{v:.2f}' for v in k02_mes.values], textposition='outside',
            hovertemplate='%{x}: %{y:.2f} kWh/usuario<extra></extra>',
        ))
        fig_k02.update_layout(
            title=dict(text='KPI 02 — kWh/usuario mensual (DEMO)', font=dict(size=13), x=0),
            xaxis_title='Mes', yaxis_title='kWh/usuario',
        )
        _chart(_layout_base(fig_k02, h=300), use_container_width=True)
        estado_k02 = k02['estado'].dropna().iloc[0] if not k02['estado'].dropna().empty else 'DEMO'
        st.caption(f"Estado: {estado_k02} · Unidad: kWh/usuario")
    else:
        st.info("KPI 02 sin valores para el período seleccionado.")

    # ── KPI 04 — Ahorro verificado [DEMO] ────────────────────────────────────
    st.markdown("## KPI 04 — Ahorro energético verificado")
    st.warning(
        "**DEMO — Valor de referencia:** Requiere línea base de ≥ 12 meses de historial. "
        "Meta establecida: ≥ 3% de reducción anual respecto al año anterior."
    )
    k04 = kpi_demo_f[kpi_demo_f['kpi'] == 'KPI-04'].copy()
    if not k04.empty and k04['valor_num'].dropna().shape[0] > 0:
        META_K04   = 3.0
        val_k04    = float(k04['valor_num'].dropna().iloc[0])
        color_k04  = C_TEAL if val_k04 >= META_K04 else C_AMBER
        st.metric("Ahorro de referencia (DEMO)", f"{val_k04:.2f}%",
                  delta=f"meta ≥ {META_K04:.0f}%",
                  delta_color="normal" if val_k04 >= META_K04 else "inverse")
        st.markdown(
            f'<div style="background:#FFF8EC;border-left:4px solid {color_k04};'
            f'border-radius:8px;padding:12px 16px">'
            f'El valor <b>{val_k04:.2f}%</b> es un estimado de referencia calculado con la energía '
            f'disponible hasta la fecha (< 12 meses de historial). '
            f'La meta es <b>≥ {META_K04:.0f}% de reducción anual</b> respecto al año anterior.</div>',
            unsafe_allow_html=True,
        )
        estado_k04 = k04['estado'].dropna().iloc[0] if not k04['estado'].dropna().empty else 'DEMO'
        st.caption(f"Estado: {estado_k04} · El valor es constante por bloque (referencia campus).")
    else:
        st.info("KPI 04 sin valores para el período seleccionado.")

    # ── KPI 06 — Performance Ratio FV [DEMO] ─────────────────────────────────
    st.markdown("## KPI 06 — Performance Ratio (PR) fotovoltaico")
    st.warning(
        "**DEMO — Valor de referencia:** Datos de irradiación solar y capacidad kWp instalada "
        "sin confirmar (integración Fronius pendiente). Referencia: PR ≥ 0.73."
    )
    k06 = kpi_demo_f[kpi_demo_f['kpi'] == 'KPI-06'].copy()
    if not k06.empty and k06['valor_num'].dropna().shape[0] > 0:
        META_K06_OBJ = 0.73
        META_K06_ALT = 0.60
        k06_mes = k06.groupby('mes')['valor_num'].mean().sort_index()
        colores_k06 = [_semaforo(v, META_K06_OBJ, META_K06_ALT) for v in k06_mes.values]
        fig_k06 = go.Figure()
        fig_k06.add_hrect(y0=META_K06_OBJ, y1=1.05, fillcolor=C_TEAL, opacity=0.05, line_width=0)
        fig_k06.add_hrect(y0=META_K06_ALT, y1=META_K06_OBJ, fillcolor=C_AMBER, opacity=0.07, line_width=0)
        fig_k06.add_trace(go.Scatter(
            x=k06_mes.index, y=k06_mes.values, mode='lines+markers',
            line=dict(color=C_PURPLE, width=2),
            marker=dict(color=colores_k06, size=9, line=dict(color='white', width=1)),
            hovertemplate='%{x}: PR = %{y:.3f}<extra></extra>',
            showlegend=False,
        ))
        fig_k06.add_hline(y=META_K06_OBJ, line_color=C_TEAL, line_dash='dot',
                          annotation_text='objetivo 0.73', annotation_position='top right',
                          annotation_font_color=C_TEAL)
        fig_k06.update_layout(
            title=dict(text='KPI 06 — Performance Ratio FV mensual (DEMO)', font=dict(size=13), x=0),
            xaxis_title='Mes', yaxis_title='PR (adimensional)',
        )
        _chart(_layout_base(fig_k06, h=300), use_container_width=True)
        estado_k06 = k06['estado'].dropna().iloc[0] if not k06['estado'].dropna().empty else 'DEMO'
        bloq_k06   = k06['bloque'].dropna().iloc[0] if not k06['bloque'].dropna().empty else '?'
        st.caption(f"Bloques FV: {bloq_k06} · Estado: {estado_k06}")
    else:
        st.info("KPI 06 sin valores para el período seleccionado.")

    # ── KPI 07 — Autosuficiencia solar [DEMO] ────────────────────────────────
    st.markdown("## KPI 07 — Autosuficiencia solar (SS)")
    st.warning(
        "**DEMO — Valor de referencia:** Exportación de energía solar al campus sin confirmar. "
        "Referencia: SS ≥ 12%."
    )
    k07 = kpi_demo_f[kpi_demo_f['kpi'] == 'KPI-07'].copy()
    if not k07.empty and k07['valor_num'].dropna().shape[0] > 0:
        META_K07 = 12.0
        k07_mes = k07.groupby('mes')['valor_num'].mean().sort_index()
        colores_k07 = [C_TEAL if v >= META_K07 else C_AMBER for v in k07_mes.values]
        fig_k07 = go.Figure(go.Bar(
            x=k07_mes.index, y=k07_mes.values,
            marker_color=colores_k07,
            text=[f'{v:.1f}%' for v in k07_mes.values], textposition='outside',
            hovertemplate='%{x}: SS = %{y:.1f}%<extra></extra>',
        ))
        fig_k07.add_hline(y=META_K07, line_color=C_TEAL, line_dash='dot',
                          annotation_text='objetivo 12%', annotation_position='top right',
                          annotation_font_color=C_TEAL)
        fig_k07.update_layout(
            title=dict(text='KPI 07 — Autosuficiencia solar % mensual (DEMO)', font=dict(size=13), x=0),
            xaxis_title='Mes', yaxis_title='%',
        )
        _chart(_layout_base(fig_k07, h=300), use_container_width=True)
        estado_k07 = k07['estado'].dropna().iloc[0] if not k07['estado'].dropna().empty else 'DEMO'
        st.caption(f"Estado: {estado_k07}")
    else:
        st.info("KPI 07 sin valores para el período seleccionado.")

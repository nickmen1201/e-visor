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
    st.plotly_chart(fig, key=f"c{_chart_n[0]}", **kwargs)

st.set_page_config(page_title="E-Visor · Ecocampus UPB", layout="wide",
                   initial_sidebar_state="expanded")

# ── Paleta ────────────────────────────────────────────────────────────────────
C_TEAL   = '#1D9E75'
C_AMBER  = '#EF9F27'
C_RED    = '#A32D2D'
C_GRAY   = '#B4B2A9'
C_BLUE   = '#378ADD'
C_PURPLE = '#534AB7'
C_BG     = '#F7F7F5'

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
    9:   7579.50,
    10: 11469.06,
    12:  2848.88,
    15:  7780.01,
    17:  7611.12,
    18: 35916.80,
}

TARIFA_BASE_COP_KWH   = 859.19
TARIFA_INDCOM_COP_KWH = 1_031.03
HOGAR_KWH_MES         = 130

UMBRAL_FP_OBJ   = 0.90
UMBRAL_FP_ALERT = 0.85
UMBRAL_DB_OBJ   = 1.0
UMBRAL_DB_ALERT = 2.0

_DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #F7F7F5; }
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E5E3DC; }
h1 { font-size: 1.6rem !important; font-weight: 700 !important; color: #1A1A18 !important; }
h2 { font-size: 1.15rem !important; font-weight: 600 !important; color: #2C2C2A !important;
     border-left: 4px solid #1D9E75; padding-left: 10px; margin-top: 1.8rem !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; color: #2C2C2A !important; }
div[data-testid="metric-container"] {
    background: #FFFFFF; border: 1px solid #E5E3DC; border-radius: 10px;
    padding: 14px 18px; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
div[data-testid="metric-container"] label { font-size: .78rem !important; color: #6B6965 !important; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.5rem !important; font-weight: 700 !important; color: #1A1A18 !important;
}
.kpi-card {
    background: #FFFFFF; border: 1px solid #E5E3DC; border-radius: 10px;
    padding: 16px 20px; box-shadow: 0 1px 4px rgba(0,0,0,.05); height: 100%;
}
.status-verde  { color: #1D9E75; font-weight: 700; }
.status-ambar  { color: #EF9F27; font-weight: 700; }
.status-rojo   { color: #A32D2D; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


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
    ind['bloque'] = ind['bloque'].astype(int)

    d12 = (ind_raw[ind_raw['indicador'] == 'IND-12']
           [['bloque', 'fecha', 'valor_num']]
           .dropna(subset=['bloque']).copy())
    d12['fecha']  = pd.to_datetime(d12['fecha'])
    d12['bloque'] = d12['bloque'].astype(int)
    d12 = (d12.groupby(['bloque', 'fecha'])['valor_num']
              .mean().reset_index()
              .rename(columns={'valor_num': 'desbalance_pct'}))
    ind = pd.merge(ind, d12, on=['bloque', 'fecha'], how='outer')

    d07 = (ind_raw[ind_raw['indicador'] == 'IND-07']
           [['bloque', 'mes', 'valor_num']]
           .dropna(subset=['bloque']).copy()
           .rename(columns={'valor_num': 'co2_mes'}))
    d07['bloque'] = d07['bloque'].astype(int)
    co2_rows = []
    for _, row in d07.iterrows():
        b, mes_str, co2 = int(row['bloque']), row['mes'], row['co2_mes']
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

    ind['entity_id']   = 'SmartMeter_SM_' + ind['bloque'].astype(str)
    ind['fp_promedio'] = np.nan
    ind['fecha']       = pd.to_datetime(ind['fecha'])

    kpi_raw = xl.parse('KPIs')
    kpi_raw['valor_num']  = pd.to_numeric(kpi_raw['valor'], errors='coerce')
    kpi_raw['bloque_int'] = pd.to_numeric(kpi_raw['bloque'], errors='coerce')
    kpi_raw['fecha'] = (pd.to_datetime(kpi_raw['mes'], format='%Y-%m', errors='coerce')
                        + pd.offsets.MonthEnd(0))
    _KPI_MAP = {
        'KPI-01': 'KPI01_kwh_m2', 'KPI-03': 'KPI03_pico_kw',
        'KPI-05': 'KPI05_CO2_tCO2e', 'KPI-08': 'KPI08_LF',
        'KPI-09': 'KPI09_f4_pct', 'KPI-10': 'KPI10_desbalance_pct',
        'KPI-11': 'KPI11_fp',
    }
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
    kpi['bloque']    = kpi['bloque'].astype(int)
    kpi['entity_id'] = 'SmartMeter_SM_' + kpi['bloque'].astype(str)
    kpi['area_m2']   = kpi['bloque'].map(AREAS_BLOQUE)
    kpi['e_wh']      = kpi['KPI01_kwh_m2'] * kpi['area_m2'] * 1000

    k03x = (kpi_raw[kpi_raw['kpi'] == 'KPI-03']
            [['bloque_int', 'fecha', 'fecha_pico', 'hora_pico']]
            .dropna(subset=['bloque_int'])
            .rename(columns={'bloque_int': 'bloque'}))
    k03x['bloque'] = k03x['bloque'].astype(int)
    kpi = pd.merge(kpi, k03x, on=['bloque', 'fecha'], how='left')

    try:
        raw = pd.read_csv(BASE / 'etsmartmeter_clean.csv',
                          parse_dates=['time_index_colombia'])
        raw['hora']  = raw['time_index_colombia'].dt.hour
        raw['fecha'] = pd.to_datetime(raw['time_index_colombia'].dt.date)
    except FileNotFoundError:
        raw = None

    return ind, kpi, raw


ind, kpi, raw = cargar_datos()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _bloque_label(entity_id):
    return entity_id.replace('SmartMeter_SM_', 'B')


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


def _layout_base(fig, h=340):
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=h, margin=dict(t=50, b=40, l=60, r=20),
        font=dict(family='Inter, sans-serif', size=12, color='#2C2C2A'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02,
                    xanchor='right', x=1, font=dict(size=11)),
    )
    fig.update_xaxes(gridcolor='#EEEEEE', linecolor='#DDDDDD')
    fig.update_yaxes(gridcolor='#EEEEEE', linecolor='#DDDDDD', rangemode='tozero')
    return fig


def barras_horizontales(serie, titulo, xlabel, color_fn=None,
                        ref_lines=None, h=None):
    """Barras horizontales genéricas con colores por umbral."""
    labels  = [str(x) for x in serie.index]
    valores = serie.values
    colores = [color_fn(v) for v in valores] if color_fn else [C_TEAL] * len(valores)
    fig = go.Figure(go.Bar(
        x=valores, y=labels, orientation='h',
        marker_color=colores, marker_line_width=0,
        text=[f'{v:.2f}' for v in valores],
        textposition='outside',
        hovertemplate='%{y}: %{x:.3f}<extra></extra>',
    ))
    if ref_lines:
        for val, color, label in ref_lines:
            fig.add_vline(x=val, line_color=color, line_dash='dot', line_width=1.5,
                          annotation_text=label, annotation_position='top right',
                          annotation_font_color=color, annotation_font_size=10)
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13, color='#1A1A18'), x=0),
        xaxis_title=xlabel,
        plot_bgcolor='white', paper_bgcolor='white',
        height=h or max(280, 36 * len(serie) + 100),
        margin=dict(t=50, b=40, l=90, r=90),
        font=dict(family='Inter, sans-serif', size=12),
    )
    fig.update_xaxes(gridcolor='#EEEEEE')
    fig.update_yaxes(gridcolor='#F0F0F0')
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
        line=dict(color=C_TEAL, width=1.8),
        marker=dict(color=C_TEAL, size=5),
        hovertemplate='%{x|%d %b}: %{y:.3f}<extra>Hábil</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=finde.index, y=finde['val'], mode='markers',
        name='Fin de semana',
        marker=dict(color=C_AMBER, size=8, symbol='diamond'),
        hovertemplate='%{x|%d %b}: %{y:.3f}<extra>Fin de semana</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=df_s.index, y=df_s['ma7'], mode='lines',
        name='Media móvil 7d',
        line=dict(color=C_GRAY, width=2.5, dash='dot'), opacity=0.8,
        hovertemplate='%{x|%d %b}: %{y:.3f}<extra>MA7</extra>',
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13), x=0),
        xaxis_title='Fecha', yaxis_title=titulo_y,
    )
    return _layout_base(fig, h=h)


def comparativo_bloques(ind_df, col, titulo_x, titulo='Promedio por bloque (período)'):
    serie = (ind_df
             .assign(bloque=ind_df['entity_id'].str.replace('SmartMeter_SM_', 'B', regex=False))
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
        number=dict(font=dict(size=60, color='#1A1A18', family='Inter'),
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


def tira_estado(kpi_df, col, titulo, color_fn, leyenda):
    """Heatmap calendario de estado (reemplaza la tira matplotlib)."""
    pivot  = kpi_df.pivot_table(index='entity_id', columns='fecha',
                                values=col, aggfunc='mean')
    fechas = pivot.columns.tolist()
    labels_y = [_bloque_label(e) for e in pivot.index]

    z      = pivot.values
    n_col  = len(fechas)
    n_row  = len(pivot)

    # Convertir a valor numérico de estado: 0=verde 0.5=ámbar 1=rojo nan=gris
    z_estado = np.full(z.shape, np.nan)
    for i in range(n_row):
        for j in range(n_col):
            v = z[i, j]
            if np.isnan(v):
                continue
            c = color_fn(v)
            z_estado[i, j] = 0.0 if c == C_TEAL else (0.5 if c == C_AMBER else 1.0)

    colorscale = [
        [0.0,  C_TEAL],
        [0.49, C_TEAL],
        [0.5,  C_AMBER],
        [0.74, C_AMBER],
        [0.75, C_RED],
        [1.0,  C_RED],
    ]
    hover = [[
        f'{_bloque_label(pivot.index[i])} · {fechas[j].strftime("%d %b %Y")}<br>'
        f'Valor: {z[i,j]:.3f}' if not np.isnan(z[i,j]) else 'Sin dato'
        for j in range(n_col)
    ] for i in range(n_row)]

    fig = go.Figure(go.Heatmap(
        z=z_estado,
        x=[f.strftime('%d-%b') for f in fechas],
        y=labels_y,
        colorscale=colorscale,
        zmin=0, zmax=1,
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
    st.markdown("## ⚡ E-Visor")
    st.markdown("**Ecocampus UPB** · Medellín")
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

if seleccion != "Todos":
    ind_f = ind_f[ind_f['entity_id'] == seleccion]
    kpi_f = kpi_f[kpi_f['entity_id'] == seleccion]

raw_f = None
if raw is not None:
    raw_f = raw[raw['fecha'].between(inicio, fin)]
    if seleccion != "Todos":
        raw_f = raw_f[raw_f['entity_id'] == seleccion]

if ind_f.empty:
    st.warning("Sin datos para el rango seleccionado.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# CABECERA
# ═══════════════════════════════════════════════════════════════════════════════
bloque_txt = ("Todos los bloques" if seleccion == "Todos"
              else f"Bloque {seleccion.replace('SmartMeter_SM_', '')}")
periodo_dias = max(1, (fin - inicio).days + 1)

st.markdown(f"# ⚡ E-Visor — Dashboard energético")
st.markdown(
    f"**{bloque_txt}** &nbsp;·&nbsp; "
    f"{inicio.strftime('%d %b %Y')} — {fin.strftime('%d %b %Y')} "
    f"({periodo_dias} días)"
)
st.divider()


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

cols_res = st.columns(6)
with cols_res[0]:
    if total_kwh_campus:
        costo = total_kwh_campus * TARIFA_BASE_COP_KWH
        st.metric("⚡ Energía consumida", f"{total_kwh_campus:,.0f} kWh",
                  help=f"Costo estimado: ${costo:,.0f} COP (EPM NT1 ene-2026)")
    else:
        st.metric("⚡ Energía consumida", "—")

with cols_res[1]:
    if co2_total is not None:
        st.metric("🌍 Emisiones CO₂", f"{co2_total:.3f} tCO₂e",
                  help=f"≈ {int(co2_total * ARBOLES_POR_TON_CO2):,} árboles jóvenes")
    else:
        st.metric("🌍 Emisiones CO₂", "—")

with cols_res[2]:
    if lf_medio is not None:
        color_lf = "normal" if lf_medio >= 0.65 else "inverse"
        st.metric("📊 Load Factor medio", f"{lf_medio:.3f}",
                  delta="≥ 0.65 objetivo" if lf_medio >= 0.65 else "< 0.65 alerta",
                  delta_color=color_lf)
    else:
        st.metric("📊 Load Factor", "—")

with cols_res[3]:
    if pico_max is not None:
        st.metric("⚡ Pico de demanda", f"{pico_max:.1f} kW",
                  help="Máximo registrado en el período")
    else:
        st.metric("⚡ Pico de demanda", "—")

with cols_res[4]:
    if fp_medio is not None:
        delta_fp = "✓ objetivo" if fp_medio >= UMBRAL_FP_OBJ else ("⚠ revisar" if fp_medio >= UMBRAL_FP_ALERT else "✗ alerta")
        st.metric("⚡ Factor de potencia", f"{fp_medio:.3f}",
                  delta=delta_fp,
                  delta_color="normal" if fp_medio >= UMBRAL_FP_OBJ else "inverse")
    else:
        st.metric("⚡ Factor de potencia", "—")

with cols_res[5]:
    if db_medio is not None:
        delta_db = "✓ normal" if db_medio < UMBRAL_DB_OBJ else ("⚠ revisar" if db_medio < UMBRAL_DB_ALERT else "✗ alerta")
        st.metric("⚖️ Desbalance tensión", f"{db_medio:.2f}%",
                  delta=delta_db,
                  delta_color="normal" if db_medio < UMBRAL_DB_OBJ else "inverse")
    else:
        st.metric("⚖️ Desbalance tensión", "—")

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_ind, tab_kpi = st.tabs(["📈 Indicadores", "🎯 KPIs"])


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
    st.markdown("## LF — Factor de carga")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        fig_lf_bar = barras_horizontales(
            ind_f.assign(bloque=ind_f['entity_id'].str.replace('SmartMeter_SM_', 'B', regex=False))
                 .groupby('bloque')['LF'].mean().sort_values(),
            titulo='LF medio por bloque',
            xlabel='Factor de carga (0–1)',
            color_fn=lambda v: _semaforo(v, 0.65, 0.50),
            ref_lines=[(0.65, C_TEAL, 'objetivo 0.65')],
        )
        _chart(fig_lf_bar, use_container_width=True)
    with col_b:
        _chart(serie_diaria(ind_f, 'LF', 'LF (adimensional)'),
                        use_container_width=True)

    # ── PAR — Peak-to-Average Ratio ─────────────────────────────────────────
    st.markdown("## PAR — Peak-to-Average Ratio")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        fig_par_bar = barras_horizontales(
            ind_f.assign(bloque=ind_f['entity_id'].str.replace('SmartMeter_SM_', 'B', regex=False))
                 .groupby('bloque')['PAR'].mean().sort_values(),
            titulo='PAR medio por bloque',
            xlabel='PAR (>1 = picos pronunciados)',
            color_fn=lambda v: _semaforo(v, 1.54, 2.0, mayor_es_mejor=False),
        )
        _chart(fig_par_bar, use_container_width=True)
    with col_b:
        _chart(serie_diaria(ind_f, 'PAR', 'PAR (adimensional)'),
                        use_container_width=True)

    # ── f₁ — Uniformidad diurna ─────────────────────────────────────────────
    st.markdown("## f₁ — Uniformidad de franja diurna")
    _d1, _r1, _fr1 = _delta_semana(ind_f, 'f1')
    _fh1 = ind_f['fecha'].max()
    _v1  = ind_f[ind_f['fecha'] == _fh1]['f1'].mean()

    col_a, col_b, col_c = st.columns([1, 1.5, 1])
    with col_a:
        _chart(card_indicador(
            _v1, 'P̄ op.', _comp['prom'] if _comp else None,
            'P_max op.', _comp['max'] if _comp else None,
            _d1, _r1, _fr1, _fh1), use_container_width=True)
    with col_b:
        _chart(serie_diaria(ind_f, 'f1', 'f₁ (adimensional)'),
                        use_container_width=True)
    with col_c:
        _chart(graficar_evidencia_f1(_comp), use_container_width=True)

    _chart(comparativo_bloques(ind_fechas, 'f1', 'f₁ (adimensional)'),
                    use_container_width=True)

    # ── f₂ — CV de carga ────────────────────────────────────────────────────
    st.markdown("## f₂ — Coeficiente de variación de carga")
    _d2, _r2, _fr2 = _delta_semana(ind_f, 'f2_CV')
    _fh2 = ind_f['fecha'].max()
    _v2  = ind_f[ind_f['fecha'] == _fh2]['f2_CV'].mean()

    col_a, col_b, col_c = st.columns([1, 1.5, 1])
    with col_a:
        _chart(card_indicador(
            _v2, 'σ op.', _comp['std'] if _comp else None,
            'P̄ op.', _comp['prom'] if _comp else None,
            _d2, _r2, _fr2, _fh2), use_container_width=True)
    with col_b:
        _chart(serie_diaria(ind_f, 'f2_CV', 'f₂ (adimensional)'),
                        use_container_width=True)
    with col_c:
        _chart(graficar_evidencia_f2(_comp), use_container_width=True)

    _chart(comparativo_bloques(ind_fechas, 'f2_CV', 'f₂ (adimensional)'),
                    use_container_width=True)

    # ── f₃ — Mínimo–promedio ────────────────────────────────────────────────
    st.markdown("## f₃ — Relación mínimo–promedio")
    _d3, _r3, _fr3 = _delta_semana(ind_f, 'f3')
    _fh3 = ind_f['fecha'].max()
    _v3  = ind_f[ind_f['fecha'] == _fh3]['f3'].mean()

    col_a, col_b, col_c = st.columns([1, 1.5, 1])
    with col_a:
        _chart(card_indicador(
            _v3, 'P_min op.', _comp['min'] if _comp else None,
            'P̄ op.', _comp['prom'] if _comp else None,
            _d3, _r3, _fr3, _fh3), use_container_width=True)
    with col_b:
        _chart(serie_diaria(ind_f, 'f3', 'f₃ (adimensional)'),
                        use_container_width=True)
    with col_c:
        _chart(graficar_evidencia_f3(_comp), use_container_width=True)

    _chart(comparativo_bloques(ind_fechas, 'f3', 'f₃ (adimensional)'),
                    use_container_width=True)

    # ── f₄ — Carga no operacional ────────────────────────────────────────────
    st.markdown("## f₄ — Factor de carga no operacional")
    if raw_f is not None and not raw_f.empty:
        f4_diario = calcular_f4_diario(raw_f)
    else:
        f4_diario = (ind_f.groupby('fecha')['f4'].mean()
                     .to_frame('f4').assign(p_op=np.nan, p_no_op=np.nan))
        st.caption("P̄ desagregada no disponible — etsmartmeter_clean.csv no encontrado.")

    if not f4_diario.empty:
        hoy_f4       = f4_diario.iloc[-1]
        fecha_hoy_f4 = f4_diario.index[-1]
        cand_f4      = f4_diario[(f4_diario.index.dayofweek == fecha_hoy_f4.dayofweek) &
                                 (f4_diario.index < fecha_hoy_f4)]
        f4_ref   = cand_f4.iloc[-1]['f4'] if not cand_f4.empty else None
        delta_f4 = float(hoy_f4['f4']) - float(f4_ref) if f4_ref is not None else None

        col_a, col_b = st.columns([1, 2])
        with col_a:
            fig_f4_card = card_indicador(
                hoy_f4['f4'],
                'P̄ no-op', hoy_f4.get('p_no_op') if pd.notna(hoy_f4.get('p_no_op', np.nan)) else None,
                'P̄ op',    hoy_f4.get('p_op')    if pd.notna(hoy_f4.get('p_op',    np.nan)) else None,
                delta_f4, f4_ref,
                cand_f4.index[-1] if not cand_f4.empty else None,
                fecha_hoy_f4,
            )
            _chart(fig_f4_card, use_container_width=True)
        with col_b:
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
        col_m1.metric("🌍 CO₂ total", f"{total_co2:.3f} tCO₂e")
        col_m2.metric("🌳 Árboles equiv.", f"{arboles:,}")
        col_m3.metric("✈️ Vuelos MDE–BOG", f"{vuelos:.1f}")
        col_m4.metric("🚗 Vehículos/año", f"{vehiculos:.2f}")

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
                   .assign(bloque=ind_f['entity_id'].str.replace('SmartMeter_SM_', 'B', regex=False))
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
                     .assign(bloque=ind_f['entity_id'].str.replace('SmartMeter_SM_', 'B', regex=False))
                     .groupby('bloque')['desbalance_pct'].mean().sort_values())
        col_a, col_b = st.columns([1, 1.5])
        with col_a:
            fig_db_bar = barras_horizontales(
                db_bloque, titulo='Desbalance medio por bloque', xlabel='%',
                color_fn=lambda v: _semaforo(v, UMBRAL_DB_OBJ, UMBRAL_DB_ALERT, mayor_es_mejor=False),
                ref_lines=[
                    (UMBRAL_DB_OBJ,   C_TEAL, f'{UMBRAL_DB_OBJ:.0f}% objetivo'),
                    (UMBRAL_DB_ALERT, C_RED,  f'{UMBRAL_DB_ALERT:.0f}% alerta'),
                ],
            )
            _chart(fig_db_bar, use_container_width=True)
        with col_b:
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
        col_a, col_b = st.columns([1, 1.5])
        with col_a:
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

        with col_b:
            total_kwh_campus = kpi01_f['e_wh'].sum() / 1_000
            costo_cop      = total_kwh_campus * TARIFA_BASE_COP_KWH
            hogares_meses  = total_kwh_campus / HOGAR_KWH_MES
            cm1, cm2, cm3 = st.columns(3)
            cm1.metric("⚡ Energía consumida", f"{total_kwh_campus:,.0f} kWh")
            cm2.metric("💰 Costo estimado", f"${costo_cop:,.0f} COP",
                       help="Tarifa EPM NT1 ene-2026: $859.19 COP/kWh")
            cm3.metric("🏠 Hogares equivalentes", f"{hogares_meses:,.0f} mes-hogar",
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
    st.markdown("## KPI 03 — Pico de demanda absoluto")
    agg = kpi_f.groupby('entity_id').agg(
        pico=('KPI03_pico_kw', 'max'),
        media_pico=('KPI03_pico_kw', 'mean'),
        sigma_pico=('KPI03_pico_kw', 'std'),
    ).copy()
    agg['alerta']   = agg['media_pico'] + agg['sigma_pico'].fillna(0)
    agg['objetivo'] = agg['media_pico'] * 0.93
    agg = agg.sort_values('pico', ascending=True)
    agg.index = [_bloque_label(e) for e in agg.index]

    fig_k3 = go.Figure()
    fig_k3.add_trace(go.Bar(
        x=agg['pico'], y=agg.index,
        orientation='h', name='Pico máx.',
        marker_color=[_semaforo(p, o, a, mayor_es_mejor=False)
                      for p, a, o in zip(agg['pico'], agg['alerta'], agg['objetivo'])],
        text=[f'{p:.1f} kW' for p in agg['pico']], textposition='outside',
        hovertemplate='%{y}: %{x:.1f} kW<extra>Pico</extra>',
    ))
    fig_k3.add_trace(go.Scatter(
        x=agg['alerta'], y=agg.index, mode='markers',
        name='Alerta (μ+1σ)', marker=dict(symbol='line-ew', color=C_RED, size=10, line=dict(width=2, color=C_RED)),
    ))
    fig_k3.add_trace(go.Scatter(
        x=agg['objetivo'], y=agg.index, mode='markers',
        name='Objetivo (μ−7%)', marker=dict(symbol='line-ew', color=C_TEAL, size=10, line=dict(width=2, color=C_TEAL)),
    ))
    fig_k3.update_layout(title=dict(text='KPI 03 — Pico de demanda por bloque', font=dict(size=13), x=0),
                         xaxis_title='kW', barmode='overlay')
    _chart(_layout_base(fig_k3, h=max(260, 36 * len(agg) + 100)), use_container_width=True)

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
    st.markdown("## KPI 08 — Load Factor")
    lf_vals            = kpi_f['KPI08_LF'].dropna()
    mu_lf              = float(lf_vals.mean()) if len(lf_vals) > 0 else 0.65
    sigma_lf           = float(lf_vals.std())  if len(lf_vals) > 1 else 0.0
    umbral_alerta_lf   = max(0.0, mu_lf - sigma_lf)
    umbral_objetivo_lf = min(1.0, mu_lf * 1.07)

    lf_medio_k8 = kpi_f.groupby('entity_id')['KPI08_LF'].mean().sort_values()
    lf_medio_k8.index = [_bloque_label(e) for e in lf_medio_k8.index]

    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        _chart(barras_horizontales(
            lf_medio_k8, titulo='KPI 08 — LF medio por bloque', xlabel='LF',
            color_fn=lambda v: _semaforo(v, umbral_objetivo_lf, umbral_alerta_lf),
            ref_lines=[
                (umbral_objetivo_lf, C_TEAL, f'objetivo {umbral_objetivo_lf:.3f}'),
                (umbral_alerta_lf,   C_RED,  f'alerta {umbral_alerta_lf:.3f}'),
            ],
        ), use_container_width=True)
    with col_b:
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

    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        _chart(barras_horizontales(
            f4_bloque_k9, titulo='KPI 09 — Consumo no operacional por bloque',
            xlabel='% (22:00–06:00)',
            color_fn=lambda v: _semaforo(v, umbral_objetivo_k9, umbral_alerta_k9, mayor_es_mejor=False),
            ref_lines=[
                (umbral_objetivo_k9, C_TEAL, f'objetivo {umbral_objetivo_k9:.1f}%'),
                (umbral_alerta_k9,   C_RED,  f'alerta {umbral_alerta_k9:.1f}%'),
            ],
        ), use_container_width=True)
    with col_b:
        if total_kwh_campus is not None and total_kwh_campus > 0:
            pct_noche  = float(f4_bloque_k9.mean()) / 100
            e_noche    = total_kwh_campus * pct_noche
            costo_noch = e_noche * TARIFA_BASE_COP_KWH
            pct_exceso = max(0.0, pct_noche - umbral_objetivo_k9 / 100)
            ahorro_kwh = total_kwh_campus * pct_exceso
            ahorro_cop = ahorro_kwh * TARIFA_BASE_COP_KWH

            cn1, cn2, cn3 = st.columns(3)
            cn1.metric("🌙 Energía nocturna", f"{e_noche:,.0f} kWh")
            cn2.metric("💸 Costo nocturno", f"${costo_noch:,.0f} COP")
            if ahorro_cop > 0:
                cn3.metric(f"💡 Ahorro potencial", f"${ahorro_cop:,.0f} COP",
                           delta=f"−{ahorro_kwh:,.0f} kWh", delta_color="inverse")
                st.warning(
                    f"**{pct_noche*100:.1f}%** del consumo ocurre entre 22:00 y 06:00 "
                    f"({e_noche:,.0f} kWh · ${costo_noch:,.0f} COP). "
                    f"Reducir al objetivo ({umbral_objetivo_k9:.1f}%) ahorraría **${ahorro_cop:,.0f} COP**."
                )
            else:
                cn3.metric("✅ Objetivo cumplido", "—")
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

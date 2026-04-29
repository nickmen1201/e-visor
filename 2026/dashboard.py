import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="E-Visor", layout="wide")
st.title("E-Visor — Dashboard energético")

# ── Paleta y estilo ───────────────────────────────────────────────────────────
C_TEAL   = '#1D9E75'
C_AMBER  = '#EF9F27'
C_RED    = '#A32D2D'
C_GRAY   = '#B4B2A9'
C_BLUE   = '#378ADD'
C_PURPLE = '#534AB7'

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.titleweight': 'bold',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': False,
})

BASE = Path(__file__).parent

# ── f₄ — Constantes y funciones ──────────────────────────────────────────────
HORA_INICIO_OPERACION = 6   # operación 06:00–21:59
HORA_FIN_OPERACION    = 22  # no operación 22:00–05:59

_DIAS_F4 = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def calcular_f4_diario(df):
    d = df[['time_index_colombia', 'activepower']].copy()
    d['hora']  = pd.to_datetime(d['time_index_colombia']).dt.hour
    d['fecha'] = pd.to_datetime(d['time_index_colombia']).dt.normalize()
    mask_op    = (d['hora'] >= HORA_INICIO_OPERACION) & (d['hora'] < HORA_FIN_OPERACION)
    p_op    = d[mask_op].groupby('fecha')['activepower'].mean().rename('p_op')
    p_no_op = d[~mask_op].groupby('fecha')['activepower'].mean().rename('p_no_op')
    res = pd.concat([p_op, p_no_op], axis=1)
    res['f4'] = res['p_no_op'] / res['p_op']
    return res.dropna(subset=['f4'])


def graficar_widget_1(f4_diario):
    df = f4_diario.sort_index()
    if df.empty:
        return go.Figure()
    hoy       = df.iloc[-1]
    fecha_hoy = df.index[-1]
    candidatos = df[(df.index.dayofweek == fecha_hoy.dayofweek) & (df.index < fecha_hoy)]
    f4_ref = candidatos.iloc[-1]['f4'] if not candidatos.empty else None
    delta  = hoy['f4'] - f4_ref if f4_ref is not None else None

    ind_kw = dict(
        mode='number+delta' if delta is not None else 'number',
        value=round(float(hoy['f4']), 3),
        number=dict(font=dict(size=64, color='#2C2C2A'), valueformat='.3f'),
        domain=dict(x=[0.1, 0.9], y=[0.45, 1.0]),
    )
    if delta is not None:
        ind_kw['delta'] = dict(
            reference=round(float(f4_ref), 3), valueformat='.3f', relative=False,
            increasing=dict(color=C_AMBER), decreasing=dict(color=C_TEAL),
        )
    fig = go.Figure(go.Indicator(**ind_kw))

    has_powers = ('p_op' in hoy.index) and pd.notna(hoy['p_op'])
    if has_powers:
        fig.add_annotation(
            x=0.5, y=0.28, xref='paper', yref='paper', showarrow=False,
            text=(f'<b>P̄ no operacional:</b> {hoy["p_no_op"]:.0f} W'
                  f'&nbsp;&nbsp;&nbsp;&nbsp;'
                  f'<b>P̄ operacional:</b> {hoy["p_op"]:.0f} W'),
            font=dict(size=14, color='#5F5E5A'), align='center',
        )
    if delta is not None:
        flecha  = '↑' if delta > 0 else '↓'
        ref_txt = candidatos.index[-1].strftime('%d %b')
        fig.add_annotation(
            x=0.5, y=0.10, xref='paper', yref='paper', showarrow=False,
            text=f'{flecha} {abs(delta):.3f} respecto al {ref_txt} (mismo día semana anterior)',
            font=dict(size=13, color=C_AMBER if delta > 0 else C_TEAL), align='center',
        )
    else:
        fig.add_annotation(
            x=0.5, y=0.10, xref='paper', yref='paper', showarrow=False,
            text='Sin referencia de la semana anterior',
            font=dict(size=12, color=C_GRAY),
        )
    fig.update_layout(
        title=dict(text=f'Valor más reciente — {fecha_hoy.strftime("%d %b %Y")}',
                   font=dict(size=13), x=0.5, xanchor='center'),
        plot_bgcolor='white', paper_bgcolor='white',
        height=260, margin=dict(t=40, b=10, l=20, r=20),
    )
    return fig


def graficar_widget_2(f4_diario):
    df = f4_diario.sort_index().copy()
    if df.empty:
        return go.Figure()
    df['es_finde'] = df.index.dayofweek >= 5
    df['ma7']      = df['f4'].rolling(7, min_periods=1).mean()
    laboral = df[~df['es_finde']]
    finde   = df[df['es_finde']]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=laboral.index, y=laboral['f4'], mode='lines+markers',
        name='Día hábil (L–V)',
        line=dict(color=C_TEAL, width=1.5), marker=dict(color=C_TEAL, size=5),
    ))
    fig.add_trace(go.Scatter(
        x=finde.index, y=finde['f4'], mode='markers',
        name='Fin de semana (S–D)',
        marker=dict(color=C_AMBER, size=7, symbol='diamond'),
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df['ma7'], mode='lines',
        name='Media móvil 7 días',
        line=dict(color=C_GRAY, width=2.5, dash='dot'), opacity=0.75,
    ))
    fig.update_layout(
        title=dict(text='Evolución diaria', font=dict(size=13), x=0, xanchor='left'),
        xaxis_title='Fecha', yaxis_title='f₄ (adimensional)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02,
                    xanchor='right', x=1, font=dict(size=11)),
        plot_bgcolor='white', paper_bgcolor='white',
        height=320, margin=dict(t=60, b=40, l=60, r=20),
        xaxis=dict(gridcolor='#EEEEEE'),
        yaxis=dict(gridcolor='#EEEEEE', rangemode='tozero'),
    )
    return fig


def graficar_widget_3(df):
    d = df.copy()
    d['hora'] = pd.to_datetime(d['time_index_colombia']).dt.hour
    d['dia']  = pd.to_datetime(d['time_index_colombia']).dt.dayofweek
    matriz = (d.groupby(['dia', 'hora'])['activepower'].mean()
               .unstack('hora')
               .reindex(index=range(7), columns=range(24)))
    fig = go.Figure(go.Heatmap(
        z=np.nan_to_num(matriz.values),
        x=list(range(24)),
        y=_DIAS_F4,
        colorscale='YlOrBr',
        colorbar=dict(title=dict(text='Potencia activa (W)', side='right')),
        hoverongaps=False,
        hovertemplate='%{y} %{x:02d}:00 — %{z:.0f} W<extra></extra>',
    ))
    for x0, x1 in [(-0.5, 5.5), (21.5, 23.5)]:
        fig.add_shape(
            type='rect', xref='x', yref='y',
            x0=x0, x1=x1, y0=-0.5, y1=6.5,
            fillcolor='rgba(44,44,42,0.12)', line=dict(width=0), layer='above',
        )
    fig.add_annotation(
        x=1.06, y=0.5, xref='paper', yref='paper', showarrow=False,
        text='← Franja<br>no operacional',
        xanchor='left', yanchor='middle',
        font=dict(size=10, color='#5F5E5A'), align='left',
    )
    fig.update_xaxes(
        title='Hora del día',
        tickvals=list(range(0, 24, 2)),
        ticktext=[f'{h:02d}:00' for h in range(0, 24, 2)],
    )
    fig.update_yaxes(autorange='reversed')
    fig.update_layout(
        title=dict(text='Perfil de carga semanal — evidencia visual de f₄',
                   font=dict(size=13), x=0, xanchor='left'),
        plot_bgcolor='white', paper_bgcolor='white',
        height=300, margin=dict(t=40, b=50, l=60, r=140),
    )
    return fig

# ── Helpers compartidos f₁–f₄ ────────────────────────────────────────────────
HORA_OP_INI = 6
HORA_OP_FIN = 22


def calcular_componentes_diurnos(df):
    d = df.copy()
    d['hora']  = pd.to_datetime(d['time_index_colombia']).dt.hour
    mask_op    = (d['hora'] >= HORA_OP_INI) & (d['hora'] < HORA_OP_FIN)
    ap_op      = d[mask_op]['activepower'].dropna()
    perfil     = d[mask_op].groupby('hora')['activepower'].mean()
    if ap_op.empty:
        return None
    return {
        'perfil': perfil,
        'prom': float(ap_op.mean()),
        'max':  float(ap_op.max()),
        'min':  float(ap_op.min()),
        'std':  float(ap_op.std()),
    }


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


def graficar_card(valor, num_lbl, num_val, den_lbl, den_val,
                  delta, ref_val, fecha_ref, fecha_hoy):
    ind_kw = dict(
        mode='number+delta' if delta is not None else 'number',
        value=round(float(valor), 3),
        number=dict(font=dict(size=64, color='#2C2C2A'), valueformat='.3f'),
        domain=dict(x=[0.1, 0.9], y=[0.45, 1.0]),
    )
    if delta is not None:
        ind_kw['delta'] = dict(
            reference=round(float(ref_val), 3), valueformat='.3f', relative=False,
            increasing=dict(color=C_AMBER), decreasing=dict(color=C_TEAL),
        )
    fig = go.Figure(go.Indicator(**ind_kw))
    if num_val is not None and den_val is not None:
        fig.add_annotation(
            x=0.5, y=0.28, xref='paper', yref='paper', showarrow=False,
            text=(f'<b>{num_lbl}:</b> {num_val:.0f} W'
                  f'&nbsp;&nbsp;&nbsp;&nbsp;'
                  f'<b>{den_lbl}:</b> {den_val:.0f} W'),
            font=dict(size=14, color='#5F5E5A'), align='center',
        )
    if delta is not None:
        flecha = '↑' if delta > 0 else '↓'
        fig.add_annotation(
            x=0.5, y=0.10, xref='paper', yref='paper', showarrow=False,
            text=(f'{flecha} {abs(delta):.3f} respecto al '
                  f'{fecha_ref.strftime("%d %b")} (mismo día semana anterior)'),
            font=dict(size=13, color=C_AMBER if delta > 0 else C_TEAL), align='center',
        )
    else:
        fig.add_annotation(
            x=0.5, y=0.10, xref='paper', yref='paper', showarrow=False,
            text='Sin referencia de la semana anterior',
            font=dict(size=12, color=C_GRAY),
        )
    fig.update_layout(
        title=dict(text=f'Valor más reciente — {fecha_hoy.strftime("%d %b %Y")}',
                   font=dict(size=13), x=0.5, xanchor='center'),
        plot_bgcolor='white', paper_bgcolor='white',
        height=260, margin=dict(t=40, b=10, l=20, r=20),
    )
    return fig


def graficar_serie_diaria(ind_df, col, titulo_y):
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
        name='Día hábil (L–V)',
        line=dict(color=C_TEAL, width=1.5), marker=dict(color=C_TEAL, size=5),
    ))
    fig.add_trace(go.Scatter(
        x=finde.index, y=finde['val'], mode='markers',
        name='Fin de semana (S–D)',
        marker=dict(color=C_AMBER, size=7, symbol='diamond'),
    ))
    fig.add_trace(go.Scatter(
        x=df_s.index, y=df_s['ma7'], mode='lines',
        name='Media móvil 7 días',
        line=dict(color=C_GRAY, width=2.5, dash='dot'), opacity=0.75,
    ))
    fig.update_layout(
        title=dict(text='Evolución diaria', font=dict(size=13), x=0, xanchor='left'),
        xaxis_title='Fecha', yaxis_title=titulo_y,
        legend=dict(orientation='h', yanchor='bottom', y=1.02,
                    xanchor='right', x=1, font=dict(size=11)),
        plot_bgcolor='white', paper_bgcolor='white',
        height=320, margin=dict(t=60, b=40, l=60, r=20),
        xaxis=dict(gridcolor='#EEEEEE'),
        yaxis=dict(gridcolor='#EEEEEE', rangemode='tozero'),
    )
    return fig


def graficar_comparativo_bloques(ind_df, col, titulo_x):
    serie = (ind_df
             .assign(bloque=ind_df['entity_id'].str.replace('SmartMeter_SM_', '', regex=False))
             .groupby('bloque')[col].mean()
             .sort_values())
    fig = go.Figure(go.Bar(
        x=serie.values, y=serie.index.tolist(),
        orientation='h', marker_color=C_BLUE,
        text=[f'{v:.3f}' for v in serie.values], textposition='outside',
    ))
    fig.update_layout(
        title=dict(text='Comparativo por bloque (promedio del período)',
                   font=dict(size=13), x=0, xanchor='left'),
        xaxis_title=titulo_x,
        plot_bgcolor='white', paper_bgcolor='white',
        height=max(280, 30 * len(serie) + 100),
        margin=dict(t=40, b=40, l=110, r=80),
        xaxis=dict(gridcolor='#EEEEEE'),
    )
    return fig


def _base_perfil_layout(fig):
    fig.update_xaxes(title='Hora del día',
                     tickvals=list(range(6, 22, 2)),
                     ticktext=[f'{h:02d}:00' for h in range(6, 22, 2)])
    fig.update_yaxes(title='Potencia activa (W)', gridcolor='#EEEEEE')
    fig.update_layout(
        title=dict(text='Perfil diurno — evidencia del cálculo',
                   font=dict(size=13), x=0, xanchor='left'),
        plot_bgcolor='white', paper_bgcolor='white',
        height=320, margin=dict(t=40, b=50, l=60, r=120),
        xaxis=dict(gridcolor='#EEEEEE'),
    )
    return fig


def graficar_evidencia_f1(comp):
    fig = go.Figure()
    if comp is None:
        fig.add_annotation(x=0.5, y=0.5, text='Datos crudos no disponibles',
                           xref='paper', yref='paper', showarrow=False)
        return fig
    p = comp['perfil']
    fig.add_trace(go.Scatter(x=p.index, y=p.values, mode='lines+markers',
                              showlegend=False,
                              line=dict(color=C_TEAL, width=2),
                              marker=dict(color=C_TEAL, size=5)))
    fig.add_hline(y=comp['prom'], line=dict(color=C_AMBER, width=1.5, dash='dash'))
    fig.add_annotation(x=p.index[-1], y=comp['prom'], xref='x', yref='y',
                       text=f'P̄ = {comp["prom"]:.0f} W (num.)',
                       showarrow=False, xanchor='right', yanchor='bottom',
                       font=dict(size=11, color=C_AMBER))
    fig.add_hline(y=comp['max'], line=dict(color=C_PURPLE, width=1.5, dash='dash'))
    fig.add_annotation(x=p.index[-1], y=comp['max'], xref='x', yref='y',
                       text=f'P_max = {comp["max"]:.0f} W (den.)',
                       showarrow=False, xanchor='right', yanchor='top',
                       font=dict(size=11, color=C_PURPLE))
    return _base_perfil_layout(fig)


def graficar_evidencia_f2(comp):
    fig = go.Figure()
    if comp is None:
        fig.add_annotation(x=0.5, y=0.5, text='Datos crudos no disponibles',
                           xref='paper', yref='paper', showarrow=False)
        return fig
    p = comp['perfil']
    xs = list(p.index) + list(p.index[::-1])
    ys = ([comp['prom'] + comp['std']] * len(p) +
          [comp['prom'] - comp['std']] * len(p))
    fig.add_trace(go.Scatter(x=xs, y=ys, fill='toself',
                              fillcolor='rgba(55,138,221,0.15)',
                              line=dict(color='rgba(0,0,0,0)'),
                              name=f'±σ = {comp["std"]:.0f} W (num.)'))
    fig.add_trace(go.Scatter(x=p.index, y=p.values, mode='lines+markers',
                              showlegend=False,
                              line=dict(color=C_TEAL, width=2),
                              marker=dict(color=C_TEAL, size=5)))
    fig.add_hline(y=comp['prom'], line=dict(color=C_AMBER, width=1.5, dash='dash'))
    fig.add_annotation(x=p.index[-1], y=comp['prom'], xref='x', yref='y',
                       text=f'P̄ = {comp["prom"]:.0f} W (den.)',
                       showarrow=False, xanchor='right', yanchor='bottom',
                       font=dict(size=11, color=C_AMBER))
    fig = _base_perfil_layout(fig)
    fig.update_layout(legend=dict(orientation='h', y=1.05, x=0, font=dict(size=10)))
    return fig


def graficar_evidencia_f3(comp):
    fig = go.Figure()
    if comp is None:
        fig.add_annotation(x=0.5, y=0.5, text='Datos crudos no disponibles',
                           xref='paper', yref='paper', showarrow=False)
        return fig
    p = comp['perfil']
    h_min = p.idxmin()
    fig.add_trace(go.Scatter(x=p.index, y=p.values, mode='lines+markers',
                              showlegend=False,
                              line=dict(color=C_TEAL, width=2),
                              marker=dict(color=C_TEAL, size=5)))
    fig.add_trace(go.Scatter(x=[h_min], y=[comp['min']], mode='markers',
                              name=f'P_min = {comp["min"]:.0f} W (num.)',
                              marker=dict(color=C_RED, size=10)))
    fig.add_hline(y=comp['prom'], line=dict(color=C_AMBER, width=1.5, dash='dash'))
    fig.add_annotation(x=p.index[-1], y=comp['prom'], xref='x', yref='y',
                       text=f'P̄ = {comp["prom"]:.0f} W (den.)',
                       showarrow=False, xanchor='right', yanchor='bottom',
                       font=dict(size=11, color=C_AMBER))
    fig.add_annotation(x=h_min, y=comp['min'], xref='x', yref='y',
                       text=f'P_min = {comp["min"]:.0f} W (num.)',
                       showarrow=False, xanchor='center', yanchor='top',
                       font=dict(size=11, color=C_RED))
    fig = _base_perfil_layout(fig)
    fig.update_layout(legend=dict(orientation='h', y=1.05, x=0, font=dict(size=10)))
    return fig


# ── CO₂ — Constantes y funciones ─────────────────────────────────────────────
FACTOR_EMISION_CO2        = 9.7018e-8   # tCO₂e / Wh
ARBOLES_POR_TON_CO2       = 45          # árboles jóvenes por tCO₂e
TON_CO2_POR_VUELO_MDE_BOG = 0.18        # tCO₂e por trayecto MDE–BOG
TON_CO2_POR_VEHICULO_ANO  = 4.6         # tCO₂e por vehículo/año (IPCC)


def graficar_widget_1_co2(ind_df, ind_full=None):
    if ind_df.empty:
        return go.Figure()
    total     = float(ind_df['CO2_tCO2e'].sum())
    fecha_ini = ind_df['fecha'].min()
    fecha_fin = ind_df['fecha'].max()
    arboles   = int(total * ARBOLES_POR_TON_CO2)
    vuelos    = total / TON_CO2_POR_VUELO_MDE_BOG
    vehiculos = total / TON_CO2_POR_VEHICULO_ANO

    delta     = None
    total_ant = None
    ref_txt   = ''
    if ind_full is not None:
        n_dias  = (fecha_fin - fecha_ini).days + 1
        ant_fin = fecha_ini - pd.Timedelta(days=1)
        ant_ini = ant_fin  - pd.Timedelta(days=n_dias - 1)
        df_ant  = ind_full[(ind_full['fecha'] >= ant_ini) & (ind_full['fecha'] <= ant_fin)]
        if not df_ant.empty:
            total_ant = float(df_ant['CO2_tCO2e'].sum())
            delta     = total - total_ant
            ref_txt   = f'{ant_ini.strftime("%d %b")}–{ant_fin.strftime("%d %b")}'

    ind_kw = dict(
        mode='number+delta' if delta is not None else 'number',
        value=total,
        number=dict(font=dict(size=64, color='#2C2C2A'), valueformat=',.3f',
                    suffix=' tCO₂e'),
        domain=dict(x=[0.05, 0.95], y=[0.50, 1.0]),
    )
    if delta is not None:
        ind_kw['delta'] = dict(
            reference=float(total_ant), valueformat='+,.3f', relative=False,
            increasing=dict(color=C_AMBER), decreasing=dict(color=C_TEAL),
        )
    fig = go.Figure(go.Indicator(**ind_kw))
    fig.add_annotation(
        x=0.5, y=0.38, xref='paper', yref='paper', showarrow=False,
        text=f'Período: {fecha_ini.strftime("%d %b %Y")} – {fecha_fin.strftime("%d %b %Y")}',
        font=dict(size=13, color='#5F5E5A'), align='center',
    )
    fig.add_annotation(
        x=0.5, y=0.20, xref='paper', yref='paper', showarrow=False,
        text=(f'\U0001f333 {arboles:,} árboles jóvenes'
              f'&nbsp;&nbsp;&nbsp;'
              f'✈️ {vuelos:.0f} vuelos MDE–BOG'
              f'&nbsp;&nbsp;&nbsp;'
              f'\U0001f697 {vehiculos:.1f} vehículos/año'),
        font=dict(size=13, color='#5F5E5A'), align='center',
    )
    if delta is not None:
        flecha = '↑' if delta > 0 else '↓'
        fig.add_annotation(
            x=0.5, y=0.05, xref='paper', yref='paper', showarrow=False,
            text=f'{flecha} {abs(delta):,.3f} tCO₂e vs período anterior ({ref_txt})',
            font=dict(size=12, color=C_AMBER if delta > 0 else C_TEAL), align='center',
        )
    else:
        fig.add_annotation(
            x=0.5, y=0.05, xref='paper', yref='paper', showarrow=False,
            text='Sin período anterior para comparar',
            font=dict(size=12, color=C_GRAY),
        )
    fig.update_layout(
        title=dict(text='Huella de carbono del Ecocampus',
                   font=dict(size=13), x=0.5, xanchor='center'),
        plot_bgcolor='white', paper_bgcolor='white',
        height=310, margin=dict(t=40, b=10, l=20, r=20),
    )
    return fig


def graficar_widget_2_co2(ind_df):
    diario = ind_df.groupby('fecha')['CO2_tCO2e'].sum().sort_index()
    if diario.empty:
        return go.Figure()
    acum     = diario.cumsum()
    es_finde = diario.index.dayofweek >= 5
    laboral  = diario[~es_finde]
    finde    = diario[es_finde]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.6, 0.4], vertical_spacing=0.08,
        subplot_titles=('Emisiones acumuladas', 'Emisiones diarias'),
    )
    fig.add_trace(go.Scatter(
        x=acum.index, y=acum.values, mode='lines',
        fill='tozeroy', fillcolor='rgba(239,159,39,0.25)',
        line=dict(color=C_AMBER, width=2),
        name='Acumulado (tCO₂e)',
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=laboral.index, y=laboral.values,
        name='Día hábil (L–V)', marker_color=C_TEAL,
    ), row=2, col=1)
    fig.add_trace(go.Bar(
        x=finde.index, y=finde.values,
        name='Fin de semana (S–D)', marker_color=C_AMBER,
    ), row=2, col=1)
    fig.update_layout(
        title=dict(text='Evolución temporal de emisiones CO₂',
                   font=dict(size=13), x=0, xanchor='left'),
        plot_bgcolor='white', paper_bgcolor='white',
        height=480, margin=dict(t=60, b=40, l=70, r=20),
        legend=dict(orientation='h', yanchor='bottom', y=1.02,
                    xanchor='right', x=1, font=dict(size=11)),
        barmode='overlay',
    )
    fig.update_yaxes(title_text='tCO₂e acumuladas', gridcolor='#EEEEEE', row=1, col=1)
    fig.update_yaxes(title_text='tCO₂e/día',       gridcolor='#EEEEEE', row=2, col=1)
    fig.update_xaxes(gridcolor='#EEEEEE', row=2, col=1)
    return fig


def graficar_widget_3_co2(ind_df, area_por_bloque=None):
    totales = (ind_df
               .assign(bloque=ind_df['entity_id'].str.replace('SmartMeter_SM_', '', regex=False))
               .groupby('bloque')['CO2_tCO2e'].sum()
               .sort_values())
    if totales.empty:
        return go.Figure()

    if area_por_bloque:
        areas = {k.replace('SmartMeter_SM_', ''): v for k, v in area_por_bloque.items()}
        comun = [b for b in totales.index if b in areas]
        if comun:
            intens = pd.Series({b: totales[b] / areas[b] for b in comun}).sort_values()
            fig = go.Figure(go.Bar(
                x=intens.values, y=intens.index.tolist(),
                orientation='h',
                marker=dict(
                    color=intens.values, colorscale='YlOrBr',
                    colorbar=dict(title=dict(text='tCO₂e/m²', side='right')),
                    showscale=True,
                ),
                text=[f'{v:.5f}' for v in intens.values], textposition='outside',
            ))
            fig.update_layout(
                title=dict(text='Intensidad de carbono por bloque (tCO₂e/m²)',
                           font=dict(size=13), x=0, xanchor='left'),
                xaxis_title='tCO₂e/m²',
                plot_bgcolor='white', paper_bgcolor='white',
                height=max(280, 30 * len(intens) + 100),
                margin=dict(t=40, b=40, l=110, r=100),
                xaxis=dict(gridcolor='#EEEEEE'),
            )
            return fig

    fig = go.Figure(go.Bar(
        x=totales.values, y=totales.index.tolist(),
        orientation='h', marker_color=C_AMBER,
        text=[f'{v:.3f}' for v in totales.values], textposition='outside',
    ))
    fig.update_layout(
        title=dict(text='Emisiones CO₂ por bloque (tCO₂e totales)',
                   font=dict(size=13), x=0, xanchor='left'),
        xaxis_title='tCO₂e',
        plot_bgcolor='white', paper_bgcolor='white',
        height=max(280, 30 * len(totales) + 100),
        margin=dict(t=40, b=40, l=110, r=80),
        xaxis=dict(gridcolor='#EEEEEE'),
    )
    return fig


# ── Carga de datos ────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos():
    ind = pd.read_csv(BASE / 'indicadores_diarios.csv')
    ind['fecha'] = pd.to_datetime(ind['fecha'])

    kpi = pd.read_csv(BASE / 'kpis_diarios.csv')
    kpi['fecha'] = pd.to_datetime(kpi['fecha'])

    try:
        raw = pd.read_csv(BASE / 'etsmartmeter_clean.csv',
                          parse_dates=['time_index_colombia'])
        raw['hora']  = raw['time_index_colombia'].dt.hour
        raw['fecha'] = pd.to_datetime(raw['time_index_colombia'].dt.date)
    except FileNotFoundError:
        raw = None

    return ind, kpi, raw

ind, kpi, raw = cargar_datos()

# ── Sidebar: filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")

    fecha_min = ind['fecha'].min().date()
    fecha_max = ind['fecha'].max().date()

    c1, c2 = st.columns(2)
    fecha_ini = c1.date_input("Inicio", fecha_min, min_value=fecha_min, max_value=fecha_max)
    hora_ini  = c1.time_input("Hora", value=pd.Timestamp("00:00").time(), key="hi")
    fecha_fin = c2.date_input("Fin",   fecha_max, min_value=fecha_min, max_value=fecha_max)
    hora_fin  = c2.time_input("Hora",  value=pd.Timestamp("23:00").time(), key="hf")

    inicio = pd.Timestamp.combine(fecha_ini, hora_ini)
    fin    = pd.Timestamp.combine(fecha_fin, hora_fin)

    medidores = ["Todos"] + sorted(ind['entity_id'].unique().tolist())
    seleccion = st.selectbox("Medidor", medidores)

# ── Filtrado ──────────────────────────────────────────────────────────────────
ind_f     = ind[ind['fecha'].between(inicio, fin)].copy()
ind_fechas = ind_f.copy()   # todos los bloques, mismo rango de fechas
kpi_f     = kpi[kpi['fecha'].between(inicio, fin)].copy()

if seleccion != "Todos":
    ind_f = ind_f[ind_f['entity_id'] == seleccion]
    kpi_f = kpi_f[kpi_f['entity_id'] == seleccion]

raw_f = None
if raw is not None:
    raw_f = raw[raw['fecha'].between(inicio, fin)]
    if seleccion != "Todos":
        raw_f = raw_f[raw_f['entity_id'] == seleccion]

if ind_f.empty:
    st.warning("No hay datos para el rango seleccionado.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Indicadores", "KPIs"])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — INDICADORES
# ═════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── LF ───────────────────────────────────────────────────────────────────
    st.subheader("LF — Factor de carga")
    lf_bloque = ind_f.groupby('entity_id')['LF'].mean().sort_values()
    REF_LF = 0.65
    colores = [C_TEAL if v >= REF_LF else C_AMBER for v in lf_bloque]
    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.5 * len(lf_bloque))))
    ax.barh(lf_bloque.index.astype(str), lf_bloque.values, color=colores, edgecolor='none')
    ax.axvline(REF_LF, color='#5F5E5A', linestyle='--', linewidth=1)
    ax.text(REF_LF, len(lf_bloque) - 0.4, f' LF = {REF_LF} (ref.)',
            ha='left', va='bottom', fontsize=10, color='#5F5E5A')
    for i, v in enumerate(lf_bloque.values):
        ax.text(v + 0.01, i, f'{v:.2f}', va='center', fontsize=10)
    ax.set_xlim(0, max(1.0, lf_bloque.max() * 1.15))
    ax.set_title('LF por bloque (promedio del período)', loc='left')
    ax.set_xlabel('Factor de carga (adimensional)')
    plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── PAR ──────────────────────────────────────────────────────────────────
    st.subheader("PAR — Peak to Average Ratio")
    par_bloque = (ind_f.groupby('entity_id')['PAR'].mean()
                  .sort_values(ascending=False).round(2).to_frame('PAR'))
    par_bloque['Lectura'] = par_bloque['PAR'].apply(
        lambda v: f'El pico es ~{v:.1f}× el promedio')
    st.dataframe(par_bloque, use_container_width=True)

    # ── Componentes diurnos del día más reciente (compartido f1/f2/f3) ────────
    if raw_f is not None and not raw_f.empty:
        _raw_hoy = raw_f[raw_f['fecha'] == raw_f['fecha'].max()]
        _comp    = calcular_componentes_diurnos(_raw_hoy)
    else:
        _comp = None

    # ── f1 ───────────────────────────────────────────────────────────────────
    st.subheader("f₁ — Uniformidad de franja diurna")
    _d1, _r1, _fr1 = _delta_semana(ind_f, 'f1')
    _fh1  = ind_f['fecha'].max()
    _v1   = ind_f[ind_f['fecha'] == _fh1]['f1'].mean()
    st.plotly_chart(graficar_card(
        _v1,
        'P̄ operacional',   _comp['prom'] if _comp else None,
        'P_max operacional', _comp['max']  if _comp else None,
        _d1, _r1, _fr1, _fh1,
    ), use_container_width=True)
    st.plotly_chart(graficar_serie_diaria(ind_f, 'f1', 'f₁ (adimensional)'),
                    use_container_width=True)
    st.plotly_chart(graficar_evidencia_f1(_comp), use_container_width=True)
    st.plotly_chart(graficar_comparativo_bloques(ind_fechas, 'f1', 'f₁ (adimensional)'),
                    use_container_width=True)

    # ── f2 ───────────────────────────────────────────────────────────────────
    st.subheader("f₂ — Coeficiente de variación de carga (CV)")
    _d2, _r2, _fr2 = _delta_semana(ind_f, 'f2_CV')
    _fh2  = ind_f['fecha'].max()
    _v2   = ind_f[ind_f['fecha'] == _fh2]['f2_CV'].mean()
    st.plotly_chart(graficar_card(
        _v2,
        'σ operacional',  _comp['std']  if _comp else None,
        'P̄ operacional', _comp['prom'] if _comp else None,
        _d2, _r2, _fr2, _fh2,
    ), use_container_width=True)
    st.plotly_chart(graficar_serie_diaria(ind_f, 'f2_CV', 'f₂ (CV, adimensional)'),
                    use_container_width=True)
    st.plotly_chart(graficar_evidencia_f2(_comp), use_container_width=True)
    st.plotly_chart(graficar_comparativo_bloques(ind_fechas, 'f2_CV', 'f₂ (adimensional)'),
                    use_container_width=True)

    # ── f3 ───────────────────────────────────────────────────────────────────
    st.subheader("f₃ — Relación mínimo–promedio")
    _d3, _r3, _fr3 = _delta_semana(ind_f, 'f3')
    _fh3  = ind_f['fecha'].max()
    _v3   = ind_f[ind_f['fecha'] == _fh3]['f3'].mean()
    st.plotly_chart(graficar_card(
        _v3,
        'P_min operacional', _comp['min']  if _comp else None,
        'P̄ operacional',    _comp['prom'] if _comp else None,
        _d3, _r3, _fr3, _fh3,
    ), use_container_width=True)
    st.plotly_chart(graficar_serie_diaria(ind_f, 'f3', 'f₃ (adimensional)'),
                    use_container_width=True)
    st.plotly_chart(graficar_evidencia_f3(_comp), use_container_width=True)
    st.plotly_chart(graficar_comparativo_bloques(ind_fechas, 'f3', 'f₃ (adimensional)'),
                    use_container_width=True)

    # ── f4 ───────────────────────────────────────────────────────────────────
    st.subheader("f₄ — Factor de carga no operacional")
    if raw_f is not None and not raw_f.empty:
        f4_diario = calcular_f4_diario(raw_f)
    else:
        f4_diario = (ind_f.groupby('fecha')['f4'].mean()
                     .to_frame('f4')
                     .assign(p_op=np.nan, p_no_op=np.nan))
        st.caption("P̄ no disponible — etsmartmeter_clean.csv no encontrado.")
    st.plotly_chart(graficar_widget_1(f4_diario), use_container_width=True)
    st.plotly_chart(graficar_widget_2(f4_diario), use_container_width=True)
    if raw_f is not None and not raw_f.empty:
        st.plotly_chart(graficar_widget_3(raw_f), use_container_width=True)
    else:
        st.caption("Heatmap no disponible sin datos crudos.")
    st.plotly_chart(graficar_comparativo_bloques(ind_fechas, 'f4', 'f₄ (adimensional)'),
                    use_container_width=True)

    # ── HU ───────────────────────────────────────────────────────────────────
    st.subheader("HU — Horas de utilización")
    hu_bloque = ind_f.groupby('entity_id')['HU_horas'].mean().sort_values()
    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.5 * len(hu_bloque))))
    ax.barh(hu_bloque.index.astype(str), hu_bloque.values, color=C_TEAL, edgecolor='none')
    for i, v in enumerate(hu_bloque.values):
        ax.text(v + hu_bloque.max() * 0.01, i, f'{v:.1f}', va='center', fontsize=10)
    ax.set_xlim(0, hu_bloque.max() * 1.15)
    ax.set_title('HU — Horas de utilización por bloque', loc='left')
    ax.set_xlabel('Horas equivalentes a máxima potencia')
    plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── CO2 ──────────────────────────────────────────────────────────────────
    st.subheader("CO₂ — Huella de carbono del Ecocampus")
    _area_bloques = None  # dict {entity_id: m²} cuando esté disponible de Planeación Física
    st.plotly_chart(graficar_widget_1_co2(ind_f, ind_full=ind), use_container_width=True)
    st.plotly_chart(graficar_widget_2_co2(ind_f), use_container_width=True)
    st.plotly_chart(graficar_widget_3_co2(ind_fechas, area_por_bloque=_area_bloques),
                    use_container_width=True)
    if _area_bloques is None:
        st.caption("Intensidad de carbono (tCO₂e/m²) no disponible — "
                   "datos de área pendientes de Planeación Física UPB.")

    # ── Desbalance ────────────────────────────────────────────────────────────
    st.subheader("Desbalance de tensión")
    serie = ind_f.groupby('fecha')['desbalance_pct'].mean().sort_index()
    UMBRAL_DB = 2.0
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.axhspan(UMBRAL_DB, max(serie.max() * 1.1, UMBRAL_DB * 1.5), color=C_RED, alpha=0.08)
    ax.plot(serie.index, serie.values, color=C_PURPLE, linewidth=1.5)
    ax.axhline(UMBRAL_DB, color=C_RED, linestyle='--', linewidth=1)
    ax.text(serie.index[-1], UMBRAL_DB, f'  umbral {UMBRAL_DB}%',
            va='center', fontsize=10, color=C_RED)
    ax.set_ylim(0, max(serie.max() * 1.15, UMBRAL_DB * 1.5))
    ax.set_title('Desbalance de tensión — evolución diaria', loc='left')
    ax.set_ylabel('%')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(); plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── FP ───────────────────────────────────────────────────────────────────
    st.subheader("Factor de potencia")
    serie = ind_f.groupby('fecha')['fp_promedio'].mean().sort_index()
    UMBRAL_FP = 0.9
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.axhspan(0, UMBRAL_FP, color=C_RED, alpha=0.08)
    ax.plot(serie.index, serie.values, color=C_PURPLE, linewidth=1.5)
    ax.axhline(UMBRAL_FP, color=C_RED, linestyle='--', linewidth=1)
    ax.text(serie.index[-1], UMBRAL_FP, f'  umbral {UMBRAL_FP}',
            va='center', fontsize=10, color=C_RED)
    ax.set_ylim(min(0.7, serie.min() * 0.98), 1.0)
    ax.set_title('Factor de potencia — evolución diaria', loc='left')
    ax.set_ylabel('FP (adimensional)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(); plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── THD-V ────────────────────────────────────────────────────────────────
    st.subheader("THD-V")
    serie = ind_f.groupby('fecha')['thd_v_pct'].mean().sort_index()
    UMBRAL_THD = 5.0
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.axhspan(UMBRAL_THD, max(serie.max() * 1.15, UMBRAL_THD * 1.4), color=C_RED, alpha=0.08)
    ax.plot(serie.index, serie.values, color=C_PURPLE, linewidth=1.5)
    ax.axhline(UMBRAL_THD, color=C_RED, linestyle='--', linewidth=1)
    ax.text(serie.index[-1], UMBRAL_THD, f'  umbral {UMBRAL_THD}%',
            va='center', fontsize=10, color=C_RED)
    ax.set_ylim(0, max(serie.max() * 1.2, UMBRAL_THD * 1.4))
    ax.set_title('THD-V — evolución diaria', loc='left')
    ax.set_ylabel('%')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(); plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — KPIs
# ═════════════════════════════════════════════════════════════════════════════
with tab2:

    if kpi_f.empty:
        st.warning("No hay KPIs para el rango seleccionado.")
        st.stop()

    # ── KPI 03 ───────────────────────────────────────────────────────────────
    st.subheader("KPI 03 — Pico de demanda absoluta")
    agg = kpi_f.groupby('entity_id').agg(
        pico=('KPI03_pico_kw', 'max'),
        media_pico=('KPI03_pico_kw', 'mean'),
        sigma_pico=('KPI03_pico_kw', 'std'),
    )
    agg['umbral'] = agg['media_pico'] + 2 * agg['sigma_pico'].fillna(0)
    agg = agg.sort_values('pico', ascending=True)
    colores = [C_RED if p > u else C_TEAL for p, u in zip(agg['pico'], agg['umbral'])]
    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.5 * len(agg))))
    ax.barh(agg.index.astype(str), agg['pico'] / 1000, color=colores,
            edgecolor='none', label='Pico máx.')
    ax.barh(agg.index.astype(str), agg['umbral'] / 1000, color='none',
            edgecolor='#5F5E5A', linewidth=1, linestyle='--', label='Umbral (μ+2σ)')
    for i, p in enumerate(agg['pico'] / 1000):
        ax.text(p + agg['pico'].max() / 1000 * 0.01, i, f'{p:.1f} kW',
                va='center', fontsize=9)
    ax.set_title('KPI 03 — Pico de demanda por bloque', loc='left')
    ax.set_xlabel('kW'); ax.legend(fontsize=9)
    plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── KPI 05 ───────────────────────────────────────────────────────────────
    st.subheader("KPI 05 — Emisiones CO₂ acumuladas")
    actual_diario = kpi_f.groupby('fecha')['KPI05_CO2_tCO2e'].sum().sort_index()
    actual_acum   = actual_diario.cumsum()
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(actual_acum.index, actual_acum.values, color=C_AMBER, linewidth=2)
    ax.fill_between(actual_acum.index, actual_acum.values, alpha=0.15, color=C_AMBER)
    ax.set_title('KPI 05 — Emisiones CO₂ acumuladas en el período', loc='left')
    ax.set_ylabel('tCO₂e acumuladas')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    fig.autofmt_xdate(); plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── KPI 08 ───────────────────────────────────────────────────────────────
    st.subheader("KPI 08 — Load Factor")
    lf_bloque = kpi_f.groupby('entity_id')['KPI08_LF'].mean().sort_values()
    UMBRAL_LF = 0.65
    colores = [C_TEAL if v >= UMBRAL_LF else C_AMBER for v in lf_bloque]
    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.5 * len(lf_bloque))))
    ax.barh(lf_bloque.index.astype(str), lf_bloque.values, color=colores, edgecolor='none')
    ax.axvline(UMBRAL_LF, color='#5F5E5A', linestyle='--', linewidth=1)
    ax.text(UMBRAL_LF, len(lf_bloque) - 0.4, f' umbral {UMBRAL_LF}',
            ha='left', va='bottom', fontsize=10, color='#5F5E5A')
    for i, v in enumerate(lf_bloque.values):
        ax.text(v + 0.01, i, f'{v:.2f}', va='center', fontsize=10)
    ax.set_xlim(0, max(1.0, lf_bloque.max() * 1.15))
    ax.set_title('KPI 08 — Load Factor por bloque', loc='left')
    ax.set_xlabel('Factor de carga (adimensional)')
    plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── KPI 09 ───────────────────────────────────────────────────────────────
    st.subheader("KPI 09 — Índice de consumo nocturno")
    f4_bloque = kpi_f.groupby('entity_id')['KPI09_f4_pct'].mean().sort_values()
    UMBRAL_F4 = 20.0
    colores = [C_RED if v > UMBRAL_F4 else C_TEAL for v in f4_bloque]
    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.5 * len(f4_bloque))))
    ax.barh(f4_bloque.index.astype(str), f4_bloque.values, color=colores, edgecolor='none')
    ax.axvline(UMBRAL_F4, color='#5F5E5A', linestyle='--', linewidth=1)
    for i, v in enumerate(f4_bloque.values):
        ax.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=10)
    ax.set_title('KPI 09 — Consumo nocturno por bloque', loc='left')
    ax.set_xlabel('% de energía consumida entre 22:00–06:59')
    plt.tight_layout()
    st.pyplot(fig); plt.close(fig)

    # ── KPI 10, 11, 12 — tiras de estado ─────────────────────────────────────
    TIRAS = [
        ('KPI10_desbalance_pct', 'KPI 10 — Desbalance de tensión',
         lambda v: C_TEAL if v < 2 else (C_AMBER if v <= 3 else C_RED),
         'verde < 2%  |  naranja 2–3%  |  rojo > 3%'),
        ('KPI11_fp', 'KPI 11 — Factor de potencia',
         lambda v: C_TEAL if v >= 0.95 else (C_AMBER if v >= 0.90 else C_RED),
         'verde ≥ 0.95  |  naranja 0.90–0.95  |  rojo < 0.90'),
        ('KPI12_thd_v_pct', 'KPI 12 — THD-V',
         lambda v: C_TEAL if v < 3 else (C_AMBER if v <= 5 else C_RED),
         'verde < 3%  |  naranja 3–5%  |  rojo > 5%'),
    ]

    for col, titulo, color_fn, leyenda in TIRAS:
        st.subheader(titulo)
        pivot = kpi_f.pivot_table(index='entity_id', columns='fecha',
                                   values=col, aggfunc='mean')
        fechas = pivot.columns.tolist()
        fig, ax = plt.subplots(figsize=(11, max(3.5, 0.45 * len(pivot) + 1.5)))
        for i, (bloque, fila) in enumerate(pivot.iterrows()):
            for j, v in enumerate(fila.values):
                c = '#EEEEEE' if pd.isna(v) else color_fn(v)
                ax.barh(i, 1, left=j, color=c, edgecolor='white', linewidth=1.5)
        ax.set_yticks(range(len(pivot)))
        ax.set_yticklabels(pivot.index.astype(str), fontsize=9)
        step = max(1, len(fechas) // 10)
        ax.set_xticks([j for j in range(0, len(fechas), step)])
        ax.set_xticklabels(
            [fechas[j].strftime('%d-%b') for j in range(0, len(fechas), step)],
            rotation=45, ha='right', fontsize=9)
        ax.set_title(f'{titulo} — estado por día', loc='left')
        ax.set_xlabel(leyenda)
        plt.tight_layout()
        st.pyplot(fig); plt.close(fig)

import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback

# --- IMPORTAÇÃO (Banco de Dados) ---
try:
    from db import ler_dados
except ImportError:
    def ler_dados(query): return pd.DataFrame()

# --- CONFIGURAÇÃO ---
COORDENADAS = {
    'EST_SEMULSP': {'lat': -3.1089, 'lon': -60.0548},
    'EST_MINDU': {'lat': -3.0780, 'lon': -60.0070},
    'ANNA RAYMUNDA': {'lat': -2.9750, 'lon': -60.0080},
    'EST_PONTA_NEGRA': {'lat': -3.0624, 'lon': -60.1044},
    # Adicione suas outras estações aqui...
}

GRAPH_CONFIG = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoScale2d'],
    'toImageButtonOptions': {'format': 'png', 'filename': 'grafico_monitoramento', 'height': 500, 'width': 800, 'scale': 2}
}

# --- FUNÇÕES AUXILIARES ---
def get_color_code(v):
    if pd.isna(v): return '#95a5a6'
    if v > 70: return '#e74c3c'     # Vermelho
    if v >= 30: return '#e67e22'    # Laranja
    if v >= 10: return '#f1c40f'    # Amarelo
    return '#2ecc71'                # Verde

def get_categoria_status(v):
    if pd.isna(v): return "SEM DADOS"
    if v > 70: return "CRÍTICO (>70mm)"
    if v >= 30: return "ATENÇÃO (30-70mm)"
    if v >= 10: return "OBSERVAÇÃO (10-30mm)"
    return "NORMAL (<10mm)"

def calcular_sensacao(t, rh):
    try:
        if pd.isna(t) or pd.isna(rh): return t
        return t + 0.5555 * (6.11 * np.exp(5417.7530 * (1/273.16 - 1/(273.15 + t))) * (rh/100) - 10)
    except: return t

def style_fig(fig, title):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, color="#2d3748", family="Inter, sans-serif")),
        title_x=0.01,
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=50),
        hovermode="x unified",
        font=dict(family="Inter, sans-serif", color="#718096", size=11),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0', zeroline=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0', zeroline=False)
    return fig

def criar_card_estiloso(titulo, valor, unidade, cor, icone, subtexto="", width=2):
    return dbc.Col(dbc.Card([
        dbc.CardBody([
            html.I(className=f"{icone}", style={"position": "absolute", "right": "15px", "top": "15px", "fontSize": "2.5rem", "opacity": "1.0", "color": cor}),
            html.H6(titulo, className="text-muted text-uppercase fw-bold mb-2", style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
            html.H4([f"{valor}", html.Small(unidade, className="text-muted fs-6 ms-1")], className="fw-bold mb-0", style={"color": "#2c3e50", "fontSize": "1.5rem"}),
            html.Small(subtexto, className="text-muted mt-2 d-block", style={"fontSize": "0.7rem"}),
        ], className="p-3 position-relative")
    ], className="shadow-sm h-100 border-0", style={"borderLeft": f"4px solid {cor}", "borderRadius": "12px", "overflow": "hidden"}), width=6, md=4, lg=width, className="mb-3")

# --- NOVA FUNÇÃO PARA TÍTULOS DE SEÇÃO ---
def criar_divisoria(titulo, icone, cor="text-primary"):
    return html.Div([
        html.H5([
            html.I(className=f"{icone} me-2"), 
            titulo
        ], className=f"fw-bold text-uppercase mt-4 mb-2 {cor}", style={"fontSize": "0.9rem", "letterSpacing": "1px"}),
        html.Hr(className="mt-0 mb-4", style={"opacity": "0.15"})
    ])

# --- LAYOUT ---
layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col([html.Div([html.H4([html.I(className="fas fa-satellite-dish me-2"), "Estações Prefeitura"], className="fw-bold text-white mb-0"), html.Small("Dados em Tempo Real (24h)", className="text-white-50")])], width=12, md=8),
        dbc.Col([dcc.Dropdown(id='filtro-estacao', placeholder="Filtrar por Estação...", className="mb-2 shadow-sm", style={"borderRadius": "8px"}), html.Div(id="timer-display", className="text-end text-white fw-bold font-monospace small")], width=12, md=4, className="d-flex flex-column justify-content-center mt-2 mt_md-0")
    ], className="py-4 px-4 mb-4 rounded-3 shadow-sm align-items-center", style={"background": "linear-gradient(135deg, #1a202c 0%, #2d3748 100%)", "marginTop": "-10px"}),

    html.H6([html.I(className="fas fa-bolt me-2 text-warning"), "Destaques Climáticos (Últimas 24h)"], className="text-secondary fw-bold text-uppercase mb-3 ms-1"),
    html.Div(id="linha-extremos"),

    # MAPA E RESUMO
    dbc.Row([
        dbc.Col([dbc.Card([dbc.CardHeader([html.I(className="fas fa-map-marked-alt me-2"), "Geolocalização - Estações Meteológicas"], className="bg-white fw-bold border-bottom"), dbc.CardBody(dcc.Graph(id='mapa-estacoes', style={"height": "500px"}, config=GRAPH_CONFIG), className="p-0 overflow-hidden", style={"borderRadius": "0 0 12px 12px"})], className="shadow-sm border-0 h-100")], width=12, lg=5, className="mb-4"),
        dbc.Col([dbc.Card([dbc.CardHeader([html.I(className="fas fa-list-ul me-2"), "Resumo das Estações"], className="bg-white fw-bold border-bottom"), dbc.CardBody(id="cards-medias", className="p-3", style={"maxHeight": "500px", "overflowY": "auto"})], className="shadow-sm border-0 h-100")], width=12, lg=7, className="mb-4"),
    ]),

    # TELEMETRIA (Cards Atuais)
    criar_divisoria("Telemetria em Tempo Real", "fas fa-broadcast-tower", "text-info"),
    dbc.Row(id="cards-atuais", className="mb-4"),

    # SEÇÃO 1: TEMPERATURA E UMIDADE
    criar_divisoria("Temperatura e Umidade Relativa", "fas fa-thermometer-half", "text-danger"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-temperatura', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-umidade', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
    ]),

    # SEÇÃO 2: CHUVAS
    criar_divisoria("Monitoramento Pluviométrico", "fas fa-cloud-showers-heavy", "text-primary"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-chuva-tempo', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-chuva-acumulado', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
    ]),

    # SEÇÃO 3: VENTOS E PRESSÃO
    criar_divisoria("Monitoramento Eólico e Pressão", "fas fa-wind", "text-success"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-vento-velocidade', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2 h-100"), width=12, lg=6, className="mb-4"),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-vento-direcao', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2 h-100"), width=12, lg=6, className="mb-4"),
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-pressao', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2 h-100"), width=12, className="mb-4"),
    ]),

    # TABELA DE AUDITORIA (SEM ALTERAÇÕES)
    criar_divisoria("Auditoria de Dados", "fas fa-list-alt", "text-dark"),
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-list-alt me-2"), 
                "Auditoria de Dados (Histórico Recente)"
            ], className="bg-white fw-bold border-bottom"),
            
            dbc.CardBody([
                dash_table.DataTable(
                    id='tabela-auditoria',
                    page_size=15, 
                    page_action='native', 
                    sort_action='native', 
                    filter_action='native', 
                    style_as_list_view=True, 
                    
                    style_header={
                        'backgroundColor': '#f8f9fa',
                        'fontWeight': 'bold',
                        'color': '#2d3748',
                        'borderBottom': '2px solid #e2e8f0',
                        'textAlign': 'center'
                    },
                    
                    style_cell={
                        'fontFamily': 'Inter, sans-serif',
                        'fontSize': '12px',
                        'textAlign': 'center',
                        'padding': '10px',
                        'color': '#4a5568'
                    },
                    
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#fcfcfc'},
                        {'if': {'filter_query': '{chuva_mm} >= 10', 'column_id': 'chuva_mm'}, 'color': '#e53e3e', 'fontWeight': 'bold'},
                        {'if': {'filter_query': '{vento_vel} >= 10', 'column_id': 'vento_vel'}, 'color': '#dd6b20', 'fontWeight': 'bold'}
                    ],
                )
            ], className="p-0")
        ], className="shadow-sm border-0 mb-5 overflow-hidden"))
    ]),

    dcc.Interval(id='data-refresh', interval=60*1000, n_intervals=0),
    dcc.Interval(id='timer-interval', interval=1000, n_intervals=0)
], className="px-4 py-2", style={"backgroundColor": "#f4f6f9"})

# --- CALLBACKS ---
def register_callbacks(app):
    @app.callback(Output('timer-display', 'children'), [Input('timer-interval', 'n_intervals')])
    def update_timer(n): return f"Atualiza em: {59 - datetime.now().second:02d}s"

    @app.callback(
        [Output('filtro-estacao', 'options'), Output('linha-extremos', 'children'),
         Output('cards-medias', 'children'), Output('cards-atuais', 'children'),
         Output('tabela-auditoria', 'data'), Output('tabela-auditoria', 'columns'),
         Output('grafico-temperatura', 'figure'), Output('grafico-umidade', 'figure'),
         Output('grafico-chuva-tempo', 'figure'), Output('grafico-chuva-acumulado', 'figure'),
         Output('grafico-pressao', 'figure'), 
         Output('grafico-vento-velocidade', 'figure'), Output('grafico-vento-direcao', 'figure'),
         Output('mapa-estacoes', 'figure')],
        [Input('data-refresh', 'n_intervals'), Input('filtro-estacao', 'value')]
    )
    def update_dashboard(n, est_filt):
        fig_empty = px.scatter(title="Aguardando dados...")
        fig_empty.update_layout(template="plotly_white", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        
        empty_return = [[]] + [None]*3 + [[], []] + [fig_empty]*8

        try:
            # 1. Carregar Dados
            query = "SELECT * FROM defesa_civil ORDER BY data_hora ASC"
            df = ler_dados(query)

            if df.empty: return empty_return

            cols_num = ['temp_ar', 'umidade', 'pressao', 'vento_vel', 'chuva_mm', 'vento_dir']
            for col in cols_num:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

            df.rename(columns={'data_hora': 'tempo'}, inplace=True)
            df['tempo'] = pd.to_datetime(df['tempo'])

            # --- TRATAMENTO (VOLTAR PARA 1min) ---
            df = df.drop_duplicates(subset=['nome_estacao', 'tempo'], keep='last')
            
            dfs_tratados = []
            for estacao, df_est in df.groupby('nome_estacao'):
                df_est = df_est.sort_values('tempo')
                df_est = df_est.set_index('tempo')
                
                # MANTENHA AQUI COMO 1min (Dados brutos precisos)
                df_res = df_est.resample('1min').mean(numeric_only=True)
                
                if 'chuva_mm' in df_est.columns:
                    # MANTENHA AQUI COMO 1min
                    df_res['chuva_mm'] = df_est['chuva_mm'].resample('1min').max()
                    
                    df_res['chuva_mm'] = df_res['chuva_mm'].ffill().fillna(0)
                    df_res['chuva_delta'] = df_res['chuva_mm'].diff().fillna(0)
                    df_res.loc[df_res['chuva_delta'] < 0, 'chuva_delta'] = 0
                    df_res['chuva_mm'] = df_res['chuva_delta']

                for col in ['temp_ar', 'umidade', 'pressao', 'vento_vel', 'vento_dir']:
                    if col in df_res.columns: df_res[col] = df_res[col].interpolate(method='linear')

                df_res['nome_estacao'] = estacao
                df_res = df_res.reset_index()
                dfs_tratados.append(df_res)
                
            if dfs_tratados: df = pd.concat(dfs_tratados, ignore_index=True)

            df = df[df['tempo'] >= (datetime.now() - timedelta(days=1))]
            if df.empty: return empty_return

            df['sensacao'] = df.apply(lambda r: calcular_sensacao(r.get('temp_ar'), r.get('umidade')), axis=1)
            df_completo = df.copy()
            options = [{'label': i, 'value': i} for i in sorted(df['nome_estacao'].unique())]
            
            if est_filt: df = df[df['nome_estacao'] == est_filt]
            if df.empty: df = df_completo

            # EXTREMOS
            acum_est = df_completo.groupby('nome_estacao')['chuva_mm'].sum() if 'chuva_mm' in df_completo.columns else pd.Series()
            def get_ext(col, f='max'):
                if df.empty or col not in df.columns: return "-", "-", "-"
                idx = df[col].idxmax() if f == 'max' else df[col].idxmin()
                if pd.isna(idx): return "-", "-", "-"
                return f"{df.loc[idx, col]:.1f}", df.loc[idx, 'nome_estacao'], df.loc[idx, 'tempo'].strftime('%H:%M')

            vtmax, etmax, htmax = get_ext('temp_ar', 'max')
            vtmin, etmin, htmin = get_ext('temp_ar', 'min')
            vsmax, esmax, hsmax = get_ext('sensacao', 'max')
            vvmax, evmax, hvmax = get_ext('vento_vel', 'max')
            vcmax = f"{acum_est.max():.1f}" if not acum_est.empty else "0"
            ecmax = acum_est.idxmax() if not acum_est.empty else "-"

            extremos = dbc.Row([
                criar_card_estiloso("Temp. Máx", vtmax, "°C", "#e74c3c", "fas fa-temperature-high", f"{etmax} {htmax}"),
                criar_card_estiloso("Temp. Mín", vtmin, "°C", "#3498db", "fas fa-temperature-low", f"{etmin} {htmin}"),
                criar_card_estiloso("Sensação Pico", vsmax, "°C", "#f39c12", "fas fa-sun", f"{esmax} {hsmax}"),
                criar_card_estiloso("Chuva 24h", vcmax, "mm", "#2c3e50", "fas fa-cloud-showers-heavy", f"{ecmax}"),
                criar_card_estiloso("Vento Máx", vvmax, "m/s", "#95a5a6", "fas fa-wind", f"{evmax} {hvmax}"),
                criar_card_estiloso("Umid. Mín", get_ext('umidade', 'min')[0], "%", "#e67e22", "fas fa-tint-slash", f"{get_ext('umidade', 'min')[1]}"),
            ])

            # CARDS & COMP
            agora = df_completo['tempo'].max() if not df_completo.empty else datetime.now()
            agg_rules = {'tempo': 'last'}
            
            if 'chuva_mm' in df_completo.columns:
                df_completo['ch_6h'] = df_completo['chuva_mm'].where(df_completo['tempo'] >= (agora - timedelta(hours=6)), 0)
                df_completo['ch_12h'] = df_completo['chuva_mm'].where(df_completo['tempo'] >= (agora - timedelta(hours=12)), 0)
                df_completo['ch_1h'] = df_completo['chuva_mm'].where(df_completo['tempo'] >= (agora - timedelta(hours=1)), 0)
                agg_rules.update({'ch_1h': 'sum', 'ch_6h': 'sum', 'ch_12h': 'sum', 'chuva_mm': 'sum'})
            
            if 'temp_ar' in df_completo.columns: agg_rules['temp_ar'] = ['min', 'max']
            if 'vento_vel' in df_completo.columns: agg_rules['vento_vel'] = 'max'
            
            medias = df_completo.groupby('nome_estacao').agg(agg_rules)
            medias.columns = ['_'.join(c).strip() if isinstance(c, tuple) else c for c in medias.columns.values]
            medias = medias.reset_index()

            # Cards
            cards_medias = []
            for _, row in medias.iterrows():
                def safe_get(key, default=0): return row.get(key, default) if pd.notnull(row.get(key)) else default
                c_1h, c_6h, c_12h, c_24h = safe_get('ch_1h_sum'), safe_get('ch_6h_sum'), safe_get('ch_12h_sum'), safe_get('chuva_mm_sum')
                def badge_chuva(valor, label):
                    cor = get_color_code(valor)
                    estilo = {"backgroundColor": cor if valor > 0 else "#edf2f7", "color": "white" if valor > 0 else "#a0aec0", "fontSize": "0.7rem", "padding": "2px 8px", "fontWeight": "bold"}
                    return dbc.Col([html.Div(label, className="text-muted small", style={"fontSize": "0.6rem"}), html.Span(f"{valor:.1f}", className="badge rounded-pill", style=estilo)], width=3, className="text-center px-0")
                tempo_str = row['tempo_last'].strftime('%H:%M') if 'tempo_last' in row else "--:--"
                cards_medias.append(dbc.Row([
                    dbc.Col([html.Span(row['nome_estacao'], className="fw-bold text-dark d-block text-truncate"), html.Small(f"🕒 {tempo_str}", className="text-muted", style={"fontSize": "0.7rem"})], width=3, className="d-flex flex-column justify-content-center"),
                    dbc.Col([html.Div([html.I(className="fas fa-arrow-down small text-primary me-1"), f"{safe_get('temp_ar_min'):.0f}°"], style={"fontSize": "0.8rem"}), html.Div([html.I(className="fas fa-arrow-up small text-danger me-1"), f"{safe_get('temp_ar_max'):.0f}°"], style={"fontSize": "0.8rem"})], width=2, className="text-center border-start border-end bg-light"),
                    dbc.Col(dbc.Row([badge_chuva(c_1h, "1h"), badge_chuva(c_6h, "6h"), badge_chuva(c_12h, "12h"), badge_chuva(c_24h, "24h")], className="g-0"), width=5),
                    dbc.Col([html.I(className="fas fa-wind text-muted mb-1"), html.Span(f"{safe_get('vento_vel_max'):.1f}", className="fw-bold small d-block")], width=2, className="text-center border-start")
                ], className="mb-2 border rounded-3 py-2 shadow-sm bg-white align-items-center g-0"))

            # Atuais
            ultimas = df_completo.sort_values('tempo').groupby('nome_estacao').last().reset_index()
            cards_atuais = []
            for _, row in ultimas.iterrows():
                cards_atuais.append(dbc.Col(dbc.Card([
                    dbc.CardHeader([html.Span(row['nome_estacao'], className="fw-bold text-truncate", style={"maxWidth": "80%", "float": "left"}), html.Span(row['tempo'].strftime('%H:%M'), className="float-end badge bg-secondary")], className="bg-transparent border-bottom pt-2 pb-2 small"),
                    dbc.CardBody([dbc.Row([
                        dbc.Col([html.H5(f"{row.get('temp_ar',0):.1f}°", className="mb-0 text-dark"), html.Small("Temp", className="text-muted small")], className="text-center border-end p-1"),
                        dbc.Col([html.H5(f"{row.get('umidade',0):.0f}%", className="mb-0 text-info"), html.Small("Umid", className="text-muted small")], className="text-center border-end p-1"),
                        dbc.Col([html.H5(f"{row.get('chuva_mm',0):.1f}", className="mb-0 text-primary"), html.Small("Chuva", className="text-muted small")], className="text-center border-end p-1"),
                        dbc.Col([html.H5(f"{row.get('vento_vel',0):.1f}", className="mb-0 text-secondary"), html.Small("Vento", className="text-muted small")], className="text-center p-1"),
                    ], className="g-0")], className="p-2")
                ], className="shadow-sm h-100 border-0"), width=12, md=6, lg=3, className="mb-3"))

            # GRÁFICOS
            def safe_plot(data, x, y, color, title):
                if data.empty or y not in data.columns: return fig_empty
                
                # --- SUAVIZAÇÃO VISUAL (10 min) ---
                # Agrupa por estação e tira a média a cada 10 minutos
                # Isso remove o ruído "ziguezague" sem perder dados na tabela/chuva
                try:
                    df_smooth = data.set_index('tempo').groupby(color)[y].resample('10min').mean().reset_index()
                except:
                    df_smooth = data # Fallback se der erro
                
                return style_fig(px.line(df_smooth, x='tempo', y=y, color=color, render_mode='svg'), title)

            fig_t = safe_plot(df, "tempo", "temp_ar", "nome_estacao", "Evolução da Temperatura (°C)")
            fig_u = safe_plot(df, "tempo", "umidade", "nome_estacao", "Umidade Relativa (%)")
            fig_p = safe_plot(df, "tempo", "pressao", "nome_estacao", "Pressão Atmosférica (hPa)")

            if not df.empty and 'chuva_mm' in df.columns:
                df_chuva_hora = df.set_index('tempo').groupby('nome_estacao').resample('1h')['chuva_mm'].sum().reset_index()
                df_chuva_hora = df_chuva_hora[df_chuva_hora['chuva_mm'] > 0]
                fig_c_t = style_fig(px.bar(df_chuva_hora, x="tempo", y="chuva_mm", color="nome_estacao", barmode='group'), "Intensidade de Chuva (mm/h)")
                fig_c_t.update_xaxes(tickformat="%H:%M")
            else: fig_c_t = fig_empty
            
            # Comparativo 6/12/24h
            if not medias.empty and 'chuva_mm_sum' in medias.columns:
                df_comp = medias[['nome_estacao', 'ch_6h_sum', 'ch_12h_sum', 'chuva_mm_sum']].copy()
                df_comp.rename(columns={'ch_6h_sum': '6h', 'ch_12h_sum': '12h', 'chuva_mm_sum': '24h'}, inplace=True)
                df_melted = df_comp.melt(id_vars='nome_estacao', var_name='Período', value_name='Milímetros')
                fig_c_a = px.bar(df_melted, x='nome_estacao', y='Milímetros', color='Período', barmode='group',
                                 title="<b>Acumulado de Chuva (Comparativo)</b>", text='Milímetros',
                                 color_discrete_map={'6h': '#e74c3c', '12h': '#f39c12', '24h': '#3498db'})
                fig_c_a.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                fig_c_a = style_fig(fig_c_a, "Acumulado de Chuva (6h / 12h / 24h)")
            else: fig_c_a = fig_empty

            if 'vento_vel' in df_completo.columns:
                df_vv = df_completo.sort_values('tempo').groupby('nome_estacao').last().reset_index().sort_values('vento_vel', ascending=False)
                fig_v_vel = go.Figure()
                for _, row in df_vv.iterrows(): fig_v_vel.add_shape(type="line", x0=row['nome_estacao'], y0=0, x1=row['nome_estacao'], y1=row['vento_vel'], line=dict(color="#cbd5e0", width=2), layer="below")
                fig_v_vel.add_trace(go.Scatter(x=df_vv['nome_estacao'], y=df_vv['vento_vel'], mode='markers+text', text=df_vv['vento_vel'].apply(lambda x: f"{x:.1f}"), textposition="top center", marker=dict(color=df_vv['vento_vel'], colorscale='Tealgrn', size=14, line=dict(width=2, color='white'), opacity=1), name="Vento Atual", hoverinfo="x+y"))
                fig_v_vel.update_layout(title=dict(text="<b>Velocidade Vento (m/s)</b>", font=dict(family="Inter, sans-serif", size=13, color="#4a5568")), yaxis=dict(showgrid=True, visible=False, range=[0, df_vv['vento_vel'].max()*1.25]), xaxis=dict(showgrid=False, tickangle=-45), margin=dict(t=40, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
            else: fig_v_vel = fig_empty

            if 'vento_dir' in df_completo.columns and 'vento_vel' in df_completo.columns:
                df_vd = df_completo.sort_values('tempo').groupby('nome_estacao').last().reset_index().dropna(subset=['vento_dir', 'vento_vel'])
                if not df_vd.empty:
                    fig_v_dir = go.Figure()
                    fig_v_dir.add_trace(go.Barpolar(r=df_vd['vento_vel'], theta=df_vd['vento_dir'], text=df_vd['nome_estacao'], marker=dict(color=df_vd['vento_vel'], colorscale='Spectral_r', line=dict(color='white', width=1), opacity=0.85), hovertemplate='<b>%{text}</b><br>Vel: %{r:.1f} m/s<br>Dir: %{theta:.0f}°<extra></extra>'))
                    fig_v_dir.update_layout(title=dict(text="<b>Direção do Vento</b>", x=0.5, font=dict(family="Inter, sans-serif", size=13, color="#4a5568")), margin=dict(t=40, b=40, l=40, r=40), paper_bgcolor='rgba(0,0,0,0)', polar=dict(bgcolor='rgba(247,250,252,0.5)', radialaxis=dict(visible=True, range=[0, df_vd['vento_vel'].max()*1.2], angle=45, tickfont=dict(size=8, color='#a0aec0')), angularaxis=dict(tickmode='array', tickvals=[0, 45, 90, 135, 180, 225, 270, 315], ticktext=['<b>N</b>', 'NE', '<b>L</b>', 'SE', '<b>S</b>', 'SO', '<b>O</b>', 'NO'], direction='clockwise', rotation=90, gridcolor='#cbd5e0', tickfont=dict(size=10, color='#4a5568'))))
                else: fig_v_dir = fig_empty
            else: fig_v_dir = fig_empty

            # --- MAPA (VERSÃO PX QUE FUNCIONOU + TEXTO PRETO) ---
            if not medias.empty and 'chuva_mm_sum' in medias.columns:
                df_mapa = pd.merge(ultimas, medias[['nome_estacao', 'chuva_mm_sum']], on='nome_estacao')
                df_mapa['lat'] = df_mapa['nome_estacao'].map(lambda x: COORDENADAS.get(x, {}).get('lat'))
                df_mapa['lon'] = df_mapa['nome_estacao'].map(lambda x: COORDENADAS.get(x, {}).get('lon'))
                df_mapa = df_mapa.dropna(subset=['lat'])
                
                if not df_mapa.empty:
                    df_mapa['txt_mapa'] = df_mapa['chuva_mm_sum'].apply(lambda x: f"{x:.0f}")
                    df_mapa['status'] = df_mapa['chuva_mm_sum'].apply(get_categoria_status)
                    
                    fig_mapa = px.scatter_mapbox(
                        df_mapa, 
                        lat="lat", lon="lon", 
                        hover_name="nome_estacao", 
                        text="txt_mapa", 
                        color="status", 
                        color_discrete_map={
                            "CRÍTICO (>70mm)": "#e74c3c", 
                            "ATENÇÃO (30-70mm)": "#e67e22", 
                            "OBSERVAÇÃO (10-30mm)": "#f1c40f", 
                            "NORMAL (<10mm)": "#2ecc71"
                        },
                        size=[30]*len(df_mapa),
                        zoom=10.5, 
                        center={"lat": -3.05, "lon": -60.03}
                    )
                    
                    # AJUSTE FINAL: PRETO PARA CONTRASTE
                    fig_mapa.update_traces(
                        mode='markers+text',
                        textposition='middle center',
                        textfont=dict(size=12, color='black', weight='bold') # Mudei para Black
                    )
                    
                    fig_mapa.update_layout(
                        mapbox_style="open-street-map", 
                        margin={"r":0,"t":0,"l":0,"b":0}, 
                        legend=dict(
                            orientation="h",       # Horizontal
                            yanchor="bottom",      # Ancora embaixo
                            y=0.02,                # Levemente acima da borda inferior
                            xanchor="center",      # <<< O SEGREDO: Ancora pelo centro
                            x=0.5,                 # Posiciona no meio exato (50%)
                            bgcolor="rgba(255,255,255,0.9)",
                            title=""               # Remove título da legenda para economizar espaço
                        )
                    )
                else: fig_mapa = fig_empty
            else: fig_mapa = fig_empty
        # --- PREPARAÇÃO DA TABELA (FORMATADA) ---
            # Criamos uma cópia para não estragar o df principal usado nos gráficos
            df_tab = df.copy().sort_values('tempo', ascending=False).head(100) # Pega os últimos 100 registros
            
            # Formata Data para Brasileiro
            df_tab['tempo_fmt'] = df_tab['tempo'].dt.strftime('%d/%m %H:%M')
            
            # Arredonda valores
            cols_dec = ['temp_ar', 'umidade', 'vento_vel', 'chuva_mm', 'pressao']
            for c in cols_dec:
                if c in df_tab.columns:
                    df_tab[c] = df_tab[c].map(lambda x: f"{x:.1f}" if pd.notnull(x) else "-")

            # Seleciona e Renomeia Colunas para Exibição
            col_map = {
                'tempo_fmt': 'Data/Hora',
                'nome_estacao': 'Estação',
                'chuva_mm': 'Chuva (mm)',
                'temp_ar': 'Temp (°C)',
                'umidade': 'Umid (%)',
                'vento_vel': 'Vento (m/s)'
            }
            
            # Filtra só as colunas que existem
            cols_finais = [c for c in col_map.keys() if c in df_tab.columns or c == 'tempo_fmt']
            df_tab = df_tab[cols_finais].rename(columns=col_map)

            # Gera dados e colunas para o Dash
            tabela_data = df_tab.to_dict('records')
            tabela_cols = [{"name": i, "id": i} for i in df_tab.columns]
        except Exception as e:
            print("❌ ERRO NO DASHBOARD:")
            traceback.print_exc()
            return empty_return

        return options, extremos, cards_medias, cards_atuais, tabela_data, tabela_cols, fig_t, fig_u, fig_c_t, fig_c_a, fig_p, fig_v_vel, fig_v_dir, fig_mapa
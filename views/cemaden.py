import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
import traceback

# --- IMPORTAÇÃO (Banco de Dados) ---
try:
    from db import ler_dados
except ImportError:
    def ler_dados(query): return pd.DataFrame()

# --- COORDENADAS ---
COORDENADAS_CEMADEN = {
    'Igarapé do Quarenta': {'lat': -3.119457, 'lon': -59.978352},
    'Igarape do Quarenta': {'lat': -3.119457, 'lon': -59.978352}, 
    'Igarapé Quarenta': {'lat': -3.119457, 'lon': -59.978352},
    'Igarape Quarenta': {'lat': -3.119457, 'lon': -59.978352},
    'Igarapé do Mindu': {'lat': -3.091422, 'lon': -60.015121},
    'Igarape do Mindu': {'lat': -3.091422, 'lon': -60.015121},
    'Puraquequara': {'lat': -3.05913, 'lon': -59.84491},
    'Colonia Antonio Aleixo': {'lat': -3.08671, 'lon': -59.88327},
    'Colônia Antônio Aleixo': {'lat': -3.08671, 'lon': -59.88327},
    'Mauazinho': {'lat': -3.1244, 'lon': -59.94},
    'Jorge Teixeira': {'lat': -3.04505, 'lon': -59.92481},
    'Cidade de Deus': {'lat': -3.01954, 'lon': -59.94026},
    'Santa Luzia': {'lat': -3.13807, 'lon': -60.00741},
    'Flores': {'lat': -3.04046, 'lon': -59.99958},
    'Bairro da União': {'lat': -3.09952, 'lon': -60.0159},
    'Bairro da Uniao': {'lat': -3.09952, 'lon': -60.0159},
    'Santa Etelvina': {'lat': -2.98676, 'lon': -60.01654},
    'Tarumã': {'lat': -3.00228, 'lon': -60.04581},
    'Redenção': {'lat': -3.05418, 'lon': -60.04631},
    'Compensa': {'lat': -3.11483, 'lon': -60.05759},
    'Gilberto Mestrinho': {'lat': -3.085, 'lon': -59.93}
}

# --- LIMIARES DE ALERTA (MANAUS) ---
LIMIARES = {
    'NORMAL': {'min': 0, 'max': 9.9, 'cor': '#2ecc71', 'cor_texto': '#2c3e50', 'icone': 'fa-check-circle'},
    'OBSERVAÇÃO': {'min': 10, 'max': 29.9, 'cor': '#f1c40f', 'cor_texto': '#2c3e50', 'icone': 'fa-exclamation-circle'},
    'ATENÇÃO': {'min': 30, 'max': 70, 'cor': '#e67e22', 'cor_texto': '#ffffff', 'icone': 'fa-exclamation-triangle'},
    'CRÍTICO': {'min': 70, 'max': 999, 'cor': '#e74c3c', 'cor_texto': '#ffffff', 'icone': 'fa-skull-crossbones'}
}

def get_nivel_alerta(valor):
    """Retorna o nível de alerta baseado no valor da chuva 24h"""
    if valor > LIMIARES['CRÍTICO']['min']:
        return 'CRÍTICO'
    elif valor >= LIMIARES['ATENÇÃO']['min']:
        return 'ATENÇÃO'
    elif valor >= LIMIARES['OBSERVAÇÃO']['min']:
        return 'OBSERVAÇÃO'
    else:
        return 'NORMAL'

# --- FUNÇÕES AUXILIARES ---
def limpar_nome_estacao(nome_sujo):
    if not isinstance(nome_sujo, str): return str(nome_sujo)
    nome = nome_sujo.replace("CEMADEN - ", "")
    nome = re.sub(r'\s*[\(\[].*?[\)\]]', '', nome)
    return nome.strip()

def get_color_code(v):
    if v > 70: return '#e74c3c'  # Vermelho
    if v >= 30: return '#e67e22' # Laranja
    if v >= 10: return '#f1c40f' # Amarelo
    return '#2ecc71'             # Verde

def get_categoria_status(v):
    if v > 70: return "CRÍTICO"
    if v >= 30: return "ATENÇÃO"
    if v >= 10: return "OBSERVAÇÃO"
    return "NORMAL"

def style_fig(fig, title):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, color="#2d3748", family="Inter, sans-serif")),
        title_x=0.5,
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=40, b=50),
        hovermode="x unified",
        font=dict(family="Inter, sans-serif", color="#718096", size=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    fig.update_xaxes(showgrid=False, linecolor='#eee')
    fig.update_yaxes(showgrid=True, gridcolor='#f0f2f5', zeroline=False)
    return fig

# --- FUNÇÃO DE DESTAQUE (Igual ao Monitoramento) ---
def criar_divisoria(titulo, icone, cor="text-primary"):
    return html.Div([
        html.H5([html.I(className=f"{icone} me-2"), titulo], 
                className=f"fw-bold text-uppercase mt-4 mb-2 {cor}", 
                style={"fontSize": "0.9rem", "letterSpacing": "1px"}),
        html.Hr(className="mt-0 mb-4", style={"opacity": "0.15"})
    ])

GRAPH_CONFIG = {
    'displayModeBar': False,
    'staticPlot': False
}

# --- LAYOUT ---
layout = dbc.Container(fluid=True, children=[
    
    # 1. CABEÇALHO
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H4([html.I(className="fas fa-cloud-showers-heavy me-2"), "CEMADEN Nacional"], className="fw-bold text-white mb-0"),
                html.Small("Monitoramento de Pluviômetros Automáticos (24h)", className="text-white-50")
            ])
        ], width=12, md=8),
        dbc.Col([
            dcc.Dropdown(id='filtro-cemaden', placeholder="Filtrar por Bairro...", className="mb-2 shadow-sm", style={"borderRadius": "8px"}),
            html.Div(id="timer-cemaden", className="text-end text-white fw-bold font-monospace small")
        ], width=12, md=4, className="d-flex flex-column justify-content-center mt-2 mt_md-0")
    ], className="py-4 px-4 mb-4 rounded-3 shadow-sm align-items-center", style={"background": "linear-gradient(135deg, #2980b9 0%, #2c3e50 100%)", "marginTop": "-10px"}),

    # 2. MAPA E TABELA
    html.H6([html.I(className="fas fa-globe-americas me-2 text-info"), "Visão Geral"], className="text-secondary fw-bold text-uppercase mb-3 ms-1"),
    
    dbc.Row([
        # Coluna 1: Mapa
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-map-marked-alt me-2"), "Distribuição Espacial"], className="bg-white fw-bold border-bottom"),
                dbc.CardBody(
                    dcc.Graph(id='mapa-cemaden', style={"height": "460px"}, config=GRAPH_CONFIG),
                    className="p-0 overflow-hidden", style={"borderRadius": "0 0 12px 12px"}
                )
            ], className="shadow-sm border-0 h-100")
        ], width=12, lg=6, className="mb-4"),

        # Coluna 2: Tabela de Ranking
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-list-ol me-2"), "Ranking de Chuva (24h)"], className="bg-white fw-bold border-bottom"),
                dbc.CardBody(id="tabela-ranking-cemaden", className="p-0", style={"overflow": "hidden", "borderRadius": "0 0 12px 12px"})
            ], className="shadow-sm border-0 h-100")
        ], width=12, lg=6, className="mb-4"),
    ]),

    # 3. CARDS DE DETALHE
    criar_divisoria("Status Detalhado por Estação", "fas fa-broadcast-tower", "text-success"),
    dbc.Row(id="cards-cemaden", className="mb-4"),

    # 4. GRÁFICO GERAL
    criar_divisoria("Comparativo de Acumulados", "fas fa-chart-bar", "text-primary"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-cemaden-geral', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, className="mb-4"),
    ]),
    
    dcc.Interval(id='cemaden-refresh', interval=60*1000, n_intervals=0),
    dcc.Interval(id='timer-regressivo-cemaden', interval=1000, n_intervals=0)
], className="px-4 py-2", style={"backgroundColor": "#f4f6f9"})


# --- CALLBACKS ---
def register_callbacks(app):
    
    @app.callback(Output('timer-cemaden', 'children'), [Input('timer-regressivo-cemaden', 'n_intervals')])
    def update_countdown(n):
        now = datetime.now()
        minutos_restantes = 9 - (now.minute % 10)
        segundos_restantes = 59 - now.second
        return f"Atualiza em: {minutos_restantes:02d}:{segundos_restantes:02d}"

    @app.callback(
        [Output('filtro-cemaden', 'options'),
         Output('tabela-ranking-cemaden', 'children'),
         Output('mapa-cemaden', 'figure'),
         Output('cards-cemaden', 'children'),
         Output('grafico-cemaden-geral', 'figure')],
        [Input('cemaden-refresh', 'n_intervals'),
         Input('filtro-cemaden', 'value')]
    )
    def update_cemaden(n, est_filt):
        fig_empty = px.scatter(title="Aguardando dados...")
        fig_empty.update_layout(template="plotly_white", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        
        empty_return = [[], html.Div("Sem dados.", className="p-3 text-muted"), fig_empty, [], fig_empty]

        try:
            # --- CONEXÃO NOVA (DB.PY) ---
            query = "SELECT * FROM cemaden ORDER BY data_hora ASC"
            df = ler_dados(query)

            if df.empty: return empty_return

            # Filtro de Data (Últimas 24h) via Python
            df['data_hora'] = pd.to_datetime(df['data_hora'])
            agora = datetime.now()
            inicio_24h = agora - timedelta(days=1)
            df = df[df['data_hora'] >= inicio_24h]

            if df.empty: return empty_return

            # Limpeza
            df['nome_limpo'] = df['nome_estacao'].apply(limpar_nome_estacao)
            cols_necessarias = ['chuva_mm', 'chuva_1h', 'chuva_6h', 'chuva_12h', 'chuva_24h']
            for col in cols_necessarias:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            options = [{'label': i, 'value': i} for i in sorted(df['nome_limpo'].unique())]
            
            df_completo = df.copy()
            if est_filt: 
                df = df[df['nome_limpo'] == est_filt]
                if df.empty: df = df_completo

            ultimas = df.groupby('nome_limpo').last().reset_index()

            # --- 1. TABELA COM DESTAQUES POR LIMIARES ---
            ranking_df = ultimas.sort_values('chuva_24h', ascending=False).copy()
            ranking_df['nivel_alerta'] = ranking_df['chuva_24h'].apply(get_nivel_alerta)
            
            # Criar DataFrame para exibição
            tabela_cols_df = ranking_df[['nome_limpo', 'chuva_1h', 'chuva_6h', 'chuva_24h', 'nivel_alerta']].copy()
            tabela_cols_df.columns = ['Bairro / Estação', 'Chuva 1h', 'Chuva 6h', 'Chuva 24h', 'Status']
            
            # Formatação
            for c in ['Chuva 1h', 'Chuva 6h', 'Chuva 24h']:
                tabela_cols_df[c] = tabela_cols_df[c].map(lambda x: f"{x:.1f} mm")

            tabela_ranking = dash_table.DataTable(
                data=tabela_cols_df.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in tabela_cols_df.columns],
                page_size=10,
                sort_action='native',
                filter_action='native',
                style_as_list_view=True,
                
                # Estilo do Cabeçalho
                style_header={
                    'backgroundColor': '#2c3e50',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'border': 'none',
                    'textAlign': 'center',
                    'fontSize': '12px',
                    'padding': '12px',
                    'fontFamily': 'Inter, sans-serif'
                },
                
                # Estilo das Células
                style_cell={
                    'textAlign': 'center',
                    'padding': '12px',
                    'fontFamily': 'Inter, sans-serif',
                    'fontSize': '12px',
                    'color': '#4a5568',
                    'border': '1px solid #e2e8f0',
                    'minWidth': '100px'
                },
                
                # Estilo Condicional MELHORADO
                style_data_conditional=[
                    # Linhas alternadas
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                    
                    # DESTAQUES PARA CHUVA 24h
                    # CRÍTICO (>70mm) - Vermelho
                    {
                        'if': {
                            'filter_query': '{Chuva 24h} >= "70.0"',
                            'column_id': 'Chuva 24h'
                        },
                        'backgroundColor': '#e74c3c',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'borderLeft': '4px solid #c0392b',
                        'fontSize': '13px'
                    },
                    
                    # ATENÇÃO (30-70mm) - Laranja
                    {
                        'if': {
                            'filter_query': '{Chuva 24h} >= "30.0" && {Chuva 24h} < "70.0"',
                            'column_id': 'Chuva 24h'
                        },
                        'backgroundColor': '#e67e22',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'borderLeft': '4px solid #d35400',
                        'fontSize': '13px'
                    },
                    
                    # OBSERVAÇÃO (10-30mm) - Amarelo
                    {
                        'if': {
                            'filter_query': '{Chuva 24h} >= "10.0" && {Chuva 24h} < "30.0"',
                            'column_id': 'Chuva 24h'
                        },
                        'backgroundColor': '#f1c40f',
                        'color': '#2c3e50',
                        'fontWeight': 'bold',
                        'borderLeft': '4px solid #f39c12',
                        'fontSize': '13px'
                    },
                    
                    # NORMAL (<10mm) - Verde claro
                    {
                        'if': {
                            'filter_query': '{Chuva 24h} < "10.0"',
                            'column_id': 'Chuva 24h'
                        },
                        'backgroundColor': '#d5f4e6',
                        'color': '#2c3e50',
                        'borderLeft': '4px solid #2ecc71'
                    },
                    
                    # Destaque para coluna Status
                    {
                        'if': {
                            'filter_query': '{Status} = "CRÍTICO"',
                            'column_id': 'Status'
                        },
                        'backgroundColor': '#e74c3c',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'fontSize': '11px',
                        'textTransform': 'uppercase',
                        'borderRadius': '12px'
                    },
                    {
                        'if': {
                            'filter_query': '{Status} = "ATENÇÃO"',
                            'column_id': 'Status'
                        },
                        'backgroundColor': '#e67e22',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'fontSize': '11px',
                        'textTransform': 'uppercase',
                        'borderRadius': '12px'
                    },
                    {
                        'if': {
                            'filter_query': '{Status} = "OBSERVAÇÃO"',
                            'column_id': 'Status'
                        },
                        'backgroundColor': '#f1c40f',
                        'color': '#2c3e50',
                        'fontWeight': 'bold',
                        'fontSize': '11px',
                        'textTransform': 'uppercase',
                        'borderRadius': '12px'
                    },
                    {
                        'if': {
                            'filter_query': '{Status} = "NORMAL"',
                            'column_id': 'Status'
                        },
                        'backgroundColor': '#2ecc71',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'fontSize': '11px',
                        'textTransform': 'uppercase',
                        'borderRadius': '12px'
                    },
                    
                    # Destaque para valores altos nas outras colunas
                    {
                        'if': {
                            'filter_query': '{Chuva 1h} >= "10.0"',
                            'column_id': 'Chuva 1h'
                        },
                        'backgroundColor': 'rgba(241, 196, 15, 0.2)',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{Chuva 6h} >= "30.0"',
                            'column_id': 'Chuva 6h'
                        },
                        'backgroundColor': 'rgba(230, 126, 34, 0.2)',
                        'fontWeight': 'bold'
                    }
                ],
                
                # Estilo da Tabela
                style_table={
                    'overflowX': 'auto',
                    'borderRadius': '8px',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'
                }
            )

            # --- 2. MAPA (CONFIGURAÇÃO PADRONIZADA COM MONITORAMENTO) ---
            ultimas['lat'] = ultimas['nome_limpo'].map(lambda x: COORDENADAS_CEMADEN.get(x, {}).get('lat'))
            ultimas['lon'] = ultimas['nome_limpo'].map(lambda x: COORDENADAS_CEMADEN.get(x, {}).get('lon'))
            df_mapa = ultimas.dropna(subset=['lat', 'lon']).copy()
            
            if not df_mapa.empty:
                # Prepara os dados para o estilo visual solicitado
                df_mapa['txt_mapa'] = df_mapa['chuva_24h'].apply(lambda x: f"{x:.0f}")
                df_mapa['status'] = df_mapa['chuva_24h'].apply(get_categoria_status)
                
                # Criando o mapa com Plotly Express (Versão que funcionou no monitoramento)
                fig_mapa = px.scatter_mapbox(
                    df_mapa, 
                    lat="lat", lon="lon", 
                    hover_name="nome_limpo", 
                    text="txt_mapa", 
                    color="status", 
                    color_discrete_map={
                        "CRÍTICO": "#e74c3c", 
                        "ATENÇÃO": "#e67e22", 
                        "OBSERVAÇÃO": "#f1c40f", 
                        "NORMAL": "#2ecc71"
                    },
                    size=[30]*len(df_mapa), # Tamanho fixo para as bolinhas
                    zoom=10.5, 
                    center={"lat": -3.05, "lon": -60.03}
                )
                
                # AJUSTE FINAL: TEXTO PRETO E CENTRALIZADO (Igual ao monitoramento)
                fig_mapa.update_traces(
                    mode='markers+text',
                    textposition='middle center',
                    textfont=dict(size=12, color='black', weight='bold')
                )
                
                # LAYOUT: LEGENDA CENTRALIZADA EM BAIXO
                fig_mapa.update_layout(
                    mapbox_style="open-street-map", 
                    margin={"r":0,"t":0,"l":0,"b":0}, 
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=0.01, 
                        xanchor="center", 
                        x=0.5, 
                        bgcolor="rgba(255,255,255,0.9)",
                        title=""
                    )
                )
            else:
                fig_mapa = fig_empty

            # --- 3. CARDS COM DESTAQUES POR LIMIARES ---
            cards = []
            for _, row in ultimas.iterrows():
                v24 = row['chuva_24h']
                nivel = get_nivel_alerta(v24)
                config = LIMIARES[nivel]
                
                # Determinar estilo baseado no nível
                if nivel in ['CRÍTICO', 'ATENÇÃO']:
                    # Níveis altos - fundo colorido com gradiente
                    card_style = {
                        "background": f"linear-gradient(135deg, {config['cor']} 0%, {config['cor']}99 100%)",
                        "borderRadius": "12px",
                        "transition": "transform 0.3s ease, box-shadow 0.3s ease",
                        "boxShadow": f"0 4px 12px {config['cor']}40",
                        "border": "none",
                        "position": "relative",
                        "overflow": "hidden"
                    }
                    
                    # Efeito de pulsação para CRÍTICO
                    if nivel == 'CRÍTICO':
                        card_style["animation"] = "pulseCritical 2s infinite"
                        card_style["border"] = "2px solid #c0392b"
                    
                    text_color = "white"
                    badge_style = "badge bg-white text-dark me-1 opacity-90"
                    
                else:
                    # Níveis baixos - fundo branco com borda colorida
                    card_style = {
                        "backgroundColor": "white",
                        "borderLeft": f"6px solid {config['cor']}",
                        "borderRadius": "12px",
                        "transition": "transform 0.3s ease",
                        "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
                        "border": "1px solid #e2e8f0",
                        "position": "relative"
                    }
                    text_color = "#2c3e50"
                    badge_style = "badge bg-light text-dark border me-1"
                
                # Ícone baseado no nível
                icon_class = config['icone']
                
                # Criar card
                card = dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            # Badge de status no topo
                            html.Div([
                                html.Span(
                                    nivel,
                                    className=f"status-badge position-absolute top-0 start-0 m-2",
                                    style={
                                        "backgroundColor": config['cor'],
                                        "color": config['cor_texto'],
                                        "fontSize": "0.65rem",
                                        "padding": "3px 10px",
                                        "borderRadius": "12px",
                                        "fontWeight": "bold",
                                        "textTransform": "uppercase"
                                    }
                                ),
                                html.I(className=f"fas {icon_class} fa-2x position-absolute top-0 end-0 m-3 opacity-25", 
                                      style={"color": config['cor_texto'] if nivel in ['NORMAL', 'OBSERVAÇÃO'] else "white"})
                            ]),
                            
                            # Nome da estação
                            html.H6(
                                row['nome_limpo'], 
                                className="text-uppercase fw-bold mb-3 mt-4", 
                                style={"fontSize": "0.75rem", "color": text_color, "letterSpacing": "0.5px"}
                            ),
                            
                            # Valor principal (24h) - Destaque maior
                            html.Div([
                                html.Div([
                                    html.Span(f"{v24:.1f}", className="fw-bold display-6", style={"color": text_color}),
                                    html.Small(" mm", className="ms-1", style={"color": text_color, "opacity": 0.8})
                                ], className="d-flex align-items-end justify-content-center"),
                                html.Small("últimas 24h", className="text-center d-block mt-1", 
                                         style={"color": text_color, "opacity": 0.8, "fontSize": "0.7rem"})
                            ], className="mb-3"),
                            
                            # Separador
                            html.Hr(className="my-2", style={"opacity": "0.2"}),
                            
                            # Valores secundários
                            html.Div([
                                html.Div([
                                    html.Small("1h: ", className="text-muted me-1"),
                                    html.Span(f"{row['chuva_1h']:.1f}", 
                                             className=f"{'fw-bold text-danger' if row['chuva_1h'] >= 10 else 'fw-bold'}", 
                                             style={"color": text_color})
                                ], className="d-flex justify-content-between mb-1"),
                                
                                html.Div([
                                    html.Small("6h: ", className="text-muted me-1"),
                                    html.Span(f"{row['chuva_6h']:.1f}", 
                                             className=f"{'fw-bold text-warning' if row['chuva_6h'] >= 30 else 'fw-bold'}", 
                                             style={"color": text_color})
                                ], className="d-flex justify-content-between")
                            ], className="small"),
                            
                            # Barra de progresso visual
                            html.Div([
                                html.Div(
                                    className="progress-bar",
                                    style={
                                        "width": f"{min(v24/100*100, 100)}%",
                                        "backgroundColor": config['cor'],
                                        "height": "4px",
                                        "borderRadius": "2px",
                                        "marginTop": "10px"
                                    }
                                )
                            ], className="progress", style={"height": "4px", "backgroundColor": "#e2e8f0", "opacity": "0.5"})
                        ])
                    ], className="h-100 card-hover", style=card_style),
                    width=12, md=6, lg=3, className="mb-3"
                )
                
                cards.append(card)

            # --- 4. GRÁFICO GERAL ---
            cores_barras = ultimas['chuva_24h'].apply(get_color_code).tolist()
            fig_bar = px.bar(ultimas, x="nome_limpo", y="chuva_24h", text="chuva_24h")
            fig_bar.update_traces(marker_color=cores_barras, texttemplate='%{text:.1f}', textposition='outside', cliponaxis=False)
            fig_bar = style_fig(fig_bar, "Acumulado Total 24h (mm)")

            return options, tabela_ranking, fig_mapa, cards, fig_bar

        except Exception as e:
            print("❌ ERRO NO CEMADEN:")
            traceback.print_exc()
            return empty_return
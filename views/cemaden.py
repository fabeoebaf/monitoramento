import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
import traceback
# Importação essencial para formatar números mantendo a ordenação correta
from dash.dash_table.Format import Format, Scheme, Symbol 

# --- IMPORTAÇÃO (Banco de Dados) ---
try:
    from db import ler_dados
except ImportError:
    def ler_dados(query): return pd.DataFrame()

# --- COORDENADAS (COM CORREÇÃO PARA BAIRRO DA UNIÃO) ---
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
    
    # --- VARIAÇÕES PARA GARANTIR QUE O BAIRRO DA UNIÃO APAREÇA ---
    'Bairro da União': {'lat': -3.09952, 'lon': -60.0159},
    'Bairro da Uniao': {'lat': -3.09952, 'lon': -60.0159},
    'Bairro União': {'lat': -3.09952, 'lon': -60.0159},
    'Bairro Uniao': {'lat': -3.09952, 'lon': -60.0159},
    'União': {'lat': -3.09952, 'lon': -60.0159},
    # -------------------------------------------------------------

    'Santa Etelvina': {'lat': -2.98676, 'lon': -60.01654},
    'Tarumã': {'lat': -3.00228, 'lon': -60.04581},
    'Redenção': {'lat': -3.05418, 'lon': -60.04631},
    'Compensa': {'lat': -3.11483, 'lon': -60.05759},
    'Gilberto Mestrinho': {'lat': -3.085, 'lon': -59.93}
}

# --- LIMIARES DE ALERTA (MANAUS) ---
LIMIARES = {
    'NORMAL': {'min': 0, 'max': 9.99, 'cor': '#2ecc71', 'cor_texto': '#2c3e50', 'icone': 'fa-cloud-sun'},
    'OBSERVAÇÃO': {'min': 10, 'max': 29.99, 'cor': '#f1c40f', 'cor_texto': '#2c3e50', 'icone': 'fa-cloud-rain'},
    'ATENÇÃO': {'min': 30, 'max': 69.99, 'cor': '#e67e22', 'cor_texto': '#ffffff', 'icone': 'fa-bolt'},
    'CRÍTICO': {'min': 70, 'max': 9999, 'cor': '#e74c3c', 'cor_texto': '#ffffff', 'icone': 'fa-house-flood-water'}
}

def get_nivel_alerta(valor):
    if valor >= 70: return 'CRÍTICO'
    if valor >= 30: return 'ATENÇÃO'
    if valor >= 10: return 'OBSERVAÇÃO'
    return 'NORMAL'

# --- FUNÇÕES AUXILIARES ---
def limpar_nome_estacao(nome_sujo):
    if not isinstance(nome_sujo, str): return str(nome_sujo)
    nome = nome_sujo.replace("CEMADEN - ", "")
    nome = re.sub(r'\s*[\(\[].*?[\)\]]', '', nome)
    # Remove espaços duplos e nas pontas (Isso ajuda no mapa!)
    return " ".join(nome.split())

def get_color_code(v):
    nivel = get_nivel_alerta(v)
    return LIMIARES[nivel]['cor']

def get_categoria_status(v):
    return get_nivel_alerta(v)

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

# --- FUNÇÃO DE DESTAQUE ---
def criar_divisoria(titulo, icone, cor="text-primary"):
    return html.Div([
        html.H5([html.I(className=f"{icone} me-2"), titulo], 
                className=f"fw-bold text-uppercase mt-4 mb-2 {cor}", 
                style={"fontSize": "0.9rem", "letterSpacing": "1px"}),
        html.Hr(className="mt-0 mb-4", style={"opacity": "0.15"})
    ])

GRAPH_CONFIG = {
    'displayModeBar': True,
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

            # --- 1. TABELA DE RANKING (COM DESTAQUE VISUAL FORTE) ---
            ranking_df = ultimas.sort_values('chuva_24h', ascending=False).reset_index(drop=True)
            ranking_df['rank'] = ranking_df.index + 1
            ranking_df['status_desc'] = ranking_df['chuva_24h'].apply(get_nivel_alerta)

            # Seleciona e ordena as colunas (MANTENDO NUMÉRICO PARA O DASH)
            tabela_data = ranking_df[['rank', 'nome_limpo', 'chuva_24h', 'status_desc', 'chuva_1h', 'chuva_6h']].to_dict('records')

            # Formatadores Visuais
            fmt_int = Format(precision=0, scheme=Scheme.fixed)
            fmt_dec = Format(precision=1, scheme=Scheme.fixed).symbol(Symbol.yes).symbol_suffix(' mm')

            tabela_ranking = dash_table.DataTable(
                data=tabela_data,
                columns=[
                    {'name': '#', 'id': 'rank', 'type': 'numeric', 'format': fmt_int},
                    {'name': 'Estação', 'id': 'nome_limpo', 'type': 'text'},
                    {'name': 'Acum. 24h', 'id': 'chuva_24h', 'type': 'numeric', 'format': fmt_dec},
                    {'name': 'Status', 'id': 'status_desc', 'type': 'text'},
                    {'name': '1h', 'id': 'chuva_1h', 'type': 'numeric', 'format': fmt_dec},
                    {'name': '6h', 'id': 'chuva_6h', 'type': 'numeric', 'format': fmt_dec},
                ],
                page_size=10,
                sort_action='native',
                style_as_list_view=True,
                
                # Estilo Geral
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'color': '#4a5568', 'borderBottom': '2px solid #e2e8f0', 'textAlign': 'center', 'fontSize': '12px'},
                style_cell={'padding': '10px', 'fontFamily': 'Inter, sans-serif', 'fontSize': '13px', 'color': '#2d3748', 'borderBottom': '1px solid #edf2f7'},
                
                # Ajuste de Largura
                style_cell_conditional=[
                    {'if': {'column_id': 'rank'}, 'width': '40px', 'textAlign': 'center', 'color': '#a0aec0'},
                    {'if': {'column_id': 'nome_limpo'}, 'textAlign': 'left', 'fontWeight': '600'},
                    {'if': {'column_id': 'chuva_24h'}, 'textAlign': 'center', 'fontWeight': 'bold'},
                    {'if': {'column_id': 'status_desc'}, 'textAlign': 'center', 'width': '110px'},
                    {'if': {'column_id': 'chuva_1h'}, 'textAlign': 'center', 'color': '#718096'},
                    {'if': {'column_id': 'chuva_6h'}, 'textAlign': 'center', 'color': '#718096'},
                ],

                # --- AQUI ESTÁ A MÁGICA DO DESTAQUE ---
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#ffffff'}, # Fundo padrão
                    {'if': {'row_index': 'even'}, 'backgroundColor': '#fcfcfc'}, # Fundo alternado

                    # 1. DESTAQUE NA COLUNA DE VALOR (Fundo Pastel)
                    # Crítico (>70)
                    {
                        'if': {'filter_query': '{chuva_24h} >= 70', 'column_id': 'chuva_24h'},
                        'backgroundColor': '#fed7d7', 'color': '#c53030' 
                    },
                    # Atenção (30-70)
                    {
                        'if': {'filter_query': '{chuva_24h} >= 30 && {chuva_24h} < 70', 'column_id': 'chuva_24h'},
                        'backgroundColor': '#feebc8', 'color': '#c05621' 
                    },
                    # Observação (10-30)
                    {
                        'if': {'filter_query': '{chuva_24h} >= 10 && {chuva_24h} < 30', 'column_id': 'chuva_24h'},
                        'backgroundColor': '#fefcbf', 'color': '#744210' 
                    },
                    # Normal (<10)
                    {
                        'if': {'filter_query': '{chuva_24h} < 10', 'column_id': 'chuva_24h'},
                        'color': '#2f855a' 
                    },

                    # 2. DESTAQUE NA COLUNA STATUS (Badge Sólida)
                    # Crítico
                    {
                        'if': {'filter_query': '{status_desc} = "CRÍTICO"', 'column_id': 'status_desc'},
                        'backgroundColor': '#e53e3e', 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '4px'
                    },
                    # Atenção
                    {
                        'if': {'filter_query': '{status_desc} = "ATENÇÃO"', 'column_id': 'status_desc'},
                        'backgroundColor': '#dd6b20', 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '4px'
                    },
                    # Observação
                    {
                        'if': {'filter_query': '{status_desc} = "OBSERVAÇÃO"', 'column_id': 'status_desc'},
                        'backgroundColor': '#d69e2e', 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '4px'
                    },
                    # Normal
                    {
                        'if': {'filter_query': '{status_desc} = "NORMAL"', 'column_id': 'status_desc'},
                        'backgroundColor': '#c6f6d5', 'color': '#22543d', 'fontWeight': 'bold', 'borderRadius': '4px'
                    },
                ]
            )

            # --- 2. MAPA ---
            ultimas['lat'] = ultimas['nome_limpo'].map(lambda x: COORDENADAS_CEMADEN.get(x, {}).get('lat'))
            ultimas['lon'] = ultimas['nome_limpo'].map(lambda x: COORDENADAS_CEMADEN.get(x, {}).get('lon'))
            df_mapa = ultimas.dropna(subset=['lat', 'lon']).copy()
            
            if not df_mapa.empty:
                df_mapa['txt_mapa'] = df_mapa['chuva_24h'].apply(lambda x: f"{x:.0f}")
                df_mapa['status'] = df_mapa['chuva_24h'].apply(get_categoria_status)
                color_map = {"CRÍTICO": "#e74c3c", "ATENÇÃO": "#e67e22", "OBSERVAÇÃO": "#f1c40f", "NORMAL": "#2ecc71"}

                fig_mapa = px.scatter_mapbox(
                    df_mapa, lat="lat", lon="lon", hover_name="nome_limpo",
                    hover_data={'lat': False, 'lon': False, 'chuva_1h': ':.1f', 'chuva_6h': ':.1f', 'chuva_24h': ':.1f'},
                    text="txt_mapa", color="status", color_discrete_map=color_map,
                    size=[30]*len(df_mapa), zoom=10.7, center={"lat": -3.065, "lon": -59.95},
                    mapbox_style="open-street-map"
                )
                fig_mapa.update_traces(mode='markers+text', textposition='middle center', textfont=dict(size=12, color='black', weight='bold'))
                fig_mapa.update_layout(
                    margin={"r":0,"t":0,"l":0,"b":0},
                    legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="center", x=0.5, bgcolor="rgba(255,255,255,0.9)", title="")
                )
            else: fig_mapa = fig_empty

            # --- 3. CARDS ---
            cards = []
            for _, row in ultimas.iterrows():
                v24 = row['chuva_24h']
                nivel = get_nivel_alerta(v24)
                config = LIMIARES[nivel]
                
                # Estilo Visual Cards
                card_style = {"borderLeft": f"5px solid {config['cor']}", "borderRadius": "12px", "backgroundColor": "white", "transition": "all 0.3s ease", "position": "relative", "overflow": "hidden"}
                texto_classe, icon_opacity, icon_color, subtexto_style = "text-dark", "0.15", config['cor'], {"color": "#6c757d"}
                
                if nivel in ['CRÍTICO', 'ATENÇÃO']:
                    card_style.update({"background": f"linear-gradient(135deg, {config['cor']} 0%, {config['cor']}dd 100%)", "border": "none"})
                    texto_classe, icon_opacity, icon_color, subtexto_style = "text-white", "0.25", "white", {"color": "rgba(255,255,255,0.8)"}

                cards.append(dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.I(className=f"fas {config['icone']}", style={"position": "absolute", "right": "10px", "top": "50%", "transform": "translateY(-50%)", "fontSize": "4rem", "opacity": icon_opacity, "color": icon_color}),
                        html.Div([
                            html.H6(row['nome_limpo'], className=f"text-uppercase fw-bold mb-1 {texto_classe}", style={"fontSize": "0.8rem", "position": "relative", "zIndex": 1}),
                            html.Div([html.Span(f"{v24:.1f}", className=f"fw-bold display-6 {texto_classe}"), html.Small(" mm", className="ms-1 fs-6", style=subtexto_style)], style={"position": "relative", "zIndex": 1}),
                            html.Div([html.Div(style={"height": "5px", "width": f"{min(v24, 100)}%", "backgroundColor": "white" if nivel in ['CRÍTICO', 'ATENÇÃO'] else config['cor'], "borderRadius": "3px", "opacity": "0.9"})], style={"width": "100%", "backgroundColor": "rgba(0,0,0,0.1)", "height": "5px", "borderRadius": "3px", "marginTop": "10px", "position": "relative", "zIndex": 1}),
                            html.Div([html.Span(f"1h: {row['chuva_1h']:.1f}mm", className="me-3"), html.Span(f"6h: {row['chuva_6h']:.1f}mm")], className="mt-3 small fw-bold", style=subtexto_style)
                        ])
                    ], className="p-3")
                ], className="shadow-sm h-100 border-0", style=card_style), width=12, md=6, lg=3, className="mb-3"))

            # --- 4. GRÁFICO GERAL ---
            fig_bar = px.bar(ranking_df, x="nome_limpo", y="chuva_24h", text="chuva_24h")
            fig_bar.update_traces(marker_color=[get_color_code(v) for v in ranking_df['chuva_24h']], texttemplate='%{text:.1f}', textposition='outside', cliponaxis=False)
            fig_bar = style_fig(fig_bar, "Acumulado Total 24h (mm)")
            fig_bar.update_layout(xaxis={'categoryorder':'total descending'}, yaxis=dict(title="Milímetros (mm)"), xaxis_title=None)
            fig_bar.add_hline(y=30, line_dash="dot", line_color="#e67e22", annotation_text="Atenção (30mm)", annotation_position="top right", opacity=0.7)

            return options, tabela_ranking, fig_mapa, cards, fig_bar 

        except Exception as e:
            traceback.print_exc()
            return empty_return
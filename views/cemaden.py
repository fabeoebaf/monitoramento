import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta

# --- IMPORTAÇÃO NOVA (Conecta no Supabase/Render) ---
from db import ler_dados

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

# --- FUNÇÕES AUXILIARES DE LÓGICA ---
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

# --- FUNÇÕES VISUAIS ---
def style_fig(fig, title):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, color="#7f8c8d")),
        title_x=0.0,
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        font=dict(family="Segoe UI, sans-serif", color="#555")
    )
    fig.update_xaxes(showgrid=False, linecolor='#eee')
    fig.update_yaxes(showgrid=True, gridcolor='#f0f2f5', zeroline=False)
    return fig

GRAPH_CONFIG = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoScale2d'],
    'toImageButtonOptions': {'format': 'png', 'filename': 'grafico_cemaden', 'height': 500, 'width': 800, 'scale': 2}
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
        ], width=8),
        dbc.Col([
            dcc.Dropdown(id='filtro-cemaden', placeholder="Filtrar por Bairro...", className="mb-2 shadow-sm", style={"borderRadius": "20px"}),
            html.Div(id="timer-cemaden", className="text-end text-white fw-bold font-monospace small")
        ], width=4, className="d-flex flex-column justify-content-center")
    ], className="py-3 px-3 mb-4 rounded-3 shadow-sm", style={"background": "linear-gradient(90deg, #2980b9 0%, #2c3e50 100%)", "marginTop": "-10px"}),

    # 2. MAPA E TABELA
    dbc.Row([
        # Coluna 1: Mapa
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-map-marked-alt me-2"), "Distribuição Espacial"], className="bg-white fw-bold border-bottom-0"),
                dbc.CardBody(
                    dcc.Graph(id='mapa-cemaden', style={"height": "460px"}, config=GRAPH_CONFIG),
                    className="p-0 overflow-hidden", style={"borderRadius": "0 0 12px 12px"}
                )
            ], className="shadow-sm border-0 h-100")
        ], width=12, lg=6, className="mb-4"),

        # Coluna 2: Tabela de Ranking
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-list-ol me-2"), "Ranking de Chuva (24h)"], className="bg-white fw-bold border-bottom-0"),
                dbc.CardBody(id="tabela-ranking-cemaden", className="p-0", style={"overflow": "hidden", "borderRadius": "0 0 12px 12px"})
            ], className="shadow-sm border-0 h-100")
        ], width=12, lg=6, className="mb-4"),
    ]),

    # 3. CARDS DE DETALHE
    html.H6("📡 Status Detalhado por Estação", className="text-muted fw-bold text-uppercase mb-3 ms-1 mt-2"),
    dbc.Row(id="cards-cemaden", className="mb-4"),

    # 4. GRÁFICO GERAL
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-cemaden-geral', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, className="mb-4"),
    ]),
    
    dcc.Interval(id='cemaden-refresh', interval=60*1000, n_intervals=0),
    dcc.Interval(id='timer-regressivo', interval=1000, n_intervals=0)
], className="px-4 py-3")


# --- CALLBACKS ---
def register_callbacks(app):
    
    @app.callback(Output('timer-cemaden', 'children'), [Input('timer-regressivo', 'n_intervals')])
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
        fig_empty.update_layout(template="plotly_white")
        
        # --- CONEXÃO NOVA (DB.PY) ---
        # Busca tudo e filtra data no Pandas para compatibilidade total
        query = "SELECT * FROM cemaden ORDER BY data_hora ASC"
        
        df = ler_dados(query)

        if df.empty:
            return [], html.Div("Sem dados recentes.", className="alert alert-warning m-3"), fig_empty, [], fig_empty

        # Filtro de Data (Últimas 24h) via Python
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        agora = datetime.now()
        inicio_24h = agora - timedelta(days=1)
        df = df[df['data_hora'] >= inicio_24h]

        if df.empty:
             return [], html.Div("Sem dados nas últimas 24h.", className="alert alert-warning m-3"), fig_empty, [], fig_empty

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

        # --- 1. TABELA ---
        ranking_df = ultimas.sort_values('chuva_24h', ascending=False)
        tabela_cols = ranking_df[['nome_limpo', 'chuva_1h', 'chuva_6h', 'chuva_24h']].copy()
        tabela_cols.columns = ['Estação', '1h', '6h', '24h']

        style_data_conditional = [
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#fcfcfc'},
            {'if': {'filter_query': '{24h} >= 10 && {24h} < 30', 'column_id': '24h'}, 'backgroundColor': '#f1c40f', 'color': 'black', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{24h} >= 30 && {24h} < 70', 'column_id': '24h'}, 'backgroundColor': '#e67e22', 'color': 'white', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{24h} >= 70', 'column_id': '24h'}, 'backgroundColor': '#e74c3c', 'color': 'white', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{24h} < 10', 'column_id': '24h'}, 'backgroundColor': '#e8f5e9', 'color': '#2e7d32', 'fontWeight': 'bold'}
        ]

        tabela_ranking = dash_table.DataTable(
            data=tabela_cols.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in tabela_cols.columns],
            page_size=8,
            style_as_list_view=True,
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
            style_cell={'textAlign': 'center', 'padding': '12px', 'fontFamily': 'Segoe UI'},
            style_data_conditional=style_data_conditional
        )

        # --- 2. MAPA ---
        ultimas['lat'] = ultimas['nome_limpo'].map(lambda x: COORDENADAS_CEMADEN.get(x, {}).get('lat'))
        ultimas['lon'] = ultimas['nome_limpo'].map(lambda x: COORDENADAS_CEMADEN.get(x, {}).get('lon'))
        df_map = ultimas.dropna(subset=['lat', 'lon']).copy()
        
        if not df_map.empty:
            df_map['status'] = df_map['chuva_24h'].apply(get_categoria_status)
            df_map['rotulo'] = df_map['chuva_24h'].apply(lambda x: f"{x:.0f}")
            
            color_map = {"CRÍTICO": "#e74c3c", "ATENÇÃO": "#e67e22", "OBSERVAÇÃO": "#f1c40f", "NORMAL": "#2ecc71"}

            fig_mapa = px.scatter_mapbox(
                df_map, lat="lat", lon="lon", hover_name="nome_limpo",
                color="status", color_discrete_map=color_map,
                size=[25]*len(df_map), zoom=10.6, center={"lat": -3.06, "lon": -59.99},
                mapbox_style="open-street-map"
            )
            fig_mapa.update_traces(
                text=df_map['rotulo'], mode='markers+text', textposition='top center',
                textfont=dict(family="Arial Black", size=14, color='black'), marker=dict(opacity=0.9)
            )
            fig_mapa.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="center", x=0.5, bgcolor="rgba(255,255,255,0.9)")
            )
        else:
            fig_mapa = fig_empty

        # --- 3. CARDS ---
        cards = []
        for _, row in ultimas.iterrows():
            v24 = row['chuva_24h']
            cor = get_color_code(v24)
            
            card_style = {"borderLeft": f"4px solid {cor}", "borderRadius": "8px", "transition": "transform 0.2s"}
            body_class = ""
            text_color = "#2c3e50"
            badge_class = "badge bg-light text-dark border me-1"
            
            if v24 >= 10:
                card_style["backgroundColor"] = cor
                text_color = "white"
                body_class = "text-white"
                badge_class = "badge bg-white text-dark border me-1 opacity-75"
                icon = html.I(className="fas fa-exclamation-triangle position-absolute top-0 end-0 m-3 opacity-50 fa-2x text-white")
            else:
                icon = html.Div()

            card = dbc.Col(dbc.Card([
                dbc.CardBody([
                    icon,
                    html.H6(row['nome_limpo'], className=f"text-uppercase fw-bold mb-2 {body_class}", style={"fontSize": "0.7rem", "color": text_color if v24 < 10 else "white"}),
                    html.Div([
                        html.Span(f"{v24:.1f}", className="fw-bold fs-2", style={"color": text_color}),
                        html.Small(" mm (24h)", className=f"ms-1 {body_class}", style={"color": text_color if v24 < 10 else "rgba(255,255,255,0.8)"})
                    ]),
                    html.Div([
                        html.Span(f"1h: {row['chuva_1h']:.1f}", className=badge_class),
                        html.Span(f"6h: {row['chuva_6h']:.1f}", className=badge_class)
                    ], className="mt-2")
                ])
            ], className=f"shadow-sm h-100 border-0", style=card_style), width=12, md=4, lg=3, className="mb-3")
            cards.append(card)

        # --- 4. GRÁFICO GERAL ---
        cores_barras = ultimas['chuva_24h'].apply(get_color_code).tolist()
        fig_bar = px.bar(ultimas, x="nome_limpo", y="chuva_24h", text="chuva_24h")
        fig_bar.update_traces(marker_color=cores_barras, texttemplate='%{text:.1f}', textposition='outside', cliponaxis=False)
        fig_bar = style_fig(fig_bar, "Acumulado Total 24h (mm)")

        return options, tabela_ranking, fig_mapa, cards, fig_bar
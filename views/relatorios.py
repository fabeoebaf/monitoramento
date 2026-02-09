import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# --- IMPORTAÇÃO NOVA (Conecta no Supabase/Render) ---
from db import ler_dados

# --- FUNÇÕES AUXILIARES ---
def get_stations(source):
    """Busca lista de estações disponíveis no banco baseado na fonte"""
    try:
        table = 'cemaden' if source == 'cemaden' else 'defesa_civil'
        query = f"SELECT DISTINCT nome_estacao FROM {table} ORDER BY nome_estacao"
        
        # Usa db.py
        df = ler_dados(query)
        
        if df.empty: return []
        return [{'label': s, 'value': s} for s in df['nome_estacao']]
    except Exception as e:
        print(f"Erro ao buscar estações: {e}")
        return []

def get_data(source, stations, start_date, end_date, freq):
    """Busca e agrega os dados para o relatório"""
    try:
        table = 'cemaden' if source == 'cemaden' else 'defesa_civil'
        
        if not stations: return pd.DataFrame()
        
        # TRUQUE DE COMPATIBILIDADE SQLITE/POSTGRES:
        # Em vez de usar ? ou %s, formatamos a string direto no Python.
        # Transforma a lista ['Estacao A', 'Estacao B'] na string "'Estacao A', 'Estacao B'"
        stations_str = ", ".join([f"'{s}'" for s in stations])
        
        query = f"""
        SELECT * FROM {table} 
        WHERE nome_estacao IN ({stations_str}) 
        AND data_hora BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
        ORDER BY data_hora ASC
        """
        
        # Usa db.py
        df = ler_dados(query)
        
        if df.empty: return df

        # Tratamento de Dados
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        cols_num = ['chuva_mm', 'temp_ar', 'umidade', 'vento_vel', 'chuva_24h']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')

        # Agregação (Resample)
        if freq == 'D': # Diário
            df.set_index('data_hora', inplace=True)
            
            # Define dicionário de agregação dinâmico (só agrega colunas que existem)
            agg_dict = {'chuva_mm': 'sum'}
            if 'temp_ar' in df.columns: agg_dict['temp_ar'] = 'mean'
            if 'umidade' in df.columns: agg_dict['umidade'] = 'mean'
            if 'vento_vel' in df.columns: agg_dict['vento_vel'] = 'max'
            
            # Agrupa
            df_grouped = df.groupby('nome_estacao').resample('D').agg(agg_dict).reset_index()
            
            # Remove dias vazios
            return df_grouped.dropna(subset=['chuva_mm'], how='all')
            
        return df # Retorna horário original
        
    except Exception as e:
        print(f"Erro SQL: {e}")
        return pd.DataFrame()

# --- LAYOUT ---
layout = dbc.Container(fluid=True, children=[
    
    dbc.Row([
        dbc.Col([
            html.H4([html.I(className="fas fa-file-alt me-2"), "Gerador de Relatórios e Figuras"], className="fw-bold text-primary mb-0"),
            html.Small("Extração de dados históricos e geração de gráficos para boletins.", className="text-muted")
        ], width=12)
    ], className="my-3"),

    dbc.Row([
        # --- COLUNA DE CONTROLES (LATERAL ESQUERDA) ---
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🛠️ Configuração", className="bg-white fw-bold"),
                dbc.CardBody([
                    
                    # 1. Fonte de Dados
                    html.Label("Fonte de Dados:", className="fw-bold small"),
                    dcc.Dropdown(
                        id='rel-source',
                        options=[
                            {'label': 'Defesa Civil (Telemetria)', 'value': 'defesa'},
                            {'label': 'CEMADEN (Nacional)', 'value': 'cemaden'}
                        ],
                        value='defesa',
                        clearable=False,
                        className="mb-3"
                    ),

                    # 2. Período
                    html.Label("Período de Análise:", className="fw-bold small"),
                    dcc.DatePickerRange(
                        id='rel-dates',
                        start_date=(datetime.now() - timedelta(days=7)).date(),
                        end_date=datetime.now().date(),
                        display_format='DD/MM/YYYY',
                        className="mb-3 w-100",
                        style={'zIndex': 1000}
                    ),

                    # 3. Estações
                    html.Label("Selecione as Estações:", className="fw-bold small"),
                    dcc.Dropdown(id='rel-stations', multi=True, placeholder="Escolha uma ou mais...", className="mb-3"),

                    # 4. Variável
                    html.Label("Variável Principal:", className="fw-bold small"),
                    dcc.Dropdown(
                        id='rel-variable',
                        options=[
                            {'label': 'Chuva (mm)', 'value': 'chuva_mm'},
                            {'label': 'Temperatura (°C)', 'value': 'temp_ar'},
                            {'label': 'Umidade (%)', 'value': 'umidade'},
                            {'label': 'Vento (m/s)', 'value': 'vento_vel'}
                        ],
                        value='chuva_mm',
                        clearable=False,
                        className="mb-3"
                    ),

                    # 5. Agregação
                    html.Label("Agregação Temporal:", className="fw-bold small"),
                    dbc.RadioItems(
                        id='rel-freq',
                        options=[
                            {'label': 'Horário (Original)', 'value': 'H'},
                            {'label': 'Diário (Acumulado/Média)', 'value': 'D'}
                        ],
                        value='H',
                        className="mb-3"
                    ),

                    # Botão Gerar
                    dbc.Button([html.I(className="fas fa-sync-alt me-2"), "Atualizar Gráfico"], id='btn-update-rel', color="primary", className="w-100 mb-2"),
                    
                    # Botão Download Dados
                    dbc.Button([html.I(className="fas fa-file-csv me-2"), "Baixar CSV"], id='btn-download-csv', color="success", outline=True, className="w-100"),
                    dcc.Download(id="download-dataframe-csv"),

                ])
            ], className="shadow-sm border-0 h-100")
        ], width=12, lg=3, className="mb-4"),

        # --- COLUNA DE VISUALIZAÇÃO (DIREITA) ---
        dbc.Col([
            # Gráfico
            dbc.Card([
                dbc.CardBody([
                    dcc.Loading(
                        dcc.Graph(
                            id='rel-graph', 
                            style={"height": "500px"},
                            # Configuração para download em Alta Resolução
                            config={
                                'displayModeBar': True,
                                'toImageButtonOptions': {
                                    'format': 'png', 'filename': 'figura_monitoramento',
                                    'height': 600, 'width': 1000, 'scale': 3 # <--- 300 DPI (Qualidade de Artigo)
                                }
                            }
                        ),
                        type="dot"
                    )
                ])
            ], className="shadow-sm border-0 mb-4"),

            # Tabela de Resumo Estatístico
            dbc.Card([
                dbc.CardHeader("📊 Resumo Estatístico do Período", className="bg-light fw-bold small"),
                dbc.CardBody(id='rel-stats-table', className="p-0")
            ], className="shadow-sm border-0")

        ], width=12, lg=9)
    ])
])

# --- CALLBACKS ---
def register_callbacks(app):
    
    # 1. Atualiza lista de estações quando muda a fonte
    @app.callback(
        Output('rel-stations', 'options'),
        Input('rel-source', 'value')
    )
    def update_stations_list(source):
        return get_stations(source)

    # 2. Gera o Gráfico e a Tabela
    @app.callback(
        [Output('rel-graph', 'figure'),
         Output('rel-stats-table', 'children')],
        [Input('btn-update-rel', 'n_clicks')],
        [State('rel-source', 'value'),
         State('rel-stations', 'value'),
         State('rel-dates', 'start_date'),
         State('rel-dates', 'end_date'),
         State('rel-variable', 'value'),
         State('rel-freq', 'value')]
    )
    def update_report(n, source, stations, start, end, var, freq):
        if not stations:
            fig_empty = px.scatter(title="Selecione pelo menos uma estação").update_layout(template="plotly_white")
            return fig_empty, html.Div("Sem dados", className="p-3 text-muted")

        df = get_data(source, stations, start, end, freq)
        
        if df.empty:
            fig_empty = px.scatter(title="Nenhum dado encontrado neste período").update_layout(template="plotly_white")
            return fig_empty, html.Div("Sem dados no período", className="p-3 text-muted")

        # Configuração do Gráfico
        nome_var = var.replace('_', ' ').title()
        coluna_tempo = 'data_hora' if 'data_hora' in df.columns else 'data_hora' 
        
        if freq == 'D':
            titulo = f"Evolução Diária - {nome_var} ({datetime.strptime(start, '%Y-%m-%d').strftime('%d/%m')} a {datetime.strptime(end, '%Y-%m-%d').strftime('%d/%m')})"
            modo = 'lines+markers'
        else:
            titulo = f"Monitoramento Horário - {nome_var}"
            modo = 'lines'

        # Se for chuva, melhor usar Barras
        if 'chuva' in var:
            fig = px.bar(df, x=coluna_tempo, y=var, color='nome_estacao', barmode='group', title=titulo)
        else:
            fig = px.line(df, x=coluna_tempo, y=var, color='nome_estacao', title=titulo)
            fig.update_traces(mode=modo)

        # Estilo "Artigo Científico"
        fig.update_layout(
            template="plotly_white",
            font=dict(family="Arial", size=12, color="black"),
            legend=dict(orientation="h", y=-0.15, title=None), # Legenda embaixo
            margin=dict(l=40, r=20, t=60, b=40),
            xaxis_title=None,
            yaxis_title=nome_var,
            hovermode="x unified"
        )
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

        # Tabela de Resumo
        stats = df.groupby('nome_estacao')[var].describe().reset_index()
        stats = stats[['nome_estacao', 'count', 'mean', 'min', 'max']]
        stats['sum'] = df.groupby('nome_estacao')[var].sum().values 
        
        # Formatação
        stats = stats.round(1)
        
        table_header = [
            html.Thead(html.Tr([html.Th("Estação"), html.Th("Média"), html.Th("Max"), html.Th("Total (Soma)")]))
        ]
        table_body = [
            html.Tbody([
                html.Tr([
                    html.Td(row['nome_estacao'], className="fw-bold"),
                    html.Td(row['mean']),
                    html.Td(row['max']),
                    html.Td(row['sum'], className="text-primary fw-bold" if 'chuva' in var else "")
                ]) for _, row in stats.iterrows()
            ])
        ]
        
        return fig, dbc.Table(table_header + table_body, bordered=True, hover=True, striped=True, className="mb-0")

    # 3. Download CSV
    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("btn-download-csv", "n_clicks"),
        [State('rel-source', 'value'),
         State('rel-stations', 'value'),
         State('rel-dates', 'start_date'),
         State('rel-dates', 'end_date'),
         State('rel-freq', 'value')]
    )
    def download_csv(n, source, stations, start, end, freq):
        if not n or not stations: return dash.no_update
        
        df = get_data(source, stations, start, end, freq)
        
        fname = f"dados_{source}_{start}_{end}.csv"
        return dcc.send_data_frame(df.to_csv, fname, index=False)
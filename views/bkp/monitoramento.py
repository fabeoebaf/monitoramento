import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import numpy as np
import os
from datetime import datetime

# Pega o diretório onde o arquivo atual está e sobe um nível para achar a raiz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'monitoramento.db')

COORDENADAS = {
    'EST_SEMULSP': {'lat': -3.1089, 'lon': -60.0548},
    'EST_MINDU': {'lat': -3.0780, 'lon': -60.0070},
    'ANNA RAYMUNDA': {'lat': -2.9750, 'lon': -60.0080},
    'EST_PONTA_NEGRA': {'lat': -3.0624, 'lon': -60.1044}
}

# --- FUNÇÕES AUXILIARES DE LÓGICA ---
def calcular_sensacao(t, rh):
    try:
        return t + 0.5555 * (6.11 * np.exp(5417.7530 * (1/273.16 - 1/(273.15 + t))) * (rh/100) - 10)
    except:
        return t

def get_color_code(v):
    if v > 70: return '#e74c3c'  # Vermelho
    if v >= 30: return '#e67e22' # Laranja
    if v >= 10: return '#f1c40f' # Amarelo
    return '#2ecc71'             # Verde

def get_categoria_status(v):
    if v > 70: return "CRÍTICO (>70mm)"
    if v >= 30: return "ATENÇÃO (30-70mm)"
    if v >= 10: return "OBSERVAÇÃO (10-30mm)"
    return "NORMAL (<10mm)"

# --- FUNÇÕES AUXILIARES VISUAIS ---
def style_fig(fig, title):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, color="#7f8c8d")),
        title_x=0.0,
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        font=dict(family="Segoe UI, sans-serif", color="#555"),
        showlegend=True 
    )
    fig.update_xaxes(showgrid=False, linecolor='#eee')
    fig.update_yaxes(showgrid=True, gridcolor='#f0f2f5', zeroline=False)
    return fig

def criar_card_estiloso(titulo, valor, unidade, cor, icone, subtexto="", width=2):
    return dbc.Col(dbc.Card([
        dbc.CardBody([
            html.I(className=f"{icone}", style={
                "position": "absolute", "right": "10px", "top": "10px",
                "fontSize": "2rem", "opacity": "0.4", "color": cor
            }),
            html.H6(titulo, className="text-muted text-uppercase fw-bold mb-2", style={"fontSize": "0.65rem"}),
            html.H4([
                f"{valor}",
                html.Small(unidade, className="text-muted fs-6 ms-1")
            ], className="fw-bold mb-0", style={"color": "#2c3e50", "fontSize": "1.2rem"}),
            html.Small(subtexto, className="text-muted mt-2 d-block", style={"fontSize": "0.65rem"}),
        ], className="p-3")
    ], className="shadow-sm h-100 border-0", style={"borderLeft": f"4px solid {cor}", "borderRadius": "8px"}), 
    width=12, md=4, lg=width, className="mb-3")

GRAPH_CONFIG = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoScale2d'],
    'toImageButtonOptions': {'format': 'png', 'filename': 'grafico_monitoramento', 'height': 500, 'width': 800, 'scale': 2}
}

# --- LAYOUT ---
layout = dbc.Container(fluid=True, children=[
    
    # 1. CABEÇALHO
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H4([html.I(className="fas fa-satellite-dish me-2"), "Centro de Monitoramento"], className="fw-bold text-white mb-0"),
                html.Small("Defesa Civil de Manaus | Dados em Tempo Real (24h)", className="text-white-50")
            ])
        ], width=8),
        dbc.Col([
            dcc.Dropdown(id='filtro-estacao', placeholder="Filtrar por Estação...", className="mb-2 shadow-sm", style={"borderRadius": "20px"}),
            html.Div(id="timer-display", className="text-end text-white fw-bold font-monospace small")
        ], width=4, className="d-flex flex-column justify-content-center")
    ], className="py-3 px-3 mb-4 rounded-3 shadow-sm", style={"background": "linear-gradient(90deg, #2c3e50 0%, #34495e 100%)", "marginTop": "-10px"}),

    # 2. EXTREMOS
    html.H6("Destaques Climáticos (Últimas 24h)", className="text-muted fw-bold text-uppercase mb-3 ms-1"),
    html.Div(id="linha-extremos"),

    # 3. MAPA E MÉDIAS
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-map-marked-alt me-2"), "Geolocalização e Alertas"], className="bg-white fw-bold border-bottom-0"),
                dbc.CardBody(
                    dcc.Graph(id='mapa-estacoes', style={"height": "500px"}, config=GRAPH_CONFIG), # Aumentei altura para caber legenda
                    className="p-0 overflow-hidden", style={"borderRadius": "0 0 12px 12px"}
                )
            ], className="shadow-sm border-0 h-100")
        ], width=12, lg=5, className="mb-4"),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-chart-bar me-2"), "Resumo por Estação"], className="bg-white fw-bold border-bottom-0"),
                dbc.CardBody(id="cards-medias", className="p-3", style={"maxHeight": "500px", "overflowY": "auto"})
            ], className="shadow-sm border-0 h-100")
        ], width=12, lg=7, className="mb-4"),
    ]),

    # 4. WATCHDOG
    html.H6("📡 Telemetria em Tempo Real (Watchdog)", className="text-muted fw-bold text-uppercase mb-3 ms-1 mt-2"),
    dbc.Row(id="cards-atuais", className="mb-4"),

    # 5. GRÁFICOS
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-temperatura', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-umidade', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-chuva-tempo', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-chuva-acumulado', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-pressao', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-rosa-ventos', config=GRAPH_CONFIG), className="shadow-sm border-0 p-2"), width=12, lg=6, className="mb-4"),
    ]),

    # 6. TABELA
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-table me-2"), "Log de Dados (Últimos 15 registros)"], className="bg-white fw-bold"),
                dbc.CardBody(
                    dash_table.DataTable(
                        id='tabela-auditoria',
                        page_size=10,
                        style_as_list_view=True,
                        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                        style_cell={'textAlign': 'center', 'padding': '12px', 'fontFamily': 'Segoe UI'},
                        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#fcfcfc'}]
                    )
                )
            ], className="shadow-sm border-0 mb-5")
        )
    ]),

    dcc.Interval(id='data-refresh', interval=60*1000, n_intervals=0),
    dcc.Interval(id='timer-interval', interval=1000, n_intervals=0)
], className="px-4 py-2")

# --- CALLBACKS ---
def register_callbacks(app):

    @app.callback(Output('timer-display', 'children'), [Input('timer-interval', 'n_intervals')])
    def update_timer(n):
        now = datetime.now()
        segundos_restantes = 59 - now.second
        return f"Atualiza em: {segundos_restantes:02d}s"

    @app.callback(
        [Output('filtro-estacao', 'options'), Output('linha-extremos', 'children'),
         Output('cards-medias', 'children'), Output('cards-atuais', 'children'),
         Output('tabela-auditoria', 'data'), Output('tabela-auditoria', 'columns'),
         Output('grafico-temperatura', 'figure'), Output('grafico-umidade', 'figure'),
         Output('grafico-chuva-tempo', 'figure'), Output('grafico-chuva-acumulado', 'figure'),
         Output('grafico-pressao', 'figure'), Output('grafico-rosa-ventos', 'figure'),
         Output('mapa-estacoes', 'figure')],
        [Input('data-refresh', 'n_intervals'), Input('filtro-estacao', 'value')]
    )
    def update_dashboard(n, est_filt):
        fig_empty = px.scatter(title="Aguardando dados...")
        fig_empty.update_layout(template="plotly_white")
        options = []

        conn = sqlite3.connect(DB_PATH)
        try:
            query = """
            SELECT * FROM defesa_civil
            WHERE data_hora >= datetime('now', '-1 day', 'localtime')
            ORDER BY data_hora ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
        except Exception as e:
            conn.close()
            print(f"Erro no Banco: {e}")
            return [options] + [None]*4 + [[], [], fig_empty, fig_empty, fig_empty, fig_empty, fig_empty, fig_empty, fig_empty]

        if df.empty:
             return [options] + [None]*4 + [[], [], fig_empty, fig_empty, fig_empty, fig_empty, fig_empty, fig_empty, fig_empty]

        cols_num = ['temp_ar', 'umidade', 'pressao', 'vento_vel', 'chuva_mm']
        for col in cols_num:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.rename(columns={'data_hora': 'tempo'}, inplace=True)
        df['tempo'] = pd.to_datetime(df['tempo'])
        df['sensacao'] = df.apply(lambda r: calcular_sensacao(r['temp_ar'], r['umidade']), axis=1)

        df_completo = df.copy()
        options = [{'label': i, 'value': i} for i in sorted(df['nome_estacao'].unique())]
        if est_filt: df = df[df['nome_estacao'] == est_filt]

        # --- 1. EXTREMOS ---
        acum_est = df_completo.groupby('nome_estacao')['chuva_mm'].sum()
        
        def get_ext_data(col, func='max'):
            if df.empty: return "-", "-", "-"
            idx = df[col].idxmax() if func == 'max' else df[col].idxmin()
            val = df.loc[idx, col]
            est = df.loc[idx, 'nome_estacao']
            hora = df.loc[idx, 'tempo'].strftime('%H:%M')
            return f"{val:.1f}", est, hora

        val_tmax, est_tmax, hora_tmax = get_ext_data('temp_ar', 'max')
        val_tmin, est_tmin, hora_tmin = get_ext_data('temp_ar', 'min')
        val_smax, est_smax, hora_smax = get_ext_data('sensacao', 'max')
        val_vmax, est_vmax, hora_vmax = get_ext_data('vento_vel', 'max')
        val_umin, est_umin, hora_umin = get_ext_data('umidade', 'min')
        val_cmax = f"{acum_est.max():.1f}"
        est_cmax = acum_est.idxmax()

        extremos = dbc.Row([
            criar_card_estiloso("Temp. Máx", val_tmax, "°C", "#e74c3c", "fas fa-temperature-high", f"{est_tmax} {hora_tmax}"),
            criar_card_estiloso("Temp. Mín", val_tmin, "°C", "#3498db", "fas fa-temperature-low", f"{est_tmin} {hora_tmin}"),
            criar_card_estiloso("Sensação Pico", val_smax, "°C", "#f39c12", "fas fa-sun", f"{est_smax} {hora_smax}"),
            criar_card_estiloso("Chuva 24h", val_cmax, "mm", "#2c3e50", "fas fa-cloud-showers-heavy", f"{est_cmax}"),
            criar_card_estiloso("Vento Máx", val_vmax, "m/s", "#95a5a6", "fas fa-wind", f"{est_vmax} {hora_vmax}"),
            criar_card_estiloso("Umid. Mín", val_umin, "%", "#e67e22", "fas fa-tint-slash", f"{est_umin} {hora_umin}"),
        ])

        # --- 2. MÉDIAS ---
        medias = df_completo.groupby('nome_estacao').agg({
            'temp_ar': 'mean', 'umidade': 'mean', 'vento_vel': 'mean', 'chuva_mm': 'sum'
        }).reset_index()
        ultimas_datas = df_completo.sort_values('tempo').groupby('nome_estacao')['tempo'].last().reset_index()
        medias = pd.merge(medias, ultimas_datas, on='nome_estacao')

        cards_medias = []
        for _, row in medias.iterrows():
            cor_chuva = get_color_code(row['chuva_mm'])
            hora_fmt = row['tempo'].strftime('%d/%m %H:%M')
            cards_medias.append(
                dbc.Row([
                    dbc.Col([
                        html.Span(row['nome_estacao'], className="fw-bold text-muted small d-block"),
                        html.Small(f"🕒 {hora_fmt}", className="text-muted", style={"fontSize": "0.65rem"})
                    ], width=4),
                    dbc.Col(html.Span(f"{row['temp_ar']:.1f}°C", className="badge bg-light text-dark border"), width=2),
                    dbc.Col(html.Span(f"{row['chuva_mm']:.1f}mm", className="badge text-white", style={"backgroundColor": cor_chuva}), width=3),
                    dbc.Col(html.Span(f"{row['vento_vel']:.1f}m/s", className="text-muted small"), width=3),
                ], className="mb-2 align-items-center border-bottom pb-1")
            )

        # --- 3. WATCHDOG ---
        ultimas = df_completo.sort_values('tempo').groupby('nome_estacao').last().reset_index()
        cards_atuais = []
        for _, row in ultimas.iterrows():
            cards_atuais.append(
                dbc.Col(dbc.Card([
                    dbc.CardHeader([
                        html.Span(row['nome_estacao'], className="fw-bold"),
                        html.Span(row['tempo'].strftime('%H:%M'), className="float-end badge bg-secondary")
                    ], className="bg-transparent border-bottom pt-3 pb-2"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([html.H4(f"{row['temp_ar']}°C", className="mb-0 text-dark"), html.Small("Temp", className="text-muted")], className="text-center border-end"),
                            dbc.Col([html.H4(f"{row['umidade']}%", className="mb-0 text-info"), html.Small("Umid", className="text-muted")], className="text-center border-end"),
                            dbc.Col([html.H4(f"{row['chuva_mm']:.1f}", className="mb-0 text-primary"), html.Small("Chuva", className="text-muted")], className="text-center"),
                        ])
                    ])
                ], className="shadow-sm h-100 border-0"), width=12, md=6, lg=3, className="mb-3")
            )

# --- 4. MAPA (CORREÇÃO DEFINITIVA DO TEXTO) ---
        df_mapa = pd.merge(ultimas, medias[['nome_estacao', 'chuva_mm']], on='nome_estacao', suffixes=('', '_total'))
        df_mapa['lat'] = df_mapa['nome_estacao'].map(lambda x: COORDENADAS.get(x, {}).get('lat'))
        df_mapa['lon'] = df_mapa['nome_estacao'].map(lambda x: COORDENADAS.get(x, {}).get('lon'))
        
        # Categorias
        df_mapa['status'] = df_mapa['chuva_mm_total'].apply(get_categoria_status)
        # O Rótulo deve ser string
        df_mapa['rotulo_chuva'] = df_mapa['chuva_mm_total'].apply(lambda x: f"{x:.1f}")

        color_map = {
            "CRÍTICO (>70mm)": "#e74c3c",
            "ATENÇÃO (30-70mm)": "#e67e22",
            "OBSERVAÇÃO (10-30mm)": "#f1c40f",
            "NORMAL (<10mm)": "#2ecc71"
        }

        fig_mapa = px.scatter_mapbox(
            df_mapa, lat="lat", lon="lon", hover_name="nome_estacao",
            color="status",
            color_discrete_map=color_map,
            text="rotulo_chuva", # <--- O PLOTLY MAPEIA SOZINHO AQUI
            size=[35]*len(df_mapa),
            zoom=10.2, center={"lat": -3.05, "lon": -60.03},
            mapbox_style="open-street-map"
        )
        
        # AQUI É O AJUSTE: NÃO passamos 'text=' de novo. Apenas ligamos o modo.
        fig_mapa.update_traces(
            mode='markers+text',       # Liga Bolinha + Texto
            textposition='middle center', # Texto NO MEIO da bolinha (Melhor leitura)
            textfont=dict(
                family="Arial Black", 
                size=14, 
                color="black" # Cor do texto
            ),
            marker=dict(opacity=0.8)
        )
        
        # Configuração da Legenda e Layout
        fig_mapa.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0}, 
            paper_bgcolor="white",
            legend=dict(
                orientation="h",
                yanchor="bottom", y=0.01,
                xanchor="center", x=0.5,
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="gray", borderwidth=1,
                title=None
            )
        )
        
        # Legenda Centralizada Embaixo
        fig_mapa.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0}, 
            paper_bgcolor="white",
            legend=dict(
                orientation="h",       # Horizontal
                yanchor="bottom", y=0.01, # Colada no fundo
                xanchor="center", x=0.5,  # Centralizada na tela
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="gray", borderwidth=1,
                title=None # Remove título da legenda para economizar espaço
            )
        )

        # --- 5. AUDITORIA ---
        df_tabela = df.tail(15).sort_values('tempo', ascending=False).copy()
        df_tabela['hora_estacao'] = df_tabela['tempo'].dt.strftime('%H:%M:%S')
        audit_data = df_tabela.to_dict('records')
        audit_cols = [{"name": i, "id": j} for i, j in [("Estação", "nome_estacao"), ("Hora", "hora_estacao"), ("Temp (°C)", "temp_ar"), ("Umid (%)", "umidade"), ("Chuva (mm)", "chuva_mm")]]

        # --- 6. GRÁFICOS ---
        
        fig_t = style_fig(px.line(df, x="tempo", y="temp_ar", color="nome_estacao", render_mode='svg'), "Evolução da Temperatura (°C)")
        fig_u = style_fig(px.line(df, x="tempo", y="umidade", color="nome_estacao", render_mode='svg'), "Umidade Relativa (%)")
        
        fig_c_t = px.bar(df, x="tempo", y="chuva_mm", color="nome_estacao")
        fig_c_t.update_traces(marker_opacity=1, marker_line_width=0)
        fig_c_t = style_fig(fig_c_t, "Intensidade de Chuva (mm) - Tempo Real")

        df_acumulado = df_completo.groupby('nome_estacao')['chuva_mm'].sum().reset_index().sort_values('chuva_mm', ascending=False)
        cores_acum = df_acumulado['chuva_mm'].apply(get_color_code)
        
        fig_c_a = px.bar(df_acumulado, x="nome_estacao", y="chuva_mm", text="chuva_mm")
        fig_c_a.update_traces(marker_color=cores_acum, texttemplate='%{text:.1f}', textposition='outside', cliponaxis=False)
        max_chuva = df_acumulado['chuva_mm'].max() if not df_acumulado.empty else 10
        fig_c_a.update_layout(yaxis_range=[0, max_chuva * 1.25]) 
        fig_c_a = style_fig(fig_c_a, "Chuva Acumulada Total (24h)")
        
        fig_p = style_fig(px.line(df, x="tempo", y="pressao", color="nome_estacao"), "Pressão Atmosférica (hPa)")
        
        fig_v = px.bar_polar(df_completo.tail(50), r="vento_vel", color="nome_estacao", template="plotly_white")
        fig_v.update_layout(title=dict(text="<b>Ventos Recentes</b>", x=0.5), margin=dict(t=30, b=20), paper_bgcolor='rgba(0,0,0,0)')

        return options, extremos, cards_medias, cards_atuais, audit_data, audit_cols, fig_t, fig_u, fig_c_t, fig_c_a, fig_p, fig_v, fig_mapa
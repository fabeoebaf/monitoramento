import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO (MANAUS) ---
LAT = -3.1019
LON = -60.025
TIMEZONE = "America/Sao_Paulo"

# --- CONFIGURAÇÃO DE DOWNLOAD (NOVO) ---
# Define como o botão de salvar vai funcionar para cada gráfico
def get_download_config(nome_arquivo):
    return {
        'displayModeBar': True, # Mostra a barra de ferramentas
        'displaylogo': False,   # Remove o logo do Plotly
        'modeBarButtonsToRemove': ['zoom', 'pan', 'select2d', 'lasso2d', 'autoScale2d'], # Remove botões desnecessários
        'toImageButtonOptions': {
            'format': 'png', # Formato
            'filename': nome_arquivo,
            'height': 600,  # Altura maior para ficar legível
            'width': 1000,  # Largura HD
            'scale': 2      # Alta resolução (Retina)
        }
    }

# --- FUNÇÕES AUXILIARES ---
def get_reference_run():
    """Estima a rodada do modelo (00Z, 06Z, 12Z, 18Z)"""
    now_utc = datetime.now(timezone.utc)
    h = now_utc.hour
    if h >= 22: return "18Z"
    elif h >= 16: return "12Z"
    elif h >= 10: return "06Z"
    elif h >= 4: return "00Z"
    else: return "18Z (Ontem)"

# --- FUNÇÕES VISUAIS ---
def style_meteogram(fig, titulo):
    """Estiliza o meteograma"""
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>", font=dict(size=16, color="#2c3e50")),
        title_x=0.0,
        template="plotly_white",
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400, 
    )
    
    # Eixo Y1 (Esquerda - Temp) - Vermelho
    fig.update_yaxes(title_text="Temperatura (°C)", secondary_y=False, showgrid=True, gridcolor='#e0e0e0', color='#FF6B6B', tickfont=dict(weight='bold'))
    
    # Eixo Y2 (Direita - Chuva) - Azul
    fig.update_yaxes(title_text="Precipitação (mm)", secondary_y=True, showgrid=False, range=[0, 25], color='#1E88E5', tickfont=dict(weight='bold'))
    
    return fig

def add_night_shading(fig, df):
    if df.empty: return fig
    start_date = df['time'].min()
    end_date = df['time'].max()
    curr_date = start_date.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if start_date.hour < 6:
        fig.add_vrect(x0=start_date, x1=start_date.replace(hour=6), 
                      fillcolor="gray", opacity=0.1, layer="below", line_width=0)

    while curr_date < end_date:
        next_morning = curr_date + timedelta(hours=12)
        fig.add_vrect(x0=curr_date, x1=next_morning, fillcolor="gray", opacity=0.10, layer="below", line_width=0)
        curr_date += timedelta(days=1)
    return fig

def get_rain_indicator(probability, precipitation):
    if precipitation > 0:
        if precipitation >= 10: return "FORTE", "#ffcdd2", "fas fa-bolt"
        elif precipitation >= 5: return "MODERADA", "#ffecb3", "fas fa-cloud-showers-heavy"
        elif precipitation >= 1: return "LEVE", "#e8f5e9", "fas fa-cloud-rain"
        else: return "MUITO LEVE", "#e3f2fd", "fas fa-cloud"
    
    if probability >= 80: return "RISCO ALTO", "#ffcdd2", "fas fa-exclamation-circle"
    elif probability >= 60: return "RISCO MÉDIO", "#ffecb3", "fas fa-exclamation"
    else: return "ESTÁVEL", "#ffffff", "fas fa-sun"

# --- LAYOUT ---
layout = dbc.Container(fluid=True, children=[
    
    dbc.Row([
        dbc.Col([
            html.H4([html.I(className="fas fa-calendar-alt me-2"), "Previsão Numérica (5 Dias)"], className="fw-bold text-primary mb-0"),
            html.Small("Comparativo: ECMWF (0.25°) vs ICON (Global)", className="text-muted")
        ], width=12)
    ], className="my-3"),

    # Cards de Resumo
    dbc.Row(id="cards-resumo", className="mb-4"),

    # GRÁFICO 1: ECMWF
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.B("Modelo ECMWF"), 
                    html.Span(" • Europeu", className="badge bg-light text-muted ms-2"),
                    html.Span(id="ref-ecmwf", className="badge bg-dark float-end")
                ], className="bg-white border-bottom-0"),
                dbc.CardBody(
                    dcc.Loading(
                        dcc.Graph(
                            id='grafico-ecmwf', 
                            config=get_download_config("meteograma_ecmwf_manaus") # <--- CONFIG AQUI
                        ), 
                    type="dot")
                )
            ], className="shadow-sm border-0 mb-4")
        ], width=12)
    ]),

    # GRÁFICO 2: ICON
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.B("Modelo ICON"), 
                    html.Span(" • Alemão DWD", className="badge bg-light text-muted ms-2"),
                    html.Span(id="ref-icon", className="badge bg-dark float-end")
                ], className="bg-white border-bottom-0"),
                dbc.CardBody(
                    dcc.Loading(
                        dcc.Graph(
                            id='grafico-icon', 
                            config=get_download_config("meteograma_icon_manaus") # <--- CONFIG AQUI
                        ), 
                    type="dot")
                )
            ], className="shadow-sm border-0 mb-4")
        ], width=12)
    ]),

    dcc.Interval(id='refresh-previsao', interval=60*60*1000, n_intervals=0) 
])

# --- LÓGICA DE DADOS ---
def get_model_data_robust(model_name):
    url = "https://api.open-meteo.com/v1/forecast"
    
    if "ecmwf" in model_name:
        hourly_vars = "temperature_2m,precipitation,surface_pressure"
    else:
        hourly_vars = "temperature_2m,precipitation,surface_pressure,precipitation_probability"

    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": hourly_vars,
        "timezone": TIMEZONE,
        "models": model_name,
        "forecast_days": 5
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        df = pd.DataFrame(data['hourly'])
        df['time'] = pd.to_datetime(df['time'])
        
        if 'precipitation_probability' not in df.columns:
            df['precipitation_probability'] = 0
            
        return df
    except Exception as e:
        print(f"Erro no modelo {model_name}: {e}")
        return pd.DataFrame()

# --- CALLBACKS ---
def register_callbacks(app):

    @app.callback(
        [Output('grafico-ecmwf', 'figure'),
         Output('grafico-icon', 'figure'),
         Output('cards-resumo', 'children'),
         Output('ref-ecmwf', 'children'),
         Output('ref-icon', 'children')],
        [Input('refresh-previsao', 'n_intervals')]
    )
    def update_forecasts(n):
        # 0. Calcula Rodada
        rodada = f"Rodada {get_reference_run()}"

        # 1. Busca Dados
        df_ecmwf = get_model_data_robust("ecmwf_ifs025") 
        df_icon = get_model_data_robust("icon_global")

        if df_ecmwf.empty or df_icon.empty:
            msg = html.Div("Erro de conexão com API Open-Meteo.", className="alert alert-danger")
            return go.Figure(), go.Figure(), [msg], "-", "-"

        # 2. Cards (ECMWF)
        df_ecmwf['dia'] = df_ecmwf['time'].dt.date
        resumo = df_ecmwf.groupby('dia').agg({
            'temperature_2m': ['min', 'max'],
            'precipitation': 'sum'
        }).reset_index()
        
        cards = []
        dias_pt = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
        
        for i in range(5):
            if i >= len(resumo): break
            row = resumo.iloc[i]
            dia_obj = row['dia'].item()
            nome_dia = dias_pt[dia_obj.weekday()]
            data_fmt = f"{nome_dia}, {dia_obj.day}/{dia_obj.month}"
            if i == 0: data_fmt = "Hoje"

            t_min = row['temperature_2m']['min']
            t_max = row['temperature_2m']['max']
            chuva = row['precipitation']['sum']
            prob = 0 
            txt_chuva, cor_bg, icon_cls = get_rain_indicator(prob, chuva)
            
            card = dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.I(className=f"{icon_cls} position-absolute end-0 top-0 m-2 opacity-25 fa-2x"),
                    html.H6(data_fmt, className="text-muted text-uppercase small fw-bold text-center"),
                    html.H4(f"{t_max:.0f}°", className="text-center fw-bold mb-0 text-dark"),
                    html.Small(f"{t_min:.0f}°", className="text-center d-block text-muted"),
                    html.Div([
                        html.Div(f"{chuva:.1f}mm", className="fw-bold fs-5"),
                        html.Small(txt_chuva, className="d-block", style={"fontSize": "0.7rem"})
                    ], className="text-center mt-2 p-1 rounded", style={"backgroundColor": cor_bg, "color": "#333"})
                ])
            ], className=f"shadow-sm border-0 border-top border-4 h-100", style={"borderColor": cor_bg}), width=True)
            cards.append(card)

        # 3. Gráficos
        def criar_meteograma(df, nome):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(go.Scatter(x=df['time'], y=df['temperature_2m'], name="Temp (°C)",
                           line=dict(color='#FF6B6B', width=3), mode='lines'), secondary_y=False)
            
            fig.add_trace(go.Bar(x=df['time'], y=df['precipitation'], name="Chuva (mm)", 
                       marker_color='#1E88E5', opacity=0.7), secondary_y=True)

            fig = add_night_shading(fig, df)
            return style_meteogram(fig, f"Meteograma Manaus - {nome}")

        fig_e = criar_meteograma(df_ecmwf, "ECMWF")
        fig_i = criar_meteograma(df_icon, "ICON")

        return fig_e, fig_i, cards, rodada, rodada
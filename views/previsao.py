from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import pytz

# --- CONFIGURAÇÃO (MANAUS) ---
LAT = -3.1019
LON = -60.025
TIMEZONE = "America/Manaus"

# --- CONFIGURAÇÃO DE DOWNLOAD ---
def get_download_config(nome_arquivo):
    return {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['zoom', 'pan', 'select2d', 'lasso2d', 'autoScale2d'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': nome_arquivo,
            'height': 600,
            'width': 1000,
            'scale': 2 # Retina Display (Alta Resolução)
        }
    }

# --- FUNÇÕES AUXILIARES ---
def get_reference_run(gen_time_ms):
    """Calcula a rodada do modelo baseada no horário UTC"""
    if not gen_time_ms: return "Aguardando..."
    
    # Converte timestamp para UTC explícito
    dt = datetime.fromtimestamp(gen_time_ms / 1000, tz=timezone.utc)
    hour = dt.hour
    
    # Regra de rodadas sinóticas (00, 06, 12, 18 UTC)
    if hour < 3: run = "00Z"
    elif hour < 9: run = "06Z"
    elif hour < 15: run = "12Z"
    else: run = "18Z"
    
    # Mostra a rodada e a hora que foi gerado (em UTC para referência técnica)
    return f"{run} ({dt.strftime('%H:%M')} UTC)"

def get_rain_indicator(probability, precipitation):
    """Define ícones e cores para o resumo do tempo"""
    # 1. Volume de chuva (Prioridade)
    if precipitation > 0.5:
        if precipitation >= 15: return "TEMPORAL", "#ffcdd2", "fas fa-bolt", "#c62828"
        elif precipitation >= 5: return "CHUVA MODERADA", "#fff9c4", "fas fa-cloud-showers-heavy", "#fbc02d"
        elif precipitation >= 0.1: return "CHUVA LEVE", "#e8f5e9", "fas fa-cloud-rain", "#2e7d32"
    
    # 2. Probabilidade (Risco)
    if probability >= 80: return "RISCO ALTO", "#ffecb3", "fas fa-exclamation-circle", "#ff8f00"
    elif probability >= 60: return "RISCO MÉDIO", "#fff3e0", "fas fa-exclamation", "#ef6c00"
    elif probability >= 30: return "POSSIBILIDADE", "#f5f5f5", "fas fa-cloud-sun", "#666"
    
    return "ESTÁVEL", "#ffffff", "fas fa-sun", "#fbc02d"

def processar_periodos_hoje(df):
    """Filtra Manhã, Tarde e Noite para o dia atual em Manaus"""
    if df.empty: return []
    
    tz = pytz.timezone(TIMEZONE)
    hoje = datetime.now(tz).date()
    df_hoje = df[df['time'].dt.date == hoje].copy()
    
    periodos = [
        {"nome": "Manhã (06-12h)", "inicio": 6, "fim": 12, "icon": "fa-coffee", "cor": "#FFC107"},
        {"nome": "Tarde (12-18h)", "inicio": 12, "fim": 18, "icon": "fa-sun", "cor": "#FF9800"},
        {"nome": "Noite (18-00h)", "inicio": 18, "fim": 23, "icon": "fa-moon", "cor": "#3F51B5"}
    ]
    
    cards = []
    for p in periodos:
        dft = df_hoje[(df_hoje['time'].dt.hour >= p['inicio']) & (df_hoje['time'].dt.hour < p['fim'])]
        
        if not dft.empty:
            temp_max = dft['temperature_2m'].max()
            # Pega sensação térmica se disponível
            sensacao = dft['apparent_temperature'].max() if 'apparent_temperature' in dft.columns else temp_max
            chuva_sum = dft['precipitation'].sum()
            prob_max = dft['precipitation_probability'].max() if 'precipitation_probability' in dft.columns else 0
            
            label_chuva, bg_color, _, _ = get_rain_indicator(prob_max, chuva_sum)
            
            cards.append({
                "titulo": p['nome'],
                "temp": f"{temp_max:.0f}°",
                "sensacao": f"{sensacao:.0f}°",
                "chuva": f"{chuva_sum:.1f} mm",
                "prob": f"{prob_max:.0f}%",
                "cor_borda": p['cor'],
                "bg_status": bg_color,
                "texto_status": label_chuva,
                "icon_periodo": p['icon']
            })
            
    return cards

def add_night_shading(fig, df):
    """Adiciona áreas escuras para representar a noite (18h as 06h)"""
    if df.empty: return fig
    start = df['time'].min(); end = df['time'].max()
    curr = start.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if start.hour < 6:
        fig.add_vrect(x0=start, x1=start.replace(hour=6), fillcolor="#2c3e50", opacity=0.08, layer="below", line_width=0)

    while curr < end:
        prox_manha = curr + timedelta(hours=12)
        fig.add_vrect(x0=curr, x1=prox_manha, fillcolor="#2c3e50", opacity=0.08, layer="below", line_width=0)
        curr += timedelta(days=1)
    return fig

# --- LÓGICA DE DADOS ---
def get_model_data_robust(model_name):
    url = "https://api.open-meteo.com/v1/forecast"
    # Adicionamos Sensação Térmica (apparent_temperature)
    hourly_vars = "temperature_2m,precipitation,surface_pressure,relative_humidity_2m,wind_speed_10m,apparent_temperature"
    
    if "icon" in model_name:
        hourly_vars += ",precipitation_probability"

    params = {
        "latitude": LAT, "longitude": LON, "hourly": hourly_vars,
        "timezone": TIMEZONE, "models": model_name, "forecast_days": 7 # Pede 7 dias para garantir a semana toda
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data['hourly'])
        df['time'] = pd.to_datetime(df['time'])
        df.attrs['generated'] = data.get('generationtime_ms', 0)
        
        if 'precipitation_probability' not in df.columns: df['precipitation_probability'] = 0
        return df
    except Exception as e:
        print(f"Erro API {model_name}: {e}")
        return pd.DataFrame()

# --- LAYOUT EXPORTÁVEL ---
layout = dbc.Container(fluid=True, children=[
    
    # Cabeçalho
    dbc.Row([
        dbc.Col([
            html.H4([html.I(className="fas fa-satellite-dish me-2"), "Previsão Numérica: Manaus"], className="fw-bold text-primary mb-0 mt-3"),
            html.Small("Comparativo Multimodelo: ECMWF (IFS 0.25°) vs ICON (DWD Global)", className="text-muted")
        ], width=12)
    ], className="mb-4"),

    # SEÇÃO 1: PREVISÃO PARA HOJE
    dbc.Row([dbc.Col(html.H6([html.I(className="fas fa-clock me-2"), "Detalhamento de Hoje"], className="fw-bold text-secondary border-bottom pb-2"), width=12)]),
    dbc.Row(id="cards-hoje", className="mb-4"),

    # SEÇÃO 2: TENDÊNCIA 5 DIAS (LISTA)
    dbc.Row([dbc.Col(html.H6([html.I(className="fas fa-calendar-week me-2"), "Tendência para 5 Dias"], className="fw-bold text-secondary border-bottom pb-2"), width=12)]),
    dbc.Row(dbc.Col(id="lista-5dias", width=12, md=12, className="mx-auto"), className="mb-4"), # Centralizado

    # SEÇÃO 3: GRÁFICO ECMWF
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.B("Modelo ECMWF"), 
                    html.Span(" • Europeu", className="badge bg-light text-muted ms-2"),
                    html.Span(id="ref-ecmwf", className="badge bg-dark float-end")
                ], className="bg-white"),
                dbc.CardBody(dcc.Loading(dcc.Graph(id='grafico-ecmwf', config=get_download_config("ecmwf_manaus")), type="dot"))
            ], className="shadow-sm border-0 mb-4")
        ], width=12)
    ]),

    # SEÇÃO 4: GRÁFICO ICON
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.B("Modelo ICON"), 
                    html.Span(" • Alemão", className="badge bg-light text-muted ms-2"),
                    html.Span(id="ref-icon", className="badge bg-dark float-end")
                ], className="bg-white"),
                dbc.CardBody(dcc.Loading(dcc.Graph(id='grafico-icon', config=get_download_config("icon_manaus")), type="dot"))
            ], className="shadow-sm border-0 mb-4")
        ], width=12)
    ]),

    dcc.Interval(id='refresh-previsao', interval=3600*1000, n_intervals=0)
])

# --- FUNÇÃO DE REGISTRO DE CALLBACKS ---
def register_callbacks(app):
    
    @app.callback(
        [Output('grafico-ecmwf', 'figure'),
         Output('grafico-icon', 'figure'),
         Output('cards-hoje', 'children'),
         Output('lista-5dias', 'children'),
         Output('ref-ecmwf', 'children'),
         Output('ref-icon', 'children')],
        [Input('refresh-previsao', 'n_intervals')]
    )
    def update_forecasts(n):
        # 1. Busca Dados
        df_ecmwf = get_model_data_robust("ecmwf_ifs025") 
        df_icon = get_model_data_robust("icon_global")

        if df_ecmwf.empty or df_icon.empty:
            return go.Figure(), go.Figure(), [], [], "Erro", "Erro"

        # ---------------------------------------------------------
        # 2. Processa Cards de HOJE (Manhã/Tarde/Noite)
        # ---------------------------------------------------------
        dados_hoje = processar_periodos_hoje(df_icon)
        layout_hoje = []
        for item in dados_hoje:
            card = dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className=f"fas {item['icon_periodo']} fa-lg me-2", style={"color": item['cor_borda']}),
                        html.B(item['titulo'], className="text-uppercase small"),
                    ], className="d-flex align-items-center mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Span(item['temp'], className="display-6 fw-bold text-dark"),
                            html.Small(["Sensação: ", html.B(item['sensacao'])], className="text-muted d-block small")
                        ], width=7),
                        dbc.Col([
                            html.Span(item['chuva'], className="fw-bold fs-5 text-primary"),
                            html.Small(f"Prob: {item['prob']}", className="text-muted d-block small")
                        ], width=5),
                    ]),
                    
                    html.Div(
                        [html.I(className="fas fa-info-circle me-1"), item['texto_status']],
                        className="mt-3 badge w-100 py-2",
                        style={"backgroundColor": item['bg_status'], "color": "#444", "fontSize": "0.8rem"}
                    )
                ])
            ], className="h-100 shadow-sm border-0 border-top border-4", style={"borderTopColor": item['cor_borda']}), width=12, md=4, className="mb-2")
            layout_hoje.append(card)

        if not layout_hoje: 
            layout_hoje = [dbc.Alert("Dados de hoje indisponíveis. (Fuso horário ou fim do dia)", color="warning")]


# ---------------------------------------------------------
        # 3. Processa Lista de 5 DIAS (Versão "Jumbo" - Maior e Mais Legível)
        # ---------------------------------------------------------
        df_ecmwf['dia'] = df_ecmwf['time'].dt.date
        resumo = df_ecmwf.groupby('dia').agg({'temperature_2m': ['min', 'max'], 'precipitation': 'sum'}).reset_index()
        
        semana_min = resumo['temperature_2m']['min'].min()
        semana_max = resumo['temperature_2m']['max'].max()
        
        layout_5dias = []
        dias_sem = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}

        # Cabeçalho da Lista (Aumentado e com espaçamento)
        layout_5dias.append(
            dbc.Row([
                dbc.Col(html.B("DIA DA SEMANA", className="text-muted small"), width=3, md=2),
                dbc.Col(html.B("PREVISÃO", className="text-muted small text-center"), width=2),
                dbc.Col(html.B("TEMPERATURA (MÍN / MÁX)", className="text-muted small text-center"), width=5, md=6),
                dbc.Col(html.B("CHUVA", className="text-muted small text-end"), width=2),
            ], className="mb-3 px-4 d-none d-md-flex align-items-center")
        )

# ... (código anterior do cabeçalho da lista) ...

        for i in range(1, 6): 
            if i >= len(resumo): break
            row = resumo.iloc[i]; dia_obj = row['dia'].item()
            t_min = row['temperature_2m']['min']
            t_max = row['temperature_2m']['max']
            precip = row['precipitation']['sum']

            # Probabilidade ICON
            prob_dia = 0
            if not df_icon.empty:
                match = df_icon[df_icon['time'].dt.date == dia_obj]
                if not match.empty: prob_dia = match['precipitation_probability'].max()

            # --- LÓGICA DE ÍCONE E TEXTO (NOVO!) ---
            # Definimos o ícone E a descrição textual baseada na severidade
            if precip > 15: 
                icon_cls = "fas fa-bolt text-danger"
                desc_texto = "TEMPORAL"
            elif precip > 5: 
                icon_cls = "fas fa-cloud-showers-heavy text-primary"
                desc_texto = "CHUVA FORTE"
            elif precip > 0.5: 
                icon_cls = "fas fa-cloud-rain text-info"
                desc_texto = "CHUVA FRACA"
            elif prob_dia > 60: 
                icon_cls = "fas fa-cloud text-secondary"
                desc_texto = "NUBLADO"
            elif prob_dia > 20: 
                icon_cls = "fas fa-cloud-sun text-secondary"
                desc_texto = "PARC. NUBLADO"
            else:
                icon_cls = "fas fa-sun text-warning"
                desc_texto = "ENSOLARADO"

            # Barra Visual
            total_range = semana_max - semana_min if semana_max != semana_min else 1
            left_p = ((t_min - semana_min) / total_range) * 100
            width_p = ((t_max - t_min) / total_range) * 100
            if width_p < 5: width_p = 5 

            item = dbc.Card(dbc.CardBody([
                dbc.Row([
                    # 1. Dia
                    dbc.Col([
                        html.H5(dias_sem[dia_obj.weekday()][:3].upper(), className="fw-bold text-dark mb-0"), 
                        html.Small(f"{dia_obj.day}/{dia_obj.month}", className="text-muted")
                    ], width=3, md=2, className="d-flex flex-column justify-content-center border-end"), # Adicionei border-end para separar
                    
                    # 2. Ícone + DESCRIÇÃO (AQUI ESTÁ A MUDANÇA VISUAL)
                    dbc.Col([
                        html.I(className=f"{icon_cls} fa-2x mb-1"),
                        # Texto da condição (Ex: CHUVA FORTE)
                        html.Span(desc_texto, className="d-block small fw-bold text-muted", style={"fontSize": "0.65rem", "letterSpacing": "1px"}),
                        # Badge de Probabilidade (se houver risco)
                        html.Div(f"{prob_dia:.0f}% Prob.", className="badge bg-light text-dark border mt-1" if prob_dia > 20 else "d-none")
                    ], width=3, md=3, className="text-center d-flex flex-column align-items-center justify-content-center"),
                    
                    # 3. Barra de Temperatura
                    dbc.Col([
                        html.Div([
                            html.Span(f"{t_min:.0f}°", className="text-secondary fw-bold fs-5 me-3"),
                            html.Div([
                                html.Div(style={
                                    "position": "absolute", "left": f"{left_p}%", "width": f"{width_p}%", 
                                    "height": "10px", "borderRadius": "6px",
                                    "background": "linear-gradient(90deg, #42a5f5, #ef5350)",
                                    "opacity": "0.8"
                                })
                            ], className="flex-grow-1 position-relative bg-light rounded-pill", style={"height": "10px"}),
                            html.Span(f"{t_max:.0f}°", className="text-dark fw-bold fs-5 ms-3")
                        ], className="d-flex align-items-center w-100")
                    ], width=4, md=5),
                    
                    # 4. Chuva (Volume)
                    dbc.Col([
                         html.Div([
                            html.I(className="fas fa-tint text-primary me-1") if precip > 0 else None,
                            html.B(f"{precip:.1f}", className="text-primary fs-5" if precip > 0 else "text-muted"),
                            html.Small(" mm", className="text-muted")
                        ], className="text-end")
                    ], width=2, className="d-flex align-items-center justify-content-end")
                ], align="center")
            ], className="py-2 px-3"), className="mb-2 border-0 shadow-sm")
            
            layout_5dias.append(item)

        # ---------------------------------------------------------
        # 4. Gráficos (Plotagem)
        # ---------------------------------------------------------
        def plot_model(df, nome):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 1. Sensação Térmica
            fig.add_trace(go.Scatter(
                x=df['time'], y=df['apparent_temperature'], name="Sensação (°C)",
                line=dict(color='#FF8A65', width=2, dash='dot', shape='spline'), opacity=0.8
            ), secondary_y=False)

            # 2. Temperatura Real
            fig.add_trace(go.Scatter(
                x=df['time'], y=df['temperature_2m'], name="Temp (°C)",
                line=dict(color='#D32F2F', width=3, shape='spline'), mode='lines'
            ), secondary_y=False)

            # 3. Chuva
            fig.add_trace(go.Bar(
                x=df['time'], y=df['precipitation'], name="Chuva (mm)", 
                marker_color='#1976D2', opacity=0.7
            ), secondary_y=True)

            # 4. Probabilidade (Área)
            if df['precipitation_probability'].sum() > 0:
                 fig.add_trace(go.Scatter(
                     x=df['time'], y=df['precipitation_probability'], name="Prob. (%)",
                     line=dict(width=0), fill='tozeroy', fillcolor='rgba(30, 136, 229, 0.1)'
                 ), secondary_y=True)

            # --- Anotações ---
            df['date'] = df['time'].dt.date
            
            # Label Máxima Temp
            daily_max_idx = df.groupby('date')['temperature_2m'].idxmax()
            df_max = df.loc[daily_max_idx]
            fig.add_trace(go.Scatter(
                x=df_max['time'], y=df_max['temperature_2m'], mode='text',
                text=df_max['temperature_2m'].apply(lambda x: f"{x:.0f}°"),
                textposition="top center", textfont=dict(color='#D32F2F', size=11, weight='bold'), showlegend=False
            ), secondary_y=False)

            # Label Máxima Chuva (se > 0.5mm)
            daily_rain_idx = df.groupby('date')['precipitation'].idxmax()
            df_rain_max = df.loc[daily_rain_idx]
            df_rain_max = df_rain_max[df_rain_max['precipitation'] > 0.5]
            fig.add_trace(go.Scatter(
                x=df_rain_max['time'], y=df_rain_max['precipitation'], mode='text',
                text=df_rain_max['precipitation'].apply(lambda x: f"{x:.1f}"),
                textposition="top center", textfont=dict(color='#1565C0', size=10, weight='bold'), showlegend=False
            ), secondary_y=True)

            # Layout Final
            fig = add_night_shading(fig, df)
            fig.update_layout(
                title=dict(text=f"<b>{nome}</b>", font=dict(size=16, color="#2c3e50")),
                template="plotly_white", margin=dict(l=10, r=10, t=50, b=10),
                legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
                hovermode="x unified", height=450, uirevision='constant'
            )
            fig.update_yaxes(title_text="Temp. / Sensação (°C)", secondary_y=False, showgrid=True, gridcolor='#f0f0f0')
            fig.update_yaxes(title_text="Chuva (mm)", secondary_y=True, showgrid=False, range=[0, None]) # Dinâmico
            return fig

        return plot_model(df_ecmwf, "ECMWF (Europeu)"), plot_model(df_icon, "ICON (Alemão)"), layout_hoje, layout_5dias, get_reference_run(df_ecmwf.attrs['generated']), get_reference_run(df_icon.attrs['generated'])
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import sys
import os

# --- CONFIGURAÇÃO DE CAMINHOS (IMPORTANTE) ---
# Adiciona a pasta 'views' ao caminho do Python para ele encontrar os arquivos
sys.path.append(os.path.join(os.path.dirname(__file__), 'views'))

# Agora o Python consegue achar os módulos dentro de /views
try:
    import monitoramento
    import cemaden
    import previsao
    import relatorios # <--- NOVA ABA
except ImportError as e:
    print(f"ERRO CRÍTICO: Não foi possível importar os módulos da pasta views. Detalhe: {e}")
    # Cria mocks para o app não fechar na cara, caso falhe
    class MockPage:
        layout = html.Div([
            html.H1("Erro de Importação"),
            html.P("Verifique se os arquivos monitoramento.py, cemaden.py, previsao.py e relatorios.py estão na pasta 'views'."),
            html.Pre(str(e))
        ], className="p-5 text-danger")
        def register_callbacks(self, app): pass
    
    # Inicializa mocks para evitar erro de "variable not defined"
    monitoramento = MockPage()
    cemaden = MockPage()
    previsao = MockPage()
    relatorios = MockPage()

# --- INICIALIZAÇÃO DO APP ---
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://use.fontawesome.com/releases/v5.15.4/css/all.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" # <--- ADICIONE ISSO
    ],
    suppress_callback_exceptions=True,
    update_title=None,          # Impede o "Updating..." de piscar
    title="Monitoramento Manaus" # Define o nome fixo da aba
)
server = app.server

# --- BARRA DE NAVEGAÇÃO ---
navbar = dbc.Navbar(
    dbc.Container([
        html.A(
            dbc.Row([
                dbc.Col(dbc.NavbarBrand("CENTRO DE OPERAÇÕES | MANAUS", className="ms-2 fw-bold text-uppercase")),
            ], align="center", className="g-0"),
            href="/",
            style={"textDecoration": "none"},
        ),
        dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
        dbc.Collapse(
            dbc.Nav([
                # Aba 1: Monitoramento (Home)
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-shield-alt me-2"), "Defesa Civil"], href="/", active="exact", className="px-3")),
                
                # Aba 2: Cemaden
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-satellite-dish me-2"), "Cemaden"], href="/cemaden", active="exact", className="px-3")),
                
                # Aba 3: Previsão
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-calendar-alt me-2"), "Previsão"], href="/previsao", active="exact", className="px-3")),
                
                # Aba 4: Relatórios (NOVA)
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-file-alt me-2"), "Relatórios"], href="/relatorios", active="exact", className="px-3")),
                
            ], className="ms-auto", navbar=True),
            id="navbar-collapse",
            navbar=True,
        ),
    ]),
    color="primary",
    dark=True,
    className="mb-4 shadow-sm",
    sticky="top"
)

# --- RODAPÉ ---
footer = html.Footer(
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.P("© 2026 Defesa Civil de Manaus - Sistema de Monitoramento Hidrometeorológico", className="text-muted mb-0 small"),
                html.Small("Dados: Prefeitura de Manaus | INMET | Cemaden | Open-Meteo", className="text-muted")
            ], width=12, className="text-center py-3")
        ])
    ], fluid=True),
    className="bg-light mt-5 border-top"
)

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    navbar,
    # Conteúdo da página (Sem Loading Global para evitar piscar a tela toda)
    dbc.Container(
        html.Div(id='page-content', style={"minHeight": "80vh"}),
        fluid=True,
        className="px-0"
    ),
    footer
], style={"backgroundColor": "#f8f9fa"})

# --- CALLBACKS GERAIS ---

# Roteador
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/cemaden':
        return cemaden.layout
    elif pathname == '/previsao':
        return previsao.layout
    elif pathname == '/relatorios': # <--- ROTA DA NOVA ABA
        return relatorios.layout
    else:
        return monitoramento.layout

# Menu Mobile
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

# Registra os callbacks dos módulos
monitoramento.register_callbacks(app)
cemaden.register_callbacks(app)
previsao.register_callbacks(app)
relatorios.register_callbacks(app) # <--- REGISTRO DA NOVA ABA

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8052)

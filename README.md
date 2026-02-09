# ⛈️ Painel de monitoramento - Manaus

> Dashboard interativo para monitoramento em tempo real de estações meteorológicas, focado na prevenção e alerta de eventos extremos na cidade de Manaus/AM.

![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Dash](https://img.shields.io/badge/Dash-Plotly-orange)

## 🎯 Objetivo
Este projeto visa fornecer uma interface visual robusta para o monitoramento de Manaus, permitindo a visualização rápida de dados críticos como **acumulado de chuva**, **nível dos rios**, **temperatura** e **ventos**. O sistema destaca automaticamente estações em estado de alerta.

## 📊 Funcionalidades Principais

### 1. Mapa Interativo (Geolocalização)
- Visualização espacial de todas as estações.
- **Marcadores Dinâmicos:** As estações mudam de cor automaticamente baseadas no acumulado de chuva das últimas 24h.
- **Dados no Mapa:** Exibição do valor pluviométrico diretamente no marcador, sem necessidade de clique.

### 2. Telemetria em Tempo Real
- Cards de KPI (Indicadores Chave) com atualização automática.
- Monitoramento de:
  - Temperatura e Sensação Térmica.
  - Umidade Relativa.
  - Velocidade e Direção do Vento.
  - Pressão Atmosférica.

### 3. Gráficos Analíticos
- **Evolução Temporal:** Gráficos de linha para temperatura e umidade.
- **Chuva:** Gráfico de barras combinando intensidade (mm/h) e acumulados (6h, 12h, 24h).
- **Vento:** Rosa dos ventos (Polar Chart) para direção e gráfico linear para velocidade.

### 4. Tabela de Auditoria (Log)
- Histórico detalhado dos últimos registros.
- **Alertas Visuais:**
  - 🔴 Células de chuva ficam **vermelhas** se > 10mm.
  - 🟠 Células de vento ficam **laranjas** se > 10 m/s.
- Filtros e ordenação nativa por colunas.

---

## 🚦 Regras de Negócio (Alertas)

O sistema classifica o status das estações com base no acumulado pluviométrico:

| Status | Faixa de Chuva (mm) | Cor |
| :--- | :--- | :--- |
| **Normal** | < 10mm | 🟢 Verde |
| **Observação** | 10mm - 30mm | 🟡 Amarelo |
| **Atenção** | 30mm - 70mm | 🟠 Laranja |
| **Crítico** | > 70mm | 🔴 Vermelho |

---

## 🛠️ Tecnologias Utilizadas

- **[Python](https://www.python.org/)**: Linguagem base.
- **[Dash](https://dash.plotly.com/)**: Framework para aplicações Web analíticas.
- **[Plotly](https://plotly.com/python/)**: Biblioteca de gráficos interativos.
- **[Pandas](https://pandas.pydata.org/)**: Manipulação e análise de dados.
- **[Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)**: Estilização responsiva.

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
- Python 3.x instalado.
- Banco de dados configurado (PostgreSQL/MySQL) ou arquivo `db.py` simulando os dados.

### Instalação

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/fabeoebaf/monitoramento.git](https://github.com/fabeoebaf/monitoramento.git)
   cd monitoramento

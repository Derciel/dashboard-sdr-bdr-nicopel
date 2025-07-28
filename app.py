from __future__ import annotations

import pandas as pd
from datetime import datetime, date, timedelta

from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    State,
    dash_table,
    no_update,
    exceptions,
    ctx
)
import dash_bootstrap_components as dbc
import plotly.express as px

# --------------------------------------
# Configurações e Helpers
# --------------------------------------

# ## << NOVO: Credenciais de admin (NÃO USE EM PRODUÇÃO REAL)
ADMIN_USER = "admin"
ADMIN_PASSWORD = "123"

def empty_fig(text: str = "Sem dados para exibir"):
    # ... (código da função sem alterações)
    fig = px.bar()
    fig.update_layout(
        xaxis={"visible": False}, yaxis={"visible": False},
        annotations=[dict(text=text, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig

def build_kpi_card(title: str, value: int | float, color: str = "primary"):
    # ... (código da função sem alterações)
    return dbc.Card([
        dbc.CardHeader(title),
        dbc.CardBody(html.H3(f"{value}", className=f"text-{color}")),
    ], className="mb-2")


# --------------------------------------
# App
# --------------------------------------

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Dashboard SDR/BDR"

COLUMNS = ["razao_social", "nome_fantasia", "cidade", "estado", "vendedor", "data_registro"]
END_DEFAULT, START_DEFAULT = date.today(), date.today() - timedelta(days=30)

header = html.Header(
    dbc.Row([
        dbc.Col(html.Img(src="/assets/logo.png", height="60px"), width="auto"),
        dbc.Col(html.H2("Dashboard de Performance | SDR & BDR", className="mb-0 text-primary"), className="ms-2", align="center"),
    ], align="center", className="my-4")
)

# ## << NOVO: Definição da janela (Modal) de Login
login_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Acesso Restrito")),
    dbc.ModalBody([
        html.Div(id='login-error-message', className="mb-3"),
        dbc.Input(id='admin-user-input', placeholder='Usuário', type='text', className="mb-3"),
        dbc.Input(id='admin-password-input', placeholder='Senha', type='password', className="mb-3"),
    ]),
    dbc.ModalFooter(
        dbc.Button("Login", id="login-button", color="primary")
    ),
], id="login-modal", is_open=False)


app.layout = dbc.Container([
    dcc.Store(id="store-data", data=[]),
    dcc.Store(id='store-delete-info', data=None),
    dcc.ConfirmDialog(id='confirm-delete-dialog', message='Você tem certeza que deseja excluir este registro?'),
    login_modal, # ## << NOVO: Adiciona a modal ao layout
    
    header,
    html.Hr(),
    
    dcc.Tabs(id="tabs-main", children=[
        dcc.Tab(label="Cadastro de Clientes", children=[
            # ... (Card de Adicionar Cliente sem alterações)
            dbc.Card(dbc.CardBody([
                html.H4("Adicionar Novo Cliente", className="card-title"),
                dbc.Row([
                    dbc.Col(dbc.Input(id="input-razao-social", placeholder="Razão Social", type="text"), md=6),
                    dbc.Col(dbc.Input(id="input-nome-fantasia", placeholder="Nome Fantasia", type="text"), md=6),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Input(id="input-cidade", placeholder="Cidade", type="text"), md=6),
                    dbc.Col(dbc.Input(id="input-estado", placeholder="UF", maxLength=2, type="text"), md=2),
                    dbc.Col(dcc.Dropdown(id="dropdown-vendedor",options=[{"label": "Angela (SDR)", "value": "Angela"}, {"label": "David (BDR)", "value": "David"}], placeholder="Selecione o vendedor", clearable=False), md=4),
                ], className="mb-3"),
                dbc.Button("Adicionar Registro", id="btn-add", color="primary"),
                html.Div(id="msg", className="mt-2"),
            ]), className="mt-4"),
            
            dbc.Card([
                dbc.CardHeader(dbc.Row([
                    dbc.Col(html.H4("Base de Clientes Cadastrada")),
                    # ## << ALTERADO: Switch agora fica dentro de um Div e começa desabilitado
                    dbc.Col(html.Div(id='admin-switch-wrapper', children=[
                        dbc.Switch(id="admin-switch", label="Modo Administrador", value=False, disabled=True)
                    ]), width="auto")
                ], justify="between", align="center")),
                dbc.CardBody(
                    dash_table.DataTable(
                        id="table-clientes",
                        columns=[{"name": c.replace("_", " ").title(), "id": c} for c in COLUMNS],
                        data=[], page_size=10, sort_action="native",
                        style_table={"overflowX": "auto"}, style_header={'fontWeight': 'bold'},
                        markdown_options={"link_target": "_self"},
                    )
                ),
            ], className="mt-4"),
        ]),
        # ... (Aba de Análise de Desempenho sem alterações)
        dcc.Tab(label="Análise de Desempenho", children=[
            dbc.Card([dbc.CardHeader(html.H4("Filtros de Análise")), dbc.CardBody(dbc.Row([
                dbc.Col([dbc.Label("Período de Análise"), dcc.DatePickerRange(id="date-range", start_date=START_DEFAULT, end_date=END_DEFAULT, display_format="DD/MM/YYYY", className="d-block")], md=4),
                dbc.Col([dbc.Label("Agrupar por"), dbc.RadioItems(id="freq-radio", options=[{"label": "Semanal", "value": "W"}, {"label": "Mensal", "value": "M"}], value="W", inline=True)], md=4, className="pt-3"),
            ]))], className="mt-4"),
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardBody([html.H3("Angela (SDR)"), html.Div(id="kpi-angela"), dcc.Graph(id="graph-angela", config={'displayModeBar': False})])]), md=6),
                dbc.Col(dbc.Card([dbc.CardBody([html.H3("David (BDR)"), html.Div(id="kpi-david"), dcc.Graph(id="graph-david", config={'displayModeBar': False})])]), md=6),
            ], className="mt-4"),
        ]),
    ]),
], fluid=True, className="dbc")


# --------------------------------------
# Callbacks
# --------------------------------------

# ## << NOVO: Callback para controlar o login e a modal
@app.callback(
    Output('login-modal', 'is_open'),
    Output('login-error-message', 'children'),
    Output('admin-switch', 'value'),
    Output('admin-user-input', 'value'),
    Output('admin-password-input', 'value'),
    Input('admin-switch-wrapper', 'n_clicks'),
    Input('login-button', 'n_clicks'),
    State('admin-user-input', 'value'),
    State('admin-password-input', 'value'),
    prevent_initial_call=True
)
def control_login_modal(switch_clicks, login_clicks, user, password):
    triggered_id = ctx.triggered_id

    # Se o usuário clicar no wrapper do switch para tentar logar
    if triggered_id == 'admin-switch-wrapper':
        return True, None, no_update, "", ""

    # Se o usuário clicar no botão de login dentro da modal
    if triggered_id == 'login-button':
        if user == ADMIN_USER and password == ADMIN_PASSWORD:
            # Login sucesso: fecha a modal e ativa o switch
            return False, None, True, "", ""
        else:
            # Login falhou: mantém a modal aberta e mostra erro
            error_msg = dbc.Alert("Usuário ou senha inválidos.", color="danger")
            return True, error_msg, no_update, user, ""
    
    return no_update, no_update, no_update, "", ""

# ## << NOVO: Callback para travar/destravar o switch (logout)
@app.callback(
    Output('admin-switch', 'disabled'),
    Input('admin-switch', 'value')
)
def control_admin_switch_lock(is_admin):
    # Se o switch for desligado (logout), ele é travado.
    # Se for ligado (login), ele é destravado.
    return not is_admin


# Callback de Adição (sem alterações lógicas)
@app.callback(
    Output("store-data", "data", allow_duplicate=True),
    Output("msg", "children"),
    Output("input-razao-social", "value"),
    Output("input-nome-fantasia", "value"),
    Output("input-cidade", "value"),
    Output("input-estado", "value"),
    Output("dropdown-vendedor", "value"),
    Input("btn-add", "n_clicks"),
    State("store-data", "data"),
    State("input-razao-social", "value"),
    State("input-nome-fantasia", "value"),
    State("input-cidade", "value"),
    State("input-estado", "value"),
    State("dropdown-vendedor", "value"),
    prevent_initial_call=True,
)
def add_record(n_clicks, data_atual, razao, fantasia, cidade, estado, vendedor):
    # ... (código da função sem alterações)
    missing = []
    if not razao: missing.append("Razão Social")
    if not fantasia: missing.append("Nome Fantasia")
    if not cidade: missing.append("Cidade")
    if not estado: missing.append("Estado")
    if not vendedor: missing.append("Vendedor")
    if missing:
        msg = dbc.Alert(f"Atenção! Preencha os campos obrigatórios: {', '.join(missing)}", color="danger")
        return no_update, msg, no_update, no_update, no_update, no_update, no_update
    data_atual = data_atual or []
    next_id = max(item.get('id', -1) for item in data_atual) + 1 if data_atual else 0
    novo_registro = {'id': next_id, "razao_social": razao, "nome_fantasia": fantasia, "cidade": cidade, "estado": estado.upper() if estado else None, "vendedor": vendedor, "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    data_atual.append(novo_registro)
    msg = dbc.Alert("Registro adicionado com sucesso!", color="success", duration=4000, dismissable=True)
    return data_atual, msg, "", "", "", "", None

# Callback da tabela (sem alterações lógicas)
@app.callback(
    Output("table-clientes", "data"),
    Output("table-clientes", "columns"),
    Input("store-data", "data"),
    Input("admin-switch", "value"),
)
def update_table(data_records, is_admin):
    # ... (código da função sem alterações)
    if not data_records:
        cols = [{"name": c.replace("_", " ").title(), "id": c} for c in COLUMNS]
        return [], cols
    display_data = [{k: v for k, v in row.items()} for row in data_records]
    if is_admin:
        for row in display_data: row['acao'] = f'[Excluir](#)'
        cols = [{"name": c.replace("_", " ").title(), "id": c} for c in COLUMNS]
        cols.append({"name": "Ação", "id": "acao", "presentation": "markdown"})
    else:
        cols = [{"name": c.replace("_", " ").title(), "id": c} for c in COLUMNS]
    return display_data, cols

# Callbacks de Exclusão (sem alterações lógicas)
@app.callback(
    Output('confirm-delete-dialog', 'displayed'),
    Output('store-delete-info', 'data'),
    Input('table-clientes', 'active_cell'),
    State('admin-switch', 'value'),
)
def display_delete_confirmation(active_cell, is_admin):
    # ... (código da função sem alterações)
    if not active_cell or not is_admin or active_cell['column_id'] != 'acao':
        return False, None
    return True, {'row_id': active_cell['row_id']}

@app.callback(
    Output('store-data', 'data', allow_duplicate=True),
    Output('store-delete-info', 'data', allow_duplicate=True),
    Input('confirm-delete-dialog', 'submit_n_clicks'),
    State('store-delete-info', 'data'),
    State('store-data', 'data'),
    prevent_initial_call=True
)
def perform_deletion(submit_n_clicks, delete_info, all_data):
    # ... (código da função sem alterações)
    if not submit_n_clicks or not delete_info or not all_data:
        return no_update, None
    row_id_to_delete = delete_info['row_id']
    updated_data = [record for record in all_data if record.get('id') != row_id_to_delete]
    return updated_data, None

# Callback de Métricas (sem alterações lógicas)
@app.callback(
    Output("graph-angela", "figure"), Output("kpi-angela", "children"),
    Output("graph-david", "figure"), Output("kpi-david", "children"),
    Input("store-data", "data"), Input("date-range", "start_date"),
    Input("date-range", "end_date"), Input("freq-radio", "value"),
)
def update_metrics(data, start_date, end_date, freq):
    # ... (código da função sem alterações)
    if not data: return empty_fig(), build_kpi_card("Total de Registros", 0), empty_fig(), build_kpi_card("Total de Registros", 0)
    df = pd.DataFrame(data)
    if df.empty: return empty_fig(), build_kpi_card("Total de Registros", 0), empty_fig(), build_kpi_card("Total de Registros", 0)
    df["data_registro"] = pd.to_datetime(df["data_registro"])
    if start_date: df = df[df["data_registro"] >= pd.to_datetime(start_date)]
    if end_date: df = df[df["data_registro"] < (pd.to_datetime(end_date) + pd.Timedelta(days=1))]
    freq_code, title_suffix, date_format = ("W-MON", "Semanal", "%d/%m/%Y") if freq == "W" else ("M", "Mensal", "%m/%Y")
    figs, kpis = [], []
    for vendedor, color in [("Angela", "primary"), ("David", "success")]:
        df_vendedor = df[df["vendedor"] == vendedor].copy()
        total_registros = len(df_vendedor)
        kpis.append(build_kpi_card("Total de Registros", total_registros, color=color))
        if total_registros == 0:
            figs.append(empty_fig(f"Sem dados para {vendedor}")); continue
        df_vendedor.set_index("data_registro", inplace=True)
        df_resampled = df_vendedor["vendedor"].resample(freq_code).count().reset_index(name="quantidade")
        df_resampled["periodo"] = df_resampled["data_registro"].dt.strftime(date_format)
        fig = px.bar(df_resampled, x="periodo", y="quantidade", text="quantidade", title=f"Registros por Período ({title_suffix})", labels={"periodo": "Período", "quantidade": "Quantidade"})
        fig.update_traces(marker_color=px.colors.qualitative.Plotly[0] if color == "primary" else px.colors.qualitative.Plotly[1], textposition="outside")
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0), yaxis_title=None, xaxis_title=None, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        figs.append(fig)
    return figs[0], kpis[0], figs[1], kpis[1]


if __name__ == "__main__":
    app.run(debug=True)
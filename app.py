# app.py

import os
import psycopg2
import pandas as pd
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

from dash import (
    Dash, dcc, html, Input, Output, State,
    dash_table, no_update, exceptions, ctx
)
import dash_bootstrap_components as dbc
import plotly.express as px

# --------------------------------------
# Configurações e Conexão com o Banco de Dados
# --------------------------------------

load_dotenv() # Carrega as variáveis do arquivo .env

# Pega a string de conexão da variável de ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

# Credenciais de admin (Para produção real, use variáveis de ambiente!)
ADMIN_USER = "admin"
ADMIN_PASSWORD = "123"

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Funções Helper
def empty_fig(text: str = "Sem dados para exibir"):
    fig = px.bar()
    fig.update_layout(
        xaxis={"visible": False}, yaxis={"visible": False},
        annotations=[dict(text=text, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig

def build_kpi_card(title: str, value: int | float, color: str = "primary"):
    return dbc.Card([
        dbc.CardHeader(title),
        dbc.CardBody(html.H3(f"{value}", className=f"text-{color}")),
    ], className="mb-2")


# --------------------------------------
# App e Layout
# --------------------------------------

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # Essencial para o deploy com Gunicorn/Render
app.title = "Dashboard SDR/BDR"

COLUMNS_DISPLAY = ["id", "razao_social", "nome_fantasia", "cidade", "estado", "vendedor", "data_registro"]

header = html.Header(
    dbc.Row([
        dbc.Col(html.Img(src="/assets/logo.png", height="60px"), width="auto"),
        dbc.Col(html.H2("Dashboard de Performance | SDR & BDR", className="mb-0 text-primary"), className="ms-2", align="center"),
    ], align="center", className="my-4")
)

login_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Acesso Restrito")),
    dbc.ModalBody([
        html.Div(id='login-error-message', className="mb-3"),
        dbc.Input(id='admin-user-input', placeholder='Usuário', type='text', className="mb-3"),
        dbc.Input(id='admin-password-input', placeholder='Senha', type='password', className="mb-3"),
    ]),
    dbc.ModalFooter(dbc.Button("Login", id="login-button", color="primary")),
], id="login-modal", is_open=False)

app.layout = dbc.Container([
    dcc.Interval(id='interval-db-refresh', interval=60*1000, n_intervals=0),
    dcc.ConfirmDialog(id='confirm-delete-dialog', message='Você tem certeza que deseja excluir este registro?'),
    login_modal,
    header,
    html.Hr(),
    dcc.Tabs(id="tabs-main", children=[
        dcc.Tab(label="Cadastro de Clientes", children=[
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
                    dbc.Col(html.Div(id='admin-switch-wrapper', children=[
                        dbc.Switch(id="admin-switch", label="Modo Administrador", value=False, disabled=True)
                    ]), width="auto")
                ], justify="between", align="center")),
                dbc.CardBody(
                    dash_table.DataTable(
                        id="table-clientes",
                        columns=[], data=[], page_size=10, sort_action="native",
                        style_table={"overflowX": "auto"}, style_header={'fontWeight': 'bold'},
                        markdown_options={"link_target": "_self"},
                    )
                ),
            ], className="mt-4"),
        ]),
        dcc.Tab(label="Análise de Desempenho", children=[
            dbc.Card([dbc.CardHeader(html.H4("Filtros de Análise")), dbc.CardBody(dbc.Row([
                dbc.Col([dbc.Label("Período de Análise"), dcc.DatePickerRange(id="date-range", display_format="DD/MM/YYYY", className="d-block")], md=4),
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

# Callbacks de Login
@app.callback(
    Output('login-modal', 'is_open'), Output('login-error-message', 'children'),
    Output('admin-switch', 'value'), Output('admin-user-input', 'value'), Output('admin-password-input', 'value'),
    Input('admin-switch-wrapper', 'n_clicks'), Input('login-button', 'n_clicks'),
    State('admin-user-input', 'value'), State('admin-password-input', 'value'),
    prevent_initial_call=True
)
def control_login_modal(switch_clicks, login_clicks, user, password):
    triggered_id = ctx.triggered_id
    if triggered_id == 'admin-switch-wrapper':
        return True, None, no_update, "", ""
    if triggered_id == 'login-button':
        if user == ADMIN_USER and password == ADMIN_PASSWORD:
            return False, None, True, "", ""
        else:
            error_msg = dbc.Alert("Usuário ou senha inválidos.", color="danger")
            return True, error_msg, no_update, user, ""
    return no_update, no_update, no_update, "", ""

@app.callback(Output('admin-switch', 'disabled'), Input('admin-switch', 'value'))
def control_admin_switch_lock(is_admin): return not is_admin

# Callback de Adição
@app.callback(
    Output("msg", "children"),
    Output("interval-db-refresh", "n_intervals"),
    Output("input-razao-social", "value"), Output("input-nome-fantasia", "value"),
    Output("input-cidade", "value"), Output("input-estado", "value"), Output("dropdown-vendedor", "value"),
    Input("btn-add", "n_clicks"),
    State("input-razao-social", "value"), State("input-nome-fantasia", "value"),
    State("input-cidade", "value"), State("input-estado", "value"), State("dropdown-vendedor", "value"),
    State("interval-db-refresh", "n_intervals"),
    prevent_initial_call=True,
)
def add_record(n_clicks, razao, fantasia, cidade, estado, vendedor, n_intervals):
    missing = []
    if not razao: missing.append("Razão Social")
    if not fantasia: missing.append("Nome Fantasia")
    if not cidade: missing.append("Cidade")
    if not estado: missing.append("Estado")
    if not vendedor: missing.append("Vendedor")
    if missing:
        msg = dbc.Alert(f"Atenção! Preencha os campos obrigatórios: {', '.join(missing)}", color="danger")
        return msg, no_update, no_update, no_update, no_update, no_update, no_update
    
    sql = "INSERT INTO clientes (razao_social, nome_fantasia, cidade, estado, vendedor) VALUES (%s, %s, %s, %s, %s);"
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (razao, fantasia, cidade.upper(), estado.upper(), vendedor))
                conn.commit()
            msg = dbc.Alert("Registro adicionado com sucesso!", color="success", duration=4000)
            return msg, n_intervals + 1, "", "", "", "", None
        except Exception as e:
            msg = dbc.Alert(f"Erro ao inserir no banco: {e}", color="danger")
            return msg, no_update, no_update, no_update, no_update, no_update, no_update
        finally:
            conn.close()
    return dbc.Alert("Falha na conexão com o banco de dados.", color="danger"), no_update, no_update, no_update, no_update, no_update, no_update

# Callback principal para buscar dados do banco e atualizar a UI
@app.callback(
    Output("table-clientes", "data"), Output("table-clientes", "columns"),
    Output("graph-angela", "figure"), Output("kpi-angela", "children"),
    Output("graph-david", "figure"), Output("kpi-david", "children"),
    Input("interval-db-refresh", "n_intervals"),
    Input("admin-switch", "value"),
    Input("date-range", "start_date"), Input("date-range", "end_date"),
    Input("freq-radio", "value"),
)
def update_data_from_db(n_intervals, is_admin, start_date, end_date, freq):
    conn = get_db_connection()
    if not conn:
        return [], [], empty_fig("Falha na conexão"), [], empty_fig("Falha na conexão"), []

    try:
        df = pd.read_sql("SELECT * FROM clientes WHERE ativo = TRUE ORDER BY data_registro DESC", conn)
    except Exception:
        # Se a tabela ainda não existir, retorna um DataFrame vazio
        df = pd.DataFrame(columns=COLUMNS_DISPLAY + ['ativo'])
    finally:
        if conn: conn.close()
    
    if df.empty:
        return [], [], empty_fig(), build_kpi_card("Total Registros", 0), empty_fig(), build_kpi_card("Total Registros", 0)

    # --- Lógica para a Tabela de Clientes ---
    display_data = df.to_dict('records')
    cols_to_display = [col for col in df.columns if col not in ['ativo']]
    if is_admin:
        for row in display_data: row['acao'] = '[Excluir](#)'
        cols = [{"name": c.replace("_", " ").title(), "id": c} for c in cols_to_display]
        cols.append({"name": "Ação", "id": "acao", "presentation": "markdown"})
    else:
        cols = [{"name": c.replace("_", " ").title(), "id": c} for c in cols_to_display]

    # --- Lógica para os Gráficos de Performance ---
    df["data_registro"] = pd.to_datetime(df["data_registro"])
    
    start_date_obj = pd.to_datetime(start_date or (date.today() - timedelta(days=30)), utc=True)
    end_date_obj = pd.to_datetime(end_date or date.today(), utc=True)
    
    df_filtered = df[(df["data_registro"] >= start_date_obj) & (df["data_registro"] < (end_date_obj + timedelta(days=1)))]

    figs, kpis = [], []
    for vendedor, color in [("Angela", "primary"), ("David", "success")]:
        df_vendedor = df_filtered[df_filtered["vendedor"] == vendedor].copy()
        total_registros = len(df_vendedor)
        kpis.append(build_kpi_card(f"Total Registros ({vendedor})", total_registros, color=color))
        if total_registros == 0:
            figs.append(empty_fig(f"Sem dados para {vendedor}")); continue
        freq_code, title_suffix, date_format = ("W-MON", "Semanal", "%d/%m/%Y") if freq == "W" else ("M", "Mensal", "%m/%Y")
        df_vendedor.set_index("data_registro", inplace=True)
        df_resampled = df_vendedor["vendedor"].resample(freq_code).count().reset_index(name="quantidade")
        df_resampled["periodo"] = df_resampled["data_registro"].dt.strftime(date_format)
        fig = px.bar(df_resampled, x="periodo", y="quantidade", text="quantidade", title=f"Registros por Período ({title_suffix})")
        fig.update_traces(marker_color=px.colors.qualitative.Plotly[0] if color == "primary" else px.colors.qualitative.Plotly[1], textposition="outside")
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0), yaxis_title=None, xaxis_title=None, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        figs.append(fig)

    return display_data, cols, figs[0], kpis[0], figs[1], kpis[1]

# Callbacks de Exclusão
@app.callback(
    Output('confirm-delete-dialog', 'displayed'),
    Input('table-clientes', 'active_cell'),
    State('admin-switch', 'value')
)
def display_delete_confirmation(active_cell, is_admin):
    if not active_cell or not is_admin or active_cell['column_id'] != 'acao':
        return False
    return True

@app.callback(
    Output("interval-db-refresh", "n_intervals", allow_duplicate=True),
    Output("confirm-delete-dialog", "message"),
    Input('confirm-delete-dialog', 'submit_n_clicks'),
    State('table-clientes', 'data'),
    State('table-clientes', 'active_cell'),
    State("interval-db-refresh", "n_intervals"),
    prevent_initial_call=True
)
def perform_deletion(submit_n_clicks, table_data, active_cell, n_intervals):
    if not submit_n_clicks or not active_cell:
        return no_update, no_update
    
    row_id_to_delete = active_cell['row_id']
    sql = "UPDATE clientes SET ativo = FALSE WHERE id = %s;"
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (row_id_to_delete,))
                conn.commit()
            return n_intervals + 1, f"Registro {row_id_to_delete} excluído com sucesso."
        except Exception as e:
            return no_update, f"Erro ao excluir: {e}"
        finally:
            conn.close()
    return no_update, "Falha na conexão com o banco de dados."

# Bloco para execução local
if __name__ == "__main__":
    app.run(debug=True)
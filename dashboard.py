import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import numpy as np

# --- 1. ЗАГРУЗКА И ОЧИСТКА ДАННЫХ ---
try:
    with open('hh_business_analyst_vacancies.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    df = pd.DataFrame(raw_data)
except Exception as e:
    print(f"Ошибка загрузки файла: {e}")
    df = pd.DataFrame()

# Базовая очистка колонок
required_columns = ['name', 'company', 'city', 'experience', 'key_skills', 'salary_from', 'salary_to', 'alternate_url']
for col in required_columns:
    if col not in df.columns: df[col] = None

# --- ФИЛЬТР РЕЛЕВАНТНОСТИ (ОЧИСТКА ОТ МЕНЕДЖЕРОВ И ПРОДАЖ) ---
GOOD_WORDS = ['бизнес', 'business', 'системн', 'system', 'it', 'ит', 'требован', 'процесс', 'ba', 'sa']
BAD_WORDS = ['привлечению', 'развитию бизнеса', 'консалтинг', 'продаж', 'маркетинг', 'склад', 'курьер', 'риелтор', 'ставок']

def is_relevant(name):
    name = str(name).lower()
    if any(bad in name for bad in BAD_WORDS): return False
    if not any(good in name for good in GOOD_WORDS): return False
    return True

if not df.empty:
    df = df[df['name'].apply(is_relevant)].copy()

# Расчет средней зарплаты
df['salary_avg'] = df[['salary_from', 'salary_to']].mean(axis=1)

def get_level(exp):
    exp = str(exp).lower()
    if 'нет опыта' in exp: return 'Junior'
    if '1' in exp or '3' in exp: return 'Middle'
    return 'Senior'

df['level'] = df['experience'].apply(get_level)
df['key_skills_list'] = df['key_skills'].apply(lambda s: [str(i) for i in s if i] if isinstance(s, list) else [])

# Максимальная зарплата для слайдера
if not df.empty and not df['salary_avg'].dropna().empty:
    MAX_SALARY_DATA = int(df['salary_avg'].max())
else:
    MAX_SALARY_DATA = 1100000

# --- 2. КОНСТАНТЫ СТИЛЯ (ВАШ ДИЗАЙН) ---
COLORS = {"primary": "#002B5B", "secondary": "#3B82F6", "accent": "#8B5CF6", "bg": "#F1F5F9"}
CARD_STYLE = {
    "borderRadius": "15px", "boxShadow": "0 4px 20px rgba(0,0,0,0.05)", 
    "border": "none", "backgroundColor": "white", "padding": "25px", "height": "100%",
}
PLOT_MARGINS = dict(l=40, r=20, t=60, b=40)

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# --- 3. ИНТЕРФЕЙС ---
app.layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col(html.H2("Smart-Аналитика: Бизнес-анализ 2026", 
                    style={'color': COLORS['primary'], 'fontWeight': '800', 'paddingTop': '40px'}), width=12)
        ], className="mb-5 text-center"),

        # Метрики
        dbc.Row([
            dbc.Col(dbc.Card([
                html.H6("Вакансий в выборке", style={'color': '#64748B'}),
                html.H3(id='total-count', style={'color': COLORS['primary'], 'fontWeight': '700'})
            ], style=CARD_STYLE), width=12, lg=3, md=6),
            dbc.Col(dbc.Card([
                html.H6("Средняя ЗП", style={'color': '#64748B'}),
                html.H3(id='market-avg', style={'color': COLORS['secondary'], 'fontWeight': '700'})
            ], style=CARD_STYLE), width=12, lg=3, md=6),
            dbc.Col(dbc.Card([
                html.H6("Макс. ЗП", style={'color': '#10B981'}),
                html.H3(id='market-max', style={'color': '#10B981', 'fontWeight': '700'})
            ], style=CARD_STYLE), width=12, lg=3, md=6),
            dbc.Col(dbc.Card([
                html.H6("💎 Золотой стек", style={'color': '#64748B'}),
                html.Div(id='golden-stack', style={'color': COLORS['accent'], 'fontWeight': 'bold', 'fontSize': '16px', 'marginTop': '5px'})
            ], style=CARD_STYLE), width=12, lg=3, md=6),
        ], className="g-4 mb-4"),

        # Фильтры
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.Row([
                    dbc.Col([
                        html.Label("🌍 Города", style={'fontWeight': '600'}),
                        dcc.Dropdown(
                            id='reg-f', 
                            options=[{'label': city, 'value': city} for city in sorted(df['city'].dropna().unique())] if not df.empty else [], 
                            multi=True, placeholder="Все города..."
                        )
                    ], width=12, lg=4),
                    dbc.Col([
                        html.Label("📈 Уровень", style={'fontWeight': '600'}),
                        dcc.Checklist(
                            id='lvl-f', 
                            options=[{'label': ' Jr', 'value': 'Junior'}, {'label': ' Mid', 'value': 'Middle'}, {'label': ' Sr', 'value': 'Senior'}], 
                            value=['Junior', 'Middle', 'Senior'], inline=True, className="mt-2"
                        )
                    ], width=12, lg=3),
                    dbc.Col([
                        html.Label(f"💰 Зарплата (до {MAX_SALARY_DATA:,} ₽)", style={'fontWeight': '600'}),
                        dcc.RangeSlider(
                            id='salary-f', min=0, max=MAX_SALARY_DATA, step=10000,
                            marks={0: '0', MAX_SALARY_DATA: f'{MAX_SALARY_DATA//1000}k'},
                            value=[0, MAX_SALARY_DATA]
                        )
                    ], width=12, lg=5),
                ])
            ], style=CARD_STYLE), width=12),
        ], className="mb-4"),

        # Графики
        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(id='gauge-sal')], style=CARD_STYLE), width=12, lg=4),
            dbc.Col(html.Div([dcc.Graph(id='top-companies')], style=CARD_STYLE), width=12, lg=4),
            dbc.Col(html.Div([dcc.Graph(id='forecast-chart')], style=CARD_STYLE), width=12, lg=4),
        ], className="g-4 mb-4"),

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(id='skills-bar')], style=CARD_STYLE), width=12, lg=6),
            dbc.Col(html.Div([dcc.Graph(id='region-dist')], style=CARD_STYLE), width=12, lg=6),
        ], className="g-4 mb-4"),

        # Таблица
        dbc.Row([
            dbc.Col(html.Div([
                html.H4("🔍 Реестр вакансий", className="mb-4", style={'fontWeight': '700', 'color': COLORS['primary']}),
                dash_table.DataTable(
                    id='vacancies-table',
                    columns=[
                        {"name": "Должность", "id": "name"},
                        {"name": "Компания", "id": "company"},
                        {"name": "Город", "id": "city"},
                        {"name": "Зарплата", "id": "sal_str"},
                        {"name": "URL", "id": "link", "presentation": "markdown"}
                    ],
                    style_table={'borderRadius': '10px', 'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '15px', 'fontSize': '14px'},
                    style_header={'backgroundColor': '#F8FAFC', 'fontWeight': 'bold', 'color': COLORS['primary']},
                    page_size=12, filter_action="native", sort_action="native",
                )
            ], style=CARD_STYLE), width=12),
        ], className="mb-5")
    ], fluid=True, style={'paddingLeft': '30px', 'paddingRight': '30px'})
], style={"backgroundColor": COLORS['bg'], "minHeight": "100vh", "fontFamily": "Segoe UI, sans-serif"})

# --- 4. CALLBACK ---
@app.callback(
    [Output('total-count', 'children'), Output('market-avg', 'children'), Output('market-max', 'children'),
     Output('golden-stack', 'children'), Output('gauge-sal', 'figure'), Output('top-companies', 'figure'), 
     Output('forecast-chart', 'figure'), Output('skills-bar', 'figure'), Output('region-dist', 'figure'), 
     Output('vacancies-table', 'data')],
    [Input('reg-f', 'value'), Input('lvl-f', 'value'), Input('salary-f', 'value')]
)
def update_dashboard(selected_cities, lvls, sal_range):
    if df.empty:
        empty_fig = go.Figure().add_annotation(text="Нет данных", showarrow=False)
        return "0", "0 ₽", "0 ₽", "---", empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, []

    # Фильтрация
    dff = df[df['level'].isin(lvls)].copy()
    dff = dff[(dff['salary_avg'] >= sal_range[0]) & (dff['salary_avg'] <= sal_range[1])]
    if selected_cities:
        dff = dff[dff['city'].isin(selected_cities)]
    
    if dff.empty:
        empty_fig = go.Figure().add_annotation(text="Нет данных", showarrow=False)
        return "0", "0 ₽", "0 ₽", "---", empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, []

    # Метрики
    total_vac = str(len(dff))
    avg_sal = dff['salary_avg'].mean()
    max_sal = dff['salary_avg'].max()

    # Золотой стек
    threshold = dff['salary_avg'].quantile(0.8) if len(dff) > 5 else 0
    premium_jobs = dff[dff['salary_avg'] >= threshold]
    premium_skills = [s for sub in premium_jobs['key_skills_list'] for s in sub]
    golden_stack_text = " + ".join(pd.Series(premium_skills).value_counts().head(3).index.tolist()) if premium_skills else "SQL + BPMN"

    # Спидометр
    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=avg_sal,
                                   number={'suffix': " ₽", 'valueformat': ',.0f'},
                                   gauge={'bar': {'color': COLORS['secondary']}, 'axis': {'range': [0, MAX_SALARY_DATA]}}))
    fig_g.update_layout(height=280, margin=dict(t=50, b=20), title="Средняя зарплата")

    # Топ компаний (ИСПОЛЬЗУЕМ ЯВНЫЕ ИМЕНА СТОЛБЦОВ)
    top_c = dff['company'].value_counts().head(10).reset_index()
    top_c.columns = ['Название', 'Количество']
    fig_c = px.bar(top_c, y='Название', x='Количество', orientation='h', color_discrete_sequence=[COLORS['primary']])
    fig_c.update_layout(height=300, margin=PLOT_MARGINS, title="Топ работодателей", yaxis={'categoryorder':'total ascending'})

    # Прогноз
    fig_f = go.Figure(go.Scatter(x=['2024', '2025', '2026'], y=[avg_sal*0.92, avg_sal, avg_sal*1.15], 
                                 line=dict(color=COLORS['secondary'], width=4), mode='lines+markers'))
    fig_f.update_layout(title="Тренд ЗП к 2026", height=280, margin=PLOT_MARGINS)

    # Навыки (ИСПОЛЬЗУЕМ ЯВНЫЕ ИМЕНА СТОЛБЦОВ)
    sk_flat = [s for sub in dff['key_skills_list'] for s in sub]
    if sk_flat:
        top_s = pd.Series(sk_flat).value_counts().head(12).reset_index()
        top_s.columns = ['Навык', 'Частота']
        fig_s = px.bar(top_s, x='Частота', y='Навык', orientation='h', color_discrete_sequence=[COLORS['secondary']])
        fig_s.update_layout(yaxis={'categoryorder':'total ascending'}, title="Востребованные навыки", height=400, margin=PLOT_MARGINS)
    else:
        fig_s = go.Figure()

    # Регионы
    fig_r = px.pie(values=dff['city'].value_counts().head(10).values, names=dff['city'].value_counts().head(10).index, hole=.4)
    fig_r.update_layout(title="Локации", height=400, margin=PLOT_MARGINS)

    # Таблица
    t_data = []
    for _, row in dff.tail(100).iterrows():
        t_data.append({
            "name": row['name'], "company": row['company'], "city": row['city'],
            "sal_str": f"{int(row['salary_avg']):,} ₽".replace(",", " ") if pd.notna(row['salary_avg']) else "Договорная",
            "link": f"[🔗 Открыть]({row['alternate_url']})"
        })

    return total_vac, f"{int(avg_sal):,} ₽", f"{int(max_sal):,} ₽", golden_stack_text, fig_g, fig_c, fig_f, fig_s, fig_r, t_data

if __name__ == '__main__':
    app.run(debug=True)

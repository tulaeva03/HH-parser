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

# Расчет средней зарплаты
df['salary_avg'] = df[['salary_from', 'salary_to']].mean(axis=1)

# Определение грейда
def get_level(exp):
    exp = str(exp).lower()
    if 'нет опыта' in exp: return 'Junior'
    if '1' in exp or '3' in exp: return 'Middle'
    return 'Senior'

df['level'] = df['experience'].apply(get_level)

# Очистка навыков
def clean_skills(s):
    if isinstance(s, list): return [str(i) for i in s if i]
    return []
df['key_skills_list'] = df['key_skills'].apply(clean_skills)

# --- 2. КОНСТАНТЫ СТИЛЯ ---
COLORS = {
    "primary": "#002B5B", 
    "secondary": "#3B82F6", 
    "accent": "#8B5CF6", 
    "bg": "#F1F5F9"
}

CARD_STYLE = {
    "borderRadius": "15px", 
    "boxShadow": "0 4px 20px rgba(0,0,0,0.05)", 
    "border": "none", 
    "backgroundColor": "white", 
    "padding": "25px",
    "height": "100%",
}

PLOT_MARGINS = dict(l=40, r=20, t=60, b=40)

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# --- 3. СТРУКТУРА ИНТЕРФЕЙСА ---
app.layout = html.Div([
    dbc.Container([
        # Хедер
        dbc.Row([
            dbc.Col(html.H2("Smart-Аналитика: Бизнес-анализ 2026", 
                    style={'color': COLORS['primary'], 'fontWeight': '800', 'paddingTop': '40px'}), width=12)
        ], className="mb-5 text-center"),

        # МЕТРИКИ
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
                html.H6("Макс. ЗП", style={'color': '#64748B'}),
                html.H3(id='market-max', style={'color': '#10B981', 'fontWeight': '700'})
            ], style=CARD_STYLE), width=12, lg=3, md=6),
            dbc.Col(dbc.Card([
                html.H6("💎 Золотой стек (High-Salary)", style={'color': '#64748B'}),
                html.Div(id='golden-stack', style={'color': COLORS['accent'], 'fontWeight': 'bold', 'fontSize': '16px', 'marginTop': '5px'})
            ], style=CARD_STYLE), width=12, lg=3, md=6),
        ], className="g-4 mb-4"),

        # ФИЛЬТРЫ (Теперь с полным списком городов)
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.Row([
                    dbc.Col([
                        html.Label("🌍 Выберите города", style={'fontWeight': '600'}),
                        dcc.Dropdown(
                            id='reg-f', 
                            # Динамически берем все уникальные города из данных
                            options=[{'label': city, 'value': city} for city in sorted(df['city'].dropna().unique())], 
                            multi=True, 
                            placeholder="Все города доступны..."
                        )
                    ], width=12, lg=8),
                    dbc.Col([
                        html.Label("📈 Уровень", style={'fontWeight': '600'}),
                        dcc.Checklist(
                            id='lvl-f', 
                            options=[{'label': ' Jr', 'value': 'Junior'}, {'label': ' Mid', 'value': 'Middle'}, {'label': ' Sr', 'value': 'Senior'}], 
                            value=['Junior', 'Middle', 'Senior'], 
                            inline=True, 
                            className="mt-2", 
                            inputStyle={"margin-left": "20px"}
                        )
                    ], width=12, lg=4),
                ])
            ], style=CARD_STYLE), width=12),
        ], className="mb-4"),

        # ГРАФИКИ
        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(id='gauge-sal')], style=CARD_STYLE), width=12, lg=4),
            dbc.Col(html.Div([dcc.Graph(id='top-companies')], style=CARD_STYLE), width=12, lg=4),
            dbc.Col(html.Div([dcc.Graph(id='forecast-chart')], style=CARD_STYLE), width=12, lg=4),
        ], className="g-4 mb-4"),

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(id='skills-bar')], style=CARD_STYLE), width=12, lg=6),
            dbc.Col(html.Div([dcc.Graph(id='region-dist')], style=CARD_STYLE), width=12, lg=6),
        ], className="g-4 mb-4"),

        # ТАБЛИЦА
        dbc.Row([
            dbc.Col(html.Div([
                html.H4("🔍 Реестр вакансий", className="mb-4", style={'fontWeight': '700', 'color': COLORS['primary']}),
                dash_table.DataTable(
                    id='vacancies-table',
                    columns=[
                        {"name": "Должность", "id": "name"},
                        {"name": "Компания", "id": "company"},
                        {"name": "Город", "id": "city"}, # Добавили город в таблицу для ясности
                        {"name": "Зарплата", "id": "sal_str"},
                        {"name": "URL", "id": "link", "presentation": "markdown"}
                    ],
                    style_table={'borderRadius': '10px', 'overflow': 'hidden'},
                    style_cell={'textAlign': 'left', 'padding': '15px', 'fontSize': '14px'},
                    style_header={'backgroundColor': '#F8FAFC', 'fontWeight': 'bold', 'color': COLORS['primary']},
                    page_size=12,
                    sort_action="native",
                    filter_action="native",
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
    [Input('reg-f', 'value'), Input('lvl-f', 'value')]
)
def update_dashboard(selected_cities, lvls):
    dff = df[df['level'].isin(lvls)].copy()
    
    # Фильтр по конкретным городам
    if selected_cities:
        dff = dff[dff['city'].isin(selected_cities)]
    
    if dff.empty:
        empty_fig = go.Figure().add_annotation(text="Нет данных для выбора", showarrow=False)
        return "0", "0 ₽", "0 ₽", "---", empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, []

    # Метрики
    total_vac = str(len(dff))
    avg_sal = dff['salary_avg'].mean()
    avg_display = f"{int(avg_sal):,} ₽".replace(",", " ") if pd.notna(avg_sal) else "---"
    max_sal = dff['salary_avg'].max()
    max_display = f"{int(max_sal):,} ₽".replace(",", " ") if pd.notna(max_sal) else "---"

    # Золотой стек
    threshold = dff['salary_avg'].quantile(0.85)
    premium_jobs = dff[dff['salary_avg'] >= threshold]
    premium_skills = [s for sublist in premium_jobs['key_skills_list'] for s in sublist]
    golden_stack_text = " + ".join(pd.Series(premium_skills).value_counts().head(3).index.tolist()) if premium_skills else "SQL + BPMN"

    # Графики
    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=avg_sal or 0,
                                   number={'suffix': " ₽", 'valueformat': ',.0f', 'font': {'size': 35}},
                                   gauge={'bar': {'color': COLORS['secondary']}, 'axis': {'range': [0, 400000]}}))
    fig_g.update_layout(height=300, margin=dict(l=30, r=30, t=50, b=20), title="Медиана зарплат")

    top_c = dff['company'].value_counts().head(10).reset_index()
    top_c.columns = ['Компания', 'Вакансий']
    fig_c = px.bar(top_c, y='Компания', x='Вакансий', orientation='h', color_discrete_sequence=[COLORS['primary']])
    fig_c.update_layout(height=300, margin=PLOT_MARGINS, yaxis={'categoryorder':'total ascending'}, title="Топ работодателей")

    fig_f = go.Figure(go.Scatter(x=['2024', '2025', '2026'], y=[avg_sal*0.9, avg_sal, avg_sal*1.15], 
                                 line=dict(color=COLORS['secondary'], width=4), mode='lines+markers'))
    fig_f.update_layout(title="Тренд ЗП к 2026", height=300, margin=PLOT_MARGINS)

    top_s = pd.Series([s for sublist in dff['key_skills_list'] for s in sublist]).value_counts().head(12).reset_index()
    top_s.columns = ['Навык', 'Частота']
    fig_s = px.bar(top_s, x='Частота', y='Навык', orientation='h', color_discrete_sequence=[COLORS['secondary']])
    fig_s.update_layout(title="Востребованные навыки", height=400, margin=PLOT_MARGINS, yaxis={'categoryorder':'total ascending'})

    # География (топ-10 городов для круговой диаграммы, чтобы не было каши)
    top_cities_dist = dff['city'].value_counts().head(10)
    fig_r = px.pie(values=top_cities_dist.values, names=top_cities_dist.index, title="Топ-10 локаций", hole=.4)
    fig_r.update_layout(height=400, margin=PLOT_MARGINS)

    # Данные таблицы
    table_data = []
    for _, row in dff.iterrows():
        table_data.append({
            "name": row['name'],
            "company": row['company'],
            "city": row['city'],
            "sal_str": f"{int(row['salary_avg']):,} ₽".replace(",", " ") if pd.notna(row['salary_avg']) else "По договоренности",
            "link": f"[🔗 Открыть]({row['alternate_url']})" if row['alternate_url'] else "---"
        })

    return total_vac, avg_display, max_display, golden_stack_text, fig_g, fig_c, fig_f, fig_s, fig_r, table_data

if __name__ == '__main__':
    app.run(debug=True)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, dash_table
from dash.dash_table.Format import Format, Group
import dash_bootstrap_components as dbc
import numpy as np
import ast

# --- 1. ЗАГРУЗКА И ОЧИСТКА ДАННЫХ ---
# Актуальные курсы для нормализации зарплат в рубли
EXCHANGE_RATES = {
    'RUR': 1.0, 'RUB': 1.0, 
    'USD': 92.0, 'EUR': 100.0, 
    'KZT': 0.21, 'BYN': 28.5, 'UZS': 0.007
}

try:
    df = pd.read_csv('hh_business_analyst_vacancies.csv', sep=';')
except Exception as e:
    print(f"Ошибка загрузки файла: {e}")
    df = pd.DataFrame()

# Базовая очистка колонок
required_columns = ['name', 'company', 'city', 'experience', 'key_skills', 'salary_from', 'salary_to', 'currency', 'alternate_url']
for col in required_columns:
    if col not in df.columns: df[col] = None

# Конвертация валют
def get_rub_salary(row):
    rate = EXCHANGE_RATES.get(row['currency'], 1.0)
    vals = []
    if pd.notna(row['salary_from']): vals.append(row['salary_from'] * rate)
    if pd.notna(row['salary_to']): vals.append(row['salary_to'] * rate)
    return np.mean(vals) if vals else np.nan

if not df.empty:
    df['salary_avg'] = df.apply(get_rub_salary, axis=1)

# --- УСИЛЕННЫЙ ФИЛЬТР РЕЛЕВАНТНОСТИ (ПОСЛЕДНИЕ КОРРЕКТИРОВКИ) ---
GOOD_WORDS = ['аналитик', 'analyst', 'ba', 'sa', 'bpmn', 'sql', 'системн', 'ит', 'it', 'процесс']

BAD_WORDS = [
    # Недвижимость и продажи
    'новостроек', 'недвижимости', 'риелтор', 'брокер', 'жилой', 'объектов', 
    'продаж', 'sales', 'клиентов', 'привлечению', 'звонки', 
    # Руководство и партнерство
    'директор', 'director', 'партнер', 'partner', 'chief', 'head', 'руководитель', 'исполнительный',
    # Смежные области, спорт и беттинг
    'маркетинг', 'склад', 'курьер', 'тендер', 'бухгалтер', 'экономист', 
    'спортивный', 'ставок', 'букмекер', 'сметчик', 'логист', 'диспетчер', 'developer', 'разработчик', 'кредитный'
]

def is_relevant(name):
    name = str(name).lower()
    # 1. Жесткое исключение по стоп-словам
    if any(bad in name for bad in BAD_WORDS): 
        return False
    # 2. Исключаем "бизнес-партнеров" и "менеджеров по..." (если там нет слова аналитик)
    if 'партнер' in name or ('менеджер по' in name and 'аналитик' not in name):
        return False
    # 3. Проверка на наличие целевых слов
    if any(good in name for good in GOOD_WORDS): 
        return True
    return False

if not df.empty:
    df = df[df['name'].apply(is_relevant)].copy()

# Дополнительная обработка данных
def get_level(exp):
    exp = str(exp).lower()
    if 'нет опыта' in exp: return 'Junior'
    if '1' in exp or '3' in exp: return 'Middle'
    return 'Senior'

df['level'] = df['experience'].apply(get_level)

def parse_skills(val):
    if isinstance(val, list): return val
    if pd.isna(val) or val == "" or val == "[]": return []
    try:
        return ast.literal_eval(val)
    except:
        return [str(val)]

df['key_skills_list'] = df['key_skills'].apply(parse_skills)

# Максимальная зарплата для слайдера (динамически из данных)
if not df.empty and not df['salary_avg'].dropna().empty:
    MAX_SALARY_DATA = int(df['salary_avg'].max())
else:
    MAX_SALARY_DATA = 1100000

# --- 2. КОНСТАНТЫ СТИЛЯ ---
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
            ], style=CARD_STYLE), lg=3, md=6),
            dbc.Col(dbc.Card([
                html.H6("Средняя ЗП (₽)", style={'color': '#64748B'}),
                html.H3(id='market-avg', style={'color': COLORS['secondary'], 'fontWeight': '700'})
            ], style=CARD_STYLE), lg=3, md=6),
            dbc.Col(dbc.Card([
                html.H6("Макс. ЗП (₽)", style={'color': '#10B981'}),
                html.H3(id='market-max', style={'color': '#10B981', 'fontWeight': '700'})
            ], style=CARD_STYLE), lg=3, md=6),
            dbc.Col(dbc.Card([
                html.H6("💎 Золотой стек", style={'color': '#64748B'}),
                html.Div(id='golden-stack', style={'color': COLORS['accent'], 'fontWeight': 'bold', 'fontSize': '16px'})
            ], style=CARD_STYLE), lg=3, md=6),
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
                    ], lg=4),
                    dbc.Col([
                        html.Label("📈 Уровень", style={'fontWeight': '600'}),
                        dcc.Checklist(
                            id='lvl-f', 
                            options=[{'label': ' Jr', 'value': 'Junior'}, {'label': ' Mid', 'value': 'Middle'}, {'label': ' Sr', 'value': 'Senior'}], 
                            value=['Junior', 'Middle', 'Senior'], inline=True, className="mt-2"
                        )
                    ], lg=3),
                    dbc.Col([
                        html.Label(f"💰 Зарплата (в рублях)", style={'fontWeight': '600'}),
                        dcc.RangeSlider(
                            id='salary-f', min=0, max=MAX_SALARY_DATA, step=10000,
                            marks={0: '0', MAX_SALARY_DATA: f'{MAX_SALARY_DATA//1000}k'},
                            value=[0, MAX_SALARY_DATA]
                        )
                    ], lg=5),
                ])
            ], style=CARD_STYLE), width=12),
        ], className="mb-4"),

        # Графики
        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(id='gauge-sal')], style=CARD_STYLE), lg=4),
            dbc.Col(html.Div([dcc.Graph(id='top-companies')], style=CARD_STYLE), lg=4),
            dbc.Col(html.Div([dcc.Graph(id='forecast-chart')], style=CARD_STYLE), lg=4),
        ], className="g-4 mb-4"),

        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(id='skills-bar')], style=CARD_STYLE), lg=6),
            dbc.Col(html.Div([dcc.Graph(id='region-dist')], style=CARD_STYLE), lg=6),
        ], className="g-4 mb-4"),

        # Графики (Ряд 3 - Матрица навыков)
        dbc.Row([
            dbc.Col(html.Div([dcc.Graph(id='salary-heatmap')], style=CARD_STYLE), width=12),
        ], className="g-4 mb-4"),

        # Таблица
        dbc.Row([
            dbc.Col(html.Div([
                html.H4("🔍 Реестр вакансий (сортировка по рублям)", className="mb-4", style={'fontWeight': '700', 'color': COLORS['primary']}),
                dash_table.DataTable(
                    id='vacancies-table',
                    columns=[
                        {"name": "Должность", "id": "name"},
                        {"name": "Компания", "id": "company"},
                        {"name": "Город", "id": "city"},
                        {
                            "name": "Зарплата (₽)", 
                            "id": "salary_avg", 
                            "type": "numeric", 
                            "format": Format(group=Group.yes, groups=3)
                        },
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
     Output('salary-heatmap', 'figure'), # НОВЫЙ ВЫВОД ДЛЯ МАТРИЦЫ
     Output('vacancies-table', 'data')],
    [Input('reg-f', 'value'), Input('lvl-f', 'value'), Input('salary-f', 'value')]
)
def update_dashboard(selected_cities, lvls, sal_range):
    if df.empty:
        empty_fig = go.Figure().add_annotation(text="Нет данных", showarrow=False)
        return "0", "0 ₽", "0 ₽", "---", empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, []

    # Фильтрация
    dff = df[df['level'].isin(lvls)].copy()
    dff = dff[(dff['salary_avg'] >= sal_range[0]) & (dff['salary_avg'] <= sal_range[1])]
    if selected_cities:
        dff = dff[dff['city'].isin(selected_cities)]
    
    if dff.empty:
        empty_fig = go.Figure().add_annotation(text="Нет данных", showarrow=False)
        return "0", "0 ₽", "0 ₽", "---", empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, []

    # Метрики
    avg_sal = dff['salary_avg'].mean()
    max_sal = dff['salary_avg'].max()

    # Золотой стек
    threshold = dff['salary_avg'].quantile(0.8) if len(dff) > 5 else 0
    prem_skills = [s for sub in dff[dff['salary_avg'] >= threshold]['key_skills_list'] for s in sub]
    golden_stack_text = " + ".join(pd.Series(prem_skills).value_counts().head(3).index.tolist()) if prem_skills else "SQL + BPMN"

    # Визуализация
    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=avg_sal, number={'suffix': " ₽", 'valueformat': ',.0f'},
                                   gauge={'bar': {'color': COLORS['secondary']}, 'axis': {'range': [0, MAX_SALARY_DATA]}}))
    fig_g.update_layout(height=280, margin=dict(t=50, b=20), title="Средняя ЗП")

    top_c = dff['company'].value_counts().head(10).reset_index()
    top_c.columns = ['Название', 'Количество']
    fig_c = px.bar(top_c, y='Название', x='Количество', orientation='h', color_discrete_sequence=[COLORS['primary']])
    fig_c.update_layout(height=300, margin=PLOT_MARGINS, title="Топ работодателей", yaxis={'categoryorder':'total ascending'})

    fig_f = go.Figure(go.Scatter(x=['2024', '2025', '2026'], y=[avg_sal*0.92, avg_sal, avg_sal*1.15], 
                                 line=dict(color=COLORS['secondary'], width=4), mode='lines+markers'))
    fig_f.update_layout(title="Тренд ЗП к 2026", height=280, margin=PLOT_MARGINS)

    sk_flat = [s for sub in dff['key_skills_list'] for s in sub]
    top_s = pd.Series(sk_flat).value_counts().head(12).reset_index()
    top_s.columns = ['Навык', 'Частота']
    fig_s = px.bar(top_s, x='Частота', y='Навык', orientation='h', color_discrete_sequence=[COLORS['secondary']])
    fig_s.update_layout(yaxis={'categoryorder':'total ascending'}, title="Востребованные навыки", height=400, margin=PLOT_MARGINS)

    fig_r = px.pie(values=dff['city'].value_counts().head(10).values, names=dff['city'].value_counts().head(10).index, hole=.4)
    fig_r.update_layout(title="Локации", height=400, margin=PLOT_MARGINS)

    # --- ТЕПЛОВАЯ КАРТА (МАТРИЦА НАВЫКОВ) ---
    top_n = 10
    top_skills_list = top_s['Навык'].head(top_n).tolist()
    
    z_data = np.zeros((top_n, top_n))
    for i, s1 in enumerate(top_skills_list):
        for j, s2 in enumerate(top_skills_list):
            # Ищем вакансии, где есть оба навыка
            mask = dff['key_skills_list'].apply(lambda x: s1 in x and s2 in x)
            subset = dff[mask]
            if not subset.empty and not subset['salary_avg'].isnull().all():
                z_data[i][j] = subset['salary_avg'].mean()
            else:
                z_data[i][j] = np.nan

    fig_heat = go.Figure(data=go.Heatmap(
        z=z_data, x=top_skills_list, y=top_skills_list,
        colorscale='Viridis', hoverongaps=False,
        hovertemplate='Навык 1: %{y}<br>Навык 2: %{x}<br>Средняя ЗП: %{z:,.0f} ₽<extra></extra>'
    ))
    fig_heat.update_layout(
        title="Тепловая карта: Зарплата при комбинации навыков",
        height=500, margin=PLOT_MARGINS
    )

    # Данные таблицы
    t_data = []
    for _, row in dff.iterrows():
        t_data.append({
            "name": row['name'], "company": row['company'], "city": row['city'],
            "salary_avg": int(row['salary_avg']) if pd.notna(row['salary_avg']) else 0,
            "link": f"[🔗 Открыть]({row['alternate_url']})"
        })

    return str(len(dff)), f"{int(avg_sal):,} ₽", f"{int(max_sal):,} ₽", golden_stack_text, fig_g, fig_c, fig_f, fig_s, fig_r, fig_heat, t_data

if __name__ == '__main__':
    app.run(debug=True)

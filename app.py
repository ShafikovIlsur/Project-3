from dash import Dash, Input, Output, State, html, dcc, no_update, ctx, MATCH, ALL
import plotly.express as px
import dash_bootstrap_components as dbc
import pandas as pd
from dash.exceptions import PreventUpdate
from get_weather import get_coords_by_address, get_weather_by_coords

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

cities = pd.DataFrame(columns=['city', 'lat', 'lon'])

mapbox = px.scatter_mapbox(width=500, height=500, lat=[], lon=[], zoom=3)
mapbox.update_layout(showlegend=False, mapbox_style="open-street-map")
mapbox.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

app.layout = html.Div([
    dbc.Container([
        html.H3("Прогноз погоды для заданного маршрута", className='text-center', style={'margin-bottom': 50}),
        dbc.Row([
            dbc.Col([
                html.H6('Введите город для добавления в маршрут'),
                dbc.Row([
                    dbc.Col([
                        dbc.Input(id='city-input', placeholder="Введите название города", style={'max-width': 400}),
                        html.H6('Выберите дневной диапазон прогноза:', style={'margin-top': 10}),
                        dbc.RadioItems(['1', '5', '10', '15'], value='1', id='range'),
                        html.H6('Текущий маршрут:', style={'margin-top': 10}),
                        html.Ul([], id='list-of-cities', style={'padding': 0})
                    ]),
                    dbc.Col(
                        dbc.Button('Добавить', id='add', className='btn', n_clicks=0,
                                   style={'background-color': 'green', 'color': 'white'})
                    )
                ]),
                dbc.Tabs(id='weather-tabs', active_tab='temperature', children=[
                    dbc.Tab(label='Температура', tab_id='temperature'),
                    dbc.Tab(label='Влажность', tab_id='humidity'),
                    dbc.Tab(label='Скорость ветра', tab_id='wind_speed'),
                    dbc.Tab(label='Вероятность дождя', tab_id='rain_probability')
                ]),
                dcc.Graph(
                    id='weather-graph',
                    style={
                        'height': '300px',
                        'width': '100%',
                        'margin-left': '0'
                    }
                )
            ]),
            dbc.Col([
                dcc.Graph(id='map', figure=mapbox, style={'height': '500px'})
            ])
        ])
    ])
])


@app.callback(
    [Output('list-of-cities', 'children'), Output('map', 'figure')],
    [Input('add', 'n_clicks'), Input({'type': 'delete', 'index': ALL}, 'n_clicks')],
    [State('city-input', 'value'), State('range', 'value')]
)
def manage_cities(add_clicks, delete_clicks, input_value, range_value):
    global cities, mapbox

    triggered_id = ctx.triggered_id

    if triggered_id == 'add' and add_clicks:
        if not input_value:
            return no_update, no_update

        if input_value in cities['city'].values:
            print(f"Город '{input_value}' уже добавлен.")
            return no_update, no_update

        try:
            lat, lon = get_coords_by_address(input_value)
            new_city = pd.DataFrame([{'city': input_value, 'lat': lat, 'lon': lon}])
            cities = pd.concat([cities, new_city], ignore_index=True)
        except Exception as e:
            print(f"Ошибка добавления: {e}")
            return no_update, no_update

    elif isinstance(triggered_id, dict) and triggered_id['type'] == 'delete':
        index_to_remove = triggered_id['index']
        if index_to_remove < len(cities):
            cities = cities.drop(index=index_to_remove).reset_index(drop=True)

    city_list = [
        html.Li([
            f"{row['city']}",
            html.Span("✖", id={'type': 'delete', 'index': i}, className='delete-cross',
                      style={'margin-left': 10, 'color': 'red', 'cursor': 'pointer'})
        ], style={
            'list-style-type': 'none', 'display': 'flex', 'justify-content': 'space-between',
            'align-items': 'center', 'border-bottom': '1px solid #ddd', 'max-width': 400
        }) for i, row in cities.iterrows()
    ]

    if not cities.empty:
        mapbox = px.line_mapbox(cities, lat='lat', lon='lon', hover_name='city', zoom=3)
        mapbox.update_traces(mode='markers+lines')
    else:
        mapbox = px.scatter_mapbox(width=500, height=500, lat=[], lon=[], zoom=3)

    mapbox.update_layout(showlegend=False, mapbox_style="open-street-map")
    mapbox.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return city_list, mapbox


@app.callback(
    Output('weather-graph', 'figure'),
    [Input('map', 'clickData'), Input('weather-tabs', 'active_tab')],
    State('range', 'value')
)
def update_weather_graph(clickData, active_tab, range_value):
    if clickData is None:
        print("clickData отсутствует")
        raise PreventUpdate

    print(f"Получено clickData: {clickData}")

    try:
        city_clicked = clickData['points'][0]['hovertext']
    except (KeyError, IndexError) as e:
        print(f"Ошибка извлечения города из clickData: {e}")
        raise PreventUpdate

    print(f"Выбранный город: {city_clicked}")

    city_data = cities[cities['city'] == city_clicked]
    if city_data.empty:
        print(f"Данные о городе {city_clicked} не найдены в DataFrame")
        raise PreventUpdate

    lat = city_data.iloc[0]['lat']
    lon = city_data.iloc[0]['lon']

    print(f"Координаты города: lat={lat}, lon={lon}")

    try:
        weather = get_weather_by_coords(lat, lon, int(range_value))
    except Exception as e:
        print(f"Ошибка получения прогноза погоды: {e}")
        raise PreventUpdate

    print(f"Прогноз погоды: {weather}")

    if not isinstance(weather, dict):
        print("Прогноз погоды имеет неверный формат")
        raise PreventUpdate

    weather_df = pd.DataFrame(weather)
    weather_df['day'] = range(1, int(range_value) + 1)

    if active_tab not in weather_df.columns:
        print(f"Нет данных для вкладки: {active_tab}")
        return px.line(title=f'Нет данных для категории: {active_tab.capitalize()}')

    fig = px.line(weather_df, x='day', y=active_tab, markers=True)
    fig.update_layout(
        title=f'{active_tab.capitalize()} для {city_clicked}',
        xaxis_title='День',
        yaxis_title='Значение'
    )
    return fig


if __name__ == '__main__':
    app.run_server()

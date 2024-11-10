import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_leaflet as dl
import pandas as pd
from geopy.distance import geodesic
import heapq
import os

# Cargar los datos y reiniciar los índices
df_cobertura = pd.read_csv('data/dataset_con_coordenadas.csv').reset_index(drop=True)
df_sin_cobertura = pd.read_csv('data/sinCoberturaCusco.csv').reset_index(drop=True)

# Crear listas de opciones para los dropdowns
opciones_inicio = [{'label': f"{row['DISTRITO']} ({row['Latitude']}, {row['Longitude']})", 'value': idx} for idx, row in df_cobertura.iterrows()]

# Crear la aplicación Dash
app = dash.Dash(__name__)

# Verificar si el archivo de usuarios existe, sino crear uno
if not os.path.exists('data/usuarios.csv'):
    pd.DataFrame(columns=["username", "password"]).to_csv('data/usuarios.csv', index=False)

usuarios = pd.read_csv("data/usuarios.csv")

# Layout de la aplicación
app.layout = html.Div(id="main-layout", children=[
    # Sección de autenticación y registro
    html.Div(id="auth-layout", children=[
        html.H1("Bienvenido"),
        dcc.Tabs(id="auth-tabs", value="login", children=[
            dcc.Tab(label="Iniciar Sesión", value="login", children=[
                html.Div([
                    html.Label("Usuario:"),
                    dcc.Input(id="login-username", type="text", placeholder="Ingrese su usuario"),
                    html.Br(),
                    html.Label("Contraseña:"),
                    dcc.Input(id="login-password", type="password", placeholder="Ingrese su contraseña"),
                    html.Br(),
                    html.Button("Ingresar", id="login-button"),
                    html.Div(id="login-error", style={"color": "red"})
                ])
            ]),
            dcc.Tab(label="Registrar Usuario", value="register", children=[
                html.Div([
                    html.Label("Nuevo Usuario:"),
                    dcc.Input(id="register-username", type="text", placeholder="Ingrese su usuario"),
                    html.Br(),
                    html.Label("Nueva Contraseña:"),
                    dcc.Input(id="register-password", type="password", placeholder="Ingrese su contraseña"),
                    html.Br(),
                    html.Button("Registrar", id="register-button"),
                    html.Div(id="register-error", style={"color": "red"})
                ])
            ])
        ])
    ]),
    # Layout de la aplicación (oculto hasta que el usuario inicie sesión)
    html.Div(id="app-layout", style={"display": "none"}, children=[
        html.H1("Ruta de Conexión entre Puntos con y sin Cobertura de Agua"),
        html.Label("Selecciona un punto de inicio (con cobertura):"),
        dcc.Dropdown(id='punto-inicio', options=opciones_inicio, placeholder="Elige un punto de inicio"),
    
        html.Label("Selecciona la distancia:"),
        dcc.Dropdown(id='distancia', options=[
            {'label': 'Cercano', 'value': 'cercanas'},
            {'label': 'Intermedio', 'value': 'intermedias'},
            {'label': 'Alejado', 'value': 'alejadas'}
        ], placeholder="Elige una distancia"),
    
        html.Label("Selecciona un punto de llegada (sin cobertura):"),
        dcc.Dropdown(id='punto-fin', options=[], placeholder="Elige un punto de llegada"),
    
        dl.Map([
            dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
        
            # Capa para los puntos de cobertura (azul)
            dl.LayerGroup(id='puntos-cobertura'),
        
            # Capa para los puntos sin cobertura (rojo)
            dl.LayerGroup(id='puntos-sin-cobertura'),
        
            # Capa para la ruta calculada
            dl.LayerGroup(id='ruta-camino')
        
        ], style={'width': '100%', 'height': '600px'}, center=[-13.5, -71.97], zoom=8)
    ])
])

# Actualizar los puntos en el mapa
@app.callback(
    [Output('puntos-cobertura', 'children'),
     Output('puntos-sin-cobertura', 'children')],
    [Input('punto-inicio', 'value')]
)
def mostrar_puntos(punto_inicio):
    puntos_cobertura = [
        dl.CircleMarker(center=[row['Latitude'], row['Longitude']], color='blue', radius=5,
                        children=dl.Tooltip(f"{row['DISTRITO']}"))
        for idx, row in df_cobertura.iterrows()
    ]
    puntos_sin_cobertura = [
        dl.CircleMarker(center=[row['Latitude'], row['Longitude']], color='red', radius=5,
                        children=dl.Tooltip(f"{row['DISTRITO']}"))
        for idx, row in df_sin_cobertura.iterrows()
    ]
    return puntos_cobertura, puntos_sin_cobertura

# Actualizar las opciones del dropdown de provincias en función de la distancia seleccionada
@app.callback(
    Output('punto-fin', 'options'),
    [Input('punto-inicio', 'value'), Input('distancia', 'value')]
)
def actualizar_opciones_fin(punto_inicio, distancia):
    if punto_inicio is None or distancia is None:
        return []

    # Obtener las coordenadas del punto de inicio seleccionado
    inicio_coords = (df_cobertura.loc[punto_inicio, 'Latitude'], df_cobertura.loc[punto_inicio, 'Longitude'])
    
    # Filtrar las provincias en función de la distancia seleccionada
    if distancia == 'cercanas':
        max_distancia = 20000  
    elif distancia == 'intermedias':
        max_distancia = 50000  
    else:
        max_distancia = 100000  

    opciones_fin = [
        {'label': f"{row['DISTRITO']} ({row['Latitude']}, {row['Longitude']})", 'value': idx}
        for idx, row in df_sin_cobertura.iterrows()
        if geodesic(inicio_coords, (row['Latitude'], row['Longitude'])).meters <= max_distancia
    ]
    
    return opciones_fin

# Callback para registrar un nuevo usuario
@app.callback(
    Output("register-error", "children"),
    Input("register-button", "n_clicks"),
    State("register-username", "value"),
    State("register-password", "value")
)
def register_user(n_clicks, username, password):
    if n_clicks:
        if not username or not password:
            return "El usuario y la contraseña no pueden estar vacíos."
        usuarios = pd.read_csv("usuarios.csv")
        if username in usuarios["username"].values:
            return "El usuario ya existe."
        # Agregar el nuevo usuario al archivo
        nuevos_datos = pd.DataFrame({"username": [username], "password": [password]})
        nuevos_datos.to_csv("data/usuarios.csv", mode="a", header=False, index=False)

        return "Usuario registrado exitosamente."
    return ""

# Callback para el inicio de sesión
@app.callback(
    [Output("app-layout", "style"), 
     Output("auth-layout", "style"),  
     Output("login-error", "children"),  
     Output("login-username", "value"),  
     Output("login-password", "value")], 
    [Input("login-button", "n_clicks")],
    [State("login-username", "value"), State("login-password", "value")]
)
def login_user(n_clicks, username, password):
    if n_clicks:
        usuarios = pd.read_csv("data/usuarios.csv")
        if username in usuarios["username"].values:
            if usuarios.loc[usuarios["username"] == username, "password"].values[0] == password:
                return {"display": "block"}, {"display": "none"}, "", "", ""
        # Error en el inicio de sesión: mostrar mensaje de error
        return {"display": "none"}, {"display": "block"}, "Usuario o contraseña incorrectos.", username, ""

    # Por defecto: mantener layout oculto
    return {"display": "none"}, {"display": "block"}, "", username, password


# Función para verificar la distancia directa
def direct_distance_check(start, end, max_distance=5000000):
    distance = geodesic(start, end).meters
    return distance <= max_distance

# Función Dijkstra para encontrar el camino más corto
def dijkstra(grafo, inicio, fin):
    heap = [(0, inicio)]
    distancias = {nodo: float("inf") for nodo in grafo}
    distancias[inicio] = 0
    caminos = {inicio: []}

    while heap:
        (distancia_actual, nodo_actual) = heapq.heappop(heap)
        
        if nodo_actual == fin:
            return caminos[fin] + [fin]
        
        for vecino, peso in grafo[nodo_actual]:
            distancia = distancia_actual + peso
            if distancia < distancias[vecino]:
                distancias[vecino] = distancia
                heapq.heappush(heap, (distancia, vecino))
                caminos[vecino] = caminos[nodo_actual] + [nodo_actual]
    
    return []

# Crear el grafo en base a las distancias entre nodos con un rango de 80 km
def construir_grafo(df, fin_coords, max_distancia=80000):
    grafo = {}
    destino_idx = len(df)  # Usar un índice entero para el destino
    puntos = [(idx, (row['Latitude'], 'Longitude')) for idx, row in df.iterrows()]
    puntos.append((destino_idx, fin_coords))  # Agregar el punto sin cobertura como destino

    for idx1, coord1 in puntos:
        conexiones = []
        for idx2, coord2 in puntos:
            if idx1 != idx2:
                distancia = geodesic(coord1, coord2).meters
                if distancia <= max_distancia:
                    conexiones.append((idx2, distancia))
        grafo[idx1] = conexiones

    return grafo, destino_idx

# Calcular la ruta y mostrarla en el mapa
@app.callback(
    Output('ruta-camino', 'children'),
    [Input('punto-inicio', 'value'), Input('punto-fin', 'value')]
)
def calcular_ruta(punto_inicio, punto_fin):
    if punto_inicio is None or punto_fin is None:
        return []

    # Obtener las coordenadas de los puntos de inicio y fin seleccionados
    inicio_coords = (df_cobertura.loc[punto_inicio, 'Latitude'], df_cobertura.loc[punto_inicio, 'Longitude'])
    fin_coords = (df_sin_cobertura.loc[punto_fin, 'Latitude'], df_sin_cobertura.loc[punto_fin, 'Longitude'])
    
    # Verificar si una conexión directa es posible
    if direct_distance_check(inicio_coords, fin_coords):
        # Dibujar una línea directa si están dentro del rango
        return [dl.Polyline(positions=[inicio_coords, fin_coords], color="green")]
    
    # Construir el grafo con un rango de 80 km para los nodos intermedios
    grafo, destino_idx = construir_grafo(df_cobertura, fin_coords, max_distancia=80000)
    
    # Calcular el camino más corto usando Dijkstra
    camino = dijkstra(grafo, punto_inicio, destino_idx)
    
    if not camino:
        return []  # Opcional: agregar un mensaje de que no se encontró camino

    # Crear la ruta en el mapa
    ruta = []
    for i in range(len(camino) - 1):
        nodo_actual = camino[i]
        siguiente_nodo = camino[i + 1]

        # Obtener coordenadas de cada par de nodos
        if nodo_actual == destino_idx:
            coord1 = fin_coords
        else:
            coord1 = (df_cobertura.loc[nodo_actual, 'Latitude'], df_cobertura.loc[nodo_actual, 'Longitude'])

        if siguiente_nodo == destino_idx:
            coord2 = fin_coords
        else:
            coord2 = (df_cobertura.loc[siguiente_nodo, 'Latitude'], df_cobertura.loc[siguiente_nodo, 'Longitude'])

        # Agregar la línea al mapa
        ruta.append(dl.Polyline(positions=[coord1, coord2], color="blue"))
    
    return ruta

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True)
#!/usr/bin/env python3
"""
Mine Armour - Real-time Multi-Sensor Dashboard
Displays real-time sensor data from MQTT broker
Sensors: Gas (LPG, CH4, Propane, Butane, H2), Heart Rate, Temperature, Humidity, GSR, GPS
"""

import os
import sys
import json
import time
import threading
import ssl
from datetime import datetime
from collections import deque
import logging

# Third-party imports
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SensorDataManager:
    """Manages real-time multi-sensor data storage and retrieval"""
    















































































































































































































































































































































































































































































































































































    def __init__(self, max_points=100):
        self.max_points = max_points
        self.data = {
            'gas_sensors': {
                'timestamps': deque(maxlen=max_points),
                'LPG': deque(maxlen=max_points),
                'CH4': deque(maxlen=max_points),
                'Propane': deque(maxlen=max_points),
                'Butane': deque(maxlen=max_points),
                'H2': deque(maxlen=max_points),
                'latest': {
                    'LPG': 0,
                    'CH4': 0,
                    'Propane': 0,
                    'Butane': 0,
                    'H2': 0,
                    'timestamp': None
                }
            },
            'health_sensors': {
                'timestamps': deque(maxlen=max_points),
                'heartRate': deque(maxlen=max_points),
                'spo2': deque(maxlen=max_points),
                'GSR': deque(maxlen=max_points),
                'stress': deque(maxlen=max_points),
            },
            'environmental_sensors': {
                'timestamps': deque(maxlen=max_points),
                'temperature': deque(maxlen=max_points),
                'humidity': deque(maxlen=max_points),
            },
            'gps_data': {
                'timestamps': deque(maxlen=max_points),
                'lat': deque(maxlen=max_points),
                'lon': deque(maxlen=max_points),
                'alt': deque(maxlen=max_points),
                'sat': deque(maxlen=max_points),
                'latest': {
                    'lat': 0.0,
                    'lon': 0.0,
                    'alt': 0.0,
                    'sat': 0
                }
            }
        }
        self.lock = threading.Lock()
    
    def add_gas_data(self, data):
        """Add new sensor data point"""
        with self.lock:
            timestamp = datetime.now()
            
            # Add gas sensor data
            self.data['gas_sensors']['timestamps'].append(timestamp)
            
            lpg = data.get('LPG', 0)
            ch4 = data.get('CH4', 0)
            propane = data.get('Propane', 0)
            butane = data.get('Butane', 0)
            h2 = data.get('H2', 0)
            
            self.data['gas_sensors']['LPG'].append(lpg)
            self.data['gas_sensors']['CH4'].append(ch4)
            self.data['gas_sensors']['Propane'].append(propane)
            self.data['gas_sensors']['Butane'].append(butane)
            self.data['gas_sensors']['H2'].append(h2)
            
            # Add health sensor data
            self.data['health_sensors']['timestamps'].append(timestamp)
            heartRate = data.get('heartRate', -1)
            spo2 = data.get('spo2', -1)
            gsr = data.get('GSR', 0)
            stress = data.get('stress', 0)
            
            self.data['health_sensors']['heartRate'].append(heartRate if heartRate != -1 else None)
            self.data['health_sensors']['spo2'].append(spo2 if spo2 != -1 else None)
            self.data['health_sensors']['GSR'].append(gsr)
            self.data['health_sensors']['stress'].append(stress)
            
            # Add environmental sensor data
            self.data['environmental_sensors']['timestamps'].append(timestamp)
            temperature = data.get('temperature', -1.0)
            humidity = data.get('humidity', -1.0)
            
            self.data['environmental_sensors']['temperature'].append(temperature if temperature != -1.0 else None)
            self.data['environmental_sensors']['humidity'].append(humidity if humidity != -1.0 else None)
            
            # Add GPS data
            self.data['gps_data']['timestamps'].append(timestamp)
            lat = data.get('lat', 0.0)
            lon = data.get('lon', 0.0)
            alt = data.get('alt', 0.0)
            sat = data.get('sat', 0)
            
            self.data['gps_data']['lat'].append(lat)
            self.data['gps_data']['lon'].append(lon)
            self.data['gps_data']['alt'].append(alt)
            self.data['gps_data']['sat'].append(sat)
            
            # Update latest values with ALL sensor data
            self.data['gas_sensors']['latest'] = {
                'LPG': lpg,
                'CH4': ch4,
                'Propane': propane,
                'Butane': butane,
                'H2': h2,
                'heartRate': heartRate,
                'spo2': spo2,
                'temperature': temperature,
                'humidity': humidity,
                'GSR': gsr,
                'stress': stress,
                'lat': lat,
                'lon': lon,
                'alt': alt,
                'sat': sat,
                'timestamp': timestamp
            }
            
            # Update GPS latest
            self.data['gps_data']['latest'] = {
                'lat': lat,
                'lon': lon,
                'alt': alt,
                'sat': sat
            }
            
            logging.info(f"All sensor data updated: Gas={lpg:.2f}, GPS=({lat:.6f},{lon:.6f}), Health=HR:{heartRate},SpO2:{spo2}")
    
    def get_gas_data(self):
        """Get gas sensor data for plotting"""
        with self.lock:
            return self.data['gas_sensors'].copy()
    
    def get_health_data(self):
        """Get health sensor data for plotting"""
        with self.lock:
            return self.data['health_sensors'].copy()
    
    def get_environmental_data(self):
        """Get environmental sensor data for plotting"""
        with self.lock:
            return self.data['environmental_sensors'].copy()
    
    def get_gps_data(self):
        """Get GPS data for mapping"""
        with self.lock:
            return self.data['gps_data'].copy()

class MQTTClient:
    """MQTT client for receiving gas sensor data"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.client = None
        self.connected = False
        
        # MQTT Configuration from environment
        self.mqtt_host = os.getenv("MQTT_HOST")
        self.mqtt_port = int(os.getenv("MQTT_PORT", 8883))
        self.mqtt_username = os.getenv("MQTT_USERNAME")
        self.mqtt_password = os.getenv("MQTT_PASSWORD")
        
        # Gas sensor topic
        self.gas_topic = "LOKI_2004"
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logging.info("Connected to MQTT broker")
            # Subscribe to gas sensor topic
            client.subscribe(self.gas_topic)
            logging.info(f"Subscribed to {self.gas_topic}")
        else:
            logging.error(f"Failed to connect to MQTT broker: {rc}")
    
    def on_message(self, client, userdata, message):
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')
            
            if topic == self.gas_topic:
                # Parse gas sensor JSON data
                data = json.loads(payload)
                self.data_manager.add_gas_data(data)
                logging.info(f"Received gas data: {data}")
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        logging.info("Disconnected from MQTT broker")
    
    def connect(self):
        try:
            # Fix: Add callback_api_version parameter for newer paho-mqtt versions
            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            
            if self.mqtt_username and self.mqtt_password:
                self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # Enable TLS for secure connection  
            import ssl
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(context)
            
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            
            logging.info(f"Connecting to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            
        except Exception as e:
            logging.error(f"Error connecting to MQTT: {e}")
    
    def disconnect(self):
        """Properly disconnect from MQTT broker"""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                logging.info("MQTT client disconnected properly")
            except Exception as e:
                logging.error(f"Error disconnecting MQTT: {e}")

# Initialize data manager and MQTT client
data_manager = SensorDataManager()
mqtt_client = MQTTClient(data_manager)

# Initialize Dash app with modern dark theme
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.CYBORG,  # Dark theme
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"  # Icons
])
app.title = "🛡 Mine Armour - Gas Sensor Dashboard"

# Custom CSS styling with darker red-black gradient theme
custom_style = {
    'backgroundColor': '#000000',
    'background': 'linear-gradient(135deg, #000000 0%, #4B0000 50%, #000000 100%)',
    'color': '#ffffff',
    'minHeight': '100vh'
}

# Header styling with darker red-black gradient
header_style = {
    'background': 'linear-gradient(135deg, #4B0000 0%, #800000 50%, #2D0000 100%)',
    'padding': '20px',
    'borderRadius': '10px',
    'marginBottom': '30px',
    'boxShadow': '0 4px 15px rgba(128, 0, 0, 0.6)',
    'border': '2px solid #800000'
}

# Card styling with darker red theme
card_style = {
    'backgroundColor': '#1A0000',
    'border': '2px solid #4B0000',
    'borderRadius': '10px',
    'boxShadow': '0 2px 10px rgba(75, 0, 0, 0.5)',
    'background': 'linear-gradient(135deg, #1A0000 0%, #2D0000 100%)'
}

# Chart styling with darker red theme
chart_style = {
    'backgroundColor': '#1A0000',
    'background': 'linear-gradient(135deg, #0D0000 0%, #1A0000 100%)',
    'borderRadius': '10px',
    'padding': '10px',
    'boxShadow': '0 2px 10px rgba(75, 0, 0, 0.5)',
    'border': '1px solid #4B0000'
}

# Custom CSS for darker red-black gradient background
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background: linear-gradient(135deg, #000000 0%, #4B0000 25%, #800000 50%, #4B0000 75%, #000000 100%) !important;
                background-attachment: fixed !important;
                margin: 0;
                padding: 0;
            }
            .dash-bootstrap {
                background: transparent !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Dashboard layout
app.layout = dbc.Container([
    # Header Section
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.I(className="fas fa-hard-hat me-3", style={
                        'color': '#FFFFFF', 
                        'fontSize': '3rem',
                        'textShadow': '3px 3px 6px rgba(0,0,0,0.8)',
                        'filter': 'drop-shadow(0 0 20px #800000)',
                        'transform': 'rotate(-5deg)'
                    }),
                    "MINE ARMOUR"
                ], className="text-center mb-4", 
                   style={'color': '#ffffff', 'font-weight': 'bold', 'fontSize': '3rem'}),
                html.P([
                    html.I(className="fas fa-broadcast-tower me-2"),
                    "MQTT Topic: LOKI_2004 | ",
                    html.I(className="fas fa-clock me-2"),
                    "Live Updates Every Second | ",
                    html.I(className="fas fa-microchip me-2"),
                    "Multi-Sensor Monitoring"
                ], className="text-center mb-0",
                   style={'color': '#a5b4fc', 'fontSize': '1.1rem'})
            ], style=header_style)
        ])
    ], className="mb-4"),
    
    # Connection Status Bar
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.I(className="fas fa-wifi me-2"),
                html.Span(id="connection-status", style={'fontWeight': 'bold'})
            ], id="status-alert", color="success", className="mb-0")
        ])
    ], className="mb-4"),
    
    # Current Values Grid
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-fire text-danger", style={'fontSize': '2rem'}),
                        html.H3(id="lpg-current", className="mb-0 mt-2", 
                               style={'color': '#ff6b6b', 'fontWeight': 'bold'}),
                        html.P("LPG Gas Level", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-cloud text-primary", style={'fontSize': '2rem'}),
                        html.H3(id="ch4-current", className="mb-0 mt-2", 
                               style={'color': '#4ecdc4', 'fontWeight': 'bold'}),
                        html.P("CH4 (Methane)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-gas-pump text-success", style={'fontSize': '2rem'}),
                        html.H3(id="propane-current", className="mb-0 mt-2", 
                               style={'color': '#45b7d1', 'fontWeight': 'bold'}),
                        html.P("Propane Gas", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-burn text-warning", style={'fontSize': '2rem'}),
                        html.H3(id="butane-current", className="mb-0 mt-2", 
                               style={'color': '#f39c12', 'fontWeight': 'bold'}),
                        html.P("Butane Gas", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-atom text-info", style={'fontSize': '2rem'}),
                        html.H3(id="h2-current", className="mb-0 mt-2", 
                               style={'color': '#9b59b6', 'fontWeight': 'bold'}),
                        html.P("H2 (Hydrogen)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-chart-line text-success", style={'fontSize': '2rem'}),
                        html.H6("System Status", className="mb-2 mt-2", style={'color': '#ffffff'}),
                        html.P(id="last-update", className="text-muted mb-0", style={'fontSize': '0.9rem'})
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2)
    ], className="mb-4"),
    
    # Additional Sensor Values Grid
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-heartbeat text-danger", style={'fontSize': '2rem'}),
                        html.H3(id="heartrate-current", className="mb-0 mt-2", 
                               style={'color': '#e74c3c', 'fontWeight': 'bold'}),
                        html.P("Heart Rate (BPM)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-lungs text-info", style={'fontSize': '2rem'}),
                        html.H3(id="spo2-current", className="mb-0 mt-2", 
                               style={'color': '#3498db', 'fontWeight': 'bold'}),
                        html.P("SpO2 (%)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-thermometer-half text-warning", style={'fontSize': '2rem'}),
                        html.H3(id="temperature-current", className="mb-0 mt-2", 
                               style={'color': '#f39c12', 'fontWeight': 'bold'}),
                        html.P("Temperature (°C)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-tint text-primary", style={'fontSize': '2rem'}),
                        html.H3(id="humidity-current", className="mb-0 mt-2", 
                               style={'color': '#2980b9', 'fontWeight': 'bold'}),
                        html.P("Humidity (%)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-hand-paper text-success", style={'fontSize': '2rem'}),
                        html.H3(id="gsr-current", className="mb-0 mt-2", 
                               style={'color': '#27ae60', 'fontWeight': 'bold'}),
                        html.P("GSR Level", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-brain text-danger", style={'fontSize': '2rem'}),
                        html.H3(id="stress-current", className="mb-0 mt-2", 
                               style={'color': '#e67e22', 'fontWeight': 'bold'}),
                        html.P("Stress Level", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2)
    ], className="mb-4"),
    
    # GPS and Additional Sensors Section Header
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-satellite-dish me-3"),
                "🛰 REAL-TIME GPS TRACKING & SENSOR MONITORING"
            ], className="text-center mb-4", 
               style={'color': '#ffffff', 'fontWeight': 'bold'})
        ])
    ], className="mb-4"),
    
    # GPS Information Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-crosshairs text-danger", style={'fontSize': '2rem'}),
                        html.H4(id="gps-lat", className="mb-0 mt-2", 
                               style={'color': '#e74c3c', 'fontWeight': 'bold'}),
                        html.P("Latitude", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-compass text-primary", style={'fontSize': '2rem'}),
                        html.H4(id="gps-lon", className="mb-0 mt-2", 
                               style={'color': '#3498db', 'fontWeight': 'bold'}),
                        html.P("Longitude", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-mountain text-success", style={'fontSize': '2rem'}),
                        html.H4(id="gps-alt", className="mb-0 mt-2", 
                               style={'color': '#27ae60', 'fontWeight': 'bold'}),
                        html.P("Altitude (m)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-satellite text-warning", style={'fontSize': '2rem'}),
                        html.H4(id="gps-sat", className="mb-0 mt-2", 
                               style={'color': '#f39c12', 'fontWeight': 'bold'}),
                        html.P("Satellites", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3)
    ], className="mb-4"),
    
    # Enhanced GPS Map (Full Width) and Health Sensor Chart
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="gps-map", 
                         config={
                             'displayModeBar': True,
                             'displaylogo': False,
                             'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                             'modeBarButtonsToAdd': ['resetViews']
                         },
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=8),  # Larger GPS map
        dbc.Col([
            html.Div([
                dcc.Graph(id="heartrate-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=4)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="spo2-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="temperature-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="humidity-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="gsr-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    # Charts Section Header
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-chart-area me-3"),
                "Real-time Gas Sensor Charts"
            ], className="text-center mb-4", 
               style={'color': '#ffffff', 'fontWeight': 'bold'})
        ])
    ], className="mb-4"),
    
    # Gas Sensor Charts with enhanced styling
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="lpg-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="ch4-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="propane-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="butane-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="h2-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=12)
    ], className="mb-4"),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=1000,  # Update every second
        n_intervals=0
    ),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(style={'borderColor': '#636e72'}),
            html.P([
                html.I(className="fas fa-hard-hat me-2"),
                "Mine Armour Dashboard | ",
                html.I(className="fas fa-calendar me-2"),
                "2025 | ",
                html.I(className="fas fa-code me-2"),
                "Real-time Gas Monitoring System"
            ], className="text-center text-muted mb-3",
               style={'fontSize': '0.9rem'})
        ])
    ])
    
], fluid=True, style=custom_style)

# Callbacks for real-time updates
@app.callback(
    [
        Output('connection-status', 'children'),
        Output('lpg-current', 'children'),
        Output('ch4-current', 'children'),
        Output('propane-current', 'children'),
        Output('butane-current', 'children'),
        Output('h2-current', 'children'),
        Output('last-update', 'children'),
        Output('heartrate-current', 'children'),
        Output('spo2-current', 'children'),
        Output('temperature-current', 'children'),
        Output('humidity-current', 'children'),
        Output('gsr-current', 'children'),
        Output('stress-current', 'children'),
        Output('gps-lat', 'children'),
        Output('gps-lon', 'children'),
        Output('gps-alt', 'children'),
        Output('gps-sat', 'children'),
    ],
    [Input('interval-component', 'n_intervals')]
)
def update_current_values(n):
    try:
        from datetime import datetime
        
        # Connection status
        status = "Connected" if mqtt_client.connected else "Disconnected"
        
        # Get latest gas sensor values
        gas_data = data_manager.get_gas_data()
        gps_data = data_manager.get_gps_data()
        
        # Format gas sensor values with better error handling
        latest = gas_data.get('latest', {})
        lpg_val = f"{latest.get('LPG', 0):.2f}" if latest.get('LPG') is not None else "---"
        ch4_val = f"{latest.get('CH4', 0):.2f}" if latest.get('CH4') is not None else "---"
        propane_val = f"{latest.get('Propane', 0):.2f}" if latest.get('Propane') is not None else "---"
        butane_val = f"{latest.get('Butane', 0):.2f}" if latest.get('Butane') is not None else "---"
        h2_val = f"{latest.get('H2', 0):.2f}" if latest.get('H2') is not None else "---"
        
        # Format additional sensor values
        heart_val = f"{latest.get('heartRate', -1)}" if latest.get('heartRate', -1) != -1 else "---"
        spo2_val = f"{latest.get('spo2', -1):.1f}%" if latest.get('spo2', -1) != -1 else "---"
        temp_val = f"{latest.get('temperature', -1.0):.1f}°C" if latest.get('temperature', -1.0) != -1.0 else "---"
        hum_val = f"{latest.get('humidity', -1.0):.1f}%" if latest.get('humidity', -1.0) != -1.0 else "---"
        gsr_val = f"{latest.get('GSR', 0)}" if latest.get('GSR', 0) else "---"
        stress_val = "HIGH" if latest.get('stress', 0) == 1 else "LOW"
        
        # Format GPS values
        gps_latest = gps_data.get('latest', {})
        lat_val = f"{gps_latest.get('lat', 0.0):.6f}" if gps_latest.get('lat', 0.0) else "---"
        lon_val = f"{gps_latest.get('lon', 0.0):.6f}" if gps_latest.get('lon', 0.0) else "---"
        alt_val = f"{gps_latest.get('alt', 0.0):.1f}" if gps_latest.get('alt', 0.0) else "---"
        sat_val = f"{gps_latest.get('sat', 0)}" if gps_latest.get('sat', 0) else "0"
        
        # Last update timestamp
        now = datetime.now()
        last_update = now.strftime("%H:%M:%S")
        
        return [status, lpg_val, ch4_val, propane_val, butane_val, h2_val, f"Last: {last_update}",
                heart_val, spo2_val, temp_val, hum_val, gsr_val, stress_val,
                lat_val, lon_val, alt_val, sat_val]
                
    except Exception as e:
        # Return default values if there's an error
        now = datetime.now()
        last_update = now.strftime("%H:%M:%S")
        return ["Disconnected", "---", "---", "---", "---", "---", f"Error: {last_update}",
                "---", "---", "---", "---", "---", "LOW",
                "---", "---", "---", "0"]

@app.callback(
    Output('lpg-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_lpg_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['LPG']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['LPG']),
            mode='lines+markers',
            name='LPG',
            line=dict(color='#800000', width=3),
            marker=dict(size=6, color='#800000'),
            fill='tonexty',
            fillcolor='rgba(128, 0, 0, 0.2)'
        ))
    
    fig.update_layout(
        title={
            'text': "🔥 LPG Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#FFFFFF', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="LPG Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,0,0,0.3)',
        font={'color': '#FFFFFF'},
        xaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        ),
        yaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        )
    )
    return fig

@app.callback(
    Output('ch4-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_ch4_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['CH4']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['CH4']),
            mode='lines+markers',
            name='CH4',
            line=dict(color='#4B0000', width=3),
            marker=dict(size=6, color='#4B0000'),
            fill='tonexty',
            fillcolor='rgba(75, 0, 0, 0.2)'
        ))
    
    fig.update_layout(
        title={
            'text': "💨 CH4 (Methane) Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#FFFFFF', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="CH4 Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,0,0,0.3)',
        font={'color': '#FFFFFF'},
        xaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        ),
        yaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        )
    )
    return fig

@app.callback(
    Output('propane-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_propane_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['Propane']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['Propane']),
            mode='lines+markers',
            name='Propane',
            line=dict(color='#45b7d1', width=3),
            marker=dict(size=6, color='#45b7d1'),
            fill='tonexty',
            fillcolor='rgba(69, 183, 209, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "⛽ Propane Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Propane Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('butane-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_butane_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['Butane']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['Butane']),
            mode='lines+markers',
            name='Butane',
            line=dict(color='#f39c12', width=3),
            marker=dict(size=6, color='#f39c12'),
            fill='tonexty',
            fillcolor='rgba(243, 156, 18, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "🧨 Butane Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Butane Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('h2-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_h2_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['H2']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['H2']),
            mode='lines+markers',
            name='H2',
            line=dict(color='#9b59b6', width=3),
            marker=dict(size=6, color='#9b59b6'),
            fill='tonexty',
            fillcolor='rgba(155, 89, 182, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "⚡ H2 (Hydrogen) Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="H2 Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

# GPS Map Callback
@app.callback(
    Output('gps-map', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_gps_map(n):
    try:
        gps_data = data_manager.get_gps_data()
        
        fig = go.Figure()
        
        # Get the latest GPS coordinates from the latest field
        latest = gps_data.get('latest', {})
        current_lat = latest.get('lat', 0.0)
        current_lon = latest.get('lon', 0.0)
        current_alt = latest.get('alt', 0.0)
        current_sat = latest.get('sat', 0)
        
        # Check if we have valid GPS coordinates
        if current_lat and current_lon and current_lat != 0.0 and current_lon != 0.0:
            
            # Add GPS trail if we have historical data
            lat_history = gps_data.get('lat', [])
            lon_history = gps_data.get('lon', [])
            
            if len(lat_history) > 1 and len(lon_history) > 1:
                # Convert to lists and show trail of recent GPS points (last 20 points)
                lat_list = list(lat_history)  # Ensure it's a list
                lon_list = list(lon_history)  # Ensure it's a list
                
                trail_size = min(20, len(lat_list))
                if trail_size > 1:
                    # Get trail points (exclude current/last point)
                    trail_lat = lat_list[max(0, len(lat_list)-trail_size-1):-1]
                    trail_lon = lon_list[max(0, len(lon_list)-trail_size-1):-1]
                    
                    if trail_lat and trail_lon and len(trail_lat) > 0 and len(trail_lon) > 0:
                        fig.add_trace(go.Scattermapbox(
                            lat=trail_lat,
                            lon=trail_lon,
                            mode='lines+markers',
                            marker=dict(size=6, color='#007BFF', opacity=0.6),
                            line=dict(width=2, color='#007BFF'),
                            name='GPS Trail',
                            hovertemplate='<b>GPS Trail</b><br>Lat: %{lat:.6f}<br>Lon: %{lon:.6f}<extra></extra>'
                        ))
            
            # Add current location marker - LARGE and VISIBLE
            fig.add_trace(go.Scattermapbox(
                lat=[current_lat],
                lon=[current_lon],
                mode='markers',
                marker=dict(
                    size=30,  # Very large marker
                    color='#FF0000',  # Bright red
                    symbol='circle'
                    # NOTE: Scattermapbox doesn't support 'line' property
                ),
                name='🔴 CURRENT LOCATION',
                text=f"📍 LIVE GPS POSITION<br>📍 Latitude: {current_lat:.6f}<br>🌍 Longitude: {current_lon:.6f}<br>🏔 Altitude: {current_alt:.1f}m<br>🛰 Satellites: {current_sat}",
                hovertemplate='<b>%{text}</b><extra></extra>'
            ))
            
            # Update map layout with enhanced visualization
            fig.update_layout(
                mapbox=dict(
                    style="open-street-map",
                    center=dict(lat=current_lat, lon=current_lon),
                    zoom=16  # Good zoom level for visibility
                ),
                title={
                    'text': f"🌍 LIVE GPS TRACKING | {current_lat:.6f}, {current_lon:.6f} | Alt: {current_alt:.1f}m | Sats: {current_sat}",
                    'x': 0.5,
                    'font': {'color': '#00FF00', 'size': 18, 'family': 'Arial Black'}
                },
                height=500,
                margin=dict(l=0, r=0, t=60, b=0),
                paper_bgcolor='rgba(0,0,0,0.95)',
                font={'color': '#ffffff'},
                showlegend=True,
                legend=dict(
                    bgcolor='rgba(0,0,0,0.8)',
                    bordercolor='#00FF00',
                    borderwidth=2,
                    font=dict(color='white', size=14)
                )
            )
        else:
            # No valid GPS data - show waiting message
            fig.update_layout(
                title={
                    'text': "🌍 GPS Location - Waiting for Signal...",
                    'x': 0.5,
                    'font': {'color': '#FFD700', 'size': 16}
                },
                height=500,
                margin=dict(l=0, r=0, t=60, b=0),
                paper_bgcolor='rgba(0,0,0,0.95)',
                plot_bgcolor='rgba(0,0,0,0.95)',
                font={'color': '#ffffff'},
                annotations=[
                    dict(
                        text="📡 Searching for GPS signal...<br>Please wait for location data",
                        showarrow=False,
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        xanchor='center', yanchor='middle',
                        font=dict(size=18, color="#FFD700"),
                        bgcolor="rgba(0,0,0,0.8)",
                        bordercolor="#FFD700",
                        borderwidth=2
                    )
                ]
            )
        
        return fig
        
    except Exception as e:
        # Error handling with specific error message
        print(f"GPS Map Error: {str(e)}")  # Debug print
        fig = go.Figure()
        fig.update_layout(
            title={
                'text': "⚠ GPS Map - Loading Error",
                'x': 0.5,
                'font': {'color': '#FF6B6B', 'size': 16}
            },
            height=500,
            margin=dict(l=0, r=0, t=60, b=0),
            paper_bgcolor='rgba(0,0,0,0.95)',
            plot_bgcolor='rgba(0,0,0,0.95)',
            font={'color': '#ffffff'},
            annotations=[
                dict(
                    text=f"❌ Error: {str(e)}<br>Checking GPS data...",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    xanchor='center', yanchor='middle',
                    font=dict(size=16, color="#FF6B6B"),
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor="#FF6B6B",
                    borderwidth=2
                )
            ]
        )
        return fig
    try:
        gps_data = data_manager.get_gps_data()
        
        fig = go.Figure()
        
        if gps_data['lat'] and gps_data['lon'] and len(gps_data['lat']) > 0:
            # Get current location
            lat_list = list(gps_data['lat'])
            lon_list = list(gps_data['lon'])
            alt_list = list(gps_data['alt']) if gps_data['alt'] else [0] * len(lat_list)
            sat_list = list(gps_data['sat']) if gps_data['sat'] else [0] * len(lat_list)
            timestamps = list(gps_data['timestamps'])
            
            current_lat = lat_list[-1] if lat_list else 0
            current_lon = lon_list[-1] if lon_list else 0
            current_alt = alt_list[-1] if alt_list else 0
            current_sat = sat_list[-1] if sat_list else 0
            
            # Add GPS trail (simplified)
            if len(lat_list) > 1:
                fig.add_trace(go.Scattermapbox(
                    lat=lat_list,
                    lon=lon_list,
                    mode='lines+markers',
                    marker=dict(size=8, color='blue', opacity=0.7),
                    line=dict(width=3, color='blue'),
                    name='GPS Trail',
                    text=[f"Time: {t.strftime('%H:%M:%S')}" for t in timestamps],
                    hovertemplate='<b>GPS Point</b><br>Lat: %{lat:.6f}<br>Lon: %{lon:.6f}<br>%{text}<extra></extra>'
                ))
            
            # Add current location marker
            fig.add_trace(go.Scattermapbox(
                lat=[current_lat],
                lon=[current_lon],
                mode='markers',
                marker=dict(
                    size=15,
                    color='red',
                    symbol='circle',
                    line=dict(width=2, color='white')
                ),
                name='Current Location',
                text=f"  Current Position<br>Lat: {current_lat:.6f}<br>Lon: {current_lon:.6f}<br>Alt: {current_alt:.1f}m<br>Satellites: {current_sat}",
                hovertemplate='<b>Current Location</b><br>%{text}<extra></extra>'
            ))
            
            fig.update_layout(
                mapbox=dict(
                    style="open-street-map",  # Free, no token required
                    center=dict(lat=current_lat, lon=current_lon),
                    zoom=16
                ),
                title={
                    'text': f"  GPS Tracking | Lat: {current_lat:.6f}, Lon: {current_lon:.6f} | Alt: {current_alt:.1f}m | Sats: {current_sat}",
                    'x': 0.5,
                    'font': {'color': '#ffffff', 'size': 14}
                },
                height=450,
                margin=dict(l=0, r=0, t=40, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                font={'color': '#ffffff'},
                showlegend=True,
                legend=dict(
                    bgcolor='rgba(0,0,0,0.8)',
                    bordercolor='#636e72',
                    borderwidth=1,
                    font=dict(color='white')
                )
            )
        else:
            # No GPS data available
            fig.update_layout(
                title={
                    'text': "🌍 GPS Location - Waiting for Signal...",
                    'x': 0.5,
                    'font': {'color': '#ffffff', 'size': 16}
                },
                height=450,
                margin=dict(l=0, r=0, t=40, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font={'color': '#ffffff'},
                annotations=[
                    dict(
                        text="📡 Searching for GPS signal...<br>Please wait for location data",
                        showarrow=False,
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        xanchor='center', yanchor='middle',
                        font=dict(size=16, color="white"),
                        bgcolor="rgba(0,0,0,0.7)",
                        bordercolor="white",
                        borderwidth=1
                    )
                ]
            )
        
        return fig
        
    except Exception as e:
        # Error handling - return simple error message
        fig = go.Figure()
        fig.update_layout(
            title={
                'text': "⚠ GPS Map Error",
                'x': 0.5,
                'font': {'color': '#ffffff', 'size': 16}
            },
            height=450,
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': '#ffffff'},
            annotations=[
                dict(
                    text=f"Map loading error: {str(e)}<br>Retrying...",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    xanchor='center', yanchor='middle',
                    font=dict(size=14, color="red"),
                    bgcolor="rgba(0,0,0,0.7)",
                    bordercolor="red",
                    borderwidth=1
                )
            ]
        )
        return fig

# Health Sensor Charts
@app.callback(
    Output('heartrate-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_heartrate_chart(n):
    health_data = data_manager.get_health_data()
    
    fig = go.Figure()
    if health_data['timestamps'] and health_data['heartRate']:
        # Filter out None values
        valid_data = [(t, hr) for t, hr in zip(health_data['timestamps'], health_data['heartRate']) if hr is not None]
        if valid_data:
            timestamps, heart_rates = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=heart_rates,
                mode='lines+markers',
                name='Heart Rate',
                line=dict(color='#e74c3c', width=3),
                marker=dict(size=6, color='#e74c3c'),
                fill='tonexty',
                fillcolor='rgba(231, 76, 60, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "❤ Heart Rate Monitor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Heart Rate (BPM)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('spo2-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_spo2_chart(n):
    health_data = data_manager.get_health_data()
    
    fig = go.Figure()
    if health_data['timestamps'] and health_data['spo2']:
        # Filter out None values
        valid_data = [(t, spo2) for t, spo2 in zip(health_data['timestamps'], health_data['spo2']) if spo2 is not None]
        if valid_data:
            timestamps, spo2_values = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=spo2_values,
                mode='lines+markers',
                name='SpO2',
                line=dict(color='#3498db', width=3),
                marker=dict(size=6, color='#3498db'),
                fill='tonexty',
                fillcolor='rgba(52, 152, 219, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "🫁 SpO2 Oxygen Saturation - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="SpO2 (%)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('temperature-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_temperature_chart(n):
    env_data = data_manager.get_environmental_data()
    
    fig = go.Figure()
    if env_data['timestamps'] and env_data['temperature']:
        # Filter out None values
        valid_data = [(t, temp) for t, temp in zip(env_data['timestamps'], env_data['temperature']) if temp is not None]
        if valid_data:
            timestamps, temperatures = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=temperatures,
                mode='lines+markers',
                name='Temperature',
                line=dict(color='#f39c12', width=3),
                marker=dict(size=6, color='#f39c12'),
                fill='tonexty',
                fillcolor='rgba(243, 156, 18, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "🌡 Temperature Monitor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('humidity-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_humidity_chart(n):
    env_data = data_manager.get_environmental_data()
    
    fig = go.Figure()
    if env_data['timestamps'] and env_data['humidity']:
        # Filter out None values
        valid_data = [(t, hum) for t, hum in zip(env_data['timestamps'], env_data['humidity']) if hum is not None]
        if valid_data:
            timestamps, humidity_values = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=humidity_values,
                mode='lines+markers',
                name='Humidity',
                line=dict(color='#2980b9', width=3),
                marker=dict(size=6, color='#2980b9'),
                fill='tonexty',
                fillcolor='rgba(41, 128, 185, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "💧 Humidity Monitor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Humidity (%)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('gsr-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_gsr_chart(n):
    health_data = data_manager.get_health_data()
    
    fig = go.Figure()
    if health_data['timestamps'] and health_data['GSR']:
        fig.add_trace(go.Scatter(
            x=list(health_data['timestamps']),
            y=list(health_data['GSR']),
            mode='lines+markers',
            name='GSR',
            line=dict(color='#27ae60', width=3),
            marker=dict(size=6, color='#27ae60'),
            fill='tonexty',
            fillcolor='rgba(39, 174, 96, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "✋ GSR (Galvanic Skin Response) - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="GSR Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

if __name__ == '__main__':
    try:
        # Connect to MQTT broker
        mqtt_client.connect()
        
        # Wait a moment for connection
        time.sleep(2)
        
        print("🛡 Starting Mine Armour Multi-Sensor Dashboard...")
        print("📊 Dashboard will be available at: http://localhost:8050")
        print("🔄 Real-time updates every second")
        print("📡 MQTT Topic: LOKI_2004 (Multi-Sensor Data)")
        print("🔥 Gas Sensors: LPG, CH4, Propane, Butane, H2")
        print("❤ Health Sensors: Heart Rate, SpO2, GSR, Stress")
        print("🌡 Environment: Temperature, Humidity")
        print("📍 GPS: Location tracking")
        
        # Run the dashboard
        app.run_server(debug=True, host='0.0.0.0', port=8050)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Mine Armour Dashboard...")
        mqtt_client.disconnect()
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        mqtt_client.disconnect()
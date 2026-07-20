# core/constants.py

# --- Red y Conexión ---
DISCOVERY_PORT = 8888           # Puerto UDP fijo para buscar servidores
BROADCAST_IP = "127.255.255.255" # Dirección IP especial para enviar a toda la red local
ENCODING = "utf-8"              # Codificación de caracteres obligatoria

# --- Protocolo ---
PROTOCOL_VERSION = 1            # Versión del protocolo actual

# --- Constantes del Juego (Recomendadas) ---
MAP_SIZE = 1000                 # El mapa mide 1000 x 1000 unidades lógicas
CIRCLE_RADIUS = 300             # Radio del círculo central
PLAYER_RADIUS = 15              # Radio del cuerpo del jugador
INTERACT_RADIUS = 40            # Distancia máxima para tomar o robar la bandera
SPEED = 200                     # Unidades por segundo de velocidad
TICK_RATE = 20                  # Envíos de estado por segundo
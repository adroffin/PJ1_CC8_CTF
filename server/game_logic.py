# server/game_logic.py
import time
import threading
import math
import random
from core.protocol import build_message

class GameEngine:
    def __init__(self, tcp_server):
        self.tcp_server = tcp_server
        self.running = False
        self.lock = threading.Lock()  # Candado para proteger la memoria compartida
        
        # --- Estado del Mundo ---
        # Jugadores: {id: {"name": str, "x": int, "y": int, "score": int, "has_flag": bool}}
        self.players = {}
        
        # Bandera: posición inicial en el centro del mapa de 1000x1000
        self.flag = {
            "x": 500,
            "y": 500,
            "carrier_id": None
        }

    def add_player(self, player_id: str, name: str):
        """Registra a un nuevo jugador en el mapa con una posición inicial."""
        with self.lock:

            # Posición aleatoria segura (cerca de los bordes)
            spawn_x = random.choice([random.randint(15, 150), random.randint(850, 985)])
            spawn_y = random.choice([random.randint(15, 150), random.randint(850, 985)])

            self.players[player_id] = {
                "name": name,
                "x": spawn_x,  # Posición inicial X
                "y": spawn_y,  # Posición inicial Y
                "score": 0,
                "has_flag": False
            }
            print(f"[ENGINE] Jugador '{name}' ({player_id}) agregado al estado del mundo en ({spawn_x},{spawn_y}).")

    def remove_player(self, player_id: str):
        """Elimina a un jugador desconectado y libera la bandera si la llevaba."""
        with self.lock:
            if player_id in self.players:
                # Si el jugador tenía la bandera, la soltamos en su última posición
                if self.flag["carrier_id"] == player_id:
                    self.flag["carrier_id"] = None
                    self.flag["x"] = 500
                    self.flag["y"] = 500
                    print(f"[ENGINE] ¡El portador se ha ido de la partida! La bandera regreso a ({self.flag['x']}, {self.flag['y']}).")
                
                del self.players[player_id]
                print(f"[ENGINE] Jugador {player_id} eliminado del mundo.")

    def update_player_input(self, player_id: str, dir_x: int, dir_y: int):
        with self.lock:
            if player_id not in self.players:
                return
            
            player = self.players[player_id]
            speed = 200
            dt = 0.05  
            
            # Si no hay dirección, salimos
            if dir_x == 0 and dir_y == 0:
                return
                
            # Normalización (Pitágoras) para evitar que la diagonal sea más rápida
            magnitude = math.hypot(dir_x, dir_y)
            norm_x = dir_x / magnitude
            norm_y = dir_y / magnitude
            
            new_x = player["x"] + (norm_x * speed * dt)
            new_y = player["y"] + (norm_y * speed * dt)
            
            # Límites del mapa (0 a 1000)
            player["x"] = max(15, min(985, round(new_x)))
            player["y"] = max(15, min(985, round(new_y)))

            # Si el jugador tiene la bandera, la bandera se mueve con él
            if self.flag["carrier_id"] == player_id:
                self.flag["x"] = player["x"]
                self.flag["y"] = player["y"]

    def handle_player_interact(self, player_id: str):
        """Procesa el intento de un jugador de agarrar o robar la bandera."""
        with self.lock:
            if player_id not in self.players:
                return
                
            player = self.players[player_id]
            
            # 1. CASO CAPTURA: La bandera está libre en el suelo
            if self.flag["carrier_id"] is None:
                # Distancia entre el jugador y la bandera
                dist = math.hypot(player["x"] - self.flag["x"], player["y"] - self.flag["y"])
                
                # Si la distancia es <= 40, captura la bandera
                if dist <= 40:
                    self.flag["carrier_id"] = player_id
                    player["has_flag"] = True
                    print(f"[ENGINE] ¡El jugador {player['name']} ha CAPTURADO la bandera!")
                    
            # 2. CASO ROBO: La bandera la tiene otro jugador
            elif self.flag["carrier_id"] != player_id:
                carrier_id = self.flag["carrier_id"]
                carrier = self.players.get(carrier_id)
                
                if carrier:
                    # Distancia entre el ladrón y el portador
                    dist = math.hypot(player["x"] - carrier["x"], player["y"] - carrier["y"])
                    
                    # Si la distancia es <= 40, roba la bandera
                    if dist <= 40:
                        # Le quitamos la bandera al portador actual
                        carrier["has_flag"] = False
                        # Se la damos al ladrón
                        self.flag["carrier_id"] = player_id
                        player["has_flag"] = True
                        print(f"[ENGINE] ¡El jugador {player['name']} ha ROBADO la bandera a {carrier['name']}!")

    def start(self):
        """Inicia el hilo maestro a 20Hz."""
        self.running = True
        engine_thread = threading.Thread(target=self._game_loop, daemon=True)
        engine_thread.start()
        print("[ENGINE] Motor de juego iniciado a 20Hz (20 ticks/segundo).")

    def stop(self):
        """Detiene el motor de juego."""
        self.running = False

    def _game_loop(self):
        """
        Bucle maestro. Se ejecuta cada 0.05 segundos (1/20 Hz).
        Toma una 'foto' del mundo y se la transmite a todos los jugadores.
        """
        target_tick_time = 1.0 / 20.0  # 0.05 segundos = 50ms
        
        while self.running:
            start_time = time.time()
            
            # 1. Copiamos el estado actual usando el Lock para evitar colisiones de hilos
            with self.lock:
                state_message = build_message(
                    "state",
                    players=self.players,
                    flag=self.flag
                )
            
            # 2. Transmitimos el estado a todos los clientes conectados
            if self.players:  # Solo transmitimos si hay al menos un jugador
                self.tcp_server.broadcast(state_message)
            
            # 3. Regulamos el tiempo para mantener los 20Hz exactos
            elapsed = time.time() - start_time
            sleep_time = max(0.0, target_tick_time - elapsed)
            time.sleep(sleep_time)
# server/game_logic.py
import time
import threading
import math
import random
from core.protocol import build_message

from core.constants import (
    MAP_SIZE,
    CIRCLE_RADIUS,
    PLAYER_RADIUS,
    INTERACT_RADIUS,
    SPEED,
    TICK_RATE,
)

class GameEngine:
    def __init__(self, tcp_server):
        self.tcp_server = tcp_server
        self.running = False
        self.last_tick = time.perf_counter()
        self.is_game_over = False
        self.winner_name = None
        self.game_state = "LOBBY"
        self.countdown_start = None
        self.game_over_start = None
        self.manual_start = False
        self.last_countdown_sec = None
        
        self.lock = threading.Lock()  # Candado para proteger la memoria compartida
        
        # --- Estado del Mundo ---
        # Jugadores: {id: {"name": str, "x": int, "y": int, "has_flag": bool}}
        self.players = {}
        
        # Bandera: posición inicial en el centro del mapa de 1000x1000
        center = MAP_SIZE // 2

        self.flag = {
            "x": center,
            "y": center,
            "owner": None
        }

    def add_player(self, player_id: str, name: str):
        """Registra a un nuevo jugador en el mapa con una posición inicial."""
        with self.lock:

            # Posición aleatoria segura (cerca de los bordes)
            spawn_x = random.choice([random.randint(PLAYER_RADIUS, 150), random.randint(850, 985)])
            spawn_y = random.choice([random.randint(PLAYER_RADIUS, 150), random.randint(850, 985)])

            self.players[player_id] = {
                "name": name,

                "x": spawn_x,
                "y": spawn_y,

                "dir_x": 0,
                "dir_y": 0,

                "has_flag": False
            }
            print(f"[ENGINE] Jugador '{name}' ({player_id}) agregado al estado del mundo en ({spawn_x},{spawn_y}).")

    def remove_player(self, player_id: str):
        """Elimina a un jugador desconectado y libera la bandera si la llevaba."""

        center = MAP_SIZE // 2

        with self.lock:
            if player_id in self.players:
                # Si el jugador tenía la bandera, la soltamos en su última posición
                if self.flag["owner"] == player_id:
                    self.flag["owner"] = None
                    self.flag["x"] = center
                    self.flag["y"] = center
                    print(f"[ENGINE] ¡El portador se ha ido de la partida! La bandera regreso a ({self.flag['x']}, {self.flag['y']}).")
                
                del self.players[player_id]
                print(f"[ENGINE] Jugador {player_id} eliminado del mundo.")

    def get_player_count(self):
        with self.lock:
            return len(self.players)

    def start_game_manually(self):
        """Activa la bandera para que el loop inicie la cuenta regresiva."""
        with self.lock:
            if self.game_state == "LOBBY" and len(self.players) >= 2:
                self.manual_start = True

    def update_player_input(self, player_id: str, dir_x: int, dir_y: int):
        """
        Guarda la última dirección enviada por el cliente.
        El movimiento real ocurre dentro del Game Loop.
        """
        if self.game_state != "PLAYING":
            return
        with self.lock:
            if player_id not in self.players:
                return

            self.players[player_id]["dir_x"] = dir_x
            self.players[player_id]["dir_y"] = dir_y

    def handle_player_interact(self, player_id: str):
        """Procesa el intento de un jugador de agarrar o robar la bandera."""
        if self.game_state != "PLAYING":
            return
        with self.lock:
            if player_id not in self.players:
                return
                
            player = self.players[player_id]
            
            # 1. CASO CAPTURA: La bandera está libre en el suelo
            if self.flag["owner"] is None:
                # Distancia entre el jugador y la bandera
                dist = math.hypot(player["x"] - self.flag["x"], player["y"] - self.flag["y"])
                
                # Si la distancia es <= 40, captura la bandera
                if dist <= INTERACT_RADIUS:
                    self.flag["owner"] = player_id
                    player["has_flag"] = True
                    print(f"[ENGINE] ¡El jugador {player['name']} ha CAPTURADO la bandera!")
                    
            # 2. CASO ROBO: La bandera la tiene otro jugador
            elif self.flag["owner"] != player_id:
                owner = self.flag["owner"]
                carrier = self.players.get(owner)
                
                if carrier:
                    # Distancia entre el ladrón y el portador
                    dist = math.hypot(player["x"] - carrier["x"], player["y"] - carrier["y"])
                    
                    # Si la distancia es <= 40, roba la bandera
                    if dist <= INTERACT_RADIUS:
                        # Le quitamos la bandera al portador actual
                        carrier["has_flag"] = False
                        # Se la damos al ladrón
                        self.flag["owner"] = player_id
                        player["has_flag"] = True
                        print(f"[ENGINE] ¡El jugador {player['name']} ha ROBADO la bandera a {carrier['name']}!")

    def start(self):
        """Inicia el hilo maestro a 20Hz."""
        self.running = True
        engine_thread = threading.Thread(target=self._game_loop, daemon=True)
        engine_thread.start()
        print(f"[ENGINE] Motor iniciado a {TICK_RATE}Hz")

    def stop(self):
        """Detiene el motor de juego."""
        self.running = False

    def _game_loop(self):
        """
        Bucle maestro. Se ejecuta cada 0.05 segundos (1/20 Hz).
        Toma una 'foto' del mundo y se la transmite a todos los jugadores.
        """
        target_tick_time = 1.0 / TICK_RATE  # 0.05 segundos = 50ms
        
        while self.running:
            current_tick = time.perf_counter()
            dt = current_tick - self.last_tick
            self.last_tick = current_tick
            start_time = current_tick
            
            # 1. Copiamos el estado actual usando el Lock para evitar colisiones de hilos
            with self.lock:

                # Cambio de estado dentro del juego
                if self.game_state == "LOBBY":
                    if len(self.players) >= 2 and self.manual_start:
                        self.game_state = "COUNTDOWN"
                        self.countdown_start = time.perf_counter()
                        self.last_countdown_sec = 5

                        # Enviar el primer número de la cuenta regresiva
                        countdown_msg = build_message("countdown", seconds=self.last_countdown_sec)
                        self.tcp_server.broadcast(countdown_msg)
                        print(f"[ENGINE] Iniciando cuenta regresiva: {self.last_countdown_sec}...")

                if self.game_state == "COUNTDOWN":
                    elapsed = time.perf_counter() - self.countdown_start
                    # Calculamos cuántos segundos quedan realmente
                    seconds_left = math.ceil(5 - elapsed)
                    
                    if seconds_left <= 0:
                        self.game_state = "PLAYING"
                        # Enviar el mensaje START al terminar la cuenta
                        start_msg = build_message("start")
                        self.tcp_server.broadcast(start_msg)
                        print("[ENGINE] La partida ha comenzado.")
                        
                    elif seconds_left < self.last_countdown_sec:
                        # Si cambió el segundo, actualizamos y disparamos el mensaje
                        self.last_countdown_sec = seconds_left
                        countdown_msg = build_message("countdown", seconds=self.last_countdown_sec)
                        self.tcp_server.broadcast(countdown_msg)

                # Movimiento de jugadores
                if self.game_state == "PLAYING":
                    for p_id, player in self.players.items():

                        dx = player["dir_x"]
                        dy = player["dir_y"]

                        if dx == 0 and dy == 0:
                            continue

                        magnitude = math.hypot(dx, dy)

                        if magnitude == 0:
                            continue

                        dx /= magnitude
                        dy /= magnitude

                        player["x"] += dx * SPEED * dt
                        player["y"] += dy * SPEED * dt

                        player["x"] = max(
                            PLAYER_RADIUS,
                            min(
                                MAP_SIZE - PLAYER_RADIUS,
                                round(player["x"])
                            )
                        )

                        player["y"] = max(
                            PLAYER_RADIUS,
                            min(
                                MAP_SIZE - PLAYER_RADIUS,
                                round(player["y"])
                            )
                        )

                        if player["has_flag"]:
                            self.flag["x"] = player["x"]
                            self.flag["y"] = player["y"]

                        # Verificar victoria
                        if player["has_flag"]:

                            center = MAP_SIZE / 2

                            distance = math.hypot(
                                player["x"] - center,
                                player["y"] - center
                            )

                            if distance > (CIRCLE_RADIUS + PLAYER_RADIUS):

                                self.is_game_over = True

                                self.game_state = "GAME_OVER"
                                self.game_over_start = time.perf_counter()
                                self.winner_name = p_id

                                print("[ENGINE] Fin de la partida.")
                                print(f"[ENGINE] {player['name']} ganó la partida.")

                                # Creamos y disparamos el mensaje dedicado de game_over para todos
                                game_over_msg = build_message("game_over", player_id=p_id, winner=p_id)
                                self.tcp_server.broadcast(game_over_msg)
                    
                if self.game_state == "GAME_OVER":

                    elapsed = time.perf_counter() - self.game_over_start

                    if self.is_game_over:
                        if elapsed >= 5:
                            # 1. Reiniciar estado general
                            self.game_state = "LOBBY"
                            self.is_game_over = False
                            self.winner_name = None
                            self.manual_start = False # Apagamos el inicio automático para que requiera click manual
                            
                            # 2. Reiniciar la bandera
                            center = MAP_SIZE // 2
                            self.flag["owner"] = None
                            self.flag["x"] = center
                            self.flag["y"] = center

                            # 3. Preparar la lista de jugadores para el broadcast del lobby y resetear posiciones
                            players_in_lobby = []
                            for p_id, player in self.players.items():

                                player["has_flag"] = False

                                player["dir_x"] = 0
                                player["dir_y"] = 0

                                player["x"] = random.choice([
                                    random.randint(PLAYER_RADIUS,150),
                                    random.randint(850,985)
                                ])

                                player["y"] = random.choice([
                                    random.randint(PLAYER_RADIUS,150),
                                    random.randint(850,985)
                                ])
                                
                                players_in_lobby.append({
                                    "id": p_id,
                                    "name": player["name"]
                                })

                            print("[ENGINE] 5 segundos transcurridos. Regresando al Lobby.")
                            
                            # 4. Fundamental: Avisarle a todos los clientes que volvimos al lobby
                            lobby_msg = {
                                "type": "lobby",
                                "players": players_in_lobby
                            }
                            self.tcp_server.broadcast(lobby_msg)

                if self.game_state in ["PLAYING", "GAME_OVER"]:
                    players_list = []
                    for p_id, p_data in self.players.items():
                        # Creamos una copia para no alterar la memoria original
                        player_info = p_data.copy()
                        # Inyectamos el ID como una propiedad interna exigida por los clientes
                        player_info["id"] = p_id
                        players_list.append(player_info)

                    # Construimos el mensaje usando la NUEVA lista en lugar del diccionario
                    state_message = build_message(
                        "state",
                        players=players_list,
                        flag=self.flag,
                        game_state=self.game_state,
                        winner=self.winner_name
                    )
                    
            
            # 2. Transmitimos el estado a todos los clientes conectados
            if self.players and self.game_state in ["PLAYING", "GAME_OVER"]:  # Solo transmitimos si hay al menos un jugador
                self.tcp_server.broadcast(state_message)
            
            # 3. Regulamos el tiempo para mantener los 20Hz exactos
            elapsed = time.perf_counter() - start_time
            sleep_time = max(0.0, target_tick_time - elapsed)
            time.sleep(sleep_time)
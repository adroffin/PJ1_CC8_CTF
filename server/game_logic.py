# server/game_logic.py
import time
import threading
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
            self.players[player_id] = {
                "name": name,
                "x": 100,  # Posición inicial X
                "y": 100,  # Posición inicial Y
                "score": 0,
                "has_flag": False
            }
            print(f"[ENGINE] Jugador '{name}' ({player_id}) agregado al estado del mundo.")

    def remove_player(self, player_id: str):
        """Elimina a un jugador desconectado y libera la bandera si la llevaba."""
        with self.lock:
            if player_id in self.players:
                # Si el jugador tenía la bandera, la soltamos en su última posición
                if self.flag["carrier_id"] == player_id:
                    self.flag["carrier_id"] = None
                    self.flag["x"] = self.players[player_id]["x"]
                    self.flag["y"] = self.players[player_id]["y"]
                    print(f"[ENGINE] ¡La bandera fue soltada en ({self.flag['x']}, {self.flag['y']})!")
                
                del self.players[player_id]
                print(f"[ENGINE] Jugador {player_id} eliminado del mundo.")

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
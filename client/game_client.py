# client/game_client.py
import socket
import threading
import json
import sys
import os
import time

from core.constants import ENCODING
from core.protocol import build_message, encode_tcp_message

if sys.platform == "win32":
    import msvcrt

class GameClient:
    def __init__(self, host: str, port: int, player_name: str):
        self.host = host
        self.port = port
        self.player_name = player_name
        self.sock = None
        self.running = False
        self.my_id = None
        self.latest_state = None
        self.game_state = "LOBBY"
        self.winner = None
        self.lobby_players = []
        self.server_config = {}

    def connect(self) -> bool:
        """Establece la conexión TCP y envía el mensaje de 'join'."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.sock.connect((self.host, self.port))
            self.running = True
            print(f"[TCP] Conectado exitosamente al servidor en {self.host}:{self.port}")
            
            # Enviar el mensaje 'join' obligatorio con la versión del protocolo
            join_msg = build_message("join", v=1, name=self.player_name)
            self.sock.sendall(encode_tcp_message(join_msg))
            
            # Iniciar un hilo para escuchar lo que nos mande el servidor (con buffer)
            threading.Thread(target=self._listen_to_server, daemon=True).start()

            # Iniciar el hilo para capturar las pulsaciones del teclado y enviarlas al servidor
            threading.Thread(target=self._input_loop, daemon=True).start()
            return True
            
        except Exception as e:
            print(f"[TCP] Error al conectar con el servidor: {e}")
            return False

    def _listen_to_server(self):
        """Escucha los mensajes del servidor aplicando la regla del buffer."""
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(1024)
                if not data:
                    print("\n[TCP] Desconectado del servidor.")
                    break
                
                buffer += data.decode(ENCODING)
                
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._handle_server_message(line.strip())
                        
            except ConnectionAbortedError:
                break
            except Exception as e:
                print(f"[TCP] Error leyendo del servidor: {e}")
                break
    
    def _handle_server_message(self, json_string: str):
        try:
            msg = json.loads(json_string)
            msg_type = msg.get("type")
            
            if msg_type == "welcome":
                self.my_id = msg.get("id")
                self.server_config = msg.get("config", {})
            elif msg_type == "state":
                self.latest_state = msg
                self.game_state = msg.get("game_state", "LOBBY")
                self.winner = msg.get("winner")
                self._render_ui()
            elif msg_type == "lobby":
                self.lobby_players = msg["players"]
        except json.JSONDecodeError:
            pass

    def _render_ui(self):
        if not self.latest_state:
            return
        
        # Limpia la pantalla en Windows para no saturar la consola
        os.system('cls' if sys.platform == 'win32' else 'clear')
        
        print("=== CAPTURA LA BANDERA CTF ===")

        print(f"Estado: {self.game_state}")

        if self.game_state == "LOBBY":
            print("Esperando más jugadores...")

        elif self.game_state == "COUNTDOWN":
            print("La partida comenzará en unos segundos...")

        elif self.game_state == "PLAYING":
            print("¡¡La partida está en curso!!")

        elif self.game_state == "GAME_OVER":

            print()

            print("===== FIN DE LA PARTIDA =====")

            if self.winner:
                print(f"Ganador: {self.winner}")

            print()

        print("Usa las teclas W, A, S, D para moverte. Presiona la tecla 'P' para tomar/robar la bandera.\n")
        
        flag = self.latest_state.get("flag", {})
        print(f"Bandera en: ({flag.get('x')}, {flag.get('y')}) | Portador: {flag.get('carrier_id') or 'Nadie'}\n")
        
        print("--- Jugadores ---")
        players = self.latest_state.get("players", [])

        for player in players:
            me_tag = ""
            if player["id"] == self.my_id:
                me_tag = " (TÚ)"
            bandera = "Sí" if player["has_flag"] else "No"

            print(
                f"- {player['name']}{me_tag}"
                f"\n   Posición: ({player['x']}, {player['y']})"
                f"\n   Lleva bandera: {bandera}\n"
            )

    def _input_loop(self):
        while self.running:
            if sys.platform == "win32" and msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                
                dir_x, dir_y = 0, 0
                if key == 'w': dir_y = -1
                elif key == 's': dir_y = 1
                elif key == 'a': dir_x = -1
                elif key == 'd': dir_x = 1
                elif key == 'p': 
                    interact_msg = build_message("interact")
                    try:
                        self.sock.sendall(encode_tcp_message(interact_msg))
                    except Exception:
                        break
                
                if dir_x != 0 or dir_y != 0:
                    input_msg = build_message("input", dir={"x": dir_x, "y": dir_y})
                    try:
                        self.sock.sendall(encode_tcp_message(input_msg))
                    except Exception:
                        break
            time.sleep(0.02)
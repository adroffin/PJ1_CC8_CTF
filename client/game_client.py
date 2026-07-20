# client/game_client.py
import socket
import threading

from core.constants import ENCODING
from core.protocol import build_message, encode_tcp_message

class GameClient:
    def __init__(self, host: str, port: int, player_name: str):
        self.host = host
        self.port = port
        self.player_name = player_name
        self.sock = None
        self.running = False

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
                        print(f"[Mensaje del Servidor] -> {line.strip()}")
                        
            except ConnectionAbortedError:
                break
            except Exception as e:
                print(f"[TCP] Error leyendo del servidor: {e}")
                break
# server/tcp_server.py
import socket
import threading
import json
import uuid

from core.constants import ENCODING
from core.protocol import build_message, encode_tcp_message

class TCPServer:
    def __init__(self, tcp_port: int):
        self.tcp_port = tcp_port
        self.running = False
        self.server_socket = None
        self.clients = {}  # Diccionario: {client_socket: player_info}
        self.game_engine = None

    def set_game_engine(self, game_engine):
        """Conecta el servidor TCP con la lógica del juego."""
        self.game_engine = game_engine

    def start(self):
        """Inicia el servidor TCP para aceptar conexiones de jugadores."""
        # Creamos el socket TCP (SOCK_STREAM)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.tcp_port))
        
        # Ponemos el socket en modo "escucha"
        self.server_socket.listen()
        self.running = True
        
        # Iniciamos un hilo principal solo para aceptar conexiones entrantes
        accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
        accept_thread.start()
        print(f"[TCP] Servidor de juego escuchando en el puerto {self.tcp_port}")

    def stop(self):
        """Detiene el servidor y cierra todas las conexiones."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[TCP] Servidor de juego detenido.")

    def broadcast(self, message_dict: dict):
        """Envía un mensaje a TODOS los clientes conectados actualmente."""
        bytes_to_send = encode_tcp_message(message_dict)
        # Copiamos la lista de sockets para iterar de forma segura
        active_sockets = list(self.clients.keys())
        
        for sock in active_sockets:
            try:
                sock.sendall(bytes_to_send)
            except Exception:
                # Si falla el envío, el hilo individual _handle_client se encargará de limpiarlo
                pass

    def _accept_connections(self):
        """Bucle infinito que acepta nuevos clientes y les asigna un hilo."""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[TCP] Nueva conexión entrante de {addr}")
                
                # Registramos el socket sin datos por ahora
                self.clients[client_socket] = {"addr": addr, "id": None, "name": None}
                
                # Creamos un hilo EXCLUSIVO para leer los mensajes de este cliente
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket, addr), 
                    daemon=True
                )
                client_thread.start()
                
            except OSError:
                break
            except Exception as e:
                print(f"[TCP] Error aceptando conexión: {e}")

    def _handle_client(self, client_socket: socket.socket, addr: tuple):
        """
        Lee continuamente los datos del cliente, implementando la regla
        obligatoria del buffer y el salto de línea (\n).
        """
        buffer = ""
        
        while self.running:
            try:
                # 1. Recibimos un trozo de bytes (hasta 1024)
                data = client_socket.recv(1024)
                
                if not data:
                    # Si recv() devuelve vacío, el cliente cerró la conexión
                    print(f"[TCP] Cliente {addr} desconectado.")
                    break
                
                # 2. Decodificamos los bytes a texto y los sumamos a nuestro "cajón temporal"
                buffer += data.decode(ENCODING)
                
                # 3. Procesamos todos los mensajes completos que haya en el buffer
                while "\n" in buffer:
                    # Cortamos el buffer en el primer \n. 
                    # 'line' tiene el mensaje, 'buffer' se queda con el resto.
                    line, buffer = buffer.split("\n", 1)
                    
                    if line.strip():  # Ignoramos líneas vacías por seguridad
                        self._process_message(line, client_socket, addr)
                        
            except ConnectionResetError:
                print(f"[TCP] Conexión perdida abruptamente con {addr}")
                break
            except Exception as e:
                print(f"[TCP] Error manejando cliente {addr}: {e}")
                break
                
        # Limpieza al salir del bucle
        if client_socket in self.clients:
            player_id = self.clients[client_socket].get("id")
            del self.clients[client_socket]
            
        if player_id and self.game_engine:
            self.game_engine.remove_player(player_id)
            
        client_socket.close()

    def _send_to_client(self, client_socket: socket.socket, message_dict: dict):
        """Empaqueta un diccionario en JSON con salto de línea y lo envía al cliente."""
        try:
            bytes_to_send = encode_tcp_message(message_dict)
            client_socket.sendall(bytes_to_send)
        except Exception as e:
            print(f"[TCP] Error al enviar mensaje: {e}")

    def _process_message(self, json_string: str, client_socket: socket.socket, addr: tuple):
        try:
            message = json.loads(json_string)
            msg_type = message.get("type")
            
            if msg_type == "join":
                player_name = message.get('name', 'JugadorDesconocido')
                
                # Generamos un ID único corto para el jugador
                player_id = str(uuid.uuid4())[:8] 
                
                # Guardamos los datos del jugador en nuestra memoria
                self.clients[client_socket]["id"] = player_id
                self.clients[client_socket]["name"] = player_name
                
                print(f"[JUEGO] Jugador '{player_name}' (ID: {player_id}) se unió.")

                # 1. Registrar en el GameEngine
                if self.game_engine:
                    self.game_engine.add_player(player_id, player_name)
                
                # 2. Respondemos con el mensaje 'welcome' exigido por el protocolo
                welcome_msg = build_message("welcome", id=player_id)
                self._send_to_client(client_socket, welcome_msg)
                print(f"      -> Enviado 'welcome' a {player_name}")
                
        except json.JSONDecodeError:
            print(f"[TCP] Error: JSON inválido recibido de {addr}")
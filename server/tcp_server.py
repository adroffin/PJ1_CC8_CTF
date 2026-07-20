# server/tcp_server.py
import socket
import threading
import json

from core.constants import ENCODING

class TCPServer:
    def __init__(self, tcp_port: int):
        self.tcp_port = tcp_port
        self.running = False
        self.server_socket = None
        self.clients = []  # Lista para guardar las conexiones activas

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

    def _accept_connections(self):
        """Bucle infinito que acepta nuevos clientes y les asigna un hilo."""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[TCP] Nueva conexión entrante de {addr}")
                
                # Registramos al cliente (más adelante esto será un objeto de sesión más complejo)
                self.clients.append(client_socket)
                
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
            self.clients.remove(client_socket)
        client_socket.close()

    def _process_message(self, json_string: str, client_socket: socket.socket, addr: tuple):
        """Convierte el string a JSON y reacciona según el tipo de mensaje."""
        try:
            message = json.loads(json_string)
            msg_type = message.get("type")
            
            print(f"[TCP] Mensaje '{msg_type}' recibido de {addr}")
            
            # Aquí es donde más adelante enrutaremos los mensajes (join, input, interact)
            if msg_type == "join":
                print(f"      -> Jugador intentando unirse: {message.get('name')}")
                
        except json.JSONDecodeError:
            print(f"[TCP] Error: JSON inválido recibido de {addr}")
# server/discovery_service.py
import socket
import threading
import logging

from core.constants import DISCOVERY_PORT, PROTOCOL_VERSION
from core.protocol import decode_message, encode_udp_message, build_message

class DiscoveryService:
    def __init__(self, server_name: str, tcp_port: int):
        self.server_name = server_name
        self.tcp_port = tcp_port
        self.running = False
        self.sock = None
        self.thread = None
        # Opcional: estado simulado para el descubrimiento inicial
        self.current_state = "lobby" 
        self.player_count = 0

    def start(self):
        """Inicia el servicio de descubrimiento UDP en su propio hilo."""
        # Creamos el socket UDP (SOCK_DGRAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Permite reutilizar la dirección rápidamente si reiniciamos el servidor
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Escuchamos en todas las interfaces de red (0.0.0.0) en el puerto fijo 8888
        self.sock.bind(('0.0.0.0', DISCOVERY_PORT))
        
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print(f"[UDP] Servicio de descubrimiento iniciado en el puerto {DISCOVERY_PORT}")

    def stop(self):
        """Detiene el servicio de descubrimiento de forma segura."""
        self.running = False
        if self.sock:
            self.sock.close()
        print("[UDP] Servicio de descubrimiento detenido.")

    def _listen(self):
        """Bucle principal que escucha y responde a las solicitudes de descubrimiento."""
        while self.running:
            try:
                # Recibimos hasta 1024 bytes y la dirección del remitente
                data, addr = self.sock.recvfrom(1024)
                self._handle_request(data, addr)
            except OSError:
                # Esto ocurre normalmente cuando cerramos el socket al detener el servidor
                break
            except Exception as e:
                print(f"[UDP] Error inesperado en descubrimiento: {e}")

    def _handle_request(self, data: bytes, addr: tuple):
        """Procesa el mensaje recibido y envía la respuesta si es válido."""
        try:
            message = decode_message(data)
            
            # Verificamos que sea un mensaje tipo 'discover'
            if message.get("type") == "discover":
                # Construimos la respuesta 'server_info' exigida por el estándar
                response_dict = build_message(
                    msg_type="server_info",
                    v=PROTOCOL_VERSION,
                    name=self.server_name,
                    tcp_port=self.tcp_port,
                    state=self.current_state,
                    players=self.player_count
                )
                
                # Codificamos a bytes y lo enviamos de vuelta directamente a la IP del cliente
                response_bytes = encode_udp_message(response_dict)
                self.sock.sendto(response_bytes, addr)
                print(f"[UDP] Respondido 'server_info' a {addr}")
                
        except Exception as e:
            # Si el JSON es inválido o hay otro error, simplemente lo ignoramos (regla de oro en UDP)
            logging.debug(f"[UDP] Mensaje ignorado de {addr}: {e}")
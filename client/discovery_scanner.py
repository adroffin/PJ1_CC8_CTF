# client/discovery_scanner.py
import socket
import time

from core.constants import DISCOVERY_PORT, BROADCAST_IP, PROTOCOL_VERSION
from core.protocol import build_message, encode_udp_message, decode_message

class DiscoveryScanner:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout

    def scan_local_network(self) -> list:
        """
        Envía un broadcast UDP y recolecta las respuestas de los servidores activos.
        Devuelve una lista de diccionarios con la información de cada servidor.
        """
        servers_found = []
        
        # 1. Crear el socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 2. Habilitar explícitamente el permiso para enviar mensajes de broadcast
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # 3. Configurar el timeout para que el ciclo de escucha no se quede bloqueado para siempre
        sock.settimeout(self.timeout)

        # 4. Construir el mensaje de descubrimiento según el estándar
        discover_msg = build_message(msg_type="discover", v=PROTOCOL_VERSION)
        discover_bytes = encode_udp_message(discover_msg)

        try:
            # 5. Enviar el mensaje a toda la red (255.255.255.255) en el puerto 8888
            print(f"[Scanner] Buscando servidores en la red local ({self.timeout}s)...")
            sock.sendto(discover_bytes, (BROADCAST_IP, DISCOVERY_PORT))
            
            # 6. Escuchar respuestas hasta que se agote el tiempo (Timeout)
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = decode_message(data)
                    
                    # Verificamos que la respuesta sea del tipo esperado
                    if response.get("type") == "server_info":
                        server_info = {
                            "ip": addr[0],  # La IP real del servidor la obtenemos del remitente
                            "name": response.get("name", "Servidor Desconocido"),
                            "tcp_port": response.get("tcp_port"),
                            "state": response.get("state"),
                            "players": response.get("players", 0)
                        }
                        servers_found.append(server_info)
                        print(f"[Scanner] ¡Servidor encontrado! {server_info['name']} en {server_info['ip']}:{server_info['tcp_port']}")
                        
                except socket.timeout:
                    # El recvfrom levanta este error si pasa el tiempo límite, es normal
                    break
                except Exception as e:
                    print(f"[Scanner] Error procesando respuesta: {e}")

        except Exception as e:
            print(f"[Scanner] Error al enviar broadcast: {e}")
        finally:
            sock.close()

        return servers_found

    def manual_connection(self, ip_address: str, tcp_port: int) -> dict:
        """
        Permite la conexión manual requerida como respaldo si el broadcast falla.
        """
        return {
            "ip": ip_address,
            "name": "Conexión Manual",
            "tcp_port": tcp_port,
            "state": "lobby",
            "players": "?"
        }
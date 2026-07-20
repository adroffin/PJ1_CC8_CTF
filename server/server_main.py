# server/server_main.py
import time
from server.discovery_service import DiscoveryService
from server.tcp_server import TCPServer

def main():
    print("--- Servidor CTF ---")

    tcp_port = 8889

    # 1. Se inicia el servidor TCP para el juego
    tcp_server = TCPServer(tcp_port=tcp_port)
    tcp_server.start()

    # 2. Se inicia el descubrimiento UDP (se le pasa el puerto tcp para que lo anuncie)
    discovery = DiscoveryService(server_name="Servidor Alpha (Python)", tcp_port=tcp_port)
    discovery.start()

    try:
        print("Presiona Ctrl+C para detener el servidor.")
        # Mantenemos el hilo principal vivo en un bucle infinito
        while True:
            time.sleep(1) 
    except KeyboardInterrupt:
        print("\nApagando servidor...")
    finally:
        discovery.stop()
        tcp_server.stop()

if __name__ == "__main__":
    main()
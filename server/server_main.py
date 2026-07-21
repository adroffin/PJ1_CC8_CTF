# server/server_main.py
import time
from server.discovery_service import DiscoveryService
from server.tcp_server import TCPServer
from server.game_logic import GameEngine

def main():
    print("--- Servidor CTF ---")

    tcp_port = 8889

    # 1. Instanciamos Servidor TCP y Engine
    tcp_server = TCPServer(tcp_port=tcp_port)
    game_engine = GameEngine(tcp_server=tcp_server)
    
    # 2. Los conectamos entre sí
    tcp_server.set_game_engine(game_engine)
    
    # 3. Arrancamos los servicios
    tcp_server.start()
    game_engine.start()
    
    # 4. Servicio de descubrimiento UDP
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
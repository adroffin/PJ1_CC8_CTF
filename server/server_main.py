# server/server_main.py
import time
from server.discovery_service import DiscoveryService

def main():
    # Inicializamos el servicio. El puerto TCP 8889 es un ejemplo por ahora
    print("--- Servidor CTF ---")
    discovery = DiscoveryService(server_name="Servidor Alpha (Python)", tcp_port=8889)
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

if __name__ == "__main__":
    main()
import time
from client.discovery_scanner import DiscoveryScanner
from client.game_client import GameClient

def main():
    print("--- Captura la Bandera ---")
    print("1. Buscar servidores en red local")
    print("2. Conexión manual por IP")
    
    opcion = input("Elige una opción: ")
    scanner = DiscoveryScanner(timeout=10.0)
    servidor_elegido = None
    
    if opcion == "1":
        servidores = scanner.scan_local_network()
        if servidores:
            print("\n--- Servidores Encontrados ---")
            for i, srv in enumerate(servidores):
                print(f"[{i+1}] {srv['name']} ({srv['ip']}:{srv['tcp_port']})")
            
            # Elegimos el primero por defecto para probar rápido
            servidor_elegido = servidores[0]
        else:
            print("No se encontraron servidores.")
            
    elif opcion == "2":
        ip = input("Ingresa la IP del servidor: ")
        puerto = int(input("Ingresa el puerto TCP: "))
        servidor_elegido = scanner.manual_connection(ip, puerto)

    # --- Nueva Lógica de Conexión TCP ---
    if servidor_elegido:
        nombre = input("\nIngresa tu nombre de jugador: ")
        cliente_tcp = GameClient(
            host=servidor_elegido["ip"], 
            port=servidor_elegido["tcp_port"], 
            player_name=nombre
        )
        
        if cliente_tcp.connect():
            try:
                # Mantenemos el hilo principal vivo SIN usar input() 
                # para no secuestrar el teclado de msvcrt
                while cliente_tcp.running:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nSaliendo del juego...")
            finally:
                cliente_tcp.running = False
                if cliente_tcp.sock:
                    cliente_tcp.sock.close()

if __name__ == "__main__":
    main()
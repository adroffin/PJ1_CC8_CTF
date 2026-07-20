# client/client_main.py
from client.discovery_scanner import DiscoveryScanner

def main():
    print("--- Captura la Bandera ---")
    print("1. Buscar servidores en red local")
    print("2. Conexión manual por IP")
    
    opcion = input("Elige una opción: ")
    scanner = DiscoveryScanner(timeout=10.0)
    
    if opcion == "1":
        servidores = scanner.scan_local_network()
        if not servidores:
            print("No se encontraron servidores en la red local.")
        else:
            print("\n--- Servidores Encontrados ---")
            for i, srv in enumerate(servidores):
                print(f"[{i+1}] {srv['name']} ({srv['ip']}:{srv['tcp_port']}) - Jugadores: {srv['players']}")
                
    elif opcion == "2":
        ip = input("Ingresa la IP del servidor: ")
        puerto = int(input("Ingresa el puerto TCP: "))
        servidor = scanner.manual_connection(ip, puerto)
        print(f"Conectando manualmente a {servidor['ip']}:{servidor['tcp_port']}...")
        
    else:
        print("Opción no válida.")

if __name__ == "__main__":
    main()
import sys
import time
import pygame
import threading

# --- IMPORTACIONES LOGICA ---
from server.tcp_server import TCPServer
from server.game_logic import GameEngine
from client.game_client import GameClient
from core.protocol import build_message, encode_tcp_message
from core.constants import MAP_SIZE, CIRCLE_RADIUS, PLAYER_RADIUS

# --- IMPORTACIONES UDP ---
from client.discovery_scanner import DiscoveryScanner
from server.discovery_service import DiscoveryService

# --- CONFIGURACIÓN DE PYGAME ---
WINDOW_SIZE = 800
SCALE = WINDOW_SIZE / MAP_SIZE
FPS = 60

C_BG = (30, 30, 30)
C_WHITE = (255, 255, 255)
C_GREEN = (50, 200, 50)
C_RED = (200, 50, 50)
C_YELLOW = (255, 215, 0)
C_GRAY = (100, 100, 100)
C_BLUE = (50, 150, 255)
C_ACTIVE_BOX = (200, 200, 200)
C_INACTIVE_BOX = (80, 80, 80)
C_ORANGE = (255, 140, 0)

class GUIClient(GameClient):
    def _render_ui(self):
        pass 
    def _input_loop(self):
        pass

def draw_text(surface, text, font, color, x, y, center=False):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("CTF Game - Launcher")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 24, bold=True)
    title_font = pygame.font.SysFont("arial", 48, bold=True)

    app_state = "MENU"
    my_server = None
    my_engine = None
    my_client = None
    my_discovery = None

    last_input_time = 0
    input_cooldown = 0.05 

    player_name = ""
    server_ip = "127.0.0.1"
    server_port_str = "5555"  
    server_port = 5555
    
    name_rect = pygame.Rect(200, 160, 400, 40)
    ip_rect = pygame.Rect(200, 250, 200, 40) 
    port_rect = pygame.Rect(410, 250, 70, 40) 
    search_btn_rect = pygame.Rect(490, 250, 110, 40) 
    
    active_input = None
    search_status = "" 
    connection_status = "" 
    
    is_searching = False 
    is_connecting = False  

    # --- DICCIONARIO DE COMUNICACIÓN ENTRE HILOS ---
    # Esto evita que los hilos secundarios modifiquen Pygame directamente
    thread_results = {
        "search_done": False,
        "search_msg": "",
        "found_ip": "",
        "found_port": 5555,
        "connect_status": None, # Puede ser "SUCCESS" o "ERROR"
        "client_instance": None,
        "client_name": ""
    }

    # --- FUNCIÓN HILO DE BÚSQUEDA ---
    def search_server_thread():
        scanner = DiscoveryScanner(timeout=2.0)
        servers = scanner.scan_local_network()
        
        if servers:
            thread_results["found_ip"] = servers[0]["ip"]
            thread_results["found_port"] = servers[0]["tcp_port"] 
            thread_results["search_msg"] = f"¡Encontrado: {servers[0]['name']}!"
        else:
            thread_results["search_msg"] = "No se encontraron servidores."
        
        thread_results["search_done"] = True

    # --- FUNCIÓN HILO DE CONEXIÓN ---
    def connect_client_thread(ip, port, name):
        temp_client = GUIClient(ip, port, name)
        
        if temp_client.connect():
            thread_results["client_instance"] = temp_client
            thread_results["client_name"] = name
            thread_results["connect_status"] = "SUCCESS"
        else:
            thread_results["connect_status"] = "ERROR"

    running = True
    while running:
        screen.fill(C_BG)
        mouse_pos = pygame.mouse.get_pos()

        # --- VERIFICAR MENSAJES DE LOS HILOS (SEGURO PARA PYGAME) ---
        if thread_results["search_done"]:
            search_status = thread_results["search_msg"]
            if thread_results["found_ip"]:
                server_ip = thread_results["found_ip"]
                server_port_str = str(thread_results["found_port"])
            is_searching = False
            thread_results["search_done"] = False

        if thread_results["connect_status"] == "SUCCESS":
            my_client = thread_results["client_instance"]
            app_state = "CLIENT"
            pygame.display.set_caption(f"CTF Game - Cliente ({thread_results['client_name']})")
            is_connecting = False
            connection_status = ""
            thread_results["connect_status"] = None
            
        elif thread_results["connect_status"] == "ERROR":
            connection_status = "Error: Servidor inalcanzable."
            is_connecting = False
            thread_results["connect_status"] = None

        # --- BUCLE DE EVENTOS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- EVENTOS DEL MENÚ ---
            if app_state == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if name_rect.collidepoint(event.pos):
                            active_input = "NAME"
                        elif ip_rect.collidepoint(event.pos):
                            active_input = "IP"
                        elif port_rect.collidepoint(event.pos):
                            active_input = "PORT"
                        else:
                            active_input = None

                        # Botón: Buscar Servidor (UDP)
                        if search_btn_rect.collidepoint(event.pos) and not is_searching and not is_connecting:
                            is_searching = True
                            search_status = "Buscando en la red..."
                            connection_status = ""
                            threading.Thread(target=search_server_thread, daemon=True).start()

                        # Botón: Servidor
                        if 200 <= mouse_pos[0] <= 600 and 340 <= mouse_pos[1] <= 420 and not is_connecting:
                            app_state = "SERVER"
                            final_name = player_name.strip() if player_name.strip() else "Servidor CTF"
                            pygame.display.set_caption(f"CTF Game - Servidor Espectador ({final_name})")
                            
                            # Aquí se asegura de iniciar tanto TCP como el servicio Discovery
                            my_server = TCPServer(5555)
                            my_engine = GameEngine(my_server)
                            my_server.set_game_engine(my_engine)
                            my_server.start()
                            my_engine.start()
                            
                            my_discovery = DiscoveryService(server_name=final_name, tcp_port=5555)
                            my_discovery.start()

                        # Botón: Cliente
                        elif 200 <= mouse_pos[0] <= 600 and 450 <= mouse_pos[1] <= 530 and not is_connecting:
                            final_name = player_name.strip() if player_name.strip() else "JugadorAnonimo"
                            final_ip = server_ip.strip() if server_ip.strip() else "127.0.0.1"
                            final_port = int(server_port_str) if server_port_str.strip() else 5555
                            
                            is_connecting = True
                            connection_status = f"Conectando a {final_ip}:{final_port}..."
                            search_status = ""
                            threading.Thread(
                                target=connect_client_thread, 
                                args=(final_ip, final_port, final_name), 
                                daemon=True
                            ).start()

                # Lógica para escribir
                if event.type == pygame.KEYDOWN and active_input:
                    if event.key == pygame.K_BACKSPACE:
                        if active_input == "NAME":
                            player_name = player_name[:-1]
                        elif active_input == "IP":
                            server_ip = server_ip[:-1]
                        elif active_input == "PORT":
                            server_port_str = server_port_str[:-1]
                    else:
                        if event.unicode.isprintable():
                            if active_input == "NAME" and len(player_name) < 15:
                                player_name += event.unicode
                            elif active_input == "IP" and len(server_ip) < 15:
                                server_ip += event.unicode
                            elif active_input == "PORT" and len(server_port_str) < 5 and event.unicode.isdigit():
                                server_port_str += event.unicode

            # --- EVENTOS DEL SERVIDOR ---
            if app_state == "SERVER" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if my_engine and my_engine.game_state == "LOBBY" and my_engine.get_player_count() >= 2:
                    if 300 <= mouse_pos[0] <= 500 and 700 <= mouse_pos[1] <= 750:
                        my_engine.start_game_manually()

            # --- EVENTOS DEL CLIENTE ---
            if app_state == "CLIENT" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and my_client.sock:
                    try:
                        my_client.sock.sendall(encode_tcp_message(build_message("interact")))
                    except:
                        pass

        # --- RENDERIZADO DEL MENÚ ---
        if app_state == "MENU":
            draw_text(screen, "CAPTURA LA BANDERA CTF", title_font, C_WHITE, WINDOW_SIZE//2, 80, center=True)
            
            draw_text(screen, "Ingresa tu nombre:", font, C_WHITE, 200, 130)
            box_color_name = C_ACTIVE_BOX if active_input == "NAME" else C_INACTIVE_BOX
            pygame.draw.rect(screen, box_color_name, name_rect, border_radius=5)
            disp_name = player_name + ("|" if active_input == "NAME" and time.time() % 1 > 0.5 else "")
            screen.blit(font.render(disp_name, True, (0, 0, 0) if active_input == "NAME" else C_WHITE), (name_rect.x + 10, name_rect.y + 5))

            draw_text(screen, "IP del Servidor y Puerto:", font, C_WHITE, 200, 220)
            
            # Dibujar caja de IP
            box_color_ip = C_ACTIVE_BOX if active_input == "IP" else C_INACTIVE_BOX
            pygame.draw.rect(screen, box_color_ip, ip_rect, border_radius=5)
            disp_ip = server_ip + ("|" if active_input == "IP" and time.time() % 1 > 0.5 else "")
            screen.blit(font.render(disp_ip, True, (0, 0, 0) if active_input == "IP" else C_WHITE), (ip_rect.x + 10, ip_rect.y + 5))

            # Dibujar caja de PUERTO
            box_color_port = C_ACTIVE_BOX if active_input == "PORT" else C_INACTIVE_BOX
            pygame.draw.rect(screen, box_color_port, port_rect, border_radius=5)
            disp_port = server_port_str + ("|" if active_input == "PORT" and time.time() % 1 > 0.5 else "")
            screen.blit(font.render(disp_port, True, (0, 0, 0) if active_input == "PORT" else C_WHITE), (port_rect.x + 10, port_rect.y + 5))

            btn_color = C_ORANGE if search_btn_rect.collidepoint(mouse_pos) else C_GRAY
            pygame.draw.rect(screen, btn_color, search_btn_rect, border_radius=5)
            draw_text(screen, "Buscar", font, C_WHITE, search_btn_rect.centerx, search_btn_rect.centery, center=True)
            
            if search_status:
                draw_text(screen, search_status, font, C_YELLOW, WINDOW_SIZE//2, 305, center=True)

            color_srv = C_BLUE if (200 <= mouse_pos[0] <= 600 and 340 <= mouse_pos[1] <= 420) else C_GRAY
            pygame.draw.rect(screen, color_srv, (200, 340, 400, 80), border_radius=10)
            draw_text(screen, "Iniciar como SERVIDOR", font, C_WHITE, WINDOW_SIZE//2, 380, center=True)
            
            color_cli = C_GREEN if (200 <= mouse_pos[0] <= 600 and 450 <= mouse_pos[1] <= 530) else C_GRAY
            pygame.draw.rect(screen, color_cli, (200, 450, 400, 80), border_radius=10)
            draw_text(screen, "Conectar como CLIENTE", font, C_WHITE, WINDOW_SIZE//2, 490, center=True)

            if connection_status:
                draw_text(screen, connection_status, font, C_YELLOW, WINDOW_SIZE//2, 550, center=True)

        # --- RENDERIZADO DEL SERVIDOR ---
        elif app_state == "SERVER":
            if my_engine:
                center_x = (MAP_SIZE // 2) * SCALE
                center_y = (MAP_SIZE // 2) * SCALE
                pygame.draw.circle(screen, (50, 50, 50), (center_x, center_y), CIRCLE_RADIUS * SCALE, 2)
                
                with my_engine.lock:
                    game_state = my_engine.game_state
                    player_count = len(my_engine.players)
                    winner = my_engine.winner_name
                    flag = my_engine.flag
                    players_list = list(my_engine.players.values())
                
                if flag.get("owner") is None:
                    fx = flag.get("x", MAP_SIZE//2) * SCALE
                    fy = flag.get("y", MAP_SIZE//2) * SCALE
                    pygame.draw.rect(screen, C_YELLOW, (fx - 10, fy - 10, 20, 20))

                for player in players_list:
                    px = player.get("x", MAP_SIZE // 2) * SCALE
                    py = player.get("y", MAP_SIZE // 2) * SCALE
                    p_name = player.get("name", "Jugador")
                    
                    color = C_YELLOW if player.get("has_flag") else C_RED
                    pygame.draw.circle(screen, color, (px, py), PLAYER_RADIUS * SCALE)
                    draw_text(screen, p_name, font, C_WHITE, px, py - 25, center=True)

                draw_text(screen, f"[ESPECTADOR] ESTADO: {game_state}", font, C_WHITE, 10, 10)
                draw_text(screen, f"Jugadores Conectados: {player_count}", font, C_WHITE, 10, 40)

                if game_state == "GAME_OVER" and winner:
                    draw_text(screen, f"¡GANADOR: {winner}!", title_font, C_YELLOW, WINDOW_SIZE//2, WINDOW_SIZE//2, center=True)

                if game_state == "LOBBY":
                    if player_count >= 2:
                        btn_color = C_GREEN if (300 <= mouse_pos[0] <= 500 and 700 <= mouse_pos[1] <= 750) else C_GRAY
                        pygame.draw.rect(screen, btn_color, (300, 700, 200, 50), border_radius=5)
                        draw_text(screen, "Iniciar Partida", font, C_WHITE, WINDOW_SIZE//2, 725, center=True)
                    else:
                        draw_text(screen, "Esperando más jugadores (Mín. 2)...", font, C_GRAY, WINDOW_SIZE//2, 725, center=True)

        # --- RENDERIZADO DEL CLIENTE ---
        elif app_state == "CLIENT":
            g_state = my_client.game_state

            state = my_client.latest_state

            if g_state == "LOBBY":
                draw_text(screen, f"LOBBY - {len(my_client.lobby_players)} Jugadores", title_font, C_WHITE, WINDOW_SIZE//2, 100, center=True)
                draw_text(screen, "Esperando a que el anfitrión inicie...", font, C_GRAY, WINDOW_SIZE//2, 150, center=True)

            elif g_state == "COUNTDOWN":
                sec = getattr(my_client, "countdown_seconds", "")
                draw_text(screen, f"¡Iniciando en {sec}!", title_font, C_YELLOW, WINDOW_SIZE//2, WINDOW_SIZE//2, center=True)

            elif g_state in ["PLAYING", "GAME_OVER"]:
                if not state:
                    draw_text(screen, "Cargando mapa...", font, C_WHITE, WINDOW_SIZE//2, WINDOW_SIZE//2, center=True)
                elif state:
                    center_x = (MAP_SIZE // 2) * SCALE
                    center_y = (MAP_SIZE // 2) * SCALE
                    pygame.draw.circle(screen, (50, 50, 50), (center_x, center_y), CIRCLE_RADIUS * SCALE, 2)
                    
                    flag = state.get("flag", {})
                    if flag.get("owner") is None:
                        fx = flag.get("x", MAP_SIZE//2) * SCALE
                        fy = flag.get("y", MAP_SIZE//2) * SCALE
                        pygame.draw.rect(screen, C_YELLOW, (fx - 10, fy - 10, 20, 20))

                    for player in state.get("players", []):
                        px = player.get("x", MAP_SIZE // 2) * SCALE
                        py = player.get("y", MAP_SIZE // 2) * SCALE

                        p_id = player.get("id")
                        p_name = player.get("name")
                        if not p_name:
                            p_name = "Jugador"
                            for lp in my_client.lobby_players:
                                if lp.get("id") == p_id:
                                    p_name = lp.get("name", "Jugador")
                                    break
                        
                        is_me = (p_id == my_client.my_id)
                        is_flag_carrier = (flag.get("owner") == p_id)
                        color = C_YELLOW if is_flag_carrier else (C_GREEN if is_me else C_RED)
                        
                        pygame.draw.circle(screen, color, (px, py), PLAYER_RADIUS * SCALE)
                        draw_text(screen, p_name, font, C_WHITE, px, py - 25, center=True)

                    if g_state == "PLAYING":
                        keys = pygame.key.get_pressed()
                        dir_x, dir_y = 0, 0
                        if keys[pygame.K_w]: dir_y -= 1
                        if keys[pygame.K_s]: dir_y += 1
                        if keys[pygame.K_a]: dir_x -= 1
                        if keys[pygame.K_d]: dir_x += 1

                        current_time = time.time()
                        if current_time - last_input_time >= input_cooldown:
                            try:
                                input_msg = build_message("input", dir={"x": dir_x, "y": dir_y})
                                my_client.sock.sendall(encode_tcp_message(input_msg))
                                last_input_time = current_time
                            except:
                                pass

                    draw_text(screen, f"ESTADO: {g_state}", font, C_WHITE, 10, 10)
                    if g_state == "GAME_OVER" and my_client.winner:

                        win_name = my_client.winner
                        for lp in my_client.lobby_players:
                            if lp.get("id") == my_client.winner:
                                win_name = lp.get("name", "Jugador")
                                break

                        draw_text(screen, f"¡GANADOR: {win_name}!", title_font, C_YELLOW, WINDOW_SIZE//2, WINDOW_SIZE//2, center=True)

        pygame.display.flip()
        clock.tick(FPS)

    if my_discovery: my_discovery.stop() 
    if my_server: my_server.stop()
    if my_engine: my_engine.stop()
    if my_client: my_client.running = False
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
import sys
import time
import pygame
import threading

# Importamos las lógicas existentes de tu proyecto
from server.tcp_server import TCPServer
from server.game_logic import GameEngine
from client.game_client import GameClient
from core.protocol import build_message, encode_tcp_message

# Importamos las constantes (asumimos que existen en tu core.constants)
from core.constants import MAP_SIZE, CIRCLE_RADIUS, PLAYER_RADIUS

# --- CONFIGURACIÓN DE PYGAME ---
WINDOW_SIZE = 800
SCALE = WINDOW_SIZE / MAP_SIZE  # Para adaptar el mapa de 1000x1000 a la ventana de 800x800
FPS = 60

# Colores
C_BG = (30, 30, 30)
C_WHITE = (255, 255, 255)
C_GREEN = (50, 200, 50)
C_RED = (200, 50, 50)
C_YELLOW = (255, 215, 0)
C_GRAY = (100, 100, 100)
C_BLUE = (50, 150, 255)
C_ACTIVE_BOX = (200, 200, 200)
C_INACTIVE_BOX = (80, 80, 80)

class GUIClient(GameClient):
    """
    Heredamos de tu GameClient original pero sobrescribimos la UI de consola 
    y la lectura de teclado para que Pygame se encargue de eso.
    """
    def _render_ui(self):
        pass  # Desactivamos el renderizado en la terminal

    def _input_loop(self):
        pass  # Desactivamos el bucle de teclado por consola (msvcrt)

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

    # Estados de la aplicación: MENU, SERVER, CLIENT
    app_state = "MENU"
    
    # Variables globales para el servidor o cliente
    my_server = None
    my_engine = None
    my_client = None

    last_input_time = 0
    input_cooldown = 0.05  # Enviar movimiento al servidor cada 50ms (20Hz)

    # Variables para el cuadro de texto del nombre
    player_name = ""
    input_rect = pygame.Rect(200, 220, 400, 50)
    input_active = False

    running = True
    while running:
        screen.fill(C_BG)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Controles en el MENÚ
            if app_state == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # Verificar si se hizo clic en el cuadro de texto
                        if input_rect.collidepoint(event.pos):
                            input_active = True
                        else:
                            input_active = False

                        # Botón de Servidor
                        if 200 <= mouse_pos[0] <= 600 and 310 <= mouse_pos[1] <= 390:
                            app_state = "SERVER"
                            pygame.display.set_caption("CTF Game - Servidor Dedicado")
                            my_server = TCPServer(5555)
                            my_engine = GameEngine(my_server)
                            my_server.set_game_engine(my_engine)
                            my_server.start()
                            my_engine.start()

                        # Botón de Cliente
                        elif 200 <= mouse_pos[0] <= 600 and 430 <= mouse_pos[1] <= 510:
                            # Si el usuario no escribió nada, le ponemos un nombre por defecto
                            final_name = player_name.strip() if player_name.strip() else "JugadorAnonimo"
                            
                            app_state = "CLIENT"
                            pygame.display.set_caption(f"CTF Game - Cliente ({final_name})")
                            # Para este ejemplo, conectamos a localhost (puedes cambiarlo)
                            my_client = GUIClient("127.0.0.1", 5555, final_name)
                            if not my_client.connect():
                                print("No se pudo conectar al servidor.")
                                app_state = "MENU"

                # Lógica para escribir en el cuadro de texto
                if event.type == pygame.KEYDOWN and input_active:
                    if event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                    else:
                        # Limitar el nombre a un máximo de 15 caracteres para no romper la UI
                        if len(player_name) < 15 and event.unicode.isprintable():
                            player_name += event.unicode

            # Controles de juego (Tecla P para bandera)
            if app_state == "CLIENT" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and my_client.sock:
                    interact_msg = build_message("interact")
                    try:
                        my_client.sock.sendall(encode_tcp_message(interact_msg))
                    except:
                        pass

        # --- DIBUJADO SEGÚN EL ESTADO DE LA APP ---
        if app_state == "MENU":
            draw_text(screen, "CAPTURA LA BANDERA CTF", title_font, C_WHITE, WINDOW_SIZE//2, 100, center=True)
            
            # Dibujar cuadro de texto para el nombre
            draw_text(screen, "Ingresa tu nombre:", font, C_WHITE, 200, 180)
            box_color = C_ACTIVE_BOX if input_active else C_INACTIVE_BOX
            pygame.draw.rect(screen, box_color, input_rect, border_radius=5)
            # Dibujar texto dentro del cuadro (añadimos cursor parpadeante si está activo)
            display_name = player_name + ("|" if input_active and time.time() % 1 > 0.5 else "")
            text_surface = font.render(display_name, True, (0, 0, 0) if input_active else C_WHITE)
            screen.blit(text_surface, (input_rect.x + 10, input_rect.y + 10))

            # Botón Servidor
            color_srv = C_BLUE if (200 <= mouse_pos[0] <= 600 and 310 <= mouse_pos[1] <= 390) else C_GRAY
            pygame.draw.rect(screen, color_srv, (200, 310, 400, 80), border_radius=10)
            draw_text(screen, "Iniciar como SERVIDOR", font, C_WHITE, WINDOW_SIZE//2, 350, center=True)
            
            # Botón Cliente
            color_cli = C_GREEN if (200 <= mouse_pos[0] <= 600 and 430 <= mouse_pos[1] <= 510) else C_GRAY
            pygame.draw.rect(screen, color_cli, (200, 430, 400, 80), border_radius=10)
            draw_text(screen, "Conectar como CLIENTE", font, C_WHITE, WINDOW_SIZE//2, 470, center=True)

        elif app_state == "SERVER":
            draw_text(screen, "SERVIDOR EN EJECUCIÓN", title_font, C_YELLOW, WINDOW_SIZE//2, 100, center=True)
            
            if my_engine:
                players_count = my_engine.get_player_count()
                game_state = my_engine.game_state
                draw_text(screen, f"Estado del Juego: {game_state}", font, C_WHITE, WINDOW_SIZE//2, 250, center=True)
                draw_text(screen, f"Jugadores conectados: {players_count}", font, C_WHITE, WINDOW_SIZE//2, 300, center=True)
                draw_text(screen, "(Cierra la ventana para apagar el servidor)", font, C_GRAY, WINDOW_SIZE//2, WINDOW_SIZE - 50, center=True)

        elif app_state == "CLIENT":
            if not my_client.latest_state:
                draw_text(screen, "Conectando / Esperando estado del servidor...", font, C_WHITE, WINDOW_SIZE//2, WINDOW_SIZE//2, center=True)
            else:
                state = my_client.latest_state
                g_state = my_client.game_state

                # 1. Dibujar el mapa y la zona segura (Safe Zone)
                center_x = (MAP_SIZE // 2) * SCALE
                center_y = (MAP_SIZE // 2) * SCALE
                pygame.draw.circle(screen, (50, 50, 50), (center_x, center_y), CIRCLE_RADIUS * SCALE, 2)
                
                # 2. Dibujar la bandera
                flag = state.get("flag", {})
                if flag.get("carrier_id") is None:
                    fx = flag.get("x", MAP_SIZE//2) * SCALE
                    fy = flag.get("y", MAP_SIZE//2) * SCALE
                    pygame.draw.rect(screen, C_YELLOW, (fx - 10, fy - 10, 20, 20))

                # 3. Dibujar jugadores
                for player in state.get("players", []):
                    px = player["x"] * SCALE
                    py = player["y"] * SCALE
                    
                    is_me = (player["id"] == my_client.my_id)
                    color = C_YELLOW if player.get("has_flag") else (C_GREEN if is_me else C_RED)
                    
                    pygame.draw.circle(screen, color, (px, py), PLAYER_RADIUS * SCALE)
                    
                    # Dibujar nombre
                    draw_text(screen, player["name"], font, C_WHITE, px, py - 25, center=True)

                # 4. Enviar inputs
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

                # 5. Dibujar UI (HUD)
                draw_text(screen, f"ESTADO: {g_state}", font, C_WHITE, 10, 10)
                if g_state == "GAME_OVER" and my_client.winner:
                    draw_text(screen, f"¡GANADOR: {my_client.winner}!", title_font, C_YELLOW, WINDOW_SIZE//2, WINDOW_SIZE//2, center=True)

        pygame.display.flip()
        clock.tick(FPS)

    # Limpieza
    if my_server:
        my_server.stop()
    if my_engine:
        my_engine.stop()
    if my_client:
        my_client.running = False
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
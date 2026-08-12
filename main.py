# main.py
"""
Punto de entrada principal del juego de fútbol.
Inicializa Pygame, crea el partido, el renderizador, el manejador de entrada
y la interfaz de usuario, y ejecuta el bucle principal con control de tiempo.
Soporta pantalla completa (F11) y no se detiene en los goles.
"""

import pygame
import sys
from backend.config import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN
from backend.game import Partido
from frontend.renderer import Renderer
from frontend.input_handler import InputHandler
from frontend.ui import UI


def main():
    """Función principal: inicializa y ejecuta el juego."""
    # 1. Inicializar Pygame
    pygame.init()

    # 2. Crear la ventana (con soporte para pantalla completa)
    flags = pygame.FULLSCREEN if FULLSCREEN else 0
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    pygame.display.set_caption("Fútbol 2D - Simulación")

    # 3. Crear el reloj para controlar los FPS y el delta time
    clock = pygame.time.Clock()

    # 4. Crear el backend (lógica del partido)
    partido = Partido(duracion_minutos=90, jugador_humano_equipo="local")

    # 5. Crear el frontend
    renderer = Renderer(screen)
    input_handler = InputHandler(partido)
    ui = UI(screen, partido)

    # 6. Bucle principal
    running = True
    while running:
        # Calcular delta time (limitado a 60 FPS)
        dt = clock.tick(60) / 1000.0

        # ---- Procesar eventos de teclado (InputHandler) ----
        input_handler.handle_events()

        # ---- Actualizar la interfaz de usuario (ratón y temporizadores) ----
        ui.update(dt)

        # ---- Sincronizar el modo de la UI con el estado del partido ----
        # Si el partido está en pausa y la UI no está en un modo especial,
        # cambiamos la UI a modo pausa.
        if partido.estado == "pausa" and ui.modo not in ("stats", "sustituciones", "tacticas"):
            ui.modo = "pausa"
        elif partido.estado != "pausa" and ui.modo == "pausa":
            ui.modo = "juego"

        # ---- Actualizar la lógica del partido ----
        # Solo si el partido está en juego y la UI no está bloqueando (ej. mostrando menú)
        if partido.estado == "jugando" and not ui.esta_activa():
            partido.update(dt)

        # ---- Obtener el estado del partido para renderizar ----
        estado = partido.obtener_estado()

        # ---- Renderizar ----
        # 1. Dibujar el campo, jugadores, pelota, etc. (renderer)
        renderer.render(estado)

        # 2. Dibujar la interfaz de usuario encima (menús, paneles, notificaciones)
        ui.dibujar(estado)

        # ---- Actualizar la pantalla ----
        pygame.display.flip()

        # ---- Verificar cierre del juego (por si input_handler no lo capturó) ----
        for event in pygame.event.get(pygame.QUIT):
            if event.type == pygame.QUIT:
                running = False
                break

    # 7. Salir limpiamente
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
# frontend/renderer.py
"""
Módulo de renderizado. Dibuja todos los elementos del juego en la pantalla:
- Campo, líneas, porterías, áreas.
- Jugadores con números, colores de equipo, barras de fatiga y estado (tarjetas, lesiones).
- Pelota.
- Marcador (goles, tiempo, posesión).
- Tácticas de cada equipo.
- Eventos (gol, tarjetas, lesiones) mediante notificaciones.
- Menú de pausa (opcional).
"""

import pygame
import math
from backend.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_RADIUS, BALL_RADIUS,
    GOAL_DEPTH, GOAL_HEIGHT,
    COLORS
)
from backend.entities import Jugador, Pelota, Equipo


class Renderer:
    """Dibuja todo el estado del juego en la pantalla."""

    def __init__(self, screen):
        self.screen = screen
        self.font_pequeño = pygame.font.Font(None, 22)
        self.font_mediano = pygame.font.Font(None, 30)
        self.font_grande = pygame.font.Font(None, 48)
        self.font_titulo = pygame.font.Font(None, 72)

        # Para notificaciones (gol, tarjetas, lesiones)
        self.notificacion = None
        self.tiempo_notificacion = 0.0

    def render(self, estado):
        """
        Dibuja todo el estado del juego.
        'estado' es el diccionario devuelto por Partido.obtener_estado().
        """
        # Limpiar pantalla
        self.screen.fill(COLORS["campo"])

        # Obtener referencias del estado
        pelota = estado["pelota"]
        equipo_local = estado["equipo_local"]
        equipo_rival = estado["equipo_rival"]
        goles_local = estado["goles_local"]
        goles_rival = estado["goles_rival"]
        estado_juego = estado["estado"]
        jugador_humano = estado["jugador_humano"]
        minuto = estado["minuto"]
        segundo = estado["segundo"]
        tiempo_total = estado["tiempo_total"]

        # 1. Dibujar el campo y las porterías
        self._dibujar_campo()
        self._dibujar_porterias()

        # 2. Dibujar jugadores (equipo local y rival)
        for jug in equipo_local.jugadores:
            self._dibujar_jugador(jug, equipo_local.color, es_local=True)
        for jug in equipo_rival.jugadores:
            self._dibujar_jugador(jug, equipo_rival.color, es_local=False)

        # 3. Destacar al jugador humano
        if jugador_humano is not None:
            pygame.draw.circle(self.screen, COLORS["destacado"],
                               (int(jugador_humano.x), int(jugador_humano.y)),
                               jugador_humano.radio + 4, 2)

        # 4. Dibujar la pelota
        self._dibujar_pelota(pelota)

        # 5. Dibujar marcador (goles, tiempo, posesión)
        self._dibujar_marcador(goles_local, goles_rival, minuto, segundo, tiempo_total)

        # 6. Dibujar tácticas de cada equipo (debajo del marcador)
        self._dibujar_tacticas(equipo_local, equipo_rival)

        # 7. Dibujar barras de fatiga de todos los jugadores (opcional, solo para el humano y poseedor)
        self._dibujar_fatigas(equipo_local, equipo_rival, jugador_humano)

        # 8. Dibujar indicadores de tarjetas y lesiones
        self._dibujar_estado_jugadores(equipo_local, equipo_rival)

        # 9. Dibujar notificaciones (gol, tarjetas, lesiones)
        self._dibujar_notificaciones()

        # 10. Si el partido está en pausa, mostrar menú de pausa
        if estado_juego == "pausa":
            self._dibujar_menu_pausa()

        # 11. Si el partido ha terminado, mostrar pantalla de fin
        if estado_juego == "fin_partido":
            self._dibujar_fin_partido(goles_local, goles_rival)

        # 12. Si hay un gol, mostrar mensaje grande
        if estado_juego == "gol":
            self._dibujar_mensaje_gol()

        # Actualizar la ventana (se hace en main.py, no aquí)

    # ------------------------------------------------------------
    #  Dibujo del campo
    # ------------------------------------------------------------
    def _dibujar_campo(self):
        """Dibuja las líneas del campo de fútbol."""
        # Línea central
        pygame.draw.line(self.screen, COLORS["lineas"],
                         (SCREEN_WIDTH // 2, 0),
                         (SCREEN_WIDTH // 2, SCREEN_HEIGHT), 2)

        # Círculo central
        centro_x = SCREEN_WIDTH // 2
        centro_y = SCREEN_HEIGHT // 2
        pygame.draw.circle(self.screen, COLORS["lineas"],
                           (centro_x, centro_y), 80, 2)
        pygame.draw.circle(self.screen, COLORS["lineas"],
                           (centro_x, centro_y), 4)

        # Áreas (rectángulos)
        self._dibujar_area(0, SCREEN_HEIGHT // 2 - GOAL_HEIGHT // 2,
                           GOAL_DEPTH * 2, GOAL_HEIGHT, COLORS["lineas"])
        self._dibujar_area(SCREEN_WIDTH - GOAL_DEPTH * 2,
                           SCREEN_HEIGHT // 2 - GOAL_HEIGHT // 2,
                           GOAL_DEPTH * 2, GOAL_HEIGHT, COLORS["lineas"])

    def _dibujar_area(self, x, y, ancho, alto, color):
        """Dibuja un rectángulo de área (línea)."""
        rect = pygame.Rect(x, y, ancho, alto)
        pygame.draw.rect(self.screen, color, rect, 2)

    def _dibujar_porterias(self):
        """Dibuja las porterías (rectángulos rellenos)."""
        # Portería izquierda (local)
        left_goal = pygame.Rect(0,
                                SCREEN_HEIGHT // 2 - GOAL_HEIGHT // 2,
                                GOAL_DEPTH, GOAL_HEIGHT)
        pygame.draw.rect(self.screen, COLORS["porteria"], left_goal)
        pygame.draw.rect(self.screen, COLORS["lineas"], left_goal, 2)

        # Portería derecha (rival)
        right_goal = pygame.Rect(SCREEN_WIDTH - GOAL_DEPTH,
                                 SCREEN_HEIGHT // 2 - GOAL_HEIGHT // 2,
                                 GOAL_DEPTH, GOAL_HEIGHT)
        pygame.draw.rect(self.screen, COLORS["porteria"], right_goal)
        pygame.draw.rect(self.screen, COLORS["lineas"], right_goal, 2)

    # ------------------------------------------------------------
    #  Dibujo de jugadores
    # ------------------------------------------------------------
    def _dibujar_jugador(self, jugador, color_equipo, es_local):
        """Dibuja un jugador con su número, barra de fatiga y estado."""
        x, y = int(jugador.x), int(jugador.y)
        radio = jugador.radio

        # Círculo del jugador (con borde)
        # El color puede variar según el estado (lesionado, expulsado)
        if hasattr(jugador, 'expulsado') and jugador.expulsado:
            color = (100, 100, 100)  # gris
        elif hasattr(jugador, 'lesionado') and jugador.lesionado:
            color = (200, 200, 200)  # gris claro
        else:
            color = color_equipo

        pygame.draw.circle(self.screen, color, (x, y), radio)
        pygame.draw.circle(self.screen, COLORS["borde_jugador"], (x, y), radio, 2)

        # Número del jugador
        numero_texto = self.font_pequeño.render(str(jugador.numero), True, COLORS["texto"])
        rect_num = numero_texto.get_rect(center=(x, y))
        self.screen.blit(numero_texto, rect_num)

        # Si tiene el balón, dibujar anillo interior
        if jugador.tiene_balon:
            pygame.draw.circle(self.screen, COLORS["balon_indicador"],
                               (x, y), radio // 2, 3)

        # Indicador de tarjeta amarilla (pequeño rectángulo)
        if hasattr(jugador, 'tarjetas_amarillas') and jugador.tarjetas_amarillas > 0:
            rect_amar = pygame.Rect(x - 6, y - radio - 12, 12, 6)
            pygame.draw.rect(self.screen, (255, 255, 0), rect_amar)

        # Barra de fatiga (debajo del jugador)
        if hasattr(jugador, 'stats') and jugador.stats is not None:
            fatiga = jugador.stats.fatiga
            ancho_barra = radio * 2
            alto_barra = 4
            barra_x = x - radio
            barra_y = y + radio + 4
            # Fondo de la barra
            pygame.draw.rect(self.screen, (50, 50, 50),
                             (barra_x, barra_y, ancho_barra, alto_barra))
            # Relleno (verde si bajo, amarillo si medio, rojo si alto)
            if fatiga < 40:
                color_barra = (0, 255, 0)
            elif fatiga < 70:
                color_barra = (255, 255, 0)
            else:
                color_barra = (255, 0, 0)
            ancho_relleno = (ancho_barra * (100 - fatiga) / 100)
            pygame.draw.rect(self.screen, color_barra,
                             (barra_x, barra_y, ancho_relleno, alto_barra))

    # ------------------------------------------------------------
    #  Pelota
    # ------------------------------------------------------------
    def _dibujar_pelota(self, pelota):
        """Dibuja la pelota."""
        x, y = int(pelota.x), int(pelota.y)
        radio = pelota.radio
        pygame.draw.circle(self.screen, COLORS["pelota"], (x, y), radio)
        pygame.draw.circle(self.screen, COLORS["borde_pelota"], (x, y), radio, 2)

    # ------------------------------------------------------------
    #  Marcador y tiempo
    # ------------------------------------------------------------
    def _dibujar_marcador(self, goles_local, goles_rival, minuto, segundo, tiempo_total):
        """Dibuja el marcador con goles y tiempo."""
        # Marcador (goles)
        texto_goles = f"{goles_local} - {goles_rival}"
        superficie = self.font_grande.render(texto_goles, True, COLORS["texto"])
        rect = superficie.get_rect(center=(SCREEN_WIDTH // 2, 40))
        # Fondo semitransparente
        fondo_rect = rect.inflate(30, 15)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), fondo_rect)
        pygame.draw.rect(self.screen, COLORS["lineas"], fondo_rect, 2)
        self.screen.blit(superficie, rect)

        # Indicadores de equipo (colores)
        pygame.draw.circle(self.screen, (0, 0, 255), (SCREEN_WIDTH // 2 - 80, 40), 15)
        pygame.draw.circle(self.screen, (255, 0, 0), (SCREEN_WIDTH // 2 + 80, 40), 15)

        # Tiempo (minuto:segundo)
        minutos_restantes = max(0, int((tiempo_total - (minuto * 60 + segundo)) / 60))
        segundos_restantes = max(0, int((tiempo_total - (minuto * 60 + segundo)) % 60))
        texto_tiempo = f"{minutos_restantes:02d}:{segundos_restantes:02d}"
        superficie_tiempo = self.font_mediano.render(texto_tiempo, True, COLORS["texto"])
        rect_tiempo = superficie_tiempo.get_rect(center=(SCREEN_WIDTH // 2, 75))
        pygame.draw.rect(self.screen, (0, 0, 0, 180), rect_tiempo.inflate(20, 10))
        self.screen.blit(superficie_tiempo, rect_tiempo)

    def _dibujar_tacticas(self, equipo_local, equipo_rival):
        """Muestra las tácticas de cada equipo."""
        tact_local = getattr(equipo_local, 'tactica_actual', 'tiki_taka')
        tact_rival = getattr(equipo_rival, 'tactica_actual', 'catenaccio')

        texto_local = self.font_pequeño.render(f"Local: {tact_local}", True, (200, 200, 200))
        texto_rival = self.font_pequeño.render(f"Rival: {tact_rival}", True, (200, 200, 200))
        self.screen.blit(texto_local, (10, 10))
        self.screen.blit(texto_rival, (SCREEN_WIDTH - 150, 10))

    # ------------------------------------------------------------
    #  Barras de fatiga (para todos o solo para el humano)
    # ------------------------------------------------------------
    def _dibujar_fatigas(self, equipo_local, equipo_rival, jugador_humano):
        """Dibuja las barras de fatiga sobre los jugadores (opcional)."""
        # Solo dibujamos la del jugador humano y del poseedor para no saturar
        for jug in equipo_local.jugadores + equipo_rival.jugadores:
            if jug == jugador_humano or jug.tiene_balon:
                if hasattr(jug, 'stats') and jug.stats is not None:
                    fatiga = jug.stats.fatiga
                    x, y = int(jug.x), int(jug.y)
                    radio = jug.radio
                    ancho_barra = radio * 2
                    alto_barra = 4
                    barra_x = x - radio
                    barra_y = y - radio - 10
                    pygame.draw.rect(self.screen, (50, 50, 50),
                                     (barra_x, barra_y, ancho_barra, alto_barra))
                    if fatiga < 40:
                        color_barra = (0, 255, 0)
                    elif fatiga < 70:
                        color_barra = (255, 255, 0)
                    else:
                        color_barra = (255, 0, 0)
                    ancho_relleno = (ancho_barra * (100 - fatiga) / 100)
                    pygame.draw.rect(self.screen, color_barra,
                                     (barra_x, barra_y, ancho_relleno, alto_barra))

    # ------------------------------------------------------------
    #  Indicadores de tarjetas y lesiones
    # ------------------------------------------------------------
    def _dibujar_estado_jugadores(self, equipo_local, equipo_rival):
        """Muestra pequeños iconos de tarjeta/lesión sobre los jugadores."""
        for jug in equipo_local.jugadores + equipo_rival.jugadores:
            x, y = int(jug.x), int(jug.y)
            radio = jug.radio
            if hasattr(jug, 'expulsado') and jug.expulsado:
                # Cruz roja
                pygame.draw.line(self.screen, (255, 0, 0),
                                 (x - 8, y - 8), (x + 8, y + 8), 3)
                pygame.draw.line(self.screen, (255, 0, 0),
                                 (x + 8, y - 8), (x - 8, y + 8), 3)
            elif hasattr(jug, 'lesionado') and jug.lesionado:
                # Cruz amarilla
                pygame.draw.line(self.screen, (255, 255, 0),
                                 (x - 8, y - 8), (x + 8, y + 8), 3)
                pygame.draw.line(self.screen, (255, 255, 0),
                                 (x + 8, y - 8), (x - 8, y + 8), 3)
            elif hasattr(jug, 'tarjetas_amarillas') and jug.tarjetas_amarillas > 0:
                # Pequeño rectángulo amarillo encima
                pygame.draw.rect(self.screen, (255, 255, 0),
                                 (x - 6, y - radio - 12, 12, 6))

    # ------------------------------------------------------------
    #  Notificaciones y mensajes
    # ------------------------------------------------------------
    def _dibujar_notificaciones(self):
        """Dibuja notificaciones emergentes (ej. tarjeta, lesión)."""
        # Esta función podría ser llamada desde el exterior con eventos
        # Por ahora, lo dejamos vacío para que se implemente con una cola de eventos
        pass

    def _dibujar_mensaje_gol(self):
        """Dibuja un gran mensaje de '¡GOL!' en el centro."""
        texto = "¡GOL!"
        superficie = self.font_titulo.render(texto, True, COLORS["gol"])
        rect = superficie.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        fondo_rect = rect.inflate(60, 30)
        pygame.draw.rect(self.screen, (0, 0, 0, 200), fondo_rect)
        pygame.draw.rect(self.screen, COLORS["gol"], fondo_rect, 4)
        self.screen.blit(superficie, rect)

    def _dibujar_menu_pausa(self):
        """Dibuja un menú de pausa simple."""
        # Fondo semitransparente
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))
        self.screen.blit(s, (0, 0))

        # Texto
        texto = "PAUSA"
        superficie = self.font_titulo.render(texto, True, (255, 255, 255))
        rect = superficie.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(superficie, rect)

        texto2 = "Presiona 'P' para reanudar"
        superficie2 = self.font_mediano.render(texto2, True, (255, 255, 255))
        rect2 = superficie2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(superficie2, rect2)

    def _dibujar_fin_partido(self, goles_local, goles_rival):
        """Dibuja la pantalla de fin del partido."""
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))

        texto = "FIN DEL PARTIDO"
        superficie = self.font_titulo.render(texto, True, (255, 255, 255))
        rect = superficie.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        self.screen.blit(superficie, rect)

        texto_marcador = f"{goles_local} - {goles_rival}"
        superficie2 = self.font_grande.render(texto_marcador, True, (255, 255, 255))
        rect2 = superficie2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(superficie2, rect2)

        # Indicar ganador
        if goles_local > goles_rival:
            ganador = "¡Local campeón!"
        elif goles_rival > goles_local:
            ganador = "¡Rival campeón!"
        else:
            ganador = "Empate"
        texto3 = self.font_mediano.render(ganador, True, (255, 255, 0))
        rect3 = texto3.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        self.screen.blit(texto3, rect3)

    # ------------------------------------------------------------
    #  Métodos auxiliares para el HUD (estadísticas del jugador seleccionado)
    # ------------------------------------------------------------
    def _dibujar_stats_jugador(self, jugador, x, y):
        """Dibuja las estadísticas de un jugador en una esquina."""
        if not hasattr(jugador, 'stats') or jugador.stats is None:
            return
        stats = jugador.stats
        lineas = [
            f"Nombre: {stats.nombre}",
            f"Nivel: {stats.nivel}  XP: {stats.xp:.0f}/{stats.xp_para_subir:.0f}",
            f"Vel: {stats.velocidad:.0f}  Res: {stats.resistencia:.0f}",
            f"Pase: {stats.pase:.0f}  Reg: {stats.regate:.0f}",
            f"Robo: {stats.robo:.0f}  Tir: {stats.tiro:.0f}",
            f"Fatiga: {stats.fatiga:.1f}%"
        ]
        for i, texto in enumerate(lineas):
            superficie = self.font_pequeño.render(texto, True, (255, 255, 255))
            self.screen.blit(superficie, (x, y + i * 20))

    # ------------------------------------------------------------
    #  Notificación de eventos (gol, tarjeta, lesión) desde game.py
    # ------------------------------------------------------------
    def mostrar_notificacion(self, texto, color=(255, 255, 255), duracion=2.0):
        """Muestra una notificación emergente."""
        self.notificacion = (texto, color, duracion)
        self.tiempo_notificacion = 0.0

    def actualizar_notificaciones(self, dt):
        """Actualiza el temporizador de notificaciones."""
        if self.notificacion:
            self.tiempo_notificacion += dt
            if self.tiempo_notificacion >= self.notificacion[2]:
                self.notificacion = None

    def _dibujar_notificaciones(self):
        """Dibuja la notificación actual, si existe."""
        if self.notificacion:
            texto, color, _ = self.notificacion
            superficie = self.font_mediano.render(texto, True, color)
            rect = superficie.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
            # Fondo semitransparente
            fondo_rect = rect.inflate(40, 20)
            pygame.draw.rect(self.screen, (0, 0, 0, 200), fondo_rect)
            pygame.draw.rect(self.screen, color, fondo_rect, 2)
            self.screen.blit(superficie, rect)

    # ------------------------------------------------------------
    #  Fin del módulo
    # ------------------------------------------------------------
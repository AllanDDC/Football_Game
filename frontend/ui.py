# frontend/ui.py
"""
Módulo de interfaz de usuario (UI) para el juego.
Proporciona elementos interactivos como menús, paneles de estadísticas,
selección de jugadores, sustituciones y notificaciones.
Se superpone al renderizado principal.
"""

import pygame
import math
from backend.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLORS
from backend.tactics import TACTICAS, aplicar_tactica_a_equipo


class UI:
    """
    Gestiona todos los elementos de la interfaz de usuario:
    - Menú de pausa con opciones (reanudar, cambiar táctica, sustituciones, salir).
    - Panel de estadísticas del jugador seleccionado (clic en jugador).
    - Panel de sustituciones (arrastrar y soltar jugadores).
    - Notificaciones emergentes.
    - Indicadores de eventos (tarjetas, lesiones, goles).
    """

    def __init__(self, screen, partido):
        self.screen = screen
        self.partido = partido
        self.font_pequeño = pygame.font.Font(None, 22)
        self.font_mediano = pygame.font.Font(None, 30)
        self.font_grande = pygame.font.Font(None, 48)

        # Estado de la UI
        self.modo = "juego"  # 'juego', 'pausa', 'stats', 'sustituciones', 'tacticas'
        self.jugador_seleccionado = None
        self.jugador_stats_visible = False

        # Botones y áreas interactivas
        self.botones = {}
        self._crear_botones()

        # Notificaciones
        self.notificacion = None
        self.tiempo_notificacion = 0.0

        # Sustituciones (arrastrar)
        self.arrastrando = False
        self.jugador_origen = None
        self.jugador_destino = None

        # Para selección con ratón
        self.raton_x = 0
        self.raton_y = 0

    def _crear_botones(self):
        """Crea los botones del menú de pausa."""
        # Botón Reanudar
        self.botones["reanudar"] = pygame.Rect(
            SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 100, 200, 50
        )
        # Botón Tácticas
        self.botones["tacticas"] = pygame.Rect(
            SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 30, 200, 50
        )
        # Botón Sustituciones
        self.botones["sustituciones"] = pygame.Rect(
            SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 40, 200, 50
        )
        # Botón Salir
        self.botones["salir"] = pygame.Rect(
            SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 110, 200, 50
        )

    def manejar_eventos(self, event):
        """
        Maneja eventos de ratón y teclado específicos de la UI.
        Retorna True si el evento fue consumido por la UI.
        """
        consumido = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            self.raton_x, self.raton_y = event.pos
            if self.modo == "juego":
                # Seleccionar jugador con clic izquierdo
                if event.button == 1:
                    self._seleccionar_jugador(self.raton_x, self.raton_y)
                    consumido = True
            elif self.modo == "pausa":
                if event.button == 1:
                    self._procesar_clic_pausa(self.raton_x, self.raton_y)
                    consumido = True
            elif self.modo == "sustituciones":
                if event.button == 1:
                    self._iniciar_arrastre(self.raton_x, self.raton_y)
                    consumido = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.modo == "sustituciones" and self.arrastrando:
                self._finalizar_arrastre(self.raton_x, self.raton_y)
                consumido = True

        elif event.type == pygame.MOUSEMOTION:
            self.raton_x, self.raton_y = event.pos
            if self.arrastrando:
                # Actualizar posición del jugador arrastrado (solo visual)
                pass

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Cerrar paneles abiertos
                if self.modo == "stats":
                    self.cerrar_stats()
                    consumido = True
                elif self.modo == "sustituciones":
                    self.modo = "pausa"
                    consumido = True
                elif self.modo == "tacticas":
                    self.modo = "pausa"
                    consumido = True

        return consumido

    def _seleccionar_jugador(self, x, y):
        """Selecciona un jugador si el clic está sobre él."""
        # Buscar entre todos los jugadores (local y rival)
        todos = self.partido.equipo_local.jugadores + self.partido.equipo_rival.jugadores
        for jug in todos:
            dx = x - jug.x
            dy = y - jug.y
            if math.hypot(dx, dy) <= jug.radio + 5:
                self.jugador_seleccionado = jug
                self.jugador_stats_visible = True
                self.modo = "stats"
                return

    def _procesar_clic_pausa(self, x, y):
        """Procesa clics en el menú de pausa."""
        if self.botones["reanudar"].collidepoint(x, y):
            self.partido.reanudar_partido()
            self.modo = "juego"
        elif self.botones["tacticas"].collidepoint(x, y):
            self.modo = "tacticas"
        elif self.botones["sustituciones"].collidepoint(x, y):
            self.modo = "sustituciones"
            self._cargar_sustitutos()
        elif self.botones["salir"].collidepoint(x, y):
            pygame.quit()
            import sys
            sys.exit()

    def _cargar_sustitutos(self):
        """Carga la lista de sustitutos (simulado)."""
        # En una implementación real, se mostrarían los jugadores disponibles
        # y los titulares. Por ahora, solo cambiamos el modo.
        pass

    def _iniciar_arrastre(self, x, y):
        """Inicia el arrastre de un jugador para sustitución."""
        # Buscar jugador en el equipo local (solo se pueden sustituir locales)
        for jug in self.partido.equipo_local.jugadores:
            dx = x - jug.x
            dy = y - jug.y
            if math.hypot(dx, dy) <= jug.radio + 10:
                self.arrastrando = True
                self.jugador_origen = jug
                return

    def _finalizar_arrastre(self, x, y):
        """Finaliza el arrastre y realiza la sustitución si procede."""
        if self.jugador_origen is None:
            return
        # Buscar otro jugador del mismo equipo para intercambiar
        for jug in self.partido.equipo_local.jugadores:
            if jug == self.jugador_origen:
                continue
            dx = x - jug.x
            dy = y - jug.y
            if math.hypot(dx, dy) <= jug.radio + 10:
                # Realizar sustitución
                self.partido.realizar_sustitucion(
                    self.partido.equipo_local,
                    jug,  # entra
                    self.jugador_origen  # sale
                )
                self.mostrar_notificacion(f"Sustitución: {jug.numero} por {self.jugador_origen.numero}")
                break
        self.arrastrando = False
        self.jugador_origen = None

    def cerrar_stats(self):
        """Cierra el panel de estadísticas."""
        self.jugador_stats_visible = False
        self.jugador_seleccionado = None
        self.modo = "juego"

    def mostrar_notificacion(self, texto, color=(255, 255, 255), duracion=2.0):
        """Muestra una notificación emergente."""
        self.notificacion = (texto, color, duracion)
        self.tiempo_notificacion = 0.0

    def update(self, dt):
        """Actualiza temporizadores de la UI."""
        if self.notificacion:
            self.tiempo_notificacion += dt
            if self.tiempo_notificacion >= self.notificacion[2]:
                self.notificacion = None

    def dibujar(self, estado):
        """
        Dibuja todos los elementos de la UI sobre el renderizado principal.
        """
        # 1. Notificaciones (siempre visibles)
        self._dibujar_notificacion()

        # 2. Panel de estadísticas (si está visible)
        if self.jugador_stats_visible and self.jugador_seleccionado:
            self._dibujar_panel_stats(self.jugador_seleccionado)

        # 3. Menú de pausa (si corresponde)
        if self.modo == "pausa":
            self._dibujar_menu_pausa()

        # 4. Panel de tácticas
        if self.modo == "tacticas":
            self._dibujar_panel_tacticas()

        # 5. Panel de sustituciones
        if self.modo == "sustituciones":
            self._dibujar_panel_sustituciones()

        # 6. Si se está arrastrando un jugador, dibujar sombra
        if self.arrastrando and self.jugador_origen:
            self._dibujar_sombra_arrastre()

    def _dibujar_notificacion(self):
        """Dibuja la notificación emergente."""
        if self.notificacion:
            texto, color, _ = self.notificacion
            superficie = self.font_mediano.render(texto, True, color)
            rect = superficie.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
            fondo_rect = rect.inflate(40, 20)
            pygame.draw.rect(self.screen, (0, 0, 0, 200), fondo_rect)
            pygame.draw.rect(self.screen, color, fondo_rect, 2)
            self.screen.blit(superficie, rect)

    def _dibujar_panel_stats(self, jugador):
        """Dibuja un panel con las estadísticas del jugador seleccionado."""
        if not hasattr(jugador, 'stats') or jugador.stats is None:
            return
        stats = jugador.stats

        # Fondo semitransparente
        panel = pygame.Rect(20, 20, 260, 200)
        s = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        self.screen.blit(s, panel)
        pygame.draw.rect(self.screen, (255, 255, 255), panel, 2)

        # Título
        titulo = f"Jugador {jugador.numero} - {stats.nombre}"
        sup = self.font_mediano.render(titulo, True, (255, 255, 255))
        self.screen.blit(sup, (panel.x + 10, panel.y + 10))

        # Estadísticas
        lineas = [
            f"Nivel: {stats.nivel}  XP: {stats.xp:.0f}/{stats.xp_para_subir:.0f}",
            f"Velocidad: {stats.velocidad:.0f}  Resistencia: {stats.resistencia:.0f}",
            f"Pase: {stats.pase:.0f}  Regate: {stats.regate:.0f}",
            f"Robo: {stats.robo:.0f}  Tiro: {stats.tiro:.0f}",
            f"Fatiga: {stats.fatiga:.1f}%"
        ]
        y = panel.y + 40
        for linea in lineas:
            sup = self.font_pequeño.render(linea, True, (200, 200, 200))
            self.screen.blit(sup, (panel.x + 10, y))
            y += 22

        # Botón cerrar (X)
        cerrar_rect = pygame.Rect(panel.x + panel.width - 30, panel.y + 5, 25, 25)
        pygame.draw.rect(self.screen, (255, 0, 0), cerrar_rect)
        sup = self.font_pequeño.render("X", True, (255, 255, 255))
        self.screen.blit(sup, cerrar_rect)

    def _dibujar_menu_pausa(self):
        """Dibuja el menú de pausa completo."""
        # Fondo semitransparente
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))

        # Título
        titulo = self.font_grande.render("PAUSA", True, (255, 255, 255))
        rect = titulo.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150))
        self.screen.blit(titulo, rect)

        # Botones
        for nombre, rect in self.botones.items():
            # Color según estado
            if rect.collidepoint(pygame.mouse.get_pos()):
                color_fondo = (80, 80, 80)
            else:
                color_fondo = (50, 50, 50)
            pygame.draw.rect(self.screen, color_fondo, rect)
            pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
            # Texto
            texto = nombre.capitalize()
            sup = self.font_mediano.render(texto, True, (255, 255, 255))
            rect_texto = sup.get_rect(center=rect.center)
            self.screen.blit(sup, rect_texto)

    def _dibujar_panel_tacticas(self):
        """Dibuja un panel para seleccionar tácticas."""
        # Fondo
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 200, 400, 400)
        s = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220))
        self.screen.blit(s, panel)
        pygame.draw.rect(self.screen, (255, 255, 255), panel, 2)

        # Título
        titulo = self.font_mediano.render("Seleccionar Táctica", True, (255, 255, 255))
        self.screen.blit(titulo, (panel.x + 10, panel.y + 10))

        # Lista de tácticas
        y = panel.y + 50
        tacticas = list(TACTICAS.keys())
        for i, nombre in enumerate(tacticas):
            rect = pygame.Rect(panel.x + 20, y + i * 40, panel.width - 40, 35)
            # Resaltar si el mouse está encima
            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(self.screen, (80, 80, 80), rect)
            else:
                pygame.draw.rect(self.screen, (50, 50, 50), rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 1)
            sup = self.font_pequeño.render(nombre, True, (255, 255, 255))
            self.screen.blit(sup, (rect.x + 10, rect.y + 8))

        # Botón volver
        volver_rect = pygame.Rect(panel.x + 20, panel.y + panel.height - 50, 100, 35)
        pygame.draw.rect(self.screen, (100, 100, 100), volver_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), volver_rect, 1)
        sup = self.font_pequeño.render("Volver", True, (255, 255, 255))
        self.screen.blit(sup, (volver_rect.x + 20, volver_rect.y + 8))

        # Detectar clics en el panel (se maneja en eventos)
        # Aquí solo dibujamos

    def _dibujar_panel_sustituciones(self):
        """Dibuja un panel para gestionar sustituciones."""
        # Fondo
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 200, 500, 400)
        s = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220))
        self.screen.blit(s, panel)
        pygame.draw.rect(self.screen, (255, 255, 255), panel, 2)

        # Título
        titulo = self.font_mediano.render("Sustituciones (arrastra y suelta)", True, (255, 255, 255))
        self.screen.blit(titulo, (panel.x + 10, panel.y + 10))

        # Lista de jugadores del equipo local (titulares)
        y = panel.y + 50
        for jug in self.partido.equipo_local.jugadores:
            rect = pygame.Rect(panel.x + 20, y, panel.width - 40, 30)
            # Color según si está lesionado/expulsado
            if hasattr(jug, 'lesionado') and jug.lesionado:
                color = (100, 100, 100)
            elif hasattr(jug, 'expulsado') and jug.expulsado:
                color = (150, 50, 50)
            else:
                color = (50, 80, 150)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 1)
            texto = f"{jug.numero} - {jug.stats.nombre if hasattr(jug,'stats') else 'Jugador'}"
            if jug.tiene_balon:
                texto += " (balón)"
            sup = self.font_pequeño.render(texto, True, (255, 255, 255))
            self.screen.blit(sup, (rect.x + 10, rect.y + 8))
            y += 35

        # Botón volver
        volver_rect = pygame.Rect(panel.x + 20, panel.y + panel.height - 50, 100, 35)
        pygame.draw.rect(self.screen, (100, 100, 100), volver_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), volver_rect, 1)
        sup = self.font_pequeño.render("Volver", True, (255, 255, 255))
        self.screen.blit(sup, (volver_rect.x + 20, volver_rect.y + 8))

    def _dibujar_sombra_arrastre(self):
        """Dibuja una sombra del jugador que se está arrastrando."""
        if self.jugador_origen:
            x, y = self.raton_x, self.raton_y
            pygame.draw.circle(self.screen, (200, 200, 200, 100),
                               (x, y), self.jugador_origen.radio, 2)
            # Número
            sup = self.font_pequeño.render(str(self.jugador_origen.numero), True, (200, 200, 200))
            rect = sup.get_rect(center=(x, y))
            self.screen.blit(sup, rect)

    # ------------------------------------------------------------
    #  Método auxiliar para verificar si la UI está activa
    # ------------------------------------------------------------
    def esta_activa(self):
        """Devuelve True si la UI está en un modo que bloquea el juego."""
        return self.modo in ("pausa", "stats", "sustituciones", "tacticas")

# ------------------------------------------------------------
#  Fin del módulo
# ------------------------------------------------------------
# frontend/input_handler.py
"""
Módulo de manejo de entrada del usuario.
Convierte eventos de teclado en acciones sobre el Partido.
Soporta:
- Movimiento: WASD / Flechas
- Sprint: Shift (aumenta velocidad y consume más stamina)
- Pase corto: Espacio (hacia la dirección de movimiento, solo si hay compañero)
- Pase largo: Shift + Espacio (solo si hay compañero)
- Devolución rápida: Ctrl + Z (o solo Z) al último pasador
- Cambio de jugador al balón: Q (cambia al jugador con balón o al más cercano)
- Pausa: P
- Cambio de táctica: 1-6 (para el equipo controlado)
- Cambio de jugador secuencial: Tab (alternativa)
- Pantalla completa: F11
- Salir: ESC
"""

import pygame
import sys
import math
from backend.tactics import TACTICAS, aplicar_tactica_a_equipo
from backend.ball_control import ejecutar_pase_por_direccion


class InputHandler:
    """
    Gestiona la entrada del usuario: teclado y ratón (opcional).
    Mantiene el estado de las teclas y traduce las pulsaciones en llamadas al Partido.
    """

    def __init__(self, partido):
        """
        Inicializa el manejador de entrada.

        :param partido: instancia de Partido (backend.game)
        """
        self.partido = partido

        # Estado de teclas de movimiento (presionadas o no)
        self.teclas_movimiento = {
            pygame.K_UP: False,
            pygame.K_DOWN: False,
            pygame.K_LEFT: False,
            pygame.K_RIGHT: False,
            pygame.K_w: False,
            pygame.K_a: False,
            pygame.K_s: False,
            pygame.K_d: False,
        }

        # Estado de teclas de acción (momentáneas)
        self.espacio_presionado = False
        self.shift_presionado = False
        self.ctrl_z_presionado = False
        self.pausa_activada = False

        # Flags de lanzamiento (se activan en KEYDOWN y se resetean tras procesar)
        self.lanzar_corto = False
        self.lanzar_largo = False

        # Para evitar múltiples pausas por pulsación
        self.pausa_activada = False

        # Para cambio de táctica (teclas numéricas)
        self.tactica_seleccionada = None  # nombre de la táctica

        # Para selección de jugador (Tab)
        self.cambiar_jugador_secuencial = False

        # Para cambio de jugador al balón (Q)
        self.cambiar_jugador_al_balon = False

        # Para Ctrl+Z (devolución rápida)
        self.ctrl_z_presionado = False
        self.ctrl_z_procesado = False  # evita múltiples activaciones por frame

    def handle_events(self):
        """
        Procesa todos los eventos de Pygame y actualiza el estado del partido.
        Debe llamarse en cada frame.
        """
        # Resetear flags de acción (se activan solo en KEYDOWN)
        self.lanzar_corto = False
        self.lanzar_largo = False
        self.tactica_seleccionada = None
        self.cambiar_jugador_secuencial = False
        self.cambiar_jugador_al_balon = False
        self.ctrl_z_procesado = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                # --- Salir del juego ---
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                # --- Pantalla completa (F11) ---
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()

                # --- Movimiento: marcar tecla como presionada ---
                if event.key in self.teclas_movimiento:
                    self.teclas_movimiento[event.key] = True

                # --- Pase corto (Espacio) ---
                if event.key == pygame.K_SPACE:
                    self.espacio_presionado = True
                    # Si Shift también está presionado, es pase largo
                    if self.shift_presionado:
                        self.lanzar_largo = True
                    else:
                        self.lanzar_corto = True

                # --- Sprint (Shift) ---
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.shift_presionado = True

                # --- Devolución rápida (Ctrl + Z o solo Z) ---
                if event.key == pygame.K_z:
                    # Se activa con Ctrl+Z o con Z sola (para facilitar)
                    self.ctrl_z_presionado = True

                # --- Pausa (P) ---
                if event.key == pygame.K_p:
                    self.pausa_activada = True

                # --- Cambio de táctica (1-6) ---
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3,
                                 pygame.K_4, pygame.K_5, pygame.K_6):
                    tacticas = list(TACTICAS.keys())
                    idx = event.key - pygame.K_1
                    if idx < len(tacticas):
                        self.tactica_seleccionada = tacticas[idx]

                # --- Cambio de jugador secuencial (Tab) ---
                if event.key == pygame.K_TAB:
                    self.cambiar_jugador_secuencial = True

                # --- Cambio de jugador al balón (Q) ---
                if event.key == pygame.K_q:
                    self.cambiar_jugador_al_balon = True

            elif event.type == pygame.KEYUP:
                # --- Movimiento: marcar tecla como liberada ---
                if event.key in self.teclas_movimiento:
                    self.teclas_movimiento[event.key] = False

                # --- Espacio liberado ---
                if event.key == pygame.K_SPACE:
                    self.espacio_presionado = False

                # --- Sprint liberado ---
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.shift_presionado = False

                # --- Ctrl+Z liberado ---
                if event.key == pygame.K_z:
                    self.ctrl_z_presionado = False

        # ------------------------------------------------------------
        #  Procesar acciones después de recorrer todos los eventos
        # ------------------------------------------------------------

        # 1. Calcular dirección de movimiento (para pases y movimiento)
        dx = 0
        dy = 0
        if self.teclas_movimiento[pygame.K_LEFT] or self.teclas_movimiento[pygame.K_a]:
            dx -= 1
        if self.teclas_movimiento[pygame.K_RIGHT] or self.teclas_movimiento[pygame.K_d]:
            dx += 1
        if self.teclas_movimiento[pygame.K_UP] or self.teclas_movimiento[pygame.K_w]:
            dy -= 1
        if self.teclas_movimiento[pygame.K_DOWN] or self.teclas_movimiento[pygame.K_s]:
            dy += 1

        # Normalizar para velocidad constante en diagonales
        if dx != 0 and dy != 0:
            norm = math.hypot(dx, dy)
            dx /= norm
            dy /= norm

        # Aplicar movimiento al jugador humano (pasando el estado de sprint)
        self.partido.mover_jugador(dx, dy, sprint=self.shift_presionado)

        # 2. Manejar pases (Espacio y Shift+Espacio) con dirección
        if self.lanzar_corto or self.lanzar_largo:
            jugador = self.partido.jugador_humano
            if jugador is not None and jugador.tiene_balon:
                # Si no hay dirección de movimiento, usar dirección por defecto (hacia arriba)
                if dx == 0 and dy == 0:
                    dx, dy = 0, -1
                # Ejecutar pase en la dirección actual (solo si hay compañero)
                equipos = [self.partido.equipo_local, self.partido.equipo_rival]
                exito = ejecutar_pase_por_direccion(
                    jugador, dx, dy, self.partido.pelota, equipos,
                    es_largo=self.lanzar_largo,
                    solo_companeros=True  # Evita pases al espacio
                )
                # Si el pase es exitoso, se actualiza el historial en game.py
                if exito:
                    # El receptor se guarda en el partido (se actualiza en ejecutar_pase)
                    pass
            # Resetear flags
            self.lanzar_corto = False
            self.lanzar_largo = False

        # 3. Manejar Ctrl+Z (devolución rápida)
        if self.ctrl_z_presionado and not self.ctrl_z_procesado:
            if hasattr(self.partido, 'pase_rapido_ctrl_z'):
                self.partido.pase_rapido_ctrl_z()
            self.ctrl_z_procesado = True

        # 4. Manejar pausa
        if self.pausa_activada:
            if self.partido.estado == "jugando":
                self.partido.pausar_partido()
            elif self.partido.estado == "pausa":
                self.partido.reanudar_partido()
            self.pausa_activada = False

        # 5. Manejar cambio de táctica
        if self.tactica_seleccionada is not None:
            equipo = self.partido.equipo_local  # controlado por el humano
            aplicar_tactica_a_equipo(equipo, self.tactica_seleccionada, self.partido.pelota, 0)
            # Registrar evento (opcional)
            if hasattr(self.partido, 'eventos'):
                from backend.match_events import EventoPartido
                self.partido.eventos.registrar_evento(
                    EventoPartido("TACTICA_CAMBIADA", None, None, f"Táctica: {self.tactica_seleccionada}")
                )
            self.tactica_seleccionada = None

        # 6. Manejar cambio de jugador secuencial (Tab)
        if self.cambiar_jugador_secuencial:
            self._cambiar_jugador_secuencial()
            self.cambiar_jugador_secuencial = False

        # 7. Manejar cambio de jugador al balón (Q)
        if self.cambiar_jugador_al_balon:
            self._cambiar_jugador_al_balon()
            self.cambiar_jugador_al_balon = False

    def _cambiar_jugador_secuencial(self):
        """
        Cambia el jugador controlado al siguiente jugador de campo del equipo local.
        (Útil para alternar entre jugadores durante el partido)
        """
        equipo = self.partido.equipo_local  # asumimos que el humano controla al local
        jugadores = equipo.jugadores
        if not jugadores:
            return

        # Buscar el índice del jugador humano actual
        idx_actual = -1
        for i, jug in enumerate(jugadores):
            if jug.es_controlado:
                idx_actual = i
                break

        if idx_actual == -1:
            idx_actual = 0

        # Buscar el siguiente jugador de campo (no portero) que no esté lesionado/expulsado
        for i in range(1, len(jugadores)):
            idx = (idx_actual + i) % len(jugadores)
            jug = jugadores[idx]
            if jug.numero != 0 and not hasattr(jug, 'lesionado') and not hasattr(jug, 'expulsado'):
                # Desactivar el control del actual
                jugadores[idx_actual].es_controlado = False
                # Activar el nuevo
                jug.es_controlado = True
                self.partido.jugador_humano = jug
                # Si el nuevo tiene el balón, actualizar referencia
                if jug.tiene_balon:
                    self.partido.jugador_con_balon = jug
                break

    def _cambiar_jugador_al_balon(self):
        """
        Cambia el control al jugador del equipo local que tiene el balón.
        Si nadie tiene el balón, cambia al más cercano al balón.
        """
        if hasattr(self.partido, 'cambiar_jugador_controlado_al_balon'):
            self.partido.cambiar_jugador_controlado_al_balon()

    def reset(self):
        """Reinicia el estado de todas las teclas (útil al perder el foco)."""
        for key in self.teclas_movimiento:
            self.teclas_movimiento[key] = False
        self.espacio_presionado = False
        self.shift_presionado = False
        self.ctrl_z_presionado = False
        self.lanzar_corto = False
        self.lanzar_largo = False
        self.pausa_activada = False
        self.tactica_seleccionada = None
        self.cambiar_jugador_secuencial = False
        self.cambiar_jugador_al_balon = False
        self.ctrl_z_procesado = False

    def obtener_estado_teclas(self):
        """Devuelve un diccionario con el estado actual de todas las teclas relevantes."""
        return {
            "movimiento": {k: v for k, v in self.teclas_movimiento.items() if v},
            "espacio": self.espacio_presionado,
            "shift": self.shift_presionado,
            "ctrl_z": self.ctrl_z_presionado,
            "pausa": self.pausa_activada,
            "tactica": self.tactica_seleccionada,
        }
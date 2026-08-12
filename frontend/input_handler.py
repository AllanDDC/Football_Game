# frontend/input_handler.py
"""
Módulo de manejo de entrada del usuario.
Soporta:
- Movimiento: WASD / Flechas
- Sprint: Shift
- Pase direccional: Espacio + dirección
- Pase por proximidad: Espacio sin dirección (al compañero más cercano con línea de pase)
- Pase largo: Shift + Espacio + dirección
- Devolución: Z (pase de vuelta al último pasador)
- Pausa: P
- Cambio de táctica: 1-6
- Cambio de jugador: Tab
- Pantalla completa: F11
- Salir: ESC
"""

import pygame
import sys
import math
from backend.tactics import TACTICAS, aplicar_tactica_a_equipo
from backend.ball_control import ejecutar_pase_por_direccion, encontrar_companero_mas_cercano, ejecutar_pase, hay_linea_pase


class InputHandler:
    def __init__(self, partido):
        self.partido = partido

        # Teclas de movimiento
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

        # Teclas de acción
        self.espacio_presionado = False
        self.shift_presionado = False
        self.z_presionado = False
        self.ctrl_z_presionado = False
        self.pausa_activada = False

        # Flags de lanzamiento
        self.lanzar_corto = False
        self.lanzar_largo = False

        # Otros
        self.tactica_seleccionada = None
        self.cambiar_jugador_secuencial = False
        self.cambiar_jugador_al_balon = False
        self.ctrl_z_procesado = False

    def handle_events(self):
        # Resetear flags
        self.lanzar_corto = False
        self.lanzar_largo = False
        self.tactica_seleccionada = None
        self.cambiar_jugador_secuencial = False
        self.cambiar_jugador_al_balon = False
        self.ctrl_z_procesado = False

        # Variable para saber si se ejecutó un pase direccional
        pase_direccional_ejecutado = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()

                if event.key in self.teclas_movimiento:
                    self.teclas_movimiento[event.key] = True

                if event.key == pygame.K_SPACE:
                    self.espacio_presionado = True
                    if self.shift_presionado:
                        self.lanzar_largo = True
                    else:
                        self.lanzar_corto = True

                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.shift_presionado = True

                # Z sin Ctrl → devolución
                if event.key == pygame.K_z:
                    if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        self.z_presionado = True
                    else:
                        self.ctrl_z_presionado = True

                if event.key == pygame.K_p:
                    self.pausa_activada = True

                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3,
                                 pygame.K_4, pygame.K_5, pygame.K_6):
                    tacticas = list(TACTICAS.keys())
                    idx = event.key - pygame.K_1
                    if idx < len(tacticas):
                        self.tactica_seleccionada = tacticas[idx]

                if event.key == pygame.K_TAB:
                    self.cambiar_jugador_secuencial = True

                if event.key == pygame.K_q:
                    self.cambiar_jugador_al_balon = True

            elif event.type == pygame.KEYUP:
                if event.key in self.teclas_movimiento:
                    self.teclas_movimiento[event.key] = False

                if event.key == pygame.K_SPACE:
                    self.espacio_presionado = False

                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.shift_presionado = False

                if event.key == pygame.K_z:
                    self.z_presionado = False
                    if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        pass
                    else:
                        self.ctrl_z_presionado = False

        # ------------------------------------------------------------
        #  Procesar acciones
        # ------------------------------------------------------------

        # 1. Movimiento
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

        if dx != 0 and dy != 0:
            norm = math.hypot(dx, dy)
            dx /= norm
            dy /= norm

        self.partido.mover_jugador(dx, dy, sprint=self.shift_presionado)

        # 2. Pase direccional (Espacio + dirección)
        if self.lanzar_corto or self.lanzar_largo:
            jugador = self.partido.jugador_humano
            if jugador is not None and jugador.tiene_balon:
                # Si hay dirección de movimiento, pase direccional
                if dx != 0 or dy != 0:
                    equipos = [self.partido.equipo_local, self.partido.equipo_rival]
                    exito = ejecutar_pase_por_direccion(
                        jugador, dx, dy, self.partido.pelota, equipos,
                        es_largo=self.lanzar_largo,
                        solo_companeros=True
                    )
                    if exito:
                        pase_direccional_ejecutado = True
            self.lanzar_corto = False
            self.lanzar_largo = False

        # 3. Pase por proximidad (Espacio sin dirección)
        # Se ejecuta si la tecla Espacio está presionada y NO se ha ejecutado un pase direccional en este frame
        if self.espacio_presionado and not pase_direccional_ejecutado:
            jugador = self.partido.jugador_humano
            if jugador is not None and jugador.tiene_balon:
                equipo_local = self.partido.equipo_local
                equipo_rival = self.partido.equipo_rival
                companeros = [j for j in equipo_local.jugadores if j != jugador and not j.tiene_balon]
                companero = encontrar_companero_mas_cercano(jugador, companeros, equipo_rival)
                if companero is not None:
                    exito = ejecutar_pase(jugador, companero, self.partido.pelota, es_largo=False)
                    if exito:
                        self.partido.ultimo_pasador = jugador
                        self.partido.ultimo_receptor = companero

        # 4. Devolución con Z (sin Ctrl)
        if self.z_presionado and not self.ctrl_z_presionado:
            if hasattr(self.partido, 'devolver_pase'):
                self.partido.devolver_pase()
            self.z_presionado = False  # para que no se repita hasta soltar y volver a presionar

        # 5. Ctrl+Z (por si acaso, aunque no se usa)
        if self.ctrl_z_presionado and not self.ctrl_z_procesado:
            if hasattr(self.partido, 'pase_rapido_ctrl_z'):
                self.partido.pase_rapido_ctrl_z()
            self.ctrl_z_procesado = True

        # 6. Pausa
        if self.pausa_activada:
            if self.partido.estado == "jugando":
                self.partido.pausar_partido()
            elif self.partido.estado == "pausa":
                self.partido.reanudar_partido()
            self.pausa_activada = False

        # 7. Táctica
        if self.tactica_seleccionada is not None:
            equipo = self.partido.equipo_local
            aplicar_tactica_a_equipo(equipo, self.tactica_seleccionada, self.partido.pelota, 0)
            if hasattr(self.partido, 'eventos'):
                from backend.match_events import EventoPartido
                self.partido.eventos.registrar_evento(
                    EventoPartido("TACTICA_CAMBIADA", None, None, f"Táctica: {self.tactica_seleccionada}")
                )
            self.tactica_seleccionada = None

        # 8. Cambio de jugador
        if self.cambiar_jugador_secuencial:
            self._cambiar_jugador_secuencial()
            self.cambiar_jugador_secuencial = False

        if self.cambiar_jugador_al_balon:
            if hasattr(self.partido, 'cambiar_jugador_controlado_al_balon'):
                self.partido.cambiar_jugador_controlado_al_balon()
            self.cambiar_jugador_al_balon = False

    def _cambiar_jugador_secuencial(self):
        equipo = self.partido.equipo_local
        jugadores = equipo.jugadores
        if not jugadores:
            return
        idx_actual = -1
        for i, jug in enumerate(jugadores):
            if jug.es_controlado:
                idx_actual = i
                break
        if idx_actual == -1:
            idx_actual = 0
        for i in range(1, len(jugadores)):
            idx = (idx_actual + i) % len(jugadores)
            jug = jugadores[idx]
            if jug.numero != 0 and not hasattr(jug, 'lesionado') and not hasattr(jug, 'expulsado'):
                jugadores[idx_actual].es_controlado = False
                jug.es_controlado = True
                self.partido.jugador_humano = jug
                if jug.tiene_balon:
                    self.partido.jugador_con_balon = jug
                break

    def reset(self):
        for key in self.teclas_movimiento:
            self.teclas_movimiento[key] = False
        self.espacio_presionado = False
        self.shift_presionado = False
        self.z_presionado = False
        self.ctrl_z_presionado = False
        self.lanzar_corto = False
        self.lanzar_largo = False
        self.pausa_activada = False
        self.tactica_seleccionada = None
        self.cambiar_jugador_secuencial = False
        self.cambiar_jugador_al_balon = False
        self.ctrl_z_procesado = False

    def obtener_estado_teclas(self):
        return {
            "movimiento": {k: v for k, v in self.teclas_movimiento.items() if v},
            "espacio": self.espacio_presionado,
            "shift": self.shift_presionado,
            "z": self.z_presionado,
            "ctrl_z": self.ctrl_z_presionado,
            "pausa": self.pausa_activada,
            "tactica": self.tactica_seleccionada,
        }
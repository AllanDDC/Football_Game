# backend/game.py
"""
Módulo principal del juego. Orquesta todos los subsistemas:
- Creación de equipos y jugadores con estadísticas.
- Bucle de actualización (física, IA, eventos).
- Gestión de marcador, tiempo, tarjetas, lesiones.
- Control de estados (jugando, pausa, fin_partido).
- Sprint con Shift (velocidad y consumo de stamina aumentados).
- Velocidad reducida gradualmente por fatiga.
- Pase rápido con Ctrl+Z (devolver al último pasador).
- Cambio de jugador controlado al balón (Q).
- Interfaz para el frontend (renderizado e input).
- Reinicio inmediato tras gol (sin pausa).
"""

import math
import random
from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_RADIUS, BALL_RADIUS,
    PLAYER_SPEED,
    SPRINT_MULTIPLIER,   # <--- importación añadida
    GOAL_HEIGHT, GOAL_DEPTH,
    COLORS
)
from .entities import Jugador, Pelota, Equipo
from .player_stats import PlayerStats
from .physics import (
    distancia_objetos,
    circulos_colisionan,
    resolver_colision_entre_jugadores,
    intentar_recoger_balon,
    aplicar_limites_campo,
    conducir_balon
)
from .ai import actualizar_ia, resolver_contacto_jugadores, calcular_precision_pase
from .tactics import aplicar_tactica_a_equipo, actualizar_tactica_segun_marcador, TACTICAS
from .dribbling import (
    ejecutar_regate,
    calcular_probabilidad_regate,
    obtener_radio_pase_largo,
    esta_dentro_radio_opaco
)
from .ball_control import (
    ejecutar_pase,
    intentar_recibir,
    ejecutar_tiro,
    aplicar_conduccion,
    puede_conducir,
    calcular_precision_tiro,
    puede_interceptar_pase,
    ejecutar_pase_por_direccion,
    hay_linea_pase,
    distancia_a_segmento
)
from .match_events import MatchEvents, Tarjeta, Lesion, EventoPartido
from .fatigue import FatigueManager


class Partido:
    """
    Controla el estado completo del partido: equipos, pelota, marcador,
    tiempo, eventos, y orquesta la actualización de todos los subsistemas.
    """

    def __init__(self, duracion_minutos=90, jugador_humano_equipo="local"):
        """
        Inicializa el partido.

        :param duracion_minutos: Duración total del partido en minutos (simulados)
        :param jugador_humano_equipo: "local" o "rival" (qué equipo controla el humano)
        """
        # --- Configuración del partido ---
        self.duracion_total = duracion_minutos * 60  # en segundos simulados
        self.tiempo_transcurrido = 0.0
        self.estado = "jugando"  # 'jugando', 'pausa', 'fin_partido'
        self.tiempo_reinicio = 0.0
        self.minuto_actual = 0
        self.segundo_actual = 0

        # --- Marcador ---
        self.goles_local = 0
        self.goles_rival = 0

        # --- Control de cambios de táctica (evita spam) ---
        self.ultimo_cambio_tactica = 0

        # --- Historial de pases (para Ctrl+Z) ---
        self.ultimo_pasador = None
        self.ultimo_receptor = None

        # --- Eventos ---
        self.eventos = MatchEvents()
        self.tarjetas_mostradas = []  # para debug / historial
        self.lesiones_actuales = []

        # --- Crear equipos ---
        self.equipo_local = self._crear_equipo("Local", (0, 0, 255), "left", es_local=True)
        self.equipo_rival = self._crear_equipo("Rival", (255, 0, 0), "right", es_local=False)

        # --- Asignar jugador humano ---
        self.jugador_humano = None
        if jugador_humano_equipo == "local":
            for jug in self.equipo_local.jugadores:
                if jug.numero == 7:
                    jug.es_controlado = True
                    self.jugador_humano = jug
                    break
            if self.jugador_humano is None:
                for jug in self.equipo_local.jugadores:
                    if jug.numero != 0:
                        jug.es_controlado = True
                        self.jugador_humano = jug
                        break
        else:
            for jug in self.equipo_rival.jugadores:
                if jug.numero == 7:
                    jug.es_controlado = True
                    self.jugador_humano = jug
                    break
            if self.jugador_humano is None:
                for jug in self.equipo_rival.jugadores:
                    if jug.numero != 0:
                        jug.es_controlado = True
                        self.jugador_humano = jug
                        break

        # --- Crear pelota ---
        self.pelota = Pelota(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        # --- Asignar balón al jugador humano ---
        if self.jugador_humano is not None:
            self.jugador_humano.recoger_balon(self.pelota)
            self.jugador_con_balon = self.jugador_humano
        else:
            jug_aleatorio = random.choice(self.equipo_local.jugadores)
            jug_aleatorio.recoger_balon(self.pelota)
            self.jugador_con_balon = jug_aleatorio

        # --- Aplicar tácticas iniciales ---
        aplicar_tactica_a_equipo(self.equipo_local, "tiki_taka", self.pelota, 0)
        aplicar_tactica_a_equipo(self.equipo_rival, "catenaccio", self.pelota, 0)

        # --- Guardar posiciones iniciales para reinicios ---
        self._guardar_posiciones_iniciales()

        # --- Configurar sustitutos ---
        self._configurar_sustitutos()

    # ------------------------------------------------------------
    #  Creación de equipos y jugadores
    # ------------------------------------------------------------
    def _crear_equipo(self, nombre, color, lado, es_local):
        equipo = Equipo(nombre, color, lado, es_local)
        posiciones = self._generar_posiciones_iniciales(lado)
        for i, (x, y) in enumerate(posiciones):
            stats_base = self._generar_stats_para_posicion(i)
            nombre_jug = f"{nombre}_{i}"
            edad = random.randint(18, 35)
            stats = PlayerStats(nombre_jug, edad, stats_base)
            jug = Jugador(x, y, nombre, es_controlado=False, numero=i)
            jug.stats = stats
            equipo.agregar_jugador(jug)
        return equipo

    def _generar_posiciones_iniciales(self, lado):
        from .ai import FORMACION_LOCAL, FORMACION_RIVAL, _posicion_base
        formacion = FORMACION_LOCAL if lado == "left" else FORMACION_RIVAL
        posiciones = []
        for i in range(11):
            x, y = _posicion_base(i, formacion)
            x += random.uniform(-10, 10)
            y += random.uniform(-10, 10)
            posiciones.append((x, y))
        return posiciones

    def _generar_stats_para_posicion(self, indice):
        stats = {
            "velocidad": random.randint(50, 85),
            "resistencia": random.randint(50, 85),
            "pase": random.randint(40, 80),
            "regate": random.randint(40, 80),
            "robo": random.randint(40, 80),
            "tiro": random.randint(40, 80)
        }
        if indice == 0:  # Portero
            stats["robo"] = random.randint(80, 95)
            stats["pase"] = random.randint(40, 60)
            stats["tiro"] = random.randint(20, 40)
        elif indice < 5:  # Defensas
            stats["robo"] += 10
            stats["velocidad"] -= 5
            stats["regate"] -= 5
        elif indice < 9:  # Mediocampistas
            stats["pase"] += 10
            stats["resistencia"] += 5
        else:  # Delanteros
            stats["tiro"] += 15
            stats["velocidad"] += 5
            stats["regate"] += 5
        return stats

    def _configurar_sustitutos(self):
        self.sustitutos_local = []
        self.sustitutos_rival = []

    def _guardar_posiciones_iniciales(self):
        self.pos_iniciales = {}
        for jug in self.equipo_local.jugadores + self.equipo_rival.jugadores:
            self.pos_iniciales[jug] = (jug.x, jug.y)

    def reiniciar_posiciones(self):
        for jug, (x, y) in self.pos_iniciales.items():
            jug.x = x
            jug.y = y
            jug.vx = 0
            jug.vy = 0

    # ------------------------------------------------------------
    #  Métodos de control del jugador humano (con sprint y fatiga)
    # ------------------------------------------------------------
    def mover_jugador(self, dx, dy, sprint=False):
        """
        Mueve al jugador humano con velocidad ajustada por sprint y fatiga.
        """
        if self.estado != "jugando" or self.jugador_humano is None:
            return

        # Velocidad base: PLAYER_SPEED, con sprint multiplica por SPRINT_MULTIPLIER
        velocidad_base = PLAYER_SPEED * (SPRINT_MULTIPLIER if sprint else 1.0)

        # Aplicar reducción gradual por fatiga
        if hasattr(self.jugador_humano, 'stats'):
            fatiga = self.jugador_humano.stats.fatiga
            factor_fatiga = 1.0 - (fatiga / 100.0) * 0.7
            factor_fatiga = max(0.3, factor_fatiga)
            velocidad = velocidad_base * factor_fatiga
        else:
            velocidad = velocidad_base

        self.jugador_humano.mover(dx, dy, velocidad, sprint=sprint)

    def lanzar_balon(self, fuerza_x=0, fuerza_y=-400):
        """Método heredado, ahora se usa principalmente para tiros."""
        if self.estado != "jugando" or self.jugador_humano is None:
            return
        if not self.jugador_humano.tiene_balon:
            return

        porteria_x = SCREEN_WIDTH if self.jugador_humano.equipo == "Local" else 0
        porteria_y = SCREEN_HEIGHT // 2
        dist_porteria = distancia_objetos(self.jugador_humano,
                                         type('obj', (object,), {'x': porteria_x, 'y': porteria_y})())
        if dist_porteria < 300 and random.random() < 0.3:
            exito = ejecutar_tiro(self.jugador_humano, self.pelota)
            if exito:
                self.eventos.registrar_evento(EventoPartido("TIRO", self.jugador_humano, "a puerta"))
                self.ultimo_pasador = None
                self.ultimo_receptor = None

    # ------------------------------------------------------------
    #  Método para Ctrl+Z (devolución rápida)
    # ------------------------------------------------------------
    def pase_rapido_ctrl_z(self):
        """
        Devuelve la pelota al último pasador si:
        - El último receptor tiene el balón.
        - Existe línea de pase libre entre el receptor y el pasador.
        """
        if self.ultimo_pasador is None or self.ultimo_receptor is None:
            return
        if not self.ultimo_receptor.tiene_balon:
            return
        if hay_linea_pase(self.ultimo_receptor, self.ultimo_pasador, self.equipo_rival, radio_deteccion=50):
            exito = ejecutar_pase(self.ultimo_receptor, self.ultimo_pasador, self.pelota, es_largo=False)
            if exito:
                self.ultimo_pasador, self.ultimo_receptor = self.ultimo_receptor, self.ultimo_pasador
                self.eventos.registrar_evento(EventoPartido("PASE_RAPIDO", self.ultimo_pasador, self.ultimo_receptor))

    # ------------------------------------------------------------
    #  Cambio de jugador controlado al balón (Q)
    # ------------------------------------------------------------
    def cambiar_jugador_controlado_al_balon(self):
        """
        Cambia el control al jugador del equipo local que tiene el balón.
        Si nadie tiene el balón, cambia al más cercano al balón.
        """
        equipo = self.equipo_local
        jugador_con_balon = None
        for jug in equipo.jugadores:
            if jug.tiene_balon:
                jugador_con_balon = jug
                break

        if jugador_con_balon is not None:
            if jugador_con_balon.es_controlado:
                return
            if self.jugador_humano is not None:
                self.jugador_humano.es_controlado = False
            jugador_con_balon.es_controlado = True
            self.jugador_humano = jugador_con_balon
            self.jugador_con_balon = jugador_con_balon
            return

        mas_cercano = None
        dist_min = float('inf')
        for jug in equipo.jugadores:
            if jug.numero == 0 or hasattr(jug, 'lesionado') or hasattr(jug, 'expulsado'):
                continue
            dist = distancia_objetos(jug, self.pelota)
            if dist < dist_min:
                dist_min = dist
                mas_cercano = jug

        if mas_cercano is not None and not mas_cercano.es_controlado:
            if self.jugador_humano is not None:
                self.jugador_humano.es_controlado = False
            mas_cercano.es_controlado = True
            self.jugador_humano = mas_cercano
            if mas_cercano.tiene_balon:
                self.jugador_con_balon = mas_cercano

    # ------------------------------------------------------------
    #  Bucle principal de actualización
    # ------------------------------------------------------------
    def update(self, dt):
        if self.estado == "fin_partido":
            return

        if self.estado == "pausa":
            self.tiempo_reinicio += dt
            if self.tiempo_reinicio >= 5.0:
                self.estado = "jugando"
            return

        self._actualizar_tiempo(dt)
        self._actualizar_tacticas()
        actualizar_ia(self.equipo_local, self.equipo_rival, self.pelota, dt, self.tiempo_transcurrido)

        if self.jugador_humano is not None:
            self.jugador_humano.actualizar(dt)
            if hasattr(self.jugador_humano, 'stats'):
                dist = math.hypot(self.jugador_humano.vx, self.jugador_humano.vy) * dt
                self.jugador_humano.stats.registrar_distancia(dist)

        self.pelota.actualizar(dt)

        if self.jugador_con_balon is not None and self.jugador_con_balon.tiene_balon:
            aplicar_conduccion(self.jugador_con_balon, self.pelota, dt)

        todos = self.equipo_local.jugadores + self.equipo_rival.jugadores
        for i in range(len(todos)):
            for j in range(i + 1, len(todos)):
                if circulos_colisionan(todos[i], todos[j]):
                    resolver_colision_entre_jugadores(todos[i], todos[j])
                    self._resolver_contacto_con_balon(todos[i], todos[j])

        self._verificar_recogida_balon()
        self._gestionar_recepcion()
        self._check_goal()
        self._gestionar_intercepciones()

        for jug in todos:
            aplicar_limites_campo(jug)
        aplicar_limites_campo(self.pelota)

        self._actualizar_fatiga(dt)

        if self.tiempo_transcurrido >= self.duracion_total:
            self.estado = "fin_partido"
            self.eventos.registrar_evento(EventoPartido("FIN_PARTIDO", None, None))

        self._gestionar_eventos_aleatorios(dt)

    # ------------------------------------------------------------
    #  Sub-funciones de actualización
    # ------------------------------------------------------------
    def _actualizar_tiempo(self, dt):
        self.tiempo_transcurrido += dt
        segundos_totales = int(self.tiempo_transcurrido)
        self.minuto_actual = segundos_totales // 60
        self.segundo_actual = segundos_totales % 60

    def _actualizar_tacticas(self):
        segundo_actual = int(self.tiempo_transcurrido)
        if segundo_actual == self.ultimo_cambio_tactica:
            return
        self.ultimo_cambio_tactica = segundo_actual
        tiempo_restante = max(0, self.duracion_total - self.tiempo_transcurrido)
        if self.goles_local != self.goles_rival or tiempo_restante < 300:
            actualizar_tactica_segun_marcador(
                self.equipo_local, self.goles_local, self.goles_rival,
                tiempo_restante, self.duracion_total
            )
            actualizar_tactica_segun_marcador(
                self.equipo_rival, self.goles_rival, self.goles_local,
                tiempo_restante, self.duracion_total
            )

    def _resolver_contacto_con_balon(self, jug1, jug2):
        if jug1.tiene_balon and jug2.tiene_balon:
            jug1.tiene_balon = False
            jug2.tiene_balon = False
            self.pelota.pegada = False
            self.pelota.dueno = None
            self.jugador_con_balon = None
            return
        if jug1.tiene_balon and jug1.equipo != jug2.equipo:
            exito_regate = ejecutar_regate(jug1, jug2, self.pelota)
            if exito_regate:
                self.jugador_con_balon = jug1
                self.eventos.registrar_evento(EventoPartido("REGATE_EXITOSO", jug1, jug2))
            else:
                self.jugador_con_balon = None
                self.eventos.registrar_evento(EventoPartido("ROBO", jug2, jug1))
            return
        if jug2.tiene_balon and jug2.equipo != jug1.equipo:
            exito_regate = ejecutar_regate(jug2, jug1, self.pelota)
            if exito_regate:
                self.jugador_con_balon = jug2
                self.eventos.registrar_evento(EventoPartido("REGATE_EXITOSO", jug2, jug1))
            else:
                self.jugador_con_balon = None
                self.eventos.registrar_evento(EventoPartido("ROBO", jug1, jug2))

    def _verificar_recogida_balon(self):
        if self.pelota.pegada:
            return
        if self.jugador_humano is not None and not self.jugador_humano.tiene_balon:
            if intentar_recoger_balon(self.jugador_humano, self.pelota):
                self.jugador_con_balon = self.jugador_humano
                self.eventos.registrar_evento(EventoPartido("RECOGIDA", self.jugador_humano, None))
                return
        for equipo in [self.equipo_local, self.equipo_rival]:
            for jug in equipo.jugadores:
                if jug == self.jugador_humano:
                    continue
                if not jug.tiene_balon and intentar_recoger_balon(jug, self.pelota):
                    self.jugador_con_balon = jug
                    self.eventos.registrar_evento(EventoPartido("RECOGIDA", jug, None))
                    return

    def _gestionar_recepcion(self):
        if self.pelota.pegada:
            return
        todos = self.equipo_local.jugadores + self.equipo_rival.jugadores
        mas_cercano = None
        dist_min = float('inf')
        for jug in todos:
            dist = distancia_objetos(jug, self.pelota)
            if dist < dist_min:
                dist_min = dist
                mas_cercano = jug
        if mas_cercano is not None and dist_min < mas_cercano.radio + self.pelota.radio + 10:
            if intentar_recibir(mas_cercano, self.pelota):
                self.jugador_con_balon = mas_cercano
                self.eventos.registrar_evento(EventoPartido("RECEPCION", mas_cercano, None))

    def _gestionar_intercepciones(self):
        if self.pelota.pegada or self.pelota.dueno is not None:
            return
        if self.pelota.vx != 0 or self.pelota.vy != 0:
            receptor_virtual = type('obj', (object,), {
                'x': self.pelota.x + self.pelota.vx * 10,
                'y': self.pelota.y + self.pelota.vy * 10
            })
            pasador_virtual = type('obj', (object,), {
                'x': self.pelota.x - self.pelota.vx * 10,
                'y': self.pelota.y - self.pelota.vy * 10
            })
            for equipo in [self.equipo_rival, self.equipo_local]:
                for defensor in equipo.jugadores:
                    if puede_interceptar_pase(defensor, self.pelota, pasador_virtual, receptor_virtual):
                        defensor.recoger_balon(self.pelota)
                        self.jugador_con_balon = defensor
                        self.eventos.registrar_evento(EventoPartido("INTERCEPCION", defensor, None))
                        return

    def _check_goal(self):
        goal_left_rect = (0, SCREEN_HEIGHT // 2 - GOAL_HEIGHT // 2, GOAL_DEPTH, GOAL_HEIGHT)
        goal_right_rect = (SCREEN_WIDTH - GOAL_DEPTH, SCREEN_HEIGHT // 2 - GOAL_HEIGHT // 2, GOAL_DEPTH, GOAL_HEIGHT)
        bx, by = self.pelota.x, self.pelota.y
        margen = self.pelota.radio
        if (goal_left_rect[0] - margen <= bx <= goal_left_rect[0] + goal_left_rect[2] + margen and
            goal_left_rect[1] - margen <= by <= goal_left_rect[1] + goal_left_rect[3] + margen):
            self._marcar_gol("rival")
        elif (goal_right_rect[0] - margen <= bx <= goal_right_rect[0] + goal_right_rect[2] + margen and
              goal_right_rect[1] - margen <= by <= goal_right_rect[1] + goal_right_rect[3] + margen):
            self._marcar_gol("local")

    def _marcar_gol(self, equipo):
        if self.estado == "fin_partido":
            return
        if equipo == "local":
            self.goles_local += 1
            if self.jugador_con_balon is not None and hasattr(self.jugador_con_balon, 'stats'):
                self.jugador_con_balon.stats.registrar_tiro(True)
                self.eventos.registrar_evento(EventoPartido("GOL", self.jugador_con_balon, None))
        else:
            self.goles_rival += 1
            if self.jugador_con_balon is not None and hasattr(self.jugador_con_balon, 'stats'):
                self.jugador_con_balon.stats.registrar_tiro(True)
                self.eventos.registrar_evento(EventoPartido("GOL", self.jugador_con_balon, None))
        self._reiniciar_tras_gol()

    def _reiniciar_tras_gol(self):
        self.reiniciar_posiciones()
        if self.jugador_humano is not None:
            self.jugador_humano.recoger_balon(self.pelota)
            self.jugador_con_balon = self.jugador_humano
        else:
            self.pelota.x = SCREEN_WIDTH // 2
            self.pelota.y = SCREEN_HEIGHT // 2
            self.pelota.pegada = False
            self.pelota.dueno = None
            self.jugador_con_balon = None
        for jug in self.equipo_local.jugadores + self.equipo_rival.jugadores:
            if hasattr(jug, 'stats'):
                jug.stats.recuperar_cansancio(1.0)
        self.ultimo_pasador = None
        self.ultimo_receptor = None

    def _gestionar_eventos_aleatorios(self, dt):
        if self.estado != "jugando":
            return
        prob_evento = 0.005 * dt
        if random.random() < prob_evento:
            todos = [j for j in (self.equipo_local.jugadores + self.equipo_rival.jugadores) if j.numero != 0]
            if not todos:
                return
            jugador = random.choice(todos)
            tipo = random.choices(
                ["tarjeta_amarilla", "tarjeta_roja", "lesion_menor", "lesion_grave"],
                weights=[0.4, 0.1, 0.3, 0.2]
            )[0]
            if tipo.startswith("tarjeta"):
                self._aplicar_tarjeta(jugador, "amarilla" if tipo == "tarjeta_amarilla" else "roja")
            else:
                self._aplicar_lesion(jugador, tipo == "lesion_grave")

    def _aplicar_tarjeta(self, jugador, tipo):
        tarjeta = Tarjeta(jugador, tipo, self.minuto_actual)
        self.tarjetas_mostradas.append(tarjeta)
        self.eventos.registrar_evento(EventoPartido(f"TARJETA_{tipo.upper()}", jugador, None))
        if tipo == "roja":
            jugador.vx = 0
            jugador.vy = 0
            jugador.expulsado = True

    def _aplicar_lesion(self, jugador, grave):
        lesion = Lesion(jugador, grave, self.minuto_actual)
        self.lesiones_actuales.append(lesion)
        self.eventos.registrar_evento(EventoPartido("LESION", jugador, None))
        if grave:
            jugador.vx = 0
            jugador.vy = 0
            jugador.lesionado = True
        else:
            if hasattr(jugador, 'stats'):
                jugador.stats.lesion_temporal = True
                jugador.stats.lesion_tiempo = self.tiempo_transcurrido + 120

    def _actualizar_fatiga(self, dt):
        for equipo in [self.equipo_local, self.equipo_rival]:
            for jug in equipo.jugadores:
                if not hasattr(jug, 'stats'):
                    continue
                velocidad_actual = math.hypot(jug.vx, jug.vy)
                sprint = getattr(jug, 'sprint', False)
                jug.stats.aplicar_cansancio(dt, velocidad_actual, sprint=sprint)

    # ------------------------------------------------------------
    #  Métodos para obtener el estado (para el frontend)
    # ------------------------------------------------------------
    def obtener_estado(self):
        return {
            "pelota": self.pelota,
            "equipo_local": self.equipo_local,
            "equipo_rival": self.equipo_rival,
            "goles_local": self.goles_local,
            "goles_rival": self.goles_rival,
            "estado": self.estado,
            "jugador_humano": self.jugador_humano,
            "minuto": self.minuto_actual,
            "segundo": self.segundo_actual,
            "tiempo_total": self.duracion_total,
            "tiempo_transcurrido": self.tiempo_transcurrido,
            "eventos": self.eventos,
            "tarjetas": self.tarjetas_mostradas,
            "lesiones": self.lesiones_actuales
        }

    # ------------------------------------------------------------
    #  Métodos para pausa y gestión de partido
    # ------------------------------------------------------------
    def pausar_partido(self):
        if self.estado == "jugando":
            self.estado = "pausa"
            self.tiempo_reinicio = 0.0

    def reanudar_partido(self):
        if self.estado == "pausa":
            self.estado = "jugando"

    def realizar_sustitucion(self, equipo, jugador_entra, jugador_sale):
        if jugador_sale in equipo.jugadores:
            jugador_entra.x, jugador_entra.y = jugador_sale.x, jugador_sale.y
            jugador_entra.stats = jugador_sale.stats
            jugador_entra.equipo = equipo.nombre
            idx = equipo.jugadores.index(jugador_sale)
            equipo.jugadores[idx] = jugador_entra
            self.eventos.registrar_evento(EventoPartido("SUSTITUCION", jugador_entra, jugador_sale))
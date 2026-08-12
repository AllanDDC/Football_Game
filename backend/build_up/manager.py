# backend/build_up/manager.py
"""
Orquestador de construcción de juego ofensiva.
Selecciona y aplica estrategias de movimiento a los jugadores
cuando su equipo tiene la pelota.
"""

import random
import math
from ..physics import mover_hacia, distancia_objetos
from ..ai import decidir_sprint
from .bandas import EstrategiaBandas
from .arrastre import EstrategiaArrastre
from .pasillos import EstrategiaPasillos
from .avance_vertical import EstrategiaAvanceVertical
from .rondos import EstrategiaRondos
from .triangulacion import EstrategiaTriangulacion
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS


class BuildUpManager:
    """
    Gestiona la construcción de juego ofensiva.
    Aplica estrategias no excluyentes según el rol del jugador.
    """

    def __init__(self, equipo):
        self.equipo = equipo
        self.es_local = equipo.es_local

        # Mapeo de roles a listas de estrategias (orden de prioridad)
        self.estrategias_por_rol = {
            "defensa": [
                EstrategiaBandas(),        # apertura en banda
                EstrategiaArrastre(),      # arrastre de marcas
                EstrategiaAvanceVertical(),# subida ofensiva (nuevo)
            ],
            "mediocampista": [
                EstrategiaTriangulacion(),
                EstrategiaPasillos(),
                EstrategiaRondos(),
                EstrategiaArrastre(),
                EstrategiaAvanceVertical(),
                EstrategiaBandas(),
            ],
            "delantero": [
                EstrategiaAvanceVertical(),
                EstrategiaPasillos(),
                EstrategiaArrastre(),
                EstrategiaBandas(),
            ],
        }

        self.contador_estrategias = {}

    def actualizar(self, equipo_rival, pelota, dt, poseedor, get_velocidad):
        if poseedor is None or poseedor.equipo != self.equipo.nombre:
            return

        # Procesar cada jugador (excepto portero y humano)
        for jug in self.equipo.jugadores:
            if jug.numero == 0:
                continue
            if jug.es_controlado:
                continue
            if hasattr(jug, 'expulsado') and jug.expulsado:
                continue
            if hasattr(jug, 'lesionado') and jug.lesionado:
                continue

            # Determinar rol
            if jug.numero < 5:
                rol = "defensa"
            elif jug.numero < 9:
                rol = "mediocampista"
            else:
                rol = "delantero"

            estrategias = self.estrategias_por_rol.get(rol, [])
            idx = self.contador_estrategias.get(jug, 0)

            destino = None
            # Intentar estrategias en orden rotativo
            for _ in range(len(estrategias)):
                estrategia = estrategias[idx % len(estrategias)]
                contexto = {
                    'poseedor': poseedor,
                    'pelota': pelota,
                    'equipo': self.equipo,
                    'equipo_rival': equipo_rival,
                    'dt': dt,
                    'get_velocidad': get_velocidad,
                    'es_local': self.es_local,
                }
                destino = estrategia.ejecutar(jug, contexto)
                if destino is not None:
                    break
                idx = (idx + 1) % len(estrategias)

            # Si ninguna estrategia dio destino, usar estrategia por defecto
            if destino is None:
                destino = self._estrategia_defecto(jug, poseedor, equipo_rival)

            if destino is not None:
                destino_x, destino_y = destino
                self._mover_jugador(jug, destino_x, destino_y, dt, get_velocidad,
                                    poseedor, pelota, equipo_rival)
                # Avanzar contador solo si se movió
                self.contador_estrategias[jug] = (idx + 1) % len(estrategias) if estrategias else 0

    def _estrategia_defecto(self, jug, poseedor, equipo_rival):
        """
        Estrategia de respaldo: moverse hacia el poseedor en ángulo,
        o avanzar verticalmente si está lejos.
        """
        # Si el jugador está muy lejos del poseedor, avanzar verticalmente
        dist_poseedor = distancia_objetos(jug, poseedor)
        if dist_poseedor > 250:
            porteria_x = SCREEN_WIDTH if self.es_local else 0
            porteria_y = SCREEN_HEIGHT / 2
            # Moverse hacia la portería rival en diagonal
            angulo = math.atan2(porteria_y - jug.y, porteria_x - jug.x)
            angulo += random.uniform(-0.3, 0.3)
            radio = 80 + random.uniform(0, 40)
            destino_x = jug.x + math.cos(angulo) * radio
            destino_y = jug.y + math.sin(angulo) * radio
            return (destino_x, destino_y)

        # Si está cerca, moverse para ofrecer línea de pase (en ángulo)
        angulo = math.atan2(jug.y - poseedor.y, jug.x - poseedor.x)
        angulo += random.uniform(-0.8, 0.8)
        radio = 60 + random.uniform(0, 30)
        destino_x = poseedor.x + math.cos(angulo) * radio
        destino_y = poseedor.y + math.sin(angulo) * radio
        return (destino_x, destino_y)

    def _mover_jugador(self, jug, destino_x, destino_y, dt, get_velocidad,
                       poseedor, pelota, equipo_rival):
        # Decidir sprint
        sprint = decidir_sprint(jug, poseedor, pelota, self.equipo, equipo_rival)

        # Velocidad según rol
        if jug.numero < 5:
            factor = 0.6
        elif jug.numero < 9:
            factor = 0.7
        else:
            factor = 0.8

        velocidad = get_velocidad(jug, factor=factor, sprint=sprint)

        destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})
        if distancia_objetos(jug, destino) < 5:
            jug.establecer_velocidad(0, 0)
            jug.actualizar(dt)
            return

        vx, vy = mover_hacia(jug, destino, velocidad, dt)
        jug.establecer_velocidad(vx, vy)
        jug.actualizar(dt)
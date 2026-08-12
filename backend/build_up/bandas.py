# backend/build_up/bandas.py
"""
Estrategia ofensiva: apertura en banda (desborde).
Los jugadores se abren a las bandas para crear amplitud,
estirar la defensa rival y generar espacios interiores.
"""

import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS


class EstrategiaBandas(EstrategiaOfensiva):
    """
    Estrategia de apertura en banda.
    - Laterales y extremos se abren a la banda correspondiente.
    - Mediocampistas pueden abrirse si el equipo necesita amplitud.
    - La profundidad de la apertura depende de la posición del poseedor.
    """

    def ejecutar(self, jug, contexto):
        """
        Calcula un destino en la banda para el jugador.

        :param jug: Jugador al que se aplica la estrategia.
        :param contexto: Diccionario con poseedor, pelota, equipo, etc.
        :return: Tupla (destino_x, destino_y) o None si no aplica.
        """
        poseedor = contexto.get('poseedor')
        equipo = contexto.get('equipo')
        es_local = contexto.get('es_local', True)
        dt = contexto.get('dt', 0.016)

        if poseedor is None:
            return None

        # Determinar si el jugador es lateral (defensa o extremo) según su índice
        # En formación 4-4-2: defensas índices 1-4, mediocampistas 5-8, delanteros 9-10
        # Los laterales suelen ser índices 2 y 3 (derecho e izquierdo)
        # Simplificamos: los jugadores con índice par (2,4,6,8,10) se abren a la derecha,
        # los impares (1,3,5,7,9) a la izquierda.
        # Pero es mejor usar un criterio basado en posición actual para mayor naturalidad.
        # Aquí usamos el índice para decidir la banda, pero podemos refinar.

        # Si el jugador ya está cerca de una banda, reforzamos su posición
        if jug.x < SCREEN_WIDTH * 0.2:
            banda = 'izquierda'
        elif jug.x > SCREEN_WIDTH * 0.8:
            banda = 'derecha'
        else:
            # Si está en el centro, decidir según índice
            if jug.numero % 2 == 0:
                banda = 'derecha'
            else:
                banda = 'izquierda'

        # Determinar la profundidad (adelante/atrás) según la posición del poseedor
        # Si el poseedor está atrás, los jugadores se abren más adelantados
        if es_local:
            if poseedor.x < SCREEN_WIDTH * 0.3:
                profundidad = 0.8  # más adelante
            elif poseedor.x < SCREEN_WIDTH * 0.6:
                profundidad = 0.6  # medio
            else:
                profundidad = 0.4  # más atrás para no estar en offside
        else:
            if poseedor.x > SCREEN_WIDTH * 0.7:
                profundidad = 0.8
            elif poseedor.x > SCREEN_WIDTH * 0.4:
                profundidad = 0.6
            else:
                profundidad = 0.4

        # Ajustar según el rol del jugador (defensa menos profundo, delantero más)
        if jug.numero < 5:  # defensa
            profundidad *= 0.6
        elif jug.numero < 9:  # mediocampista
            profundidad *= 0.8
        # delanteros se quedan con profundidad completa

        # Calcular coordenada X en la banda
        if banda == 'izquierda':
            x = PLAYER_RADIUS + 30
        else:
            x = SCREEN_WIDTH - PLAYER_RADIUS - 30

        # Calcular Y según la profundidad (entre 0.2 y 0.8 de la altura)
        y_min = SCREEN_HEIGHT * 0.15
        y_max = SCREEN_HEIGHT * 0.85
        # La Y depende de la posición del poseedor para crear líneas de pase
        if poseedor:
            # Si el poseedor está en la misma banda, nos movemos más adelante
            if (poseedor.x < SCREEN_WIDTH * 0.3 and banda == 'izquierda') or (poseedor.x > SCREEN_WIDTH * 0.7 and banda == 'derecha'):
                y = poseedor.y - 50  # adelantarse
            else:
                # Si el poseedor está en el centro, buscar espacio en diagonal
                angulo = math.atan2(poseedor.y - jug.y, poseedor.x - jug.x)
                y = jug.y + math.sin(angulo) * 100 * (0.5 + profundidad * 0.5)
        else:
            # Si no hay poseedor, usar Y de la posición base
            y = SCREEN_HEIGHT / 2 + (jug.numero - 5) * 20

        # Limitar Y dentro del campo
        y = max(y_min, min(y_max, y))

        # Limitar coordenadas finales
        x, y = self._limitar_campo(x, y)

        # Si el jugador ya está en la banda y cerca del destino, no mover
        if abs(jug.x - x) < 20 and abs(jug.y - y) < 20:
            return None

        return (x, y)
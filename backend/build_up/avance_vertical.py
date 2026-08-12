# backend/build_up/avance_vertical.py
"""
Estrategia ofensiva: avance vertical (profundidad).
Los jugadores se mueven hacia adelante (hacia la portería rival)
para recibir balones en profundidad, rompiendo la línea defensiva rival.
Busca generar ocasiones de gol mediante desmarques de ruptura.
"""

import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..physics import distancia_objetos


class EstrategiaAvanceVertical(EstrategiaOfensiva):
    """
    Estrategia de avance vertical.
    - Delanteros y extremos buscan espacio en profundidad.
    - Mediocampistas se proyectan para apoyar el ataque.
    - Se calcula la mejor posición entre líneas o a espaldas de la defensa.
    """

    def ejecutar(self, jug, contexto):
        """
        Calcula un destino hacia adelante para recibir en profundidad.

        :param jug: Jugador al que se aplica la estrategia.
        :param contexto: Diccionario con poseedor, pelota, equipo, etc.
        :return: Tupla (destino_x, destino_y) o None si no aplica.
        """
        poseedor = contexto.get('poseedor')
        equipo = contexto.get('equipo')
        equipo_rival = contexto.get('equipo_rival')
        es_local = contexto.get('es_local', True)
        dt = contexto.get('dt', 0.016)
        get_velocidad = contexto.get('get_velocidad')

        # Solo aplica a jugadores ofensivos (índices ≥ 5)
        if jug.numero < 5:
            return None

        if poseedor is None or jug.tiene_balon:
            return None

        # Determinar la portería rival
        porteria_x = SCREEN_WIDTH if es_local else 0
        porteria_y = SCREEN_HEIGHT / 2

        # Obtener la línea defensiva rival
        defensas_rivales = [j for j in equipo_rival.jugadores if j.numero < 5 and j.numero > 0]
        if not defensas_rivales:
            # Si no hay defensas, ir directamente a portería
            destino_x = porteria_x + random.uniform(-50, 50)
            destino_y = porteria_y + random.uniform(-50, 50)
            return self._limitar_campo(destino_x, destino_y)

        # Calcular la posición del último defensor (el más adelantado)
        if es_local:
            ultimo_defensor = max(defensas_rivales, key=lambda j: j.x)
        else:
            ultimo_defensor = min(defensas_rivales, key=lambda j: j.x)

        # La posición de avance vertical es ligeramente detrás del último defensor
        # para evitar el fuera de juego, pero con un margen
        if es_local:
            # Si somos locales, avanzamos hacia la derecha
            destino_x = ultimo_defensor.x + random.uniform(20, 60)
        else:
            destino_x = ultimo_defensor.x - random.uniform(20, 60)

        # La Y se ajusta para buscar un espacio entre defensas
        # Buscar el espacio más grande entre defensas en el eje Y
        espacios = []
        defensas_ordenadas = sorted(defensas_rivales, key=lambda j: j.y)
        for i in range(len(defensas_ordenadas) - 1):
            j1 = defensas_ordenadas[i]
            j2 = defensas_ordenadas[i + 1]
            espacio = j2.y - j1.y
            if espacio > 50:  # Si hay suficiente espacio entre dos defensas
                espacios.append((j1.y + j2.y) / 2)

        if espacios:
            destino_y = random.choice(espacios) + random.uniform(-20, 20)
        else:
            # Si no hay espacios, usar el centro de la portería
            destino_y = porteria_y + random.uniform(-60, 60)

        # Limitar la profundidad máxima
        if es_local:
            destino_x = min(SCREEN_WIDTH - PLAYER_RADIUS, destino_x)
            # No ir más allá de la portería
            if destino_x > SCREEN_WIDTH - 30:
                destino_x = SCREEN_WIDTH - 30
        else:
            destino_x = max(PLAYER_RADIUS, destino_x)
            if destino_x < 30:
                destino_x = 30

        # Si el jugador es mediocampista, no se adelanta tanto
        if 5 <= jug.numero <= 8:
            # Los mediocampistas se proyectan pero no tanto como los delanteros
            if es_local:
                destino_x = min(destino_x, jug.x + 100)
            else:
                destino_x = max(destino_x, jug.x - 100)

        # Limitar Y
        destino_y = max(SCREEN_HEIGHT * 0.1, min(SCREEN_HEIGHT * 0.9, destino_y))

        # Si el destino está muy lejos del jugador, reducir distancia para no desordenar
        dist = math.hypot(destino_x - jug.x, destino_y - jug.y)
        if dist > 150:
            factor = 150 / dist
            destino_x = jug.x + (destino_x - jug.x) * factor
            destino_y = jug.y + (destino_y - jug.y) * factor

        # Si ya está cerca del destino, no mover
        if abs(jug.x - destino_x) < 20 and abs(jug.y - destino_y) < 20:
            return None

        return (destino_x, destino_y)
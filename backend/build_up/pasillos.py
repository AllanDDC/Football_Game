# backend/build_up/pasillos.py
"""
Estrategia ofensiva: creación de pasillos interiores.
Los jugadores se mueven entre líneas defensivas rivales para recibir el balón
en zonas de peligro (entre centrales y laterales, o entre mediocampo y defensa).
Busca romper la estructura defensiva rival.
"""

import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..physics import distancia_objetos


class EstrategiaPasillos(EstrategiaOfensiva):
    """
    Estrategia para moverse entre líneas y crear pasillos de pase.
    Se aplica principalmente a mediocampistas ofensivos y delanteros.
    """

    def ejecutar(self, jug, contexto):
        """
        Calcula un destino entre líneas defensivas rivales.

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

        # Solo aplica a mediocampistas y delanteros (índices 5-10)
        if jug.numero < 5:
            return None

        if poseedor is None or jug.tiene_balon:
            return None

        # Buscar espacios entre líneas defensivas rivales
        # 1. Obtener la línea defensiva rival promedio
        defensas_rivales = [j for j in equipo_rival.jugadores if j.numero < 5 and j.numero > 0]
        if not defensas_rivales:
            return None

        # Calcular el centro de la línea defensiva
        y_defensas = [j.y for j in defensas_rivales]
        y_promedio = sum(y_defensas) / len(y_defensas)

        # Determinar qué tan adelante está la defensa rival
        x_defensas = [j.x for j in defensas_rivales]
        x_promedio = sum(x_defensas) / len(x_defensas)

        # Buscar un hueco entre defensas (entre dos defensas)
        huecos = []
        for i in range(len(defensas_rivales) - 1):
            j1 = defensas_rivales[i]
            j2 = defensas_rivales[i + 1]
            # Si están cerca horizontalmente, hay un hueco vertical
            if abs(j1.x - j2.x) < 60:
                hueco_y = (j1.y + j2.y) / 2
                huecos.append((j1.x, hueco_y))

        # Si no hay huecos, usar el centro de la defensa
        if huecos:
            hueco = random.choice(huecos)
            destino_x = hueco[0] + random.uniform(-30, 30)
            destino_y = hueco[1] + random.uniform(-30, 30)
        else:
            # Si no hay huecos, buscar espacio entre la línea defensiva y el mediocampo
            # Buscar mediocampistas rivales
            mediocampistas_rivales = [j for j in equipo_rival.jugadores if 5 <= j.numero < 9]
            if mediocampistas_rivales:
                y_mediocampistas = [j.y for j in mediocampistas_rivales]
                y_media = sum(y_mediocampistas) / len(y_mediocampistas)
                # El espacio está entre la defensa y el mediocampo
                destino_y = (y_promedio + y_media) / 2 + random.uniform(-20, 20)
            else:
                destino_y = y_promedio + random.uniform(-40, 40)

            # Profundidad: un poco adelante de la línea defensiva
            if es_local:
                destino_x = x_promedio + 50 + random.uniform(0, 30)
            else:
                destino_x = x_promedio - 50 + random.uniform(-30, 0)

        # Limitar al campo
        destino_x, destino_y = self._limitar_campo(destino_x, destino_y)

        # Si el destino está muy lejos del jugador, reducir distancia para no desordenar
        dist = math.hypot(destino_x - jug.x, destino_y - jug.y)
        if dist > 150:
            # Acercar el destino gradualmente
            factor = 150 / dist
            destino_x = jug.x + (destino_x - jug.x) * factor
            destino_y = jug.y + (destino_y - jug.y) * factor

        # Si ya está cerca del destino, no mover
        if abs(jug.x - destino_x) < 20 and abs(jug.y - destino_y) < 20:
            return None

        return (destino_x, destino_y)
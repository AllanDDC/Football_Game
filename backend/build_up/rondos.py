# backend/build_up/rondos.py
"""
Estrategia ofensiva: rondos (movimientos circulares).
Simula el clásico rondo de entrenamiento: jugadores se mueven alrededor del poseedor
formando un círculo, ofreciendo líneas de pase cortas y cambiando constantemente de orientación.
Ideal para mantener la posesión en campo propio y avanzar combinando.
"""

import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..physics import distancia_objetos


class EstrategiaRondos(EstrategiaOfensiva):
    """
    Estrategia de rondo: movimiento circular alrededor del poseedor.
    Los jugadores sin balón se mueven en un radio de 80-150 píxeles alrededor del poseedor,
    cambiando de posición para ofrecer líneas de pase.
    """

    def ejecutar(self, jug, contexto):
        """
        Calcula un destino en un movimiento circular alrededor del poseedor.

        :param jug: Jugador al que se aplica la estrategia.
        :param contexto: Diccionario con poseedor, pelota, equipo, etc.
        :return: Tupla (destino_x, destino_y) o None si no aplica.
        """
        poseedor = contexto.get('poseedor')
        equipo = contexto.get('equipo')
        es_local = contexto.get('es_local', True)
        dt = contexto.get('dt', 0.016)
        get_velocidad = contexto.get('get_velocidad')
        pelota = contexto.get('pelota')

        if poseedor is None or jug.tiene_balon:
            return None

        # Solo aplica a jugadores cercanos al poseedor (distancia < 250)
        dist_poseedor = distancia_objetos(jug, poseedor)
        if dist_poseedor > 250:
            return None

        # El rondo se aplica preferentemente a defensas y mediocampistas (índices 1-8)
        # Delanteros también pueden participar, pero menos frecuente
        if jug.numero >= 9 and random.random() < 0.5:
            # Delanteros a veces se mantienen más adelante
            return None

        # Parámetros del rondo
        radio_base = 80 + random.uniform(0, 40)  # radio del círculo
        velocidad_angular = 1.0 + random.uniform(-0.5, 1.0)  # velocidad de giro (rad/s)

        # Calcular el ángulo actual del jugador respecto al poseedor
        angulo_actual = math.atan2(jug.y - poseedor.y, jug.x - poseedor.x)

        # Incrementar el ángulo para simular movimiento circular
        # El incremento depende del tiempo y de una componente aleatoria
        incremento = velocidad_angular * dt * 0.8  # factor de suavizado
        # Añadir pequeña variación para que no sea un círculo perfecto
        incremento += random.uniform(-0.1, 0.1) * dt

        nuevo_angulo = angulo_actual + incremento

        # Calcular nuevo destino en el círculo
        destino_x = poseedor.x + math.cos(nuevo_angulo) * radio_base
        destino_y = poseedor.y + math.sin(nuevo_angulo) * radio_base

        # Ajustar el radio para salir del círculo si hay un compañero cerca
        # (para evitar colisiones)
        for comp in equipo.jugadores:
            if comp == jug or comp == poseedor:
                continue
            if distancia_objetos(jug, comp) < 30:
                # Si hay un compañero muy cerca, aumentar radio para separarse
                radio_base += 20
                destino_x = poseedor.x + math.cos(nuevo_angulo) * radio_base
                destino_y = poseedor.y + math.sin(nuevo_angulo) * radio_base
                break

        # Limitar el destino al campo
        destino_x, destino_y = self._limitar_campo(destino_x, destino_y)

        # Si el destino está demasiado cerca del poseedor, ajustar
        dist_nueva = math.hypot(destino_x - poseedor.x, destino_y - poseedor.y)
        if dist_nueva < 50:
            # Aumentar radio para crear más separación
            radio_base = 70
            destino_x = poseedor.x + math.cos(nuevo_angulo) * radio_base
            destino_y = poseedor.y + math.sin(nuevo_angulo) * radio_base
            destino_x, destino_y = self._limitar_campo(destino_x, destino_y)

        # Si ya está cerca del destino, no mover
        if abs(jug.x - destino_x) < 15 and abs(jug.y - destino_y) < 15:
            return None

        return (destino_x, destino_y)
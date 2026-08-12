# backend/build_up/arrastre.py
"""
Estrategia ofensiva: arrastre de marcas.
Los jugadores se mueven para atraer a los defensores rivales,
creando espacios para sus compañeros.
Puede ser:
- Arrastre hacia atrás: simular que se retira para recibir, atrayendo a un defensor.
- Arrastre hacia la banda: abrirse para estirar la defensa.
- Arrastre diagonal: moverse entre líneas para desordenar la zaga.
"""

import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS


class EstrategiaArrastre(EstrategiaOfensiva):
    """
    Estrategia para arrastrar marcas y generar espacios.
    Se aplica a jugadores que no tienen el balón y están en posición de crear peligro.
    """

    def ejecutar(self, jug, contexto):
        """
        Calcula un destino para arrastrar a un defensor.

        :param jug: Jugador al que se aplica la estrategia.
        :param contexto: Diccionario con poseedor, pelota, equipo, etc.
        :return: Tupla (destino_x, destino_y) o None si no aplica.
        """
        poseedor = contexto.get('poseedor')
        equipo = contexto.get('equipo')
        es_local = contexto.get('es_local', True)
        dt = contexto.get('dt', 0.016)
        get_velocidad = contexto.get('get_velocidad')
        equipo_rival = contexto.get('equipo_rival')

        if poseedor is None or get_velocidad is None:
            return None

        # Determinar si este jugador es candidato a arrastrar
        # Preferiblemente jugadores adelantados (mediocampistas y delanteros)
        if jug.numero < 5:  # defensas raramente arrastran (a menos que sea muy ofensivo)
            # Solo si la táctica es muy ofensiva
            if random.random() < 0.2:
                pass
            else:
                return None

        # Si el jugador ya tiene el balón, no arrastra
        if jug.tiene_balon:
            return None

        # Decidir tipo de arrastre según contexto
        tipo = self._decidir_tipo_arrastre(jug, poseedor, equipo, es_local)

        if tipo == 'retroceso':
            destino = self._arrastre_retroceso(jug, poseedor, es_local)
        elif tipo == 'banda':
            destino = self._arrastre_banda(jug, poseedor, es_local)
        elif tipo == 'diagonal':
            destino = self._arrastre_diagonal(jug, poseedor, es_local)
        else:
            return None

        if destino is None:
            return None

        x, y = self._limitar_campo(destino[0], destino[1])
        # Si ya está cerca del destino, no mover
        if abs(jug.x - x) < 20 and abs(jug.y - y) < 20:
            return None
        return (x, y)

    def _decidir_tipo_arrastre(self, jug, poseedor, equipo, es_local):
        """
        Decide qué tipo de arrastre realizar según el contexto.
        """
        # Factores:
        # - Si el poseedor está cerca, arrastre de retroceso para dar opción de pase.
        # - Si el jugador está en una banda, arrastre de banda.
        # - Si el equipo necesita romper líneas, arrastre diagonal.

        dist_poseedor = math.hypot(jug.x - poseedor.x, jug.y - poseedor.y) if poseedor else 999

        if dist_poseedor < 120:
            # Cerca del poseedor: retroceso para recibir y atraer
            return 'retroceso'

        # Si el jugador está en una banda (cerca de los bordes)
        if jug.x < SCREEN_WIDTH * 0.2 or jug.x > SCREEN_WIDTH * 0.8:
            # Si además hay espacio en la banda, arrastre de banda
            if (es_local and jug.x < SCREEN_WIDTH * 0.2) or (not es_local and jug.x > SCREEN_WIDTH * 0.8):
                return 'banda'

        # Si el jugador está entre líneas (zona central), arrastre diagonal
        if jug.x > SCREEN_WIDTH * 0.25 and jug.x < SCREEN_WIDTH * 0.75:
            return 'diagonal'

        # Por defecto, arrastre de retroceso
        return 'retroceso'

    def _arrastre_retroceso(self, jug, poseedor, es_local):
        """
        El jugador se retira unos metros hacia atrás para atraer a su marcador.
        """
        # Dirección desde el poseedor hacia el jugador (para retroceder hacia el poseedor)
        if poseedor:
            dx = jug.x - poseedor.x
            dy = jug.y - poseedor.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                # Retroceder en la dirección opuesta al poseedor (alejarse)
                destino_x = jug.x - (dx / dist) * 60 + random.uniform(-20, 20)
                destino_y = jug.y - (dy / dist) * 60 + random.uniform(-20, 20)
            else:
                destino_x = jug.x + random.uniform(-50, 50)
                destino_y = jug.y - 50
        else:
            # Sin poseedor, retroceder hacia el campo propio
            if es_local:
                destino_x = jug.x - 50 + random.uniform(-20, 20)
            else:
                destino_x = jug.x + 50 + random.uniform(-20, 20)
            destino_y = jug.y + random.uniform(-30, 30)

        return (destino_x, destino_y)

    def _arrastre_banda(self, jug, poseedor, es_local):
        """
        El jugador se mueve hacia la banda para estirar la defensa.
        """
        # Determinar banda (izquierda o derecha según posición actual)
        if jug.x < SCREEN_WIDTH * 0.5:
            banda_x = PLAYER_RADIUS + 40
        else:
            banda_x = SCREEN_WIDTH - PLAYER_RADIUS - 40

        # La Y varía según la posición del poseedor para crear líneas de pase
        if poseedor:
            # Buscar estar en diagonal o en la misma línea
            if abs(jug.y - poseedor.y) < 30:
                # Si está muy alineado, moverse para desmarcarse
                destino_y = poseedor.y + random.uniform(-80, 80)
            else:
                destino_y = poseedor.y + (jug.y - poseedor.y) * 0.5
        else:
            destino_y = jug.y + random.uniform(-40, 40)

        # Asegurar que la Y esté dentro de los límites
        destino_y = max(SCREEN_HEIGHT * 0.15, min(SCREEN_HEIGHT * 0.85, destino_y))

        return (banda_x, destino_y)

    def _arrastre_diagonal(self, jug, poseedor, es_local):
        """
        Movimiento en diagonal entre líneas para arrastrar a un defensor fuera de posición.
        """
        if poseedor:
            # Diagonal en dirección a la portería rival pero con desviación
            porteria_x = SCREEN_WIDTH if es_local else 0
            porteria_y = SCREEN_HEIGHT / 2

            # Vector hacia portería
            dx = porteria_x - jug.x
            dy = porteria_y - jug.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                # Moverse en diagonal con un ángulo de 30-60 grados respecto a la portería
                angulo = math.atan2(dy, dx) + random.uniform(-0.6, 0.6)
                radio = 80 + random.uniform(0, 40)
                destino_x = jug.x + math.cos(angulo) * radio
                destino_y = jug.y + math.sin(angulo) * radio
            else:
                destino_x = jug.x + random.uniform(-50, 50)
                destino_y = jug.y + random.uniform(-50, 50)
        else:
            destino_x = jug.x + random.uniform(-60, 60)
            destino_y = jug.y + random.uniform(-60, 60)

        return (destino_x, destino_y)
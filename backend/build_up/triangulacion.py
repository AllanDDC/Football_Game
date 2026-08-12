# backend/build_up/triangulacion.py
"""
Estrategia ofensiva: triangulación y pases de 3 hombres.
Los jugadores se posicionan formando triángulos con el poseedor y otro compañero,
ofreciendo líneas de pase seguras y permitiendo el avance combinativo.
Ideal para mantener la posesión y progresar en el campo.
"""

import math
import random
from .base import EstrategiaOfensiva
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..physics import distancia_objetos


class EstrategiaTriangulacion(EstrategiaOfensiva):
    """
    Estrategia de triangulación: formar triángulos con poseedor y otro compañero.
    El jugador se mueve al vértice libre del triángulo, buscando
    líneas de pase y espacios entre los rivales.
    """

    def ejecutar(self, jug, contexto):
        """
        Calcula un destino para formar un triángulo con el poseedor y otro compañero.

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

        if poseedor is None or jug.tiene_balon:
            return None

        # Solo aplica a mediocampistas y defensas ofensivos (índices 1-8)
        # Los delanteros a veces participan
        if jug.numero >= 9 and random.random() < 0.4:
            return None

        # Buscar un compañero cercano para formar el triángulo
        # (no el poseedor ni el propio jugador)
        companero = self._buscar_companero(jug, poseedor, equipo)
        if companero is None:
            return None

        # Calcular el vértice del triángulo (posición ideal para este jugador)
        destino = self._calcular_vertice_triangulo(jug, poseedor, companero, equipo_rival, es_local)

        if destino is None:
            return None

        destino_x, destino_y = destino
        destino_x, destino_y = self._limitar_campo(destino_x, destino_y)

        # Si el destino está muy lejos del jugador, reducir distancia
        dist = math.hypot(destino_x - jug.x, destino_y - jug.y)
        if dist > 150:
            factor = 150 / dist
            destino_x = jug.x + (destino_x - jug.x) * factor
            destino_y = jug.y + (destino_y - jug.y) * factor

        # Si ya está cerca del destino, no mover
        if abs(jug.x - destino_x) < 20 and abs(jug.y - destino_y) < 20:
            return None

        return (destino_x, destino_y)

    def _buscar_companero(self, jug, poseedor, equipo):
        """
        Busca un compañero adecuado para formar triángulo.
        Prioriza compañeros cercanos al poseedor pero no al propio jugador.
        """
        mejores = []
        for comp in equipo.jugadores:
            if comp == jug or comp == poseedor or comp.tiene_balon:
                continue
            # Distancia al poseedor
            dist_poseedor = distancia_objetos(poseedor, comp)
            # Distancia al jugador
            dist_jug = distancia_objetos(jug, comp)
            # Buscar compañeros a distancia media (no muy cerca ni muy lejos)
            if 50 < dist_poseedor < 200 and dist_jug < 250:
                # Mejor si está en una posición angular distinta
                angulo_jug = math.atan2(jug.y - poseedor.y, jug.x - poseedor.x)
                angulo_comp = math.atan2(comp.y - poseedor.y, comp.x - poseedor.x)
                diff_angulo = abs(angulo_jug - angulo_comp)
                if diff_angulo > 0.3:  # Suficientemente separado
                    mejores.append(comp)

        if mejores:
            return random.choice(mejores)
        return None

    def _calcular_vertice_triangulo(self, jug, poseedor, companero, equipo_rival, es_local):
        """
        Calcula el vértice del triángulo para este jugador.
        Idealmente, el triángulo debe ser:
        - Equilátero o isósceles, con lados de 80-120 píxeles.
        - Orientado hacia la portería rival o hacia espacios libres.
        """
        # Vectores desde el poseedor al jugador y al compañero
        vx_jug = jug.x - poseedor.x
        vy_jug = jug.y - poseedor.y
        vx_comp = companero.x - poseedor.x
        vy_comp = companero.y - poseedor.y

        # Distancias desde el poseedor
        d_jug = math.hypot(vx_jug, vy_jug)
        d_comp = math.hypot(vx_comp, vy_comp)

        # Si el jugador o el compañero están muy cerca del poseedor, ajustar
        if d_jug < 30:
            # Si el jugador está muy cerca, alejarlo
            angulo = math.atan2(vy_jug, vx_jug)
            d_jug = 80
            vx_jug = math.cos(angulo) * d_jug
            vy_jug = math.sin(angulo) * d_jug
        if d_comp < 30:
            angulo = math.atan2(vy_comp, vx_comp)
            d_comp = 80
            vx_comp = math.cos(angulo) * d_comp
            vy_comp = math.sin(angulo) * d_comp

        # Calcular la mediana entre los dos vectores
        # El vértice ideal es el punto que forma un triángulo isósceles con base entre jug y comp
        # Calculamos el punto medio entre jug y comp
        mx = (jug.x + companero.x) / 2
        my = (jug.y + companero.y) / 2

        # Vector desde el poseedor al punto medio
        vx_m = mx - poseedor.x
        vy_m = my - poseedor.y
        d_m = math.hypot(vx_m, vy_m)

        if d_m == 0:
            # Si el punto medio coincide con el poseedor, usar dirección aleatoria
            angulo = random.uniform(0, 2 * math.pi)
            d_m = 100
            vx_m = math.cos(angulo) * d_m
            vy_m = math.sin(angulo) * d_m

        # La distancia ideal para el vértice es un poco mayor que la distancia al punto medio
        # para formar un triángulo más abierto
        distancia_vertice = d_m * 1.2 + 20

        # Dirección perpendicular a la línea que une jug y comp (para abrir el triángulo)
        # Vector perpendicular al vector que une jug y comp
        ux = jug.x - companero.x
        uy = jug.y - companero.y
        if math.hypot(ux, uy) > 0:
            # Normalizar y rotar 90 grados
            norm = math.hypot(ux, uy)
            ux /= norm
            uy /= norm
            # Perpendicular (rotación 90 grados)
            px = -uy
            py = ux
        else:
            px, py = 0, 1

        # Elegir la dirección perpendicular que apunte hacia la portería rival
        # o hacia el espacio más libre
        porteria_x = SCREEN_WIDTH if es_local else 0
        porteria_y = SCREEN_HEIGHT / 2
        dir_porteria = math.atan2(porteria_y - poseedor.y, porteria_x - poseedor.x)

        # Calcular ángulo del vector perpendicular
        ang_perp = math.atan2(py, px)
        # Calcular ángulo hacia la portería
        ang_porteria = math.atan2(porteria_y - poseedor.y, porteria_x - poseedor.x)

        # Elegir la perpendicular que más se acerque a la dirección de la portería
        diff1 = abs(ang_perp - ang_porteria)
        diff2 = abs(ang_perp + math.pi - ang_porteria)
        if diff2 < diff1:
            # Invertir perpendicular
            px = -px
            py = -py
            ang_perp += math.pi

        # Añadir pequeña variación para no ser predecible
        variacion = random.uniform(-0.3, 0.3)
        ang_perp += variacion

        # Calcular destino: desde el poseedor en la dirección perpendicular
        destino_x = poseedor.x + math.cos(ang_perp) * distancia_vertice
        destino_y = poseedor.y + math.sin(ang_perp) * distancia_vertice

        # Asegurar que el destino no esté demasiado cerca de la portería rival
        # (evitar offside o posiciones muy adelantadas)
        if es_local and destino_x > SCREEN_WIDTH * 0.9:
            destino_x = SCREEN_WIDTH * 0.85
        elif not es_local and destino_x < SCREEN_WIDTH * 0.1:
            destino_x = SCREEN_WIDTH * 0.15

        return (destino_x, destino_y)
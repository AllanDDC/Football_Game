# backend/build_up/base.py
"""
Clase base para todas las estrategias ofensivas de construcción de juego.
Define la interfaz común y proporciona utilidades auxiliares.
"""

from ..physics import mover_hacia, distancia_objetos
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS


class EstrategiaOfensiva:
    """
    Clase base para estrategias ofensivas (desmarques, triangulaciones, etc.).
    Cada estrategia debe implementar el método `ejecutar`.
    """

    def ejecutar(self, jug, contexto):
        """
        Calcula un destino (x, y) para el jugador según la estrategia.

        :param jug: Jugador al que se aplica la estrategia.
        :param contexto: Diccionario con:
            - 'poseedor': Jugador que tiene el balón (o None).
            - 'pelota': Objeto Pelota.
            - 'equipo': Equipo al que pertenece el jugador.
            - 'equipo_rival': Equipo contrario.
            - 'dt': Delta time.
            - 'get_velocidad': Función que retorna la velocidad efectiva (jug, factor, sprint).
            - 'es_local': Booleano indicando si el equipo es local.
        :return: Tupla (destino_x, destino_y) o None si no aplica.
        """
        raise NotImplementedError

    # ------------------------------------------------------------
    #  Métodos auxiliares para las estrategias
    # ------------------------------------------------------------
    def _mover_hacia(self, jug, destino_x, destino_y, contexto):
        """
        Aplica movimiento al jugador hacia el destino usando la velocidad del contexto.
        Retorna True si se movió, False si ya está en el destino.
        """
        get_velocidad = contexto.get('get_velocidad')
        dt = contexto.get('dt', 0.016)
        if get_velocidad is None:
            return False

        # Obtener velocidad efectiva (factor base 0.7, sin sprint por defecto)
        velocidad = get_velocidad(jug, factor=0.7, sprint=False)

        # Crear objeto destino
        destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})

        # Calcular distancia para evitar movimientos innecesarios
        dist = distancia_objetos(jug, destino)
        if dist < 5:
            # Si ya está muy cerca, detener
            jug.establecer_velocidad(0, 0)
            jug.actualizar(dt)
            return True

        # Mover hacia el destino
        vx, vy = mover_hacia(jug, destino, velocidad, dt)
        jug.establecer_velocidad(vx, vy)
        jug.actualizar(dt)
        return True

    def _limitar_campo(self, x, y, radio=PLAYER_RADIUS):
        """Limita una coordenada dentro del campo."""
        x = max(radio, min(SCREEN_WIDTH - radio, x))
        y = max(radio, min(SCREEN_HEIGHT - radio, y))
        return x, y

    def _angulo_entre(self, origen, destino):
        """Calcula el ángulo (en radianes) desde origen hacia destino."""
        import math
        return math.atan2(destino.y - origen.y, destino.x - origen.x)
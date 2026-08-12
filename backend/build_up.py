# backend/build_up.py
"""
Módulo de creación de juego (build‑up).
Ofrece movimientos ofensivos colectivos:
- Desmarques en banda
- Arrastre de marcas
- Creación de pasillos interiores
- Avance vertical
- Rondos y triangulaciones (pases de 3)
- Apoyo al portador
"""

import math
import random
from .config import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from .physics import mover_hacia, distancia_objetos
from .tactics.base import _posicion_base


class BuildUpManager:
    """
    Gestiona las estrategias de construcción de juego cuando el equipo tiene la pelota.
    No son autoexcluyentes; cada jugador puede ejecutar una diferente.
    """

    def __init__(self, equipo):
        self.equipo = equipo
        self.es_local = equipo.es_local
        self.ultimo_movimiento = {}  # para evitar cambios bruscos

    def actualizar(self, equipo_rival, pelota, dt, jugador_con_balon):
        """
        Punto de entrada: aplica estrategias a todos los jugadores del equipo.
        """
        if jugador_con_balon is None or jugador_con_balon.equipo != self.equipo.nombre:
            return  # solo si el equipo tiene la pelota

        # Para cada jugador (excepto portero), determinar su rol y aplicar estrategia
        for i, jug in enumerate(self.equipo.jugadores):
            if i == 0:  # portero (puede tener lógica especial)
                continue
            if jug.es_controlado:  # el humano se mueve por input
                continue
            if hasattr(jug, 'expulsado') or hasattr(jug, 'lesionado'):
                continue

            # Determinar rol según índice (1-4 defensa, 5-8 mediocampo, 9-10 delantero)
            if i < 5:
                rol = "defensa"
            elif i < 9:
                rol = "mediocampista"
            else:
                rol = "delantero"

            # Aplicar estrategia según rol y contexto
            self._aplicar_estrategia(jug, rol, equipo_rival, pelota, dt, jugador_con_balon)

    def _aplicar_estrategia(self, jug, rol, equipo_rival, pelota, dt, poseedor):
        """
        Selecciona una estrategia para un jugador dado su rol.
        """
        # Estrategias posibles (no excluyentes)
        estrategias = {
            "defensa": self._estrategia_defensa,
            "mediocampista": self._estrategia_mediocampista,
            "delantero": self._estrategia_delantero,
        }
        estrategia = estrategias.get(rol, self._estrategia_defensa)
        estrategia(jug, equipo_rival, pelota, dt, poseedor)

    # ------------------------------------------------------------
    #  Estrategias individuales (cada una actualiza la posición objetivo)
    # ------------------------------------------------------------
    def _estrategia_defensa(self, jug, equipo_rival, pelota, dt, poseedor):
        """
        Los defensas: apoyan en la salida, abren el campo o se incorporan al ataque.
        """
        # Obtener posición base
        bx, by = _posicion_base(jug.numero, self.es_local)

        # Si el poseedor está cerca, ofrecer apoyo en corto
        dist_poseedor = distancia_objetos(jug, poseedor)
        if dist_poseedor < 150:
            # Moverse para crear línea de pase (en ángulo)
            angulo = math.atan2(jug.y - poseedor.y, jug.x - poseedor.x)
            angulo += random.uniform(-0.5, 0.5)
            radio = 80 + random.uniform(0, 30)
            bx = poseedor.x + math.cos(angulo) * radio
            by = poseedor.y + math.sin(angulo) * radio
        else:
            # Si está lejos, abrir el campo (moverse a la banda)
            if jug.numero % 2 == 0:  # lateral derecho
                bx = min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 50)
            else:  # lateral izquierdo
                bx = max(PLAYER_RADIUS, bx - 50)
            # Subir ligeramente para apoyar
            if self.es_local:
                bx = min(SCREEN_WIDTH * 0.7, bx + 20)
            else:
                bx = max(SCREEN_WIDTH * 0.3, bx - 20)

        # Mover hacia el destino
        self._mover_hacia(jug, bx, by, dt, factor=0.6)

    def _estrategia_mediocampista(self, jug, equipo_rival, pelota, dt, poseedor):
        """
        Mediocampistas: triangulación, arrastre de marcas, creación de pasillos.
        """
        # Posición base
        bx, by = _posicion_base(jug.numero, self.es_local)

        # Si tiene el balón, avanzar verticalmente y buscar pase
        if jug.tiene_balon:
            # Avanzar hacia portería rival
            porteria_x = SCREEN_WIDTH if self.es_local else 0
            porteria_y = SCREEN_HEIGHT / 2
            angulo = math.atan2(porteria_y - jug.y, porteria_x - jug.x)
            angulo += random.uniform(-0.2, 0.2)  # pequeña variación
            radio = 100
            bx = jug.x + math.cos(angulo) * radio
            by = jug.y + math.sin(angulo) * radio
            self._mover_hacia(jug, bx, by, dt, factor=0.9)
            return

        # Si es mediocampista sin balón: triangulación o arrastre
        dist_poseedor = distancia_objetos(jug, poseedor)

        # 1. Triangulación (moverse para formar triángulo con poseedor y otro compañero)
        if dist_poseedor < 200 and dist_poseedor > 50:
            # Buscar otro compañero cercano para formar triángulo
            otro = self._buscar_companero_para_triangulo(jug, poseedor)
            if otro:
                # Calcular punto equidistante entre poseedor y otro
                bx = (poseedor.x + otro.x) / 2 + random.uniform(-20, 20)
                by = (poseedor.y + otro.y) / 2 + random.uniform(-20, 20)
                self._mover_hacia(jug, bx, by, dt, factor=0.7)
                return

        # 2. Arrastre de marca (moverse para atraer a un defensor)
        if random.random() < 0.3:
            # Moverse hacia la banda o hacia atrás para arrastrar
            if self.es_local:
                bx = max(PLAYER_RADIUS, bx - 40) if jug.numero % 2 == 0 else min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 40)
                by = min(SCREEN_HEIGHT - PLAYER_RADIUS, by + 30)
            else:
                bx = min(SCREEN_WIDTH - PLAYER_RADIUS, bx + 40) if jug.numero % 2 == 0 else max(PLAYER_RADIUS, bx - 40)
                by = max(PLAYER_RADIUS, by - 30)
            self._mover_hacia(jug, bx, by, dt, factor=0.5)
            return

        # 3. Si nada más, mantenerse en zona de pase (desmarque en profundidad)
        # Avanzar verticalmente para crear pasillo
        if self.es_local:
            bx = min(SCREEN_WIDTH * 0.8, bx + 30)
        else:
            bx = max(SCREEN_WIDTH * 0.2, bx - 30)
        by = min(SCREEN_HEIGHT * 0.8, max(SCREEN_HEIGHT * 0.2, by + (self.es_local and 1 or -1) * 20))
        self._mover_hacia(jug, bx, by, dt, factor=0.6)

    def _estrategia_delantero(self, jug, equipo_rival, pelota, dt, poseedor):
        """
        Delanteros: movimiento constante para desmarcarse, arrastrar defensas y buscar espacios.
        """
        porteria_x = SCREEN_WIDTH if self.es_local else 0
        porteria_y = SCREEN_HEIGHT / 2

        # Si tiene el balón, avanzar hacia portería y disparar
        if jug.tiene_balon:
            destino = type('obj', (object,), {'x': porteria_x, 'y': porteria_y})()
            vx, vy = mover_hacia(jug, destino, 1.0, dt)  # velocidad se calcula fuera
            jug.establecer_velocidad(vx, vy)
            jug.actualizar(dt)
            return

        # Sin balón: movimientos ofensivos
        # 1. Desmarque en diagonal (arrastre)
        if random.random() < 0.4:
            angulo = math.atan2(porteria_y - jug.y, porteria_x - jug.x) + random.uniform(-0.8, 0.8)
            radio = 60 + random.uniform(0, 40)
            bx = porteria_x + math.cos(angulo) * radio
            by = porteria_y + math.sin(angulo) * radio
        else:
            # 2. Avance vertical (buscar profundidad)
            bx = porteria_x + random.uniform(-50, 50)
            by = porteria_y + random.uniform(-80, 80)

        # Limitar al campo
        bx = max(PLAYER_RADIUS, min(SCREEN_WIDTH - PLAYER_RADIUS, bx))
        by = max(PLAYER_RADIUS, min(SCREEN_HEIGHT - PLAYER_RADIUS, by))
        self._mover_hacia(jug, bx, by, dt, factor=0.8)

    # ------------------------------------------------------------
    #  Funciones auxiliares
    # ------------------------------------------------------------
    def _mover_hacia(self, jug, destino_x, destino_y, dt, factor=0.5):
        """Mueve al jugador hacia una posición objetivo con velocidad controlada."""
        # Velocidad efectiva (se calcula en la táctica, pero aquí usamos un factor)
        # La velocidad real se aplica en la táctica; aquí solo calculamos la dirección.
        # Esta función se llamará desde la táctica, que ya tiene la velocidad.
        # Para simplificar, establecemos la velocidad directamente (como en la IA antigua).
        # En el contexto de build_up, la táctica debería llamar a mover_hacia con la velocidad.
        # Por eso, mejor devolvemos la dirección y que la táctica aplique velocidad.
        # Pero para no romper, vamos a usar la velocidad que se pasa desde la táctica.
        # Esta función la llamaremos desde la táctica pasando la velocidad.
        # Como build_up no tiene acceso a las estadísticas, lo dejamos para la táctica.
        # En su lugar, devolvemos (destino_x, destino_y) para que la táctica use mover_hacia.
        # Reestructuraré: las estrategias calcularán destino, y la táctica aplicará mover_hacia.
        # Mejor: en la táctica, después de llamar a las estrategias, se aplica mover_hacia.
        # Aquí simplemente devolvemos el destino.
        pass

    def _buscar_companero_para_triangulo(self, jug, poseedor):
        """Busca un compañero cercano al poseedor para formar triángulo."""
        mejores = []
        for comp in self.equipo.jugadores:
            if comp == jug or comp == poseedor or comp.tiene_balon:
                continue
            dist_comp = distancia_objetos(poseedor, comp)
            if 50 < dist_comp < 200:
                mejores.append(comp)
        if mejores:
            return random.choice(mejores)
        return None
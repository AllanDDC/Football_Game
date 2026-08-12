# backend/build_up/manager.py
"""
Orquestador de construcción de juego ofensiva.
Selecciona y aplica estrategias de movimiento a los jugadores
cuando su equipo tiene la pelota.
"""

import random
from ..physics import mover_hacia, distancia_objetos
from ..ai import decidir_sprint
from .bandas import EstrategiaBandas
from .arrastre import EstrategiaArrastre
from .pasillos import EstrategiaPasillos
from .avance_vertical import EstrategiaAvanceVertical
from .rondos import EstrategiaRondos
from .triangulacion import EstrategiaTriangulacion


class BuildUpManager:
    """
    Gestiona la construcción de juego ofensiva.
    Aplica estrategias no excluyentes según el rol del jugador.
    """

    def __init__(self, equipo):
        """
        :param equipo: Equipo al que pertenecen los jugadores.
        """
        self.equipo = equipo
        self.es_local = equipo.es_local

        # Mapeo de roles a listas de estrategias (orden de prioridad)
        self.estrategias_por_rol = {
            "defensa": [
                EstrategiaBandas(),        # apertura en banda
                EstrategiaRondos(),        # rondos en zona defensiva
                EstrategiaArrastre(),      # arrastre de marcas
            ],
            "mediocampista": [
                EstrategiaTriangulacion(), # pases de 3
                EstrategiaPasillos(),      # creación de pasillos
                EstrategiaRondos(),        # rondos
                EstrategiaArrastre(),      # arrastre
                EstrategiaAvanceVertical(),# proyección ofensiva
                EstrategiaBandas(),        # apertura en banda
            ],
            "delantero": [
                EstrategiaAvanceVertical(),# profundidad
                EstrategiaPasillos(),      # entre líneas
                EstrategiaArrastre(),      # arrastre
                EstrategiaBandas(),        # apertura en banda
            ],
        }

        # Para evitar que siempre se ejecute la misma estrategia,
        # guardamos un contador de turnos por jugador.
        self.contador_estrategias = {}

    def actualizar(self, equipo_rival, pelota, dt, poseedor, get_velocidad):
        """
        Aplica estrategias ofensivas a todos los jugadores del equipo.

        :param equipo_rival: Equipo contrario.
        :param pelota: Objeto Pelota.
        :param dt: Delta time.
        :param poseedor: Jugador que tiene el balón (o None).
        :param get_velocidad: Función (jug, factor, sprint) -> velocidad.
        """
        if poseedor is None or poseedor.equipo != self.equipo.nombre:
            # Si no hay poseedor o no es de nuestro equipo, no hacer nada.
            return

        # Procesar cada jugador (excepto portero y el controlado por humano)
        for jug in self.equipo.jugadores:
            if jug.numero == 0:  # portero
                continue
            if jug.es_controlado:  # jugador humano
                continue
            if hasattr(jug, 'expulsado') and jug.expulsado:
                continue
            if hasattr(jug, 'lesionado') and jug.lesionado:
                continue

            # Determinar rol según índice
            if jug.numero < 5:
                rol = "defensa"
            elif jug.numero < 9:
                rol = "mediocampista"
            else:
                rol = "delantero"

            # Obtener lista de estrategias para este rol
            estrategias = self.estrategias_por_rol.get(rol, [])

            # Obtener el índice de estrategia actual para este jugador (rotación)
            idx = self.contador_estrategias.get(jug, 0)
            # Intentar aplicar estrategias en orden rotativo
            for _ in range(len(estrategias)):
                estrategia = estrategias[idx % len(estrategias)]
                # Preparar contexto
                contexto = {
                    'poseedor': poseedor,
                    'pelota': pelota,
                    'equipo': self.equipo,
                    'equipo_rival': equipo_rival,
                    'dt': dt,
                    'get_velocidad': get_velocidad,
                    'es_local': self.es_local,
                }
                # Ejecutar estrategia
                destino = estrategia.ejecutar(jug, contexto)
                if destino is not None:
                    # Si la estrategia devuelve un destino, aplicarlo
                    destino_x, destino_y = destino
                    self._mover_jugador(jug, destino_x, destino_y, dt, get_velocidad, poseedor, pelota, equipo_rival)
                    # Avanzar el contador para la próxima vez
                    self.contador_estrategias[jug] = (idx + 1) % len(estrategias)
                    break
                # Si no se aplicó, probar la siguiente estrategia (rotar)
                idx = (idx + 1) % len(estrategias)
            else:
                # Si ninguna estrategia dio destino, no hacer nada
                pass

    def _mover_jugador(self, jug, destino_x, destino_y, dt, get_velocidad, poseedor, pelota, equipo_rival):
        """
        Aplica movimiento al jugador hacia el destino, decidiendo si sprintar.
        """
        # Decidir si debe sprintar en función del contexto
        sprint = decidir_sprint(jug, poseedor, pelota, self.equipo, equipo_rival)

        # Obtener velocidad efectiva
        factor_base = 0.7
        # Si es delantero o extremo, un poco más rápido
        if jug.numero >= 9:
            factor_base = 0.8
        elif jug.numero < 5:
            factor_base = 0.6

        velocidad = get_velocidad(jug, factor=factor_base, sprint=sprint)

        # Crear objeto destino
        destino = type('obj', (object,), {'x': destino_x, 'y': destino_y})

        # Si ya está muy cerca, detener
        if distancia_objetos(jug, destino) < 5:
            jug.establecer_velocidad(0, 0)
            jug.actualizar(dt)
            return

        # Mover hacia el destino
        vx, vy = mover_hacia(jug, destino, velocidad, dt)
        jug.establecer_velocidad(vx, vy)
        jug.actualizar(dt)
# backend/entities.py
import math
from .config import (
    PLAYER_RADIUS,
    BALL_RADIUS,
    PLAYER_SPEED,
    BALL_FRICTION,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    AI_CHASE_DISTANCE
)


class Jugador:
    """Representa a un jugador en el campo (círculo)."""

    def __init__(self, x, y, equipo_nombre, es_controlado=False, numero=0):
        self.x = x
        self.y = y
        self.radio = PLAYER_RADIUS
        self.equipo = equipo_nombre
        self.es_controlado = es_controlado
        self.numero = numero
        self.vx = 0.0
        self.vy = 0.0
        self.velocidad_max = PLAYER_SPEED
        self.tiene_balon = False
        self.sprint = False  # Para control de fatiga extra

    def mover(self, dx, dy, velocidad, sprint=False):
        """
        Establece la velocidad del jugador a partir de la dirección deseada.
        Si sprint es True, se activa el modo sprint para consumo de stamina.
        """
        self.sprint = sprint
        if dx == 0 and dy == 0:
            self.vx = 0.0
            self.vy = 0.0
            return
        longitud = math.hypot(dx, dy)
        self.vx = (dx / longitud) * velocidad
        self.vy = (dy / longitud) * velocidad

    def establecer_velocidad(self, vx, vy):
        """Usado por la IA para asignar velocidad directamente."""
        self.vx = vx
        self.vy = vy

    def actualizar(self, dt):
        """Actualiza la posición aplicando la velocidad y los límites del campo."""
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Rebote / contención en los bordes de la pantalla
        self.x = max(self.radio, min(SCREEN_WIDTH - self.radio, self.x))
        self.y = max(self.radio, min(SCREEN_HEIGHT - self.radio, self.y))

    def distancia_a(self, otro):
        """Calcula la distancia euclidiana a otro objeto (jugador o pelota)."""
        return math.hypot(self.x - otro.x, self.y - otro.y)

    def recoger_balon(self, pelota):
        """Adhiere la pelota a este jugador."""
        pelota.dueno = self
        pelota.pegada = True
        self.tiene_balon = True

    def lanzar_balon(self, pelota, fuerza_x=0, fuerza_y=-400):
        """
        Despega la pelota del jugador y le aplica una velocidad inicial.
        Por defecto lanza hacia arriba (frente al jugador).
        """
        if self.tiene_balon and pelota.dueno == self:
            pelota.dueno = None
            pelota.pegada = False
            self.tiene_balon = False
            pelota.vx = fuerza_x
            pelota.vy = fuerza_y


class Pelota:
    """Representa el balón (círculo más pequeño)."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radio = BALL_RADIUS
        self.vx = 0.0
        self.vy = 0.0
        self.dueno = None      # Referencia al Jugador que la tiene pegada
        self.pegada = True     # True si está adherida a un jugador

    def actualizar(self, dt):
        """
        Actualiza la posición de la pelota.
        Si está pegada, sigue al dueño.
        Si está libre, aplica rozamiento y rebotes.
        """
        if self.pegada and self.dueno is not None:
            # La pelota se coloca justo delante del jugador (hacia arriba en Y)
            self.x = self.dueno.x
            self.y = self.dueno.y - self.dueno.radio - self.radio - 4
            return

        # Si está libre, aplicamos física
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Rozamiento (fricción)
        self.vx *= (1 - BALL_FRICTION * dt)
        self.vy *= (1 - BALL_FRICTION * dt)
        if abs(self.vx) < 0.5:
            self.vx = 0.0
        if abs(self.vy) < 0.5:
            self.vy = 0.0

        # Rebotes en los bordes
        if self.x - self.radio < 0:
            self.x = self.radio
            self.vx = abs(self.vx) * 0.6
        elif self.x + self.radio > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radio
            self.vx = -abs(self.vx) * 0.6

        if self.y - self.radio < 0:
            self.y = self.radio
            self.vy = abs(self.vy) * 0.6
        elif self.y + self.radio > SCREEN_HEIGHT:
            self.y = SCREEN_HEIGHT - self.radio
            self.vy = -abs(self.vy) * 0.6

    def soltar(self, vx=0, vy=0):
        """Despega la pelota manualmente (usado por eventos externos)."""
        self.dueno = None
        self.pegada = False
        self.vx = vx
        self.vy = vy


class Equipo:
    """Contiene un grupo de jugadores y su información colectiva."""

    def __init__(self, nombre, color, lado, es_local=False):
        self.nombre = nombre        # ej. "Local", "Visitante"
        self.color = color          # tupla (R, G, B)
        self.lado = lado            # 'left' o 'right'
        self.es_local = es_local
        self.jugadores = []

    def agregar_jugador(self, jugador):
        """Añade un jugador al equipo y asigna su equipo."""
        jugador.equipo = self.nombre
        self.jugadores.append(jugador)

    def obtener_jugadores(self):
        """Devuelve la lista de jugadores."""
        return self.jugadores

    def obtener_portero(self):
        """Devuelve el primer jugador (o el que tenga número 1) como portero."""
        for jug in self.jugadores:
            if jug.numero == 1:
                return jug
        return self.jugadores[0] if self.jugadores else None

    def obtener_jugador_con_balon(self):
        """Retorna el jugador de este equipo que tenga el balón, o None."""
        for jug in self.jugadores:
            if jug.tiene_balon:
                return jug
        return None
# backend/match_events.py
"""
Módulo para la gestión de eventos del partido (goles, tarjetas, lesiones, sustituciones, etc.).
Define clases para representar eventos y almacenar el historial.
"""

import time

class EventoPartido:
    """
    Representa un evento ocurrido durante el partido.
    """
    def __init__(self, tipo, jugador1=None, jugador2=None, descripcion=""):
        self.tipo = tipo          # 'GOL', 'PASE', 'REGATE', 'ROBO', 'TARJETA_AMARILLA', 'TARJETA_ROJA', 'LESION', 'SUSTITUCION', etc.
        self.jugador1 = jugador1  # Jugador principal involucrado
        self.jugador2 = jugador2  # Jugador secundario (opcional)
        self.descripcion = descripcion
        self.timestamp = time.time()

    def __str__(self):
        return f"[{self.tipo}] {self.jugador1} {self.descripcion}"


class Tarjeta:
    """
    Representa una tarjeta (amarilla o roja) mostrada a un jugador.
    """
    def __init__(self, jugador, tipo, minuto):
        self.jugador = jugador
        self.tipo = tipo          # 'amarilla' o 'roja'
        self.minuto = minuto      # minuto del partido
        self.timestamp = time.time()

    def __str__(self):
        return f"Tarjeta {self.tipo.upper()} para {self.jugador} en minuto {self.minuto}"


class Lesion:
    """
    Representa una lesión de un jugador.
    """
    def __init__(self, jugador, grave, minuto):
        self.jugador = jugador
        self.grave = grave        # True si es grave, False si es menor
        self.minuto = minuto
        self.timestamp = time.time()

    def __str__(self):
        return f"Lesión {'grave' if self.grave else 'menor'} de {self.jugador} en minuto {self.minuto}"


class MatchEvents:
    """
    Almacena y gestiona el historial de eventos del partido.
    """
    def __init__(self):
        self.eventos = []

    def registrar_evento(self, evento):
        """Agrega un evento al historial."""
        self.eventos.append(evento)

    def obtener_eventos(self):
        """Devuelve la lista de eventos registrados."""
        return self.eventos

    def obtener_eventos_recientes(self, cantidad=10):
        """Devuelve los últimos N eventos."""
        return self.eventos[-cantidad:]

    def obtener_eventos_por_tipo(self, tipo):
        """Devuelve los eventos que coinciden con un tipo dado."""
        return [e for e in self.eventos if e.tipo == tipo]

    def limpiar(self):
        """Limpia el historial de eventos."""
        self.eventos.clear()

    def __str__(self):
        return f"MatchEvents (total: {len(self.eventos)})"
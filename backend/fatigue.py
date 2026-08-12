# backend/fatigue.py
"""
Módulo encargado de gestionar la fatiga (cansancio) de los jugadores.
Proporciona funciones para calcular el incremento de fatiga, la recuperación,
y el factor de penalización que se aplica a las estadísticas.
"""

from .config import FATIGUE_RATE, FATIGUE_THRESHOLD


# ------------------------------------------------------------
#  Funciones de cálculo de fatiga
# ------------------------------------------------------------
def calcular_incremento_fatiga(velocidad_actual, dt, velocidad_maxima=300):
    """
    Calcula cuánto aumenta la fatiga en un intervalo de tiempo dado.

    :param velocidad_actual: Velocidad a la que se mueve el jugador (píxeles/segundo)
    :param dt: Intervalo de tiempo en segundos
    :param velocidad_maxima: Velocidad máxima del jugador (para normalizar)
    :return: Incremento de fatiga (puntos, escala 0-100)
    """
    # Si la velocidad es muy baja, no se cansa
    if velocidad_actual < 50:
        return 0.0

    # Normalizar la velocidad respecto a la máxima (0-1)
    factor_velocidad = min(1.0, velocidad_actual / velocidad_maxima)

    # El incremento base es FATIGUE_RATE por segundo a velocidad máxima
    incremento = factor_velocidad * FATIGUE_RATE * dt

    return incremento


def calcular_factor_fatiga(fatiga_actual):
    """
    Calcula el factor de penalización que se aplica a las estadísticas
    según el nivel de fatiga.

    :param fatiga_actual: Nivel de fatiga (0-100)
    :return: Factor multiplicador (1.0 = sin penalización, 0.3 = máximo penalización)
    """
    if fatiga_actual <= FATIGUE_THRESHOLD:
        return 1.0  # Sin penalización

    # Penalización lineal desde el umbral hasta 100
    # Cuando fatiga=100, factor=0.3
    rango = 100 - FATIGUE_THRESHOLD
    if rango <= 0:
        return 1.0

    factor = 1.0 - (fatiga_actual - FATIGUE_THRESHOLD) / rango * 0.7
    return max(0.3, factor)  # Nunca baja de 0.3


def recuperar_fatiga(fatiga_actual, dt, tasa_recuperacion=10.0):
    """
    Reduce la fatiga con el tiempo (descanso).

    :param fatiga_actual: Nivel de fatiga actual
    :param dt: Tiempo de descanso en segundos
    :param tasa_recuperacion: Puntos de fatiga recuperados por segundo
    :return: Nuevo nivel de fatiga
    """
    nueva_fatiga = fatiga_actual - tasa_recuperacion * dt
    return max(0.0, nueva_fatiga)


# ------------------------------------------------------------
#  Clase opcional para gestionar la fatiga de un jugador
# ------------------------------------------------------------
class FatigueManager:
    """
    Gestiona el estado de fatiga de un jugador individual.
    Encapsula el valor actual y proporciona métodos para actualizarlo.
    """

    def __init__(self, fatiga_inicial=0.0):
        self.fatiga = fatiga_inicial

    def aplicar_esfuerzo(self, velocidad_actual, dt, velocidad_maxima=300):
        """
        Aplica el cansancio por correr.
        """
        incremento = calcular_incremento_fatiga(velocidad_actual, dt, velocidad_maxima)
        self.fatiga = min(100.0, self.fatiga + incremento)
        return self.fatiga

    def descansar(self, dt, tasa_recuperacion=10.0):
        """
        Recupera fatiga durante el descanso.
        """
        self.fatiga = recuperar_fatiga(self.fatiga, dt, tasa_recuperacion)
        return self.fatiga

    def obtener_factor(self):
        """
        Devuelve el factor de penalización actual.
        """
        return calcular_factor_fatiga(self.fatiga)

    def reiniciar(self):
        """Reinicia la fatiga a cero."""
        self.fatiga = 0.0

    def __str__(self):
        return f"Fatiga: {self.fatiga:.1f}% (factor: {self.obtener_factor():.2f})"


# ------------------------------------------------------------
#  Ejemplo de uso (para pruebas)
# ------------------------------------------------------------
if __name__ == "__main__":
    # Prueba rápida
    fm = FatigueManager()
    print(fm)
    # Simular 2 segundos de carrera a velocidad máxima
    fm.aplicar_esfuerzo(300, 2.0)
    print(fm)
    # Descansar 1 segundo
    fm.descansar(1.0)
    print(fm) 
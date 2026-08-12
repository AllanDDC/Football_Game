# backend/player_stats.py
"""
Módulo de estadísticas de jugadores.
Gestiona habilidades, experiencia, cansancio, edad, y cálculos de rendimiento.
Incluye recuperación pasiva de fatiga cuando el jugador se mueve poco,
y consumo extra de stamina durante el sprint.
"""

import math
import random
from .config import DEFAULT_STATS, FATIGUE_RATE, FATIGUE_THRESHOLD


class PlayerStats:
    """
    Gestiona las estadísticas individuales de un jugador:
    - Habilidades base (velocidad, resistencia, pase, regate, robo, tiro)
    - Experiencia (XP) y nivel
    - Cansancio (fatiga) que afecta al rendimiento
    - Edad (para simular decadencia)
    - Contadores de acciones para XP post-partido
    """

    def __init__(self, nombre="", edad=20, stats_override=None):
        """
        :param nombre: Nombre del jugador (opcional)
        :param edad: Edad en años (afecta a la decadencia)
        :param stats_override: Diccionario con valores personalizados para las stats
        """
        self.nombre = nombre
        self.edad = edad
        self.nivel = 1
        self.xp = 0
        self.xp_para_subir = 100  # XP necesaria para subir de nivel

        # Estadísticas base (escala 0-100)
        self.stats_base = DEFAULT_STATS.copy()
        if stats_override:
            self.stats_base.update(stats_override)

        # Cansancio acumulado (0 = descansado, 100 = agotado)
        self.fatiga = 0.0

        # Contadores de acciones (para otorgar XP al final del partido)
        self.contador_pases = 0
        self.contador_pases_fallidos = 0
        self.contador_regates = 0
        self.contador_regates_fallidos = 0
        self.contador_robos = 0
        self.contador_tiros = 0
        self.contador_goles = 0
        self.distancia_recorrida = 0.0  # en píxeles

        # Para simular la "fecha de vencimiento": a partir de cierta edad, las stats bajan
        self.edad_decadencia = 32  # a partir de esta edad empieza a bajar

        # Para lesiones temporales (afectan rendimiento)
        self.lesion_temporal = False
        self.lesion_tiempo = 0.0

    # ------------------------------------------------------------
    #  Propiedades para obtener estadísticas efectivas (con fatiga, edad, nivel)
    # ------------------------------------------------------------
    @property
    def velocidad(self):
        return self._stat_efectiva("velocidad")

    @property
    def resistencia(self):
        return self._stat_efectiva("resistencia")

    @property
    def pase(self):
        return self._stat_efectiva("pase")

    @property
    def regate(self):
        return self._stat_efectiva("regate")

    @property
    def robo(self):
        return self._stat_efectiva("robo")

    @property
    def tiro(self):
        return self._stat_efectiva("tiro")

    def _stat_efectiva(self, stat_name):
        """Aplica el efecto del cansancio, edad, nivel y lesiones a una estadística."""
        base = self.stats_base[stat_name]

        # 1. Efecto del cansancio (fatiga) - gradual
        # Si fatiga=0, factor=1.0; si fatiga=100, factor=0.3
        factor_fatiga = 1.0 - (self.fatiga / 100.0) * 0.7
        factor_fatiga = max(0.3, factor_fatiga)

        # 2. Efecto de la edad (decadencia)
        if self.edad > self.edad_decadencia:
            anos_decadencia = self.edad - self.edad_decadencia
            factor_edad = 1.0 - (anos_decadencia * 0.02)  # 2% por año
            factor_edad = max(0.5, factor_edad)
        else:
            factor_edad = 1.0

        # 3. Efecto del nivel (bonificación)
        factor_nivel = 1.0 + (self.nivel - 1) * 0.02  # +2% por nivel

        # 4. Efecto de lesión temporal (reduce un 30%)
        factor_lesion = 0.7 if self.lesion_temporal else 1.0

        # Estadística efectiva = base * factores
        efectiva = base * factor_fatiga * factor_edad * factor_nivel * factor_lesion
        # Limitar entre 0 y 100
        return max(0, min(100, efectiva))

    # ------------------------------------------------------------
    #  Métodos para registrar acciones (se llaman desde el juego)
    # ------------------------------------------------------------
    def registrar_pase(self, exitoso=True):
        if exitoso:
            self.contador_pases += 1
        else:
            self.contador_pases_fallidos += 1

    def registrar_regate(self, exitoso=True):
        if exitoso:
            self.contador_regates += 1
        else:
            self.contador_regates_fallidos += 1

    def registrar_robo(self):
        self.contador_robos += 1

    def registrar_tiro(self, es_gol=False):
        self.contador_tiros += 1
        if es_gol:
            self.contador_goles += 1

    def registrar_distancia(self, distancia):
        """Distancia recorrida en píxeles (acumulada)."""
        self.distancia_recorrida += distancia

    # ------------------------------------------------------------
    #  Gestión de fatiga (incluye recuperación pasiva y sprint)
    # ------------------------------------------------------------
    def aplicar_cansancio(self, dt, velocidad_actual, sprint=False):
        """
        Incrementa la fatiga según la velocidad actual y si está en sprint.
        Si la velocidad es baja, se recupera pasivamente.
        """
        # Umbral para considerar que está corriendo (más de 30 px/s)
        if velocidad_actual > 30:
            # Incremento base proporcional a la velocidad
            incremento = (velocidad_actual / 300.0) * FATIGUE_RATE * dt
            # Si está en sprint, multiplicar por 1.5 (consumo extra)
            if sprint:
                incremento *= 1.5
            self.fatiga = min(100, self.fatiga + incremento)
        else:
            # Si se mueve poco o está quieto, recupera fatiga (recuperación pasiva)
            self.recuperar_cansancio(dt * 0.5)  # tasa reducida

    def recuperar_cansancio(self, dt, tasa=5.0):
        """
        Recupera fatiga con el tiempo (descanso).
        La tasa por defecto es 5 puntos por segundo.
        """
        self.fatiga = max(0, self.fatiga - tasa * dt)

    # ------------------------------------------------------------
    #  Sistema de experiencia y nivel
    # ------------------------------------------------------------
    def ganar_xp(self, cantidad):
        """Añade XP y sube de nivel si corresponde."""
        self.xp += cantidad
        while self.xp >= self.xp_para_subir:
            self.xp -= self.xp_para_subir
            self.subir_nivel()

    def subir_nivel(self):
        """Sube de nivel y mejora ligeramente todas las estadísticas base."""
        self.nivel += 1
        for stat in self.stats_base:
            self.stats_base[stat] = min(100, self.stats_base[stat] + random.randint(1, 3))
        self.xp_para_subir = int(self.xp_para_subir * 1.2)

    def calcular_xp_partido(self):
        """
        Calcula el XP ganado durante el partido según las acciones realizadas.
        Se llama al final del partido.
        """
        xp = 0
        # Pases exitosos: +2 XP cada uno
        xp += self.contador_pases * 2
        # Pases fallidos: -1 XP (penalización)
        xp -= self.contador_pases_fallidos * 1
        # Regates exitosos: +5 XP
        xp += self.contador_regates * 5
        # Regates fallidos: -2 XP
        xp -= self.contador_regates_fallidos * 2
        # Robos: +4 XP
        xp += self.contador_robos * 4
        # Tiros: +3 XP (gol +10 extra)
        xp += self.contador_tiros * 3
        xp += self.contador_goles * 10
        # Distancia recorrida: +1 XP por cada 100 píxeles
        xp += int(self.distancia_recorrida / 100)

        return max(0, xp)

    def reset_contadores(self):
        """Reinicia los contadores de acciones para el próximo partido."""
        self.contador_pases = 0
        self.contador_pases_fallidos = 0
        self.contador_regates = 0
        self.contador_regates_fallidos = 0
        self.contador_robos = 0
        self.contador_tiros = 0
        self.contador_goles = 0
        self.distancia_recorrida = 0.0

    # ------------------------------------------------------------
    #  Métodos de cálculo de probabilidades (regate, robo, etc.)
    # ------------------------------------------------------------
    def probabilidad_regate(self, defensor_stats):
        """
        Calcula la probabilidad de que este jugador supere a un defensor en un 1vs1.
        Fórmula: (regate_atacante / (regate_atacante + robo_defensor)) * factor_cansancio
        """
        ataque = self.regate
        defensa = defensor_stats.robo
        if ataque + defensa == 0:
            return 0.5
        prob = ataque / (ataque + defensa)
        # Factor de cansancio: si el atacante está muy cansado, reduce la probabilidad
        factor_fatiga = 1.0 - (self.fatiga / 200.0)  # máximo 50% de reducción
        prob *= factor_fatiga
        return max(0.1, min(0.9, prob))

    def probabilidad_robo(self, atacante_stats):
        """
        Probabilidad de que este jugador (defensor) robe el balón al atacante.
        Simétrica a la de regate.
        """
        prob_ataque = atacante_stats.probabilidad_regate(self)
        return 1.0 - prob_ataque

    # ------------------------------------------------------------
    #  Métodos de entrenamiento (para cuando el jugador no juega)
    # ------------------------------------------------------------
    def entrenar(self, horas=1):
        """
        Simula el entrenamiento en segundo plano.
        Cada hora de entrenamiento da XP y puede subir alguna estadística específica.
        """
        xp_ganada = horas * 5
        self.ganar_xp(xp_ganada)
        if random.random() < 0.3 * horas:
            stat = random.choice(list(self.stats_base.keys()))
            incremento = random.randint(1, 2)
            self.stats_base[stat] = min(100, self.stats_base[stat] + incremento)

    # ------------------------------------------------------------
    #  Representación
    # ------------------------------------------------------------
    def __str__(self):
        return (f"{self.nombre} (Niv.{self.nivel}) | Vel:{self.velocidad:.0f} "
                f"Res:{self.resistencia:.0f} Pas:{self.pase:.0f} Reg:{self.regate:.0f} "
                f"Rob:{self.robo:.0f} Tir:{self.tiro:.0f} | Fat:{self.fatiga:.1f}%")
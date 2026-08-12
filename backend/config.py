# backend/config.py
# ============================================================
# Constantes globales del juego
# ============================================================

# --- Ventana ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FULLSCREEN = False          # True para iniciar en pantalla completa (puede cambiarse con F11)

# --- Jugadores ---
PLAYER_RADIUS = 20          # Radio del círculo del jugador
PLAYER_SPEED = 200          # Velocidad base (trote) - reducida para que el sprint sea más significativo
SPRINT_MULTIPLIER = 1.6     # Multiplicador de velocidad al correr (Shift)

# --- Pelota ---
BALL_RADIUS = 8
BALL_FRICTION = 0.98        # Factor de rozamiento (1 = sin fricción)

# --- IA ---
AI_CHASE_DISTANCE = 200     # Distancia a la que los rivales persiguen al poseedor

# --- Porterías ---
GOAL_WIDTH = 80             # Ancho de la portería (no se usa directamente en el código)
GOAL_HEIGHT = 150           # Alto de la portería
GOAL_DEPTH = 30             # Profundidad de la portería (hacia dentro del campo)

# --- Colores (para el renderizado) ---
COLORS = {
    "campo": (34, 139, 34),        # verde césped
    "lineas": (255, 255, 255),     # blanco
    "porteria": (50, 50, 50),      # gris oscuro
    "borde_jugador": (0, 0, 0),    # negro
    "texto": (255, 255, 255),      # blanco
    "balon_indicador": (255, 215, 0),  # dorado
    "pelota": (255, 255, 255),     # blanco
    "borde_pelota": (0, 0, 0),     # negro
    "gol": (255, 215, 0),          # dorado
    "destacado": (255, 255, 0)     # amarillo
}

# --- Estadísticas base (para futuras expansiones) ---
# Valores por defecto para las habilidades de los jugadores (escala 0-100)
DEFAULT_STATS = {
    "velocidad": 70,
    "resistencia": 70,
    "pase": 60,
    "regate": 60,
    "robo": 60,
    "tiro": 60
}

# Factor de cansancio: cada segundo de carrera reduce la resistencia en este valor
FATIGUE_RATE = 0.5          # puntos por segundo

# Umbral de cansancio a partir del cual se reducen las habilidades
FATIGUE_THRESHOLD = 30      # por debajo de este valor, empieza a afectar

# --- Otras configuraciones ---
FPS = 60                    # Fotogramas por segundo objetivo
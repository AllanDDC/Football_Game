# backend/build_up/__init__.py
"""
Módulo de construcción de juego ofensivo (build‑up).
Contiene estrategias para generar movimiento sin balón,
desmarques, triangulaciones, rondos, apertura en banda,
arrastre de marcas, creación de pasillos y avance vertical.
"""

from .manager import BuildUpManager
from .base import EstrategiaOfensiva
from .bandas import EstrategiaBandas
from .arrastre import EstrategiaArrastre
from .pasillos import EstrategiaPasillos
from .avance_vertical import EstrategiaAvanceVertical
from .rondos import EstrategiaRondos
from .triangulacion import EstrategiaTriangulacion

__all__ = [
    'BuildUpManager',
    'EstrategiaOfensiva',
    'EstrategiaBandas',
    'EstrategiaArrastre',
    'EstrategiaPasillos',
    'EstrategiaAvanceVertical',
    'EstrategiaRondos',
    'EstrategiaTriangulacion',
]
# backend/tactics/__init__.py
from .base import TacticaBase, _posicion_base, _get_velocidad_efectiva
from .catenaccio import Catenaccio
from .tiki_taka import TikiTaka
from .presion_alta import PresionAlta
from .contragolpe import Contragolpe
from .total import Total
from .jogo_bonito import JogoBonito
from .bloque_bajo import BloqueBajo

TACTICAS_CLASES = {
    "catenaccio": Catenaccio,
    "tiki_taka": TikiTaka,
    "presion_alta": PresionAlta,
    "contragolpe": Contragolpe,
    "total": Total,
    "jogo_bonito": JogoBonito,
    "bloque_bajo": BloqueBajo,
}
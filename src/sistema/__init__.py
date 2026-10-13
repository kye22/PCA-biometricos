"""Sistema de reconocimiento facial con PCA.

    from sistema import inscribir, verificar, identificar
"""
from .api import (
    identificar,
    identificar_sd,
    identificar_t,
    inscribir,
    inscribir_sd,
    inscribir_t,
    verificar,
    verificar_sd,
    verificar_t,
)

__all__ = [
    "inscribir", "verificar", "identificar",
    "inscribir_sd", "verificar_sd", "identificar_sd",
    "inscribir_t", "verificar_t", "identificar_t",
]

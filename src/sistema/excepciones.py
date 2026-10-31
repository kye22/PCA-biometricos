"""Errores propios del sistema."""


class ErrorSistema(Exception):
    """Base de todos los errores del sistema."""


class CaraNoEncontrada(ErrorSistema):
    """El detector no encuentra ninguna cara en la foto."""


class ModeloNoEntrenado(ErrorSistema):
    """No existe el modelo PCA en disco: ejecutar scripts/entrenar_pca.py."""


class TemplateInvalido(ErrorSistema):
    """El template no tiene la forma o los valores esperados."""


class IdDesconocido(ErrorSistema):
    """El id no está inscrito en la BD."""


class CalidadInsuficiente(ErrorSistema):
    """La foto no sirve para decidir con fiabilidad (varias caras, tapada, girada...)."""

    def __init__(self, motivos: list[str], mensaje: str = ""):
        super().__init__(mensaje or ", ".join(motivos))
        self.motivos = motivos

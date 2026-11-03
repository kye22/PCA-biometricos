"""Clave secreta, cifrado de templates y firmas. Responsable: módulo 5 (seguridad).

Supuesto: el rival tiene el código, el modelo y la BD, pero NO la clave. La clave vive fuera de
git (datos/clave.key, o la variable de entorno SISTEMA_CLAVE en hexadecimal); montar.py la crea
si no existe. De ella se derivan tres subclaves independientes:

- templates: AES-256-GCM por fila, con el id como dato asociado. Sin la clave la BD no se puede
  leer (ni invertir a una cara, ni copiar un template a verificar_t), y una fila no se puede
  mover a otro id ni retocar.
- BD: HMAC-SHA256 del archivo entero (bd.firma). Detecta filas añadidas, borradas o cambiadas.
- modelo: HMAC-SHA256 de pca.npz (incluye el umbral). Detecta un umbral o eigenfaces cambiados.
"""
import base64
import hashlib
import hmac
import os
import secrets
from functools import lru_cache

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config
from .excepciones import ClaveNoEncontrada, Manipulado


def crear_clave() -> bool:
    """Crea la clave si no existe (nunca la sobrescribe). -> True si la ha creado."""
    if os.getenv("SISTEMA_CLAVE") or config.RUTA_CLAVE.exists():
        return False
    config.RUTA_CLAVE.parent.mkdir(parents=True, exist_ok=True)
    config.RUTA_CLAVE.write_text(secrets.token_hex(32), encoding="utf-8")
    return True


@lru_cache(maxsize=1)
def _clave() -> bytes:
    texto = os.getenv("SISTEMA_CLAVE") or (config.RUTA_CLAVE.read_text(encoding="utf-8").strip()
                                           if config.RUTA_CLAVE.exists() else "")
    if not texto:
        raise ClaveNoEncontrada(f"Falta la clave ({config.RUTA_CLAVE} o SISTEMA_CLAVE); ejecuta scripts/montar.py")
    return bytes.fromhex(texto)


def olvidar_clave() -> None:
    _clave.cache_clear()


def _subclave(uso: str) -> bytes:
    return hmac.new(_clave(), uso.encode(), hashlib.sha256).digest()


def firmar(datos: bytes, uso: str) -> str:
    return hmac.new(_subclave(uso), datos, hashlib.sha256).hexdigest()


def comprobar(datos: bytes, firma: str, uso: str, que: str) -> None:
    if not hmac.compare_digest(firmar(datos, uso), firma or ""):
        raise Manipulado(f"{que}: la firma no coincide (modificado o clave distinta)")


def cifrar(id: str, template: np.ndarray) -> str:
    nonce = secrets.token_bytes(12)
    datos = np.asarray(template, np.float32).tobytes()
    return base64.b64encode(nonce + AESGCM(_subclave("templates")).encrypt(nonce, datos, id.encode())).decode()


def descifrar(id: str, texto: str) -> np.ndarray:
    try:
        crudo = base64.b64decode(texto, validate=True)
        datos = AESGCM(_subclave("templates")).decrypt(crudo[:12], crudo[12:], id.encode())
    except (InvalidTag, ValueError) as e:
        raise Manipulado(f"BD: la fila de '{id}' no se puede descifrar (modificada o movida de id)") from e
    return np.frombuffer(datos, np.float32).copy()


def clave_modelo() -> bytes:
    return _subclave("modelo")

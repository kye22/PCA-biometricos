"""Modifica únicamente una COPIA TEMPORAL de la BD y prueba la verificación HMAC.

    python ataques/escritura_bd.py --modo alterar
    python ataques/escritura_bd.py --modo borrar-todo

Nunca altera datos/bd.csv ni datos/bd.firma originales.
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema import bd, config
from sistema.excepciones import Manipulado


def ejecutar(modo: str) -> str:
    original = config.RUTA_BD
    firma_original = original.with_suffix(".firma")
    if not original.is_file() or not firma_original.is_file():
        raise FileNotFoundError("Faltan BD o firma: monta el sistema primero")
    with tempfile.TemporaryDirectory(prefix="ataque-bd-") as carpeta:
        ruta = Path(carpeta) / "bd.csv"
        firma = ruta.with_suffix(".firma")
        shutil.copy2(original, ruta)
        shutil.copy2(firma_original, firma)
        bd.cargar(ruta)  # control de referencia: la copia original debe ser válida
        if modo == "alterar":
            lineas = ruta.read_text(encoding="utf-8").splitlines()
            if len(lineas) < 2:
                raise ValueError("No hay filas para modificar")
            id_, cifrado = lineas[1].split(",", 1)
            lineas[1] = f"atacante_{id_},{cifrado}"
            ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        elif modo == "borrar-todo":
            ruta.unlink()
            firma.unlink()
        else:
            raise ValueError(f"Modo no soportado: {modo}")
        try:
            base = bd.cargar(ruta)
        except Manipulado:
            return "Ataque detectado: la copia no supera la firma HMAC"
        if modo == "borrar-todo" and base == {}:
            return "LIMITACIÓN DETECTADA: eliminar BD y firma produce una BD vacía, sin alarma de manipulación"
        return "AVISO: la copia modificada se ha aceptado; estudiar el comportamiento"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modo", choices=["alterar", "borrar-todo"], default="alterar")
    args = p.parse_args()
    try:
        print(ejecutar(args.modo))
    except (FileNotFoundError, ValueError) as exc:
        p.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()

"""Inspección PASIVA del CSV en el supuesto de lectura sin clave. No revela ciphertext completo.

    python ataques/lectura_bd.py

No llama a descifrar() ni imprime el secreto del disco.
"""
import base64
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema import config


def main() -> None:
    if not config.RUTA_BD.is_file():
        raise SystemExit("No existe bd.csv: ejecuta primero scripts/montar.py")
    with config.RUTA_BD.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    ids = sorted({f["id"] for f in filas})
    print(f"Filas con templates: {len(filas)}; ids visibles en claro: {len(ids)}")
    print("Ejemplo de id visible:", ids[0] if ids else "(ninguno)")
    if filas:
        cifrado = filas[0]["template"]
        try:
            crudo = base64.b64decode(cifrado, validate=True)
            print(f"Campo de template: {len(cifrado)} caracteres base64; {len(crudo)} bytes cifrados")
            print("Sin la clave no se puede obtener directamente el vector PCA desde este campo.")
        except ValueError:
            print("El campo de la primera fila no tiene formato base64 válido")
    print(f"Clave local en la misma máquina: {'sí' if config.RUTA_CLAVE.exists() else 'no'}")
    print("Esta última línea NO demuestra que el atacante pueda leer la clave: depende de sus permisos.")


if __name__ == "__main__":
    main()

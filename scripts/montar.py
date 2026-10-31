"""Monta el sistema completo con un solo comando:

    python scripts/montar.py [--componentes 50] [--far 0.02]

1. Descomprime Dataset.tar.gz (el del profe) en datos/fotos/ si aún no está.
2. Junta esas fotos con las de datos/extra/ (Arbeloa) -> ids a partir del nombre de archivo.
3. Detecta y alinea cada cara; informa de las que fallan.
   Si el id está en datos/ojos_manuales.json se alinea con esos ojos y se inscribe con _sd.
4. Entrena PCA con esas caras (+ sus espejos, para tener más variedad).
5. Inscribe a todos en una BD nueva (datos/bd.csv) con la API normal.
6. Calcula un umbral PROVISIONAL a partir de las distancias entre personas distintas y lo
   guarda dentro del modelo. Ver docs/decisiones.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import argparse
import hashlib
import json

import numpy as np

from sistema import api, bd, comparador, config, dataset, detector, imagen, preprocesado
from sistema.excepciones import CaraNoEncontrada
from sistema.pca import ModeloPCA

RUTA_OJOS_MANUALES = config.RAIZ / "datos" / "ojos_manuales.json"


def preparar_fotos() -> list[tuple[str, object]]:
    if not (config.RUTA_FOTOS.exists() and any(config.RUTA_FOTOS.iterdir())):
        if not config.RUTA_DATASET.exists():
            sys.exit(f"No encuentro {config.RUTA_DATASET}. Ponlo en la raíz del repo.")
        n = dataset.extraer_dataset(config.RUTA_DATASET, config.RUTA_FOTOS)
        print(f"Descomprimido {config.RUTA_DATASET.name}: {n} fotos -> {config.RUTA_FOTOS}")
    fotos = dataset.listar_inscripcion(config.RUTA_FOTOS, config.RUTA_EXTRA)
    ids = [i for i, _ in fotos]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        print(f"Aviso: ids con varias fotos (se inscriben todas): {sorted(repetidos)}")
    return fotos


def ruta_relativa(f) -> str:
    """Relativa a la raíz del repo si se puede (así vale en otro PC o en Docker)."""
    try:
        return f.resolve().relative_to(config.RAIZ).as_posix()
    except ValueError:
        return str(f.resolve())


def ojos_manuales() -> dict:
    if not RUTA_OJOS_MANUALES.exists():
        return {}
    datos = json.loads(RUTA_OJOS_MANUALES.read_text(encoding="utf-8"))
    return {k: v for k, v in datos.items() if not k.startswith("_")}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--componentes", type=int, default=config.N_COMPONENTES)
    p.add_argument("--far", type=float, default=0.02,
                   help="fracción de impostores que se aceptaría con el umbral (por defecto 2%%)")
    args = p.parse_args()

    fotos = preparar_fotos()

    # --- 3. detección -------------------------------------------------------------
    print(f"\nDetección de caras ({len(fotos)} fotos):")
    manuales = ojos_manuales()
    validas, caras, fallos = [], [], []
    for id_, f in fotos:
        try:
            img = imagen.leer(f)
            if id_ in manuales:
                det = detector.alinear_manual(img, *manuales[id_])
                info = "ojos marcados a mano (se inscribe con _sd)"
            else:
                det = detector.localizar(img)
                info = f"{det.cascada}, ojos {'detectados' if det.ojos_detectados else 'ESTIMADOS'}"
            cara = det.cara
        except (CaraNoEncontrada, ValueError) as e:
            fallos.append((id_, f.name, str(e)))
            print(f"  FALLO {f.name}: {e}")
            continue
        validas.append((id_, f, det.cara if id_ in manuales else None))
        caras.append(preprocesado.normalizar(cara))
        print(f"  ok    {f.name:48s} {info}")

    # --- 4. entrenamiento ---------------------------------------------------------
    entrenamiento = np.stack(caras + [c[:, ::-1] for c in caras])   # + espejos
    modelo = ModeloPCA.entrenar(entrenamiento, args.componentes)
    modelo.guardar(config.RUTA_MODELO)
    api.recargar()
    print(f"\nPCA: {len(entrenamiento)} caras de entrenamiento -> K={modelo.dim} eigenfaces "
          f"({modelo.varianza_explicada():.0%} de la varianza)")

    # --- 5. inscripción -------------------------------------------------------------
    bd.borrar()
    inscritos = {}
    for id_, f, manual in validas:
        if manual is not None:   # cara ya alineada con los ojos marcados a mano
            api.inscribir_sd(id_, manual)
        else:
            api.inscribir(id_, f)
        inscritos.setdefault(id_, []).append({
            "foto": ruta_relativa(f),
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        })
    config.RUTA_INSCRITOS.write_text(json.dumps(inscritos, indent=1, ensure_ascii=False), encoding="utf-8")

    # --- 6. umbral provisional --------------------------------------------------------
    base = bd.cargar()
    ids = sorted(base)
    impostoras = [comparador.distancia_a_id(base[a][0], base[b])
                  for i, a in enumerate(ids) for b in ids[i + 1:]]
    modelo.umbral = float(np.quantile(impostoras, args.far))
    modelo.guardar(config.RUTA_MODELO)
    api.recargar()

    print(f"\nInscritos: {len(base)} personas -> {config.RUTA_BD}")
    print(f"Distancias entre personas distintas: mín {min(impostoras):.1f}, "
          f"mediana {np.median(impostoras):.1f}, máx {max(impostoras):.1f}")
    print(f"Umbral PROVISIONAL = {modelo.umbral:.2f} (acepta al {args.far:.0%} de los pares de "
          f"impostores; la tasa de falso rechazo es desconocida hasta tener fotos de prueba)")
    if fallos:
        print(f"\nNO inscritos ({len(fallos)}): " + ", ".join(i for i, _, _ in fallos))
        print(f"  -> para inscribirlos, marca sus ojos en {RUTA_OJOS_MANUALES.name}")


if __name__ == "__main__":
    main()

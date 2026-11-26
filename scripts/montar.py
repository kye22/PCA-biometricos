"""Monta el sistema completo con un solo comando:

    python scripts/montar.py [--far 0.02]

1. Descomprime Dataset.tar.gz (el dataset) en datos/fotos/ si aún no está.
2. Junta esas fotos con las de datos/extra/ (Arbeloa) -> ids a partir del nombre de archivo.
3. Detecta y alinea cada cara; informa de las que fallan.
   Si el id está en datos/ojos_manuales.json se alinea con esos ojos y se inscribe con _sd.
4. Carga el extractor PCA genérico (modelos/pca_base.npz), entrenado con miles de caras de una
   base diversa (scripts/entrenar_pca.py), y comprueba que es el que está fijado en el código.
   NO se entrena con los inscritos: la BD solo guarda a quien tiene acceso.
5. Crea la clave secreta si no existe (datos/clave.key, fuera de git) e inscribe a todos en una
   BD nueva (datos/bd.csv, cifrada y firmada) con la API normal.
6. Calcula un umbral PROVISIONAL a partir de las distancias entre personas distintas y lo
   guarda dentro del modelo (pca.npz, firmado con la clave).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import argparse
import hashlib
import json

import numpy as np

from sistema import api, bd, calidad, comparador, config, dataset, detector, imagen, preprocesado, seguridad
from sistema.excepciones import CaraNoEncontrada
from sistema.pca import ModeloPCA

RUTA_OJOS_MANUALES = config.RAIZ / "datos" / "ojos_manuales.json"


def preparar_fotos(manifiesto: Path | None = None) -> list[tuple[str, Path]]:
    """
    Prepara las fotografías que se utilizarán para la inscripción.

    Si se proporciona un manifiesto, utiliza exclusivamente las fotos
    del grupo 'inscripcion'.

    Sin manifiesto, mantiene el comportamiento original.
    """

    # Extraer el dataset del profesor si todavía no está disponible.
    if not (
        config.RUTA_FOTOS.exists()
        and any(config.RUTA_FOTOS.iterdir())
    ):
        if not config.RUTA_DATASET.exists():
            sys.exit(
                f"No encuentro {config.RUTA_DATASET}. "
                "Ponlo en la raíz del repositorio."
            )

        n = dataset.extraer_dataset(
            config.RUTA_DATASET,
            config.RUTA_FOTOS
        )

        print(
            f"Descomprimido {config.RUTA_DATASET.name}: "
            f"{n} fotos -> {config.RUTA_FOTOS}"
        )

    # Seleccionar las fotografías de inscripción.
    if manifiesto is not None:
        grupos = dataset.leer_particion(manifiesto, config.RAIZ)
        fotos = grupos["inscripcion"]

        print(
            f"Partición de inscripción: {manifiesto} "
            f"({len(fotos)} fotografías)"
        )
    else:
        # Comportamiento original, conservado por compatibilidad.
        fotos = dataset.listar_inscripcion(
            config.RUTA_FOTOS,
            config.RUTA_EXTRA
        )

    # Avisar si alguna identidad tiene varias fotografías inscritas.
    ids = [id_ for id_, _ in fotos]

    repetidos = {
        id_ for id_ in ids
        if ids.count(id_) > 1
    }

    if repetidos:
        print(
            "Aviso: identidades con varias fotos "
            f"de inscripción: {sorted(repetidos)}"
        )

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
    p.add_argument("--far", type=float, default=0.02,
                   help="fracción de impostores que se aceptaría con el umbral (por defecto 2%%)")
    p.add_argument("--umbral", type=float, default=None,
                   help="fijar el umbral a mano (p. ej. 0.45, el calibrado con evaluacion/calibrar_umbral.py)")

    p.add_argument(
        "--recrear",
        action="store_true",
        help="Reconstruye la base de datos y el modelo, reemplazando la inscripción anterior"
    )

    p.add_argument(
        "--manifiesto",
        type=Path,
        default=None,
        help="archivo JSON que define las fotografías de inscripción"
    )

    args = p.parse_args()
    # Evitar reconstrucciones accidentales de una instalación existente.
        # Validar los parámetros antes de iniciar el montaje.
    if not 0 < args.far < 1:
        p.error("--far debe ser una fracción mayor que 0 y menor que 1")

    if args.umbral is not None and not 0 <= args.umbral <= 2:
        p.error("--umbral debe estar entre 0 y 2 (distancia coseno)")

    if not args.recrear:
        bd_existente = (
            config.RUTA_BD.exists()
            or config.RUTA_BD.with_suffix(".firma").exists()
            or config.RUTA_MODELO.exists()
        )

        if bd_existente:
            sys.exit(
                "Ya existe una inscripción. El montaje se ha cancelado "
                "para evitar sobrescribir la base de datos y el modelo.\n"
                "Si deseas reconstruirlos, ejecuta montar.py con --recrear."
            )

    # Comprobar el extractor antes de procesar fotos o modificar datos.
    if not config.RUTA_MODELO_BASE.is_file():
        sys.exit(
            f"ERROR: no se encuentra el extractor PCA genérico: "
            f"{config.RUTA_MODELO_BASE}\n"
            "Se cancela el montaje. No se entrenará un PCA "
            "alternativo con las personas inscritas."
        )

    fotos = preparar_fotos(args.manifiesto)
        # El cálculo del umbral necesita comparar identidades diferentes.
    identidades = {id_ for id_, _ in fotos}

    if len(identidades) < 2:
        sys.exit(
            "ERROR: se necesitan al menos dos identidades diferentes "
            "para calcular el umbral provisional."
        )


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
                avisos = calidad.problemas(calidad.medir(det))
                if avisos:   # al inscribir solo se avisa: se inscribe lo que trae el dataset
                    info += f"  AVISO calidad: {', '.join(avisos)}"
            cara = det.cara
        except (CaraNoEncontrada, ValueError) as e:
            fallos.append((id_, f.name, str(e)))
            print(f"  FALLO {f.name}: {e}")
            continue
        validas.append((id_, f, det.cara if id_ in manuales else None))
        caras.append(preprocesado.normalizar(cara))
        print(f"  ok    {f.name:48s} {info}")

    # No reconstruir el sistema si alguna fotografía ha fallado.
    # Hasta este punto todavía no hemos borrado la BD ni guardado
    # un nuevo modelo operativo.
    if fallos:
        nombres = ", ".join(nombre for _, nombre, _ in fallos)

        sys.exit(
            f"\nERROR: montaje cancelado.\n"
            f"Han fallado {len(fallos)} fotografías: {nombres}\n\n"
            "La base de datos y el modelo operativo existentes "
            "no se han modificado.\n"
            f"Revisa las fotografías o las coordenadas de "
            f"{RUTA_OJOS_MANUALES.name} antes de repetir el montaje."
        )

    # --- 4. extractor -------------------------------------------------------------
    # El extractor debe ser siempre el PCA genérico del repositorio.
    modelo = ModeloPCA.cargar(config.RUTA_MODELO_BASE)

    if modelo.huella() != config.HUELLA_MODELO_BASE:
        sys.exit(
            f"{config.RUTA_MODELO_BASE.name} no es el del repositorio "
            "(huella distinta). "
            "Si lo has reentrenado tú, actualiza config.HUELLA_MODELO_BASE."
        )

    print(
        f"\nPCA genérico ({config.RUTA_MODELO_BASE.name}): "
        f"K={modelo.k} eigenfaces + interior, "
        f"template de {modelo.dim} "
        f"({modelo.varianza_explicada():.0%} "
        "de la varianza de su base de entrenamiento)"
    )



    if seguridad.crear_clave():
        print(f"Clave nueva en {config.RUTA_CLAVE} (secreta: no va en git; sin ella la BD no se puede leer)")
    api.recargar()
    modelo.umbral = None
    modelo.guardar(config.RUTA_MODELO, seguridad.clave_modelo())
    api.recargar()

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
    modelo.umbral = args.umbral if args.umbral is not None else float(np.quantile(impostoras, args.far))
    modelo.guardar(config.RUTA_MODELO, seguridad.clave_modelo())
    api.recargar()

    print(f"\nInscritos: {len(base)} personas -> {config.RUTA_BD}")
    print(f"Distancias entre personas distintas: mín {min(impostoras):.3f}, "
          f"mediana {np.median(impostoras):.3f}, máx {max(impostoras):.3f}")
    if args.umbral is not None:
        print(f"Umbral = {modelo.umbral:.3f} (fijado con --umbral)")
    else:
        print(f"Umbral PROVISIONAL = {modelo.umbral:.3f} (acepta al {args.far:.0%} de los pares de "
              f"impostores; el falso rechazo se mide con fotos distintas de las inscritas)")



if __name__ == "__main__":
    main()

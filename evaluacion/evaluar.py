"""Evalúa verificación 1:1 e identificación 1:N con fotos NO inscritas.

    python evaluacion/evaluar.py --grupo prueba
    python evaluacion/evaluar.py --grupo calibracion --salida evaluacion/resultados/calibracion.json

Requiere haber montado la BD usando el MISMO --manifiesto. No cambia el sistema.
Distancias ausentes (rechazo de detector/calidad) cuentan como rechazo genuino y
como rechazo impostor, no se eliminan silenciosamente de las métricas.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from sistema import api, bd, comparador, config, dataset
from sistema.excepciones import ErrorSistema

from evaluacion.metricas import eer, far_frr, rank1


def _comprobar_inscripcion(grupos: dict, base: dict) -> None:
    """Evita evaluar accidentalmente sobre una BD creada con todas las fotos."""
    if not config.RUTA_INSCRITOS.is_file():
        raise ValueError("No existe inscritos.json: monta el sistema con --manifiesto")
    registradas = json.loads(config.RUTA_INSCRITOS.read_text(encoding="utf-8"))
    esperadas = {}
    for id_, f in grupos["inscripcion"]:
        esperadas.setdefault(id_, []).append(hashlib.sha256(f.read_bytes()).hexdigest())
    if set(base) != set(esperadas) or any(
        sorted(f["sha256"] for f in registradas.get(id_, [])) != sorted(huellas)
        or len(base.get(id_, [])) != len(huellas)
        for id_, huellas in esperadas.items()
    ):
        raise ValueError("La BD no coincide con la partición. Ejecuta montar.py --manifiesto ... --recrear")


def obtener_scores(manifiesto: Path, grupo: str) -> dict:
    if grupo not in ("calibracion", "prueba"):
        raise ValueError("El grupo debe ser calibracion o prueba")
    particion = dataset.leer_particion(manifiesto, config.RAIZ)
    base = bd.cargar()
    if len(base) < 2:
        raise ValueError("Faltan inscritos: ejecuta scripts/montar.py")
    _comprobar_inscripcion(particion, base)
    umbral = float(api.umbral())

    genuinas, impostoras, top1, desconocidas, rangos = [], [], [], [], []
    errores = {}
    casos = []
    for tipo, entradas in (("genuino", particion[grupo]), ("desconocido", particion["desconocidos"] if grupo == "prueba" else [])):
        for id_, f in entradas:
            error = None
            ranking = []
            try:
                template, _det, _cara = api.extraer(f, con_detector=True, control=True)
                ranking = comparador.ranking(template, base)
            except (ErrorSistema, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                errores[type(exc).__name__] = errores.get(type(exc).__name__, 0) + 1

            distancias = dict(ranking)
            top_id, top_d = ranking[0] if ranking else (None, float("inf"))
            caso = {"tipo": tipo, "id_real": id_,
                    "foto": f.resolve().relative_to(config.RAIZ.resolve()).as_posix(),
                    "top1": top_id, "distancia_top1": top_d if np.isfinite(top_d) else None,
                    "error": error, "aceptado": top_d <= umbral}
            if tipo == "genuino":
                d = distancias.get(id_, float("inf"))
                genuinas.append(d)
                top1.append(top_id == id_)
                rango = next((pos for pos, (candidato, _) in enumerate(ranking, 1)
                              if candidato == id_), None)
                rangos.append(rango)
                caso["distancia_genuina"] = d if np.isfinite(d) else None
                caso["rango_real"] = rango
                caso["identificacion_correcta"] = top_id == id_ and top_d <= umbral
                impostoras.extend(distancias.get(otro, float("inf")) for otro in base if otro != id_)
            else:
                desconocidas.append(top_d)
                impostoras.extend(distancias.get(otro, float("inf")) for otro in base)
            casos.append(caso)

    try:
        ruta_manifiesto = Path(manifiesto).resolve().relative_to(config.RAIZ.resolve()).as_posix()
    except ValueError:
        ruta_manifiesto = str(manifiesto)
    resultado = {"grupo": grupo, "manifiesto": ruta_manifiesto, "umbral": umbral,
                 "n_inscritos": len(base), "n_genuinos": len(genuinas),
                 "n_impostores_verificacion": len(impostoras),
                 "n_desconocidos": len(desconocidas), "rechazos_entrada": errores,
                 "casos": casos,
                 "genuinas": [d if np.isfinite(d) else None for d in genuinas],
                 "impostoras": [d if np.isfinite(d) else None for d in impostoras],
                 "desconocidas": [d if np.isfinite(d) else None for d in desconocidas]}
    if genuinas and impostoras:
        fmr, fnmr = far_frr(genuinas, impostoras, [umbral])
        eer_aprox, u_eer = eer(genuinas, impostoras)
        resultado.update({"FAR_verificacion": float(fmr[0]), "FRR_verificacion": float(fnmr[0]),
                          "EER_aproximada": eer_aprox, "umbral_EER_solo_diagnostico": u_eer,
                          "rank1_sin_umbral": rank1(top1),
                          "cmc": [sum(r is not None and r <= k for r in rangos) / len(genuinas)
                                  for k in range(1, len(base) + 1)],
                          "identificacion_correcta_con_umbral": sum(c.get("identificacion_correcta", False)
                                                                        for c in casos) / len(genuinas)})
    if desconocidas:
        resultado["FPIR_desconocidos"] = float(np.mean(np.asarray(desconocidas) <= umbral))
    return resultado


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifiesto", type=Path, default=config.RAIZ / "evaluacion" / "particion.json")
    p.add_argument("--grupo", choices=["calibracion", "prueba"], default="prueba")
    p.add_argument("--salida", type=Path)
    args = p.parse_args()
    try:
        r = obtener_scores(args.manifiesto, args.grupo)
    except (ErrorSistema, OSError, ValueError) as exc:
        p.exit(2, f"ERROR de evaluación: {exc}\n")
    destino = args.salida or config.RAIZ / "evaluacion" / "resultados" / f"{args.grupo}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(r, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Inscritos: {r['n_inscritos']}; genuinos: {r['n_genuinos']}; "
          f"impostores 1:1: {r['n_impostores_verificacion']}; desconocidos: {r['n_desconocidos']}")
    for k in ("FAR_verificacion", "FRR_verificacion", "EER_aproximada", "rank1_sin_umbral",
              "identificacion_correcta_con_umbral", "FPIR_desconocidos"):
        if k in r:
            print(f"{k}: {r[k]:.2%}")
    if not r["n_desconocidos"]:
        print("AVISO: sin fotos de desconocidos; FPIR de identificación abierta NO estimable")
    print(f"Umbral fijo evaluado: {r['umbral']:.4f} (EER solo diagnóstico; no reajustar con test)")
    print(f"Resultados: {destino}")


if __name__ == "__main__":
    main()

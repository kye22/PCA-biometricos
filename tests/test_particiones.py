"""La partición impide mezclar entrenamiento, calibración y prueba."""
import json

import pytest

from sistema import config, dataset
from evaluacion import particiones


def _archivo(ruta, marcador: str):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(marcador.encode())
    return ruta


def test_particion_reproducible_y_sin_solapamiento(tmp_path, monkeypatch):
    fotos = tmp_path / "datos/fotos"
    extra = tmp_path / "datos/extra"
    pruebas = tmp_path / "datos/pruebas"
    _archivo(fotos / "ana_2020.jpg", "foto-ana-original")
    _archivo(fotos / "beto_2020.jpg", "foto-beto-original")
    _archivo(extra / "ana" / "01.jpg", "ana-1")
    _archivo(extra / "ana" / "02.jpg", "ana-2")
    _archivo(extra / "ana" / "03.jpg", "ana-3")
    _archivo(pruebas / "otra_persona" / "desconocida.jpg", "otra")
    for key, value in (("RAIZ", tmp_path), ("RUTA_FOTOS", fotos),
                       ("RUTA_EXTRA", extra), ("RUTA_PRUEBAS", pruebas)):
        monkeypatch.setattr(config, key, value)
    datos = particiones.generar(semilla=42)
    assert particiones.generar(semilla=42) == datos
    assert len(datos["inscripcion"]) == 2
    assert len(datos["calibracion"]) == 1
    assert len(datos["prueba"]) == 2
    assert len(datos["desconocidos"]) == 1
    manifiesto = tmp_path / "particion.json"
    manifiesto.write_text(json.dumps(datos), encoding="utf-8")
    grupos = dataset.leer_particion(manifiesto, tmp_path)
    assert len(grupos["calibracion"]) == 1


def test_rechaza_misma_foto_en_inscripcion_y_prueba(tmp_path):
    foto = _archivo(tmp_path / "a.jpg", "foto")
    datos = {"version": 1, "inscripcion": [{"id": "ana", "foto": foto.name}],
             "prueba": [{"id": "ana", "foto": foto.name}]}
    manifiesto = tmp_path / "particion.json"
    manifiesto.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(ValueError, match="repetida"):
        dataset.leer_particion(manifiesto, tmp_path)


def test_rechaza_duplicado_exactamente_igual(tmp_path):
    _archivo(tmp_path / "a.jpg", "mismo-contenido")
    _archivo(tmp_path / "b.jpg", "mismo-contenido")
    datos = {"version": 1, "inscripcion": [{"id": "ana", "foto": "a.jpg"}],
             "prueba": [{"id": "ana", "foto": "b.jpg"}]}
    manifiesto = tmp_path / "particion.json"
    manifiesto.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(ValueError, match="idéntico"):
        dataset.leer_particion(manifiesto, tmp_path)

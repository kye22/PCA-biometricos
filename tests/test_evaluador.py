"""Comprobaciones que evitan medir el propio conjunto de inscripción."""
import hashlib
import json

import numpy as np
import pytest

from evaluacion.evaluar import _comprobar_inscripcion
from sistema import config


def test_evaluador_exige_las_mismas_fotos_inscritas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUTA_INSCRITOS", tmp_path / "inscritos.json")
    foto = tmp_path / "ana.jpg"
    foto.write_bytes(b"imagen-ficticia")
    huella = hashlib.sha256(foto.read_bytes()).hexdigest()
    grupos = {"inscripcion": [("ana", foto)]}
    config.RUTA_INSCRITOS.write_text(json.dumps({"ana": [{"sha256": huella}]}), encoding="utf-8")
    _comprobar_inscripcion(grupos, {"ana": [np.ones(2)]})
    with pytest.raises(ValueError, match="no coincide"):
        _comprobar_inscripcion(grupos, {"ana": [np.ones(2), np.ones(2)]})


def test_evaluador_detecta_foto_inscrita_distinta(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUTA_INSCRITOS", tmp_path / "inscritos.json")
    foto = tmp_path / "ana.jpg"
    foto.write_bytes(b"imagen-verdadera")
    grupos = {"inscripcion": [("ana", foto)]}
    config.RUTA_INSCRITOS.write_text(json.dumps({"ana": [{"sha256": "0" * 64}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="no coincide"):
        _comprobar_inscripcion(grupos, {"ana": [np.ones(2)]})

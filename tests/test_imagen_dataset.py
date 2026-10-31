import io
import tarfile

import numpy as np
from PIL import Image

from sistema import dataset, imagen


def _png(color=(10, 20, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 6), color).save(buf, "PNG")
    return buf.getvalue()


def test_leer_bytes_devuelve_bgr():
    img = imagen.leer(_png((10, 20, 200)))   # RGB
    assert img.shape == (6, 8, 3) and tuple(img[0, 0]) == (200, 20, 10)   # BGR


def test_leer_ignora_la_extension(tmp_path):
    """En el dataset hay un AVIF y un WebP con extensión .jpg: se lee por contenido."""
    f = tmp_path / "engaño.jpg"
    f.write_bytes(_png())
    assert imagen.leer(f).shape == (6, 8, 3)


def test_id_desde_archivo():
    assert dataset.id_desde_archivo("serenna_williams_2017.jpg") == "serenna_williams"
    assert dataset.id_desde_archivo("elisabeth_II_1945.jpg") == "elisabeth_ii"
    assert dataset.id_desde_archivo("tini_2021.png") == "tini"
    assert dataset.id_desde_archivo("james_phelps_(gemelo_weasley)_2011.jpg") == "james_phelps_(gemelo_weasley)"


def test_extraer_dataset_plano_y_sin_rutas_raras(tmp_path):
    tar = tmp_path / "d.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        for nombre in ["Dataset/ana_2020.png", "../fuera_2020.png", "Dataset/notas.txt"]:
            datos = _png() if nombre.endswith(".png") else b"hola"
            info = tarfile.TarInfo(nombre)
            info.size = len(datos)
            t.addfile(info, io.BytesIO(datos))
    n = dataset.extraer_dataset(tar, tmp_path / "fotos")
    assert n == 2
    assert sorted(p.name for p in (tmp_path / "fotos").iterdir()) == ["ana_2020.png", "fuera_2020.png"]
    assert not (tmp_path / "fuera_2020.png").exists()
    assert [i for i, _ in dataset.listar_inscripcion(tmp_path / "fotos")] == ["ana", "fuera"]

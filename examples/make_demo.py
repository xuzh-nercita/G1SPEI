"""Create small synthetic rasters: no external data or network required."""

import argparse
import json
from pathlib import Path

import numpy as np
from osgeo import gdal, osr

from g1spei.parameters import sha256


def make_demo(directory):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    params = root / "parameters"
    params.mkdir()
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    entries = []

    def raster(path, value, coarse=False):
        n, size = (8, 0.1) if coarse else (80, 0.01)
        ds = gdal.GetDriverByName("GTiff").Create(str(path), n, n, 1, gdal.GDT_Float32)
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform((-110, size, 0, 41, 0, -size))
        ds.GetRasterBand(1).SetNoDataValue(-9999)
        ds.GetRasterBand(1).WriteArray(np.full((n, n), value, dtype=np.float32))
        ds = None

    for role, value in {
        "precipitation_coarse_mean": 50,
        "precipitation_coarse_std": 20,
        "temperature_coarse_mean": 15,
        "precipitation_fine_mean": 60,
        "precipitation_fine_std": 25,
        "temperature_fine_mean": 14,
        "heat_index": 50,
        "gamma_alpha": 20,
        "gamma_beta": 50,
    }.items():
        path = params / f"{role}.tif"
        raster(path, value, coarse="coarse" in role)
        entries.append(
            {
                "path": path.name,
                "role": role,
                "month": None if role == "heat_index" else 7,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    (params / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "synthetic-demo",
                "calibration_period": "synthetic",
                "gamma_offset_mm": 1000,
                "spei_clip": 3.09,
                "files": entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    raster(root / "precipitation.tif", 0.070, coarse=True)
    raster(root / "temperature.tif", 290.15, coarse=True)
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    print(make_demo(parser.parse_args().directory))

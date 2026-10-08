import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from osgeo import gdal

from g1spei.parameters import load, verify
from g1spei.pipeline import run
from g1spei.raster import coastal_fill, open_raster, read
from g1spei.science import QA

spec = importlib.util.spec_from_file_location(
    "demo", Path(__file__).parents[1] / "examples/make_demo.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def execute(root, **kwargs):
    return run(
        root / "parameters",
        root / "precipitation.tif",
        root / "temperature.tif",
        root / "result",
        2025,
        7,
        "m_month",
        "K",
        tile_size=32,
        **kwargs
    )


def test_end_to_end_and_refuse_overwrite(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    report = execute(root)
    assert report["statistics"]["spei"]["count"] == 80 * 80
    np.testing.assert_allclose(
        read(open_raster(root / "result/G1SPEI_precipitation_2025_07.tif")), 85, atol=1e-4
    )
    np.testing.assert_allclose(
        read(open_raster(root / "result/G1SPEI_temperature_2025_07.tif")), 16, atol=2e-5
    )
    assert (root / "result/run.json").is_file()
    assert not (root / "result/work").exists()
    with pytest.raises(FileExistsError):
        execute(root)


def change_pixel(path, value, x=3, y=3):
    ds = gdal.Open(str(path), gdal.GA_Update)
    ds.GetRasterBand(1).WriteArray(np.array([[value]], np.float32), x, y)
    ds = None


def test_finite_missing_input_never_becomes_climatology(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    change_pixel(root / "precipitation.tif", -9999)
    change_pixel(root / "temperature.tif", -9999)
    execute(root)
    p = read(open_raster(root / "result/G1SPEI_precipitation_2025_07.tif"))
    t = read(open_raster(root / "result/G1SPEI_temperature_2025_07.tif"))
    assert np.isnan(p[35, 35]) and np.isnan(t[35, 35])
    assert np.isfinite(p[5, 5])


def test_low_std_mask_propagates_to_fine_grid(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    change_pixel(root / "parameters/precipitation_coarse_std.tif", 0.004)
    execute(root)
    p = read(open_raster(root / "result/G1SPEI_precipitation_2025_07.tif"))
    qa = read(open_raster(root / "result/G1SPEI_qa_2025_07.tif"))
    assert np.isnan(p[35, 35])
    assert int(qa[35, 35]) & QA.LOW_PRECIP_STD


def test_coastal_extension_does_not_fill_interior_missing():
    arr = np.ones((8, 8), float)
    arr[:, :2] = np.nan
    arr[4, 4] = np.nan
    ocean = np.zeros_like(arr, dtype=bool)
    ocean[:, :2] = True
    result, filled = coastal_fill(arr, ocean)
    assert np.isnan(result[4, 4])
    assert np.isfinite(result[3, 1]) and filled[3, 1]


def test_missing_coarse_parameter_is_not_treated_as_ocean(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    change_pixel(root / "parameters/precipitation_coarse_std.tif", -9999)
    execute(root)
    p = read(open_raster(root / "result/G1SPEI_precipitation_2025_07.tif"))
    qa = read(open_raster(root / "result/G1SPEI_qa_2025_07.tif"))
    assert np.isnan(p[35, 35])
    assert int(qa[35, 35]) & int(QA.INVALID_PARAMETER)


def test_parameter_checksum_and_path_traversal(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    assert verify(root / "parameters")["verified_files"] == 9
    change_pixel(root / "parameters/gamma_alpha.tif", 0)
    with pytest.raises(ValueError, match="Checksum"):
        verify(root / "parameters")
    path = root / "parameters/manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files"][0]["path"] = "../precipitation.tif"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="unsafe"):
        load(root / "parameters")


def test_grid_mismatch_rejected(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    ds = gdal.Open(str(root / "temperature.tif"), gdal.GA_Update)
    ds.SetGeoTransform((-109, 0.1, 0, 41, 0, -0.1))
    ds = None
    with pytest.raises(ValueError, match="Grid mismatch"):
        execute(root)


def test_packed_forcing_requires_explicit_unpacking(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    ds = gdal.Open(str(root / "temperature.tif"), gdal.GA_Update)
    ds.GetRasterBand(1).SetScale(0.01)
    ds = None
    with pytest.raises(ValueError, match="Unpack"):
        execute(root)


def test_window_preserves_geographic_location(tmp_path):
    root = demo.make_demo(tmp_path / "demo")
    execute(root, window=(10, 20, 30, 40))
    ds = open_raster(root / "result/G1SPEI_spei_2025_07.tif")
    assert (ds.RasterXSize, ds.RasterYSize) == (30, 40)
    np.testing.assert_allclose(ds.GetGeoTransform(), (-109.9, 0.01, 0, 40.8, 0, -0.01))

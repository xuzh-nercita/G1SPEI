import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from g1spei.parameters import monthly_paths
from g1spei.raster import open_raster, read


def module(relative, name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_heat_index_regeneration(tmp_path):
    demo = module("examples/make_demo.py", "demo_heat").make_demo(tmp_path / "demo")
    tool = module("scripts/build_heat_index.py", "build_heat")
    output = tmp_path / "heat.tif"
    # Reuse one constant field twelve times to independently check the sum.
    tool.build(demo / "parameters", "temperature_fine_mean.tif", output, "synthetic")
    expected = 12 * (14 / 5) ** 1.514
    np.testing.assert_allclose(read(open_raster(output)), expected, rtol=1e-6)
    with pytest.raises(FileExistsError):
        tool.build(demo / "parameters", "temperature_fine_mean.tif", output, "synthetic")


def test_explicit_forcing_alignment(tmp_path):
    demo = module("examples/make_demo.py", "demo_align").make_demo(tmp_path / "demo")
    tool = module("scripts/align_forcing.py", "align")
    output = tmp_path / "aligned.tif"
    tool.align(demo / "temperature.tif", demo / "parameters/temperature_coarse_mean.tif", output)
    np.testing.assert_allclose(read(open_raster(output)), 290.15, atol=1e-4)


def test_duplicate_manifest_role_rejected(tmp_path):
    demo = module("examples/make_demo.py", "demo_manifest").make_demo(tmp_path / "demo")
    path = demo / "parameters/manifest.json"
    content = json.loads(path.read_text())
    content["files"].append(content["files"][0])
    path.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="Duplicate"):
        monthly_paths(demo / "parameters", 7)

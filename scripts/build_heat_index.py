"""Regenerate climatological heat index from 12 monthly mean temperature rasters.

Inputs must be in degrees Celsius and cover the intended common baseline period.
The pattern must contain {month}, for example TEM_1km_1951_2025_{month}_mean_21base.tif.
"""

import argparse
from pathlib import Path

import numpy as np

from g1spei.raster import check_grid, create, open_raster, read, tiles


def build(input_directory, pattern, output, baseline):
    output = Path(output)
    partial = output.with_suffix(output.suffix + ".partial")
    if output.exists() or partial.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    sources = [open_raster(Path(input_directory) / pattern.format(month=m)) for m in range(1, 13)]
    for source in sources[1:]:
        check_grid(source, sources[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    target = create(partial, sources[0])
    target.SetMetadata({"BASELINE": baseline, "METHOD": "sum((max(monthly_mean_T_C,0)/5)^1.514)"})
    for win in tiles(sources[0].RasterXSize, sources[0].RasterYSize):
        result = np.zeros((win[3], win[2]), np.float64)
        for source in sources:
            result += (np.maximum(read(source, win), 0) / 5) ** 1.514
        target.GetRasterBand(1).WriteArray(result.astype(np.float32), win[0], win[1])
    target = None
    partial.rename(output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-directory", required=True)
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--baseline", required=True)
    print(build(**vars(parser.parse_args())))

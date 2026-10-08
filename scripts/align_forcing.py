"""Explicitly align a single-band forcing raster to the coarse parameter grid.

Units and time meaning are unchanged. Inspect longitude convention before use.
"""

import argparse
from pathlib import Path

from osgeo import gdal

from g1spei.raster import check_grid, open_raster


def align(source, template, output):
    source, template, output = Path(source), Path(template), Path(output)
    partial = output.with_suffix(output.suffix + ".partial")
    if output.exists() or partial.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    src, ref = open_raster(source), open_raster(template)
    if not src.GetProjection():
        raise ValueError("Source must have a valid CRS")
    gt = ref.GetGeoTransform()
    output.parent.mkdir(parents=True, exist_ok=True)
    ds = gdal.Warp(
        str(partial),
        src,
        format="GTiff",
        dstSRS=ref.GetProjection(),
        outputBounds=(
            gt[0],
            gt[3] + ref.RasterYSize * gt[5],
            gt[0] + ref.RasterXSize * gt[1],
            gt[3],
        ),
        width=ref.RasterXSize,
        height=ref.RasterYSize,
        outputType=gdal.GDT_Float32,
        resampleAlg="bilinear",
        dstNodata=float("nan"),
        errorThreshold=0,
        creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=3", "TILED=YES"],
    )
    check_grid(ds, ref)
    ds.SetMetadataItem("PROCESSING", "Explicit bilinear alignment; original units retained")
    ds = None
    partial.rename(output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    print(align(**vars(parser.parse_args())))

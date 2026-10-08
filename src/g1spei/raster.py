"""Small GDAL helpers with explicit missing-data and grid contracts."""

import numpy as np
from osgeo import gdal, osr

gdal.UseExceptions()
osr.UseExceptions()


def open_raster(path):
    ds = gdal.Open(str(path), gdal.GA_ReadOnly)
    if ds is None or ds.RasterCount != 1:
        raise ValueError(f"Expected a readable single-band GeoTIFF: {path}")
    band = ds.GetRasterBand(1)
    if band.GetScale() not in (None, 1) or band.GetOffset() not in (None, 0):
        raise ValueError(f"Unpack scale/offset to physical values before using this raster: {path}")
    return ds


def read(ds, window=None):
    band = ds.GetRasterBand(1)
    values = band.ReadAsArray(*(window or (0, 0, ds.RasterXSize, ds.RasterYSize)))
    values = np.asarray(values, dtype=np.float64)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        values[values == nodata] = np.nan
    values[~np.isfinite(values)] = np.nan
    return values


def check_grid(ds, reference):
    equal = (ds.RasterXSize, ds.RasterYSize) == (reference.RasterXSize, reference.RasterYSize)
    equal &= np.allclose(ds.GetGeoTransform(), reference.GetGeoTransform(), rtol=0, atol=1e-8)
    left, right = osr.SpatialReference(), osr.SpatialReference()
    left.ImportFromWkt(ds.GetProjection())
    right.ImportFromWkt(reference.GetProjection())
    if not equal or not left.IsSame(right):
        raise ValueError(f"Grid mismatch: {ds.GetDescription()} vs {reference.GetDescription()}")


def check_geographic(ds):
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)
    gt = ds.GetGeoTransform()
    if not srs.IsSame(wgs) or gt[2] != 0 or gt[4] != 0 or gt[1] <= 0 or gt[5] >= 0:
        raise ValueError("Parameters must be north-up WGS84 longitude/latitude grids")


def create(path, reference, window=None, integer=False):
    x, y, width, height = window or (0, 0, reference.RasterXSize, reference.RasterYSize)
    gt = list(reference.GetGeoTransform())
    gt[0] += x * gt[1]
    gt[3] += y * gt[5]
    ds = gdal.GetDriverByName("GTiff").Create(
        str(path),
        width,
        height,
        1,
        gdal.GDT_UInt16 if integer else gdal.GDT_Float32,
        options=[
            "TILED=YES",
            "COMPRESS=DEFLATE",
            f"PREDICTOR={2 if integer else 3}",
            "BIGTIFF=IF_SAFER",
            "NUM_THREADS=1",
        ],
    )
    ds.SetGeoTransform(gt)
    ds.SetProjection(reference.GetProjection())
    ds.GetRasterBand(1).SetNoDataValue(65535 if integer else float("nan"))
    return ds


def write_array(path, array, reference):
    ds = create(path, reference)
    ds.GetRasterBand(1).WriteArray(array.astype(np.float32))
    ds = None


def warp_vrt(path, source, target):
    gt = target.GetGeoTransform()
    return gdal.Warp(
        str(path),
        str(source),
        format="VRT",
        dstSRS=target.GetProjection(),
        outputBounds=(
            gt[0],
            gt[3] + target.RasterYSize * gt[5],
            gt[0] + target.RasterXSize * gt[1],
            gt[3],
        ),
        width=target.RasterXSize,
        height=target.RasterYSize,
        resampleAlg="bilinear",
        srcNodata=float("nan"),
        dstNodata=float("nan"),
        errorThreshold=0,
    )


def coastal_fill(array, eligible, distance=2):
    """IDW extension into reference-ocean cells only; never repair interior gaps."""
    if distance <= 0:
        return array.copy(), np.zeros(array.shape, dtype=bool)
    memory = gdal.GetDriverByName("MEM").Create(
        "", array.shape[1], array.shape[0], 1, gdal.GDT_Float32
    )
    band = memory.GetRasterBand(1)
    band.SetNoDataValue(float("nan"))
    band.WriteArray(array.astype(np.float32))
    mask = gdal.GetDriverByName("MEM").Create("", array.shape[1], array.shape[0], 1, gdal.GDT_Byte)
    mask.GetRasterBand(1).WriteArray(np.isfinite(array).astype(np.uint8) * 255)
    gdal.FillNodata(band, mask.GetRasterBand(1), distance, 0)
    filled = band.ReadAsArray()
    used = eligible & ~np.isfinite(array) & np.isfinite(filled)
    result = array.copy()
    result[used] = filled[used]
    return result, used


def tiles(width, height, size=512):
    for y in range(0, height, size):
        for x in range(0, width, size):
            yield x, y, min(size, width - x), min(size, height - y)

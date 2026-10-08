"""One month, one tiled run, four physical outputs and a bitmask QA raster."""

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from osgeo import gdal

from . import __version__
from .parameters import monthly_paths, sha256
from .raster import (
    check_geographic,
    check_grid,
    coastal_fill,
    create,
    open_raster,
    read,
    tiles,
    warp_vrt,
    write_array,
)
from .science import QA, pet_thornthwaite, precipitation_mm, spei_gamma


def prepare_coarse(
    paths, p_path, t_path, p_unit, t_unit, year, month, min_std, fill_distance, target, work
):
    ds = {
        k: open_raster(paths[k])
        for k in (
            "precipitation_coarse_mean",
            "precipitation_coarse_std",
            "temperature_coarse_mean",
        )
    }
    reference = ds["precipitation_coarse_mean"]
    p_ds, t_ds = open_raster(p_path), open_raster(t_path)
    for item in [*ds.values(), p_ds, t_ds]:
        check_grid(item, reference)
    p = precipitation_mm(read(p_ds), p_unit, year, month)
    t = read(t_ds) - (273.15 if t_unit == "K" else 0)
    pm, ps, tm = (
        read(ds[k])
        for k in (
            "precipitation_coarse_mean",
            "precipitation_coarse_std",
            "temperature_coarse_mean",
        )
    )
    p_land = np.isfinite(pm) & np.isfinite(ps)
    t_land = np.isfinite(tm)
    reference_land = np.isfinite(pm) | np.isfinite(ps) | t_land
    p_parameter_bad = reference_land & (~p_land | (pm < 0) | (ps <= 0))
    t_parameter_bad = reference_land & ~t_land
    low = p_land & ((ps <= 0) | (ps < min_std))
    p_missing = p_land & (~np.isfinite(p) | (p < 0))
    t_missing = t_land & ~np.isfinite(t)
    z = np.full(pm.shape, np.nan)
    good = p_land & ~low & ~p_missing & (pm >= 0)
    z[good] = (p[good] - pm[good]) / ps[good]
    anomaly = t - tm
    z, p_fill = coastal_fill(z, ~reference_land, fill_distance)
    anomaly, t_fill = coastal_fill(anomaly, ~reference_land, fill_distance)
    fields = {
        "z": z,
        "anomaly": anomaly,
        "low_std": low,
        "p_missing": p_missing,
        "t_missing": t_missing,
        "coastal_p": p_fill,
        "coastal_t": t_fill,
        "p_parameter_bad": p_parameter_bad,
        "t_parameter_bad": t_parameter_bad,
    }
    warped = {}
    for name, values in fields.items():
        path = work / f"{name}.tif"
        write_array(path, values, reference)
        warped[name] = warp_vrt(work / f"{name}.vrt", path, target)
    return warped


def run(
    parameters,
    precipitation,
    temperature,
    output,
    year,
    month,
    precipitation_unit,
    temperature_unit,
    profile="guarded",
    min_std=None,
    coastal_distance=2,
    tile_size=512,
    window=None,
):
    if not (1900 <= year <= 9999 and 1 <= month <= 12):
        raise ValueError("Year must be 1900..9999; month must be 1..12")
    if tile_size < 16 or tile_size > 2048 or coastal_distance < 0:
        raise ValueError("Tile size must be 16..2048; coastal distance must be nonnegative")
    if profile not in ("guarded", "reference"):
        raise ValueError("Unknown calculation profile")
    min_std = (0.1 if profile == "guarded" else 0.0) if min_std is None else min_std
    if not np.isfinite(min_std) or min_std < 0:
        raise ValueError("Minimum precipitation standard deviation must be finite and >= 0")
    manifest, paths = monthly_paths(parameters, month)
    fine_keys = [k for k in paths if "coarse" not in k]
    fine = {k: open_raster(paths[k]) for k in fine_keys}
    target = fine["temperature_fine_mean"]
    check_geographic(target)
    for item in fine.values():
        check_grid(item, target)
    region = tuple(window or (0, 0, target.RasterXSize, target.RasterYSize))
    x0, y0, width, height = region
    if (
        min(x0, y0) < 0
        or min(width, height) <= 0
        or x0 + width > target.RasterXSize
        or y0 + height > target.RasterYSize
    ):
        raise ValueError("Requested pixel window is outside the parameter grid")
    output = Path(output).resolve()
    pending = output.with_name(output.name + ".partial")
    if output.exists() or pending.exists():
        raise FileExistsError(f"Output or incomplete run already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    pending.mkdir()
    work = pending / "work"
    work.mkdir()
    gdal.SetCacheMax(256 * 1024 * 1024)
    started = time.time()
    report = {
        "software_version": __version__,
        "parameter_version": manifest["version"],
        "parameter_manifest_sha256": sha256(Path(parameters) / "manifest.json"),
        "date": f"{year:04d}-{month:02d}",
        "profile": profile,
        "min_coarse_precip_std_mm": min_std,
        "coastal_distance_coarse_pixels": coastal_distance,
        "precipitation_input": str(Path(precipitation).resolve()),
        "temperature_input": str(Path(temperature).resolve()),
        "precipitation_input_unit": precipitation_unit,
        "temperature_input_unit": temperature_unit,
        "window": list(region),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "calibration_period": manifest["calibration_period"],
        "pet_heat_index": "1951-2025 monthly-temperature climatology",
        "warning": "Rapid-update PET differs from historical annual-heat-index PET. Guarded QC is not a refit of Gamma parameters.",
    }
    outputs, coarse = {}, {}
    counters = {flag.name: 0 for flag in QA}
    stats = {
        key: {"count": 0, "min": None, "max": None, "sum": 0.0}
        for key in ("precipitation", "temperature", "pet", "spei")
    }
    units = {
        "precipitation": "mm/month",
        "temperature": "degree_Celsius",
        "pet": "mm/month",
        "spei": "1",
        "qa": "bitmask",
    }
    try:
        coarse = prepare_coarse(
            paths,
            precipitation,
            temperature,
            precipitation_unit,
            temperature_unit,
            year,
            month,
            min_std,
            coastal_distance,
            target,
            work,
        )
        for key in units:
            outputs[key] = create(
                pending / f"G1SPEI_{key}_{year:04d}_{month:02d}.tif",
                target,
                region,
                integer=key == "qa",
            )
            outputs[key].SetMetadata(
                {
                    "DATE": report["date"],
                    "UNITS": units[key],
                    "SOFTWARE_VERSION": __version__,
                    "PARAMETER_VERSION": manifest["version"],
                    "CALIBRATION_PERIOD": manifest["calibration_period"],
                    "PROFILE": profile,
                    "MIN_COARSE_PRECIP_STD_MM": str(min_std),
                    "HEAT_INDEX": report["pet_heat_index"],
                }
            )
            outputs[key].GetRasterBand(1).SetDescription(key)
            outputs[key].GetRasterBand(1).SetUnitType(units[key])
        gt = target.GetGeoTransform()
        land_count = 0
        for tile_number, (x, y, w, h) in enumerate(tiles(width, height, tile_size), 1):
            if (tile_number - 1) % 100 == 0:
                progress = {
                    "tiles_completed": tile_number - 1,
                    "rows_started": y,
                    "rows_total": height,
                    "elapsed_seconds": time.time() - started,
                }
                (pending / "progress.json").write_text(json.dumps(progress), encoding="utf-8")
                print(json.dumps(progress), flush=True)
            win = x + x0, y + y0, w, h
            data = {
                k: read(fine[k], win) for k in ("temperature_fine_mean", "precipitation_fine_mean")
            }
            land = np.isfinite(data["temperature_fine_mean"]) | np.isfinite(
                data["precipitation_fine_mean"]
            )
            if not np.any(land):
                missing = np.full((h, w), np.nan, dtype=np.float32)
                for key in stats:
                    outputs[key].GetRasterBand(1).WriteArray(missing, x, y)
                outputs["qa"].GetRasterBand(1).WriteArray(
                    np.full((h, w), 65535, dtype=np.uint16), x, y
                )
                continue
            data.update({k: read(ds, win) for k, ds in fine.items() if k not in data})
            z, an = read(coarse["z"], win), read(coarse["anomaly"], win)
            low = read(coarse["low_std"], win) > 1e-12
            p_missing = read(coarse["p_missing"], win) > 1e-12
            t_missing = read(coarse["t_missing"], win) > 1e-12
            coarse_p_bad = read(coarse["p_parameter_bad"], win) > 1e-12
            coarse_t_bad = read(coarse["t_parameter_bad"], win) > 1e-12
            land_count += int(land.sum())
            qa = np.zeros((h, w), dtype=np.uint16)
            qa[low] |= int(QA.LOW_PRECIP_STD)
            qa[p_missing | t_missing] |= int(QA.MISSING_FORCING)
            filled = (read(coarse["coastal_p"], win) > 1e-12) | (
                read(coarse["coastal_t"], win) > 1e-12
            )
            qa[filled] |= int(QA.COASTAL_EXTENSION)
            p = data["precipitation_fine_mean"] + z * data["precipitation_fine_std"]
            p_bad_parameters = (data["precipitation_fine_mean"] < 0) | (
                data["precipitation_fine_std"] < 0
            )
            p_bad_parameters |= ~np.isfinite(data["precipitation_fine_mean"]) | ~np.isfinite(
                data["precipitation_fine_std"]
            )
            qa[p_bad_parameters] |= int(QA.INVALID_PARAMETER)
            qa[coarse_p_bad | coarse_t_bad] |= int(QA.INVALID_PARAMETER)
            p[low | p_missing | p_bad_parameters | coarse_p_bad] = np.nan
            qa[np.isfinite(p) & (p < 0)] |= int(QA.PRECIP_FLOORED)
            p = np.maximum(p, 0)
            qa[np.isfinite(p) & (p > 5000)] |= int(QA.PRECIP_ABOVE_5000_MM)
            t = data["temperature_fine_mean"] + an
            t[t_missing | coarse_t_bad] = np.nan
            qa[land & (~np.isfinite(z) | ~np.isfinite(an)) & ~low] |= int(QA.MISSING_FORCING)
            latitudes = gt[3] + (np.arange(win[1], win[1] + h) + 0.5) * gt[5]
            pet, pet_qa = pet_thornthwaite(
                t, data["heat_index"], latitudes, year, month, legacy=profile == "reference"
            )
            spei, spei_qa = spei_gamma(
                p,
                pet,
                data["gamma_alpha"],
                data["gamma_beta"],
                offset=manifest["gamma_offset_mm"],
                limit=manifest["spei_clip"],
            )
            qa |= pet_qa | spei_qa
            for flag in QA:
                counters[flag.name] += int(np.count_nonzero(land & ((qa & int(flag)) != 0)))
            qa[~land] = 65535
            values = {"precipitation": p, "temperature": t, "pet": pet, "spei": spei}
            for key, array in values.items():
                array[~land] = np.nan
                finite = array[np.isfinite(array)]
                if finite.size:
                    stat = stats[key]
                    stat["count"] += int(finite.size)
                    stat["sum"] += float(finite.sum(dtype=np.float64))
                    mn, mx = float(finite.min()), float(finite.max())
                    stat["min"] = mn if stat["min"] is None else min(mn, stat["min"])
                    stat["max"] = mx if stat["max"] is None else max(mx, stat["max"])
                outputs[key].GetRasterBand(1).WriteArray(array.astype(np.float32), x, y)
            outputs["qa"].GetRasterBand(1).WriteArray(qa, x, y)
        for stat in stats.values():
            stat["mean"] = stat.pop("sum") / stat["count"] if stat["count"] else None
        report.update(
            status="complete",
            elapsed_seconds=time.time() - started,
            land_pixels=land_count,
            statistics=stats,
            qa_pixel_counts=counters,
        )
        outputs.clear()
        coarse.clear()
        # Only remove intermediates created inside this new, verified run directory.
        if work.resolve().parent != pending.resolve() or work.name != "work":
            raise RuntimeError("Unsafe intermediate directory")
        shutil.rmtree(work)
        (pending / "run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        pending.rename(output)
        print(f"Complete: {output}", flush=True)
        return report
    except Exception as error:
        report.update(status="failed", error=str(error), elapsed_seconds=time.time() - started)
        (pending / "failure.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise

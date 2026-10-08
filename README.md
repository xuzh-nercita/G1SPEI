# G1SPEI rapid production framework

Produce monthly 1-km precipitation, temperature, potential evapotranspiration (PET),
and SPEI-1 from an ERA5-Land monthly forcing pair and reusable parameter maps.
The parameter baseline for SPEI is **1951–2025**. This package evaluates previously
fitted Gamma distributions; it does not refit the full historical record each month.

**Author:** Zhenheng Xu · xuzh@nercita.org.cn · **Code license:** MIT.

[中文指南](README_zh.md) · [Scientific definitions](docs/METHODS.md) ·
[Input specification](docs/INPUTS.md) · [Parameter release](docs/PARAMETERS.md) ·
[Quality flags and changes](docs/CHANGES_AND_QA.md) · [Release checklist](docs/RELEASE.md)

## Status and scope

This is release candidate **1.0.0rc1**. It implements reproducible tiled calculations,
explicit units and missing-data masks, and safe output handling. The validation report
documents tests actually completed on the accompanying parameter release. The code
does not itself download ERA5-Land or determine whether an input month is final.
Use a complete monthly forcing field; later revisions of preliminary ERA5-Land data
require a new run in a new output directory.

The default `guarded` profile screens unstable coarse precipitation standard
deviations. Its default threshold (0.1 mm/month) is an explicit numerical safeguard,
not an empirically optimized climatological threshold. Rapid PET uses climatological
heat index, whereas the historical G1SPEI dataset used annual heat indices. Consequently,
rapid updates are **not guaranteed to reproduce historical G1SPEI exactly**.

## Install

Use a conda-forge environment so GDAL's Python package and native library agree.
From the repository directory:

```sh
conda env create -f environment.yml
conda activate g1spei
python -m pip install --no-deps --no-build-isolation -e .
python -m g1spei --version
python -m pytest -q
```

The commands are the same in PowerShell, Anaconda Prompt and a Unix shell.
Do not install a mismatched GDAL wheel over an existing GIS application's environment.

## Run a small example without downloading the global parameters

```sh
python examples/make_demo.py demo
python -m g1spei verify-parameters --parameters demo/parameters
python -m g1spei run --parameters demo/parameters --precipitation demo/precipitation.tif --temperature demo/temperature.tif --precipitation-unit m_month --temperature-unit K --year 2025 --month 7 --output demo/result
```

The example is synthetic, covers a small grid and is not a scientific dataset.
It should produce uniform precipitation of 85 mm/month and temperature of 16 °C.
Five GeoTIFFs and `run.json` are written. A second run to the same output path fails
instead of overwriting results.

## Run a real month

1. Obtain the separately distributed parameter bundle. Its Zenodo record is not yet
   published; see [parameter setup](docs/PARAMETERS.md). Do not substitute the 1990
   test heat-index file.
2. Extract all parameter archives into one parent directory. That directory must
   contain `manifest.json` and the folders listed in it.
3. Verify the full bundle once after download or transfer:

```sh
python -m g1spei verify-parameters --parameters ../G1SPEI-parameters-v1.0.0
```

4. Prepare two single-band GeoTIFFs on the **exact coarse parameter grid**. Check
   [INPUTS.md](docs/INPUTS.md) for the required grid and units. Raw CDS downloads
   may need conversion from NetCDF/GRIB and regridding before using this CLI.
5. Run, for example:

```sh
python -m g1spei run --parameters ../G1SPEI-parameters-v1.0.0 --precipitation inputs/precipitation_2026_01.tif --temperature inputs/temperature_2026_01.tif --precipitation-unit m_month --temperature-unit K --year 2026 --month 1 --output runs/2026-01
```

Use `m_day` instead if the precipitation file stores the monthly average of daily
totals in metres/day. The software then multiplies by the actual month length.
Do not use `m_day` for data already accumulated to monthly totals.

For a quick spatial check, add `--window 9000 6000 256 256`. These are zero-based
pixel offsets and dimensions on the 1-km parameter grid, not longitude/latitude.

## Outputs and resources

| File | Meaning |
|---|---|
| `G1SPEI_precipitation_YYYY_MM.tif` | Monthly precipitation, mm/month |
| `G1SPEI_temperature_YYYY_MM.tif` | Monthly mean temperature, °C |
| `G1SPEI_pet_YYYY_MM.tif` | Monthly Thornthwaite PET, mm/month |
| `G1SPEI_spei_YYYY_MM.tif` | SPEI-1, dimensionless, bounded to ±3.09 |
| `G1SPEI_qa_YYYY_MM.tif` | UInt16 bitmask; inspect alongside numerical outputs |
| `run.json` | Inputs, units, version, profile, timing, ranges and QA counts |

Physical outputs are losslessly compressed Float32 GeoTIFFs with NaN NoData.
QA uses NoData=65535. The parameter grid is 43,200 × 21,600 at 30 arc-seconds;
valid coverage is determined by input masks, not by the map plotting extent.
Each fine-grid tile is processed through the four stages before moving on. The
default tile size is 512. A global run also holds several 3,600 × 1,800 coarse arrays;
allow at least 8 GB free RAM and 20 GB free output/scratch disk space, in addition
to approximately 41 GB for the extracted parameters. Runtime depends on storage.

Completed outputs are committed by directory rename. Interrupted runs remain in
`OUTPUT.partial`, with `failure.json` when an exception was caught. Use a different
output directory to rerun; verify a partial run before deleting it manually. There
is no automatic overwrite or resume of partial raster tiles.

## Reproducibility and citation

Keep the software version, parameter manifest checksum, forcing source/version,
units and `run.json` with results. Cite the software using `CITATION.cff`, the
parameter record once published, and the underlying ERA5-Land/WorldClim sources.
The MIT license applies to code and documentation, **not automatically to the
parameter rasters or their source datasets**. Parameter licensing is separate.

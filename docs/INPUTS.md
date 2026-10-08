# Input contract

## Monthly forcing

Supply one precipitation and one temperature single-band GeoTIFF for the same,
complete calendar month. Units are mandatory CLI arguments. There is no automatic
date inference from filenames and no automatic download or time aggregation.
The caller must select the intended month/band before running this program.

| Argument | Stored quantity | Conversion |
|---|---|---|
| `--precipitation-unit m_month` | Total monthly precipitation, m | ×1000 |
| `--precipitation-unit mm_month` | Total monthly precipitation, mm | Identity |
| `--precipitation-unit m_day` | Monthly mean daily accumulated precipitation, m/day | ×1000×days |
| `--precipitation-unit mm_day` | Monthly mean daily accumulated precipitation, mm/day | ×days |
| `--temperature-unit K` | Monthly mean 2-m temperature, K | −273.15 |
| `--temperature-unit C` | Monthly mean 2-m temperature, °C | Identity |

Negative precipitation and non-finite input values are treated as missing, as are
values equal to the input band's declared NoData. Undeclared finite sentinel values
cannot be reliably inferred. Set NoData correctly when exporting your source data.
Stored pixel values must already be physical values in the declared units. Rasters
with nonidentity scale/offset metadata are rejected rather than silently treated
as unpacked values. Decode packed NetCDF/GRIB data before creating these GeoTIFFs.

The forcing grid must match the coarse climatology: WGS84 (EPSG:4326), 3600 columns,
1800 rows, north-up. The supplied legacy reference has this affine geotransform:

```text
(-180.00082337073323, 0.10000045742818513, 0,
   90.00041168536661, 0, -0.10000045742818513)
```

These are the **actual legacy parameter coordinates**, not idealized 0.1° boundaries.
The program checks both dimensions and affine transform (absolute tolerance 1e-8),
as well as CRS. This prevents silently mixing shifted grids. A raw CDS grid may
have different origins, longitude conventions, order, or pixel registration.
Use `scripts/align_forcing.py` to explicitly resample a correctly georeferenced
single-band field to the parameter template before production. Inspect the result.
This changes the sampling grid only, not units or temporal accumulation. A dataset
encoded on 0–360° longitudes needs appropriate longitude handling upstream;
do not simply relabel its coordinates as −180–180°.

Example alignment for a January temperature field:

```sh
python scripts/align_forcing.py --source inputs/temperature_raw.tif --template ../G1SPEI-parameters-v1.0.0/ERA5_temperature/ERA5_TEM_1970_2000_1_mean.tif --output inputs/temperature_2026_01.tif
```

For precipitation use the corresponding monthly precipitation coarse-mean template.
Use the resulting files in `g1spei run`; select the units of their actual stored values.

## Parameter grids and physical definitions

Fine fields use EPSG:4326, 43200×21600, geotransform
`(-180, 1/120, 0, 90, 0, -1/120)`. This is a 30 arc-second angular grid;
its physical east-west cell size varies with latitude. "1 km" is nominal.
Fine temperature and precipitation climatologies represent 1970–2000; monthly
coarse climatologies use the same period. Temperature climatologies are in °C;
precipitation means/standard deviations are in mm/month.

Gamma shape and scale maps use the historical 1951–2025 calibration. Beta is the
**scale**, not the reciprocal rate. Heat index is derived from the 12 monthly mean
temperatures over 1951–2025, not from the mean of 75 annual heat-index maps.

References for upstream conventions:

- [ECMWF ERA5-Land data documentation](https://confluence.ecmwf.int/pages/viewpage.action?pageId=212460134)
- [GDAL FillNodata API](https://gdal.org/en/stable/api/python/utilities.html): default filling uses inverse-distance weighting, not nearest-neighbour interpolation.

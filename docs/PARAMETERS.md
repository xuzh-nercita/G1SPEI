# Parameter bundle v1.0.0

**Download/DOI status:** not yet deposited. The author will upload the prepared
archives to Zenodo. Add the actual version-specific DOI here after deposit; no
placeholder URL should be treated as a working download link.

Extract every archive into one directory, then place the distributed `manifest.json`
at its root. Archives contain different folders/files; none replaces another.
Keep the original paths. Run `g1spei verify-parameters --parameters DIRECTORY`
to check every byte against the SHA-256 manifest before using new downloads.
Routine `run` checks file presence, sizes, grids and numerical validity but does
not reread 41 GB for full checksums every month.

| Role | Count | Folder | Baseline / units |
|---|---:|---|---|
| Coarse mean temperature | 12 | ERA5_temperature | 1970–2000; °C |
| Coarse precipitation mean/std | 24 | ERA5_precipitation | 1970–2000; mm/month |
| Fine mean temperature | 12 | WorldClim_temperature | 1970–2000; °C |
| Fine mean precipitation | 12 | WorldClim_precipitation/WorldClim_mean | 1970–2000; mm/month |
| Fine RF precipitation std | 12 | WorldClim_precipitation/WorldClim_std_RF | Local variability; mm/month |
| Gamma alpha/beta | 24 | SPEI_1km_params | 1951–2025; shape / scale |
| Climatological heat index | 1 | PET_1km_params | 1951–2025; dimensionless |

No annual 1990 test heat index, global latitude raster, old outputs, overviews or
notebook caches are required. Latitude is calculated from pixel-centre coordinates.
The updated heat-index file is named `Heat_Index_1951_2025_climatology.tif`.

## Precision and compression

The supplied GeoTIFFs are already mostly losslessly compressed. They are distributed
without packing to scaled Int16. Gamma beta can be below 0.001 and alpha can exceed
one million; a common integer scale factor would lose relevant precision or overflow.
Neither switching containers to NetCDF4 nor ZIP guarantees a substantial reduction
for already compressed arrays. Archives are storage containers for convenient
distribution; individual raster checksums remain the reproducibility record.

The local preparation process copies 96 maps without changing pixels and verifies
the destination SHA-256. Heat index is recomputed from twelve monthly temperature
climatologies using Float64 accumulation and Float32 storage. The full-grid difference
against the existing baseline heat index is recorded in the validation report.

## Licensing and provenance

MIT applies to the software. The parameter bundle includes WorldClim climatologies,
ERA5-Land-derived climatologies and author-derived RF/Gamma/heat-index fields.
Confirm source-data redistribution terms and assign an appropriate data license
before publishing the Zenodo record. Do not label all source data MIT by inheritance.

Source information: [ERA5-Land](https://doi.org/10.5194/essd-13-4349-2021),
[WorldClim 2](https://doi.org/10.1002/joc.5086),
[WorldClim data site](https://www.worldclim.org/data/worldclim21.html).

If a source layer cannot be redistributed, distribute the author-derived maps
separately and provide a recipe for obtaining/preparing that source. Update the
manifest and version whenever bytes, provenance or scientific definitions change.

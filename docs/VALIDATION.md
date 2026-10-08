# Executed validation, 8 October 2026

This report describes executed checks, not planned CI jobs. The full-grid test used
the supplied 2025-12 monthly-total ERA5-Land precipitation (m/month) and temperature
(K), with the guarded profile and 0.1 mm/month coarse standard-deviation threshold.

## Tests completed

- 18 synthetic/unit/integration tests passed: finite NoData, missing forcing,
  incomplete coarse parameters, low sigma, units, leap years, polar daylight,
  final PET cap, Gamma support/tails, grid mismatch, checksums, output safety,
  spatial windows, heat-index generation and explicit forcing alignment.
- Python syntax and Black formatting checked; an installable wheel built and
  imported separately from the source tree. A synthetic CLI pipeline was tested.
- All 96 copied parameter rasters were verified against source SHA-256. One
  climatological heat-index raster was regenerated, giving 97 required rasters.
- Heat index compared at 309,278,141 valid pixels against the
  existing baseline: maximum absolute difference 6.1035156e-05,
  mean absolute difference 4.2562136e-06, mask mismatches 0.
- Actual 64×64 Rockies (1990-07) and Sahara (1964-11) windows checked with both
  profiles. Rockies centre precipitation was 104.88652 mm and SPEI approximately
  2.396, matching the prior implementation within rounding. The Sahara centre's
  approximately 42112.8 mm precipitation was retained/flagged in reference mode
  and excluded in guarded mode because sigma was approximately 0.00465 mm/month.
- One complete global month produced at 43200×21600. Every stored output block
  was read back; validity counts, ranges, means and all QA counts agreed with the
  run report. All eight parameter archives passed ZIP CRC verification.

## Global execution

- Completed month: 2025-12.
- Runtime: 13.82 minutes on the local Windows workstation;
  this is not a cross-hardware performance guarantee.
- Observed peak process resident memory: 0.72 GiB.
- Reference land pixels (union of fine temperature/precipitation means): 309,278,141.
- Valid SPEI pixels: 302,697,046.
- Pixels affected by low coarse sigma: 3,187,440 (1.031% of reference land pixels;
  this is an unweighted pixel fraction, not land-area percentage).
- Precipitation above 5000 mm/month: 0 pixels.
- Numerical-failure flag: 0 pixels.

| Output | Valid cells | Minimum | Maximum | Mean |
|---|---:|---:|---:|---:|
| precipitation | 305,945,666 | 0 | 1193.81 | 43.1672 |
| temperature | 309,133,106 | -45.6124 | 35.2946 | -4.94502 |
| pet | 309,133,106 | 0 | 479.273 | 33.0361 |
| spei | 302,697,046 | -3.09 | 3.09 | 0.0211615 |

## Limits of these checks

This is a software/numerical validation, not a new independent drought-skill study.
Only one full global month was run; full historical recalibration or exhaustive
global validation of all calendar months was not performed. Other months' parameter
files were copied/checksummed, not all fully decompressed in a global run. The Linux
GitHub Actions workflow is prepared but has not yet run on GitHub.

The 0.1 mm/month sigma threshold is a disclosed numerical safeguard, not a threshold
optimized against observations. It reduces valid coverage and cannot ensure every
remaining high precipitation value is physically correct. Investigate flagged values.
The climatological heat index and final low-temperature PET cap can differ from
historical annual-PET processing while the original Gamma calibration remains fixed.
Scientific acceptance of these differences needs a separate historical evaluation.

The parameter DOI and data-license choice remain for the depositor; code licensing
has been confirmed as MIT. No external upload was performed in this preparation.

# Numerical definitions and reproducibility

Let `m` be calendar month, `P_c` current coarse precipitation in mm/month and `T_c`
current coarse temperature in °C. `B` denotes bilinear interpolation to the target
grid after bounded IDW coastal extension. Monthly coarse and fine climatologies
are denoted `mu_c`, `mu_f`; precipitation standard deviations are `sigma_c`, `sigma_f`.

```text
T_f = mu_T,f + B(T_c - mu_T,c)
Z_c = (P_c - mu_P,c) / sigma_P,c
P_f = max(0, mu_P,f + B(Z_c) * sigma_P,f)
```

The fine precipitation standard deviation is supplied by the precomputed Random
Forest model. This package evaluates that field and does not train the model.
Only jointly valid operands enter arithmetic. Unstable coarse standard deviations
are explicitly flagged; the default profile excludes values below 0.1 mm/month.
Zero and negative standard deviations are always invalid.

Missing forcing over a valid coarse reference land cell is never replaced with
zero anomaly. `gdal.FillNodata` is allowed to add values only to cells with missing
coarse reference climatology. Interior missing or unstable cells remain excluded.
Cells with a mixture of valid and missing coarse parameters are parameter failures,
not candidates for ocean filling; their influence is masked and flagged separately.
The radius is measured in coarse pixels (default 2), not a uniform kilometre
distance. Longitude distances vary with latitude. Interpolated invalidity flags
are conservatively propagated to any affected fine cell. Coastal filling is a
limited spatial extrapolation, not a physical guarantee of land-sea continuity.

## Thornthwaite PET

The reusable heat index is:

```text
I_clim = sum_m [(max(mean_1951:2025(T_f,m), 0) / 5)^1.514]
I_safe = max(I_clim, 0.1)
a = 6.75e-7 I_safe^3 - 7.71e-5 I_safe^2 + 1.792e-2 I_safe + 0.49239
PET_0 = 16 (10 max(T_f, 0) / I_safe)^a
PET = PET_0 (mean_daylight_hours / 12) (days_in_month / 30)
```

Daylight is the monthly mean of daily `24/pi * arccos(-tan(latitude)*tan(delta))`,
with the arccos argument clipped to [-1,1] and
`delta = 0.409 sin(2*pi*day_of_year/365 - 1.39)`. The empirical 365 denominator
is retained; actual day-of-year and month length include leap days in `guarded` mode.
Latitudes are pixel centres. This implementation computes daylight by row rather
than allocating a global latitude cube.

For valid cells at T≤0 °C, PET=0. In guarded mode, the final monthly PET is limited
to 50 mm when 0<T≤5 °C. Missing temperature or heat index remains missing. A zero
climatological heat index uses the 0.1 floor when a new month is warm; it does not
unconditionally force new warm-month PET to zero.

Historical 1951–2025 PET used each year's full annual heat index. Climatological
heat index enables monthly updates without future temperatures from the same year,
but introduces a methodological difference from historical PET. This code does not
claim that difference is zero or that the cap is independently calibrated.

## SPEI-1

```text
x = P_f - PET + 1000
F = regularized_lower_incomplete_gamma(alpha, max(x,0) / beta)
SPEI = clip(inverse_standard_normal_CDF(F), -3.09, +3.09)
```

`alpha` and `beta` are the shape and scale parameters previously fitted separately
for each month and fine-grid pixel over 1951–2025. No fitting or parameter resampling
occurs during a monthly run. Calculations use Float64, outputs Float32.

For x≤0, the result is −3.09 and QA flags identify extrapolation below the Gamma
support; this matches the historical calculation's lower-tail convention. Alpha
or beta that is missing/non-positive gives NoData. Tail saturation at either bound
is flagged, including when the CDF numerically rounds to zero or one.

This is the project's **shifted-Gamma implementation**, not the log-logistic
definition used by some other SPEI products. The shift, fitted parameters, heat-index
choice, masks, and clipping convention must be retained when comparing results.
Only the one-month accumulation scale is implemented. Monthly SPEI-1 alone does not
identify submonthly flash-drought onset rates.

## Source provenance

The release refactors the four original production notebooks into one CLI. It
retains the supplied downscaling climatologies, RF standard deviation and fitted
Gamma parameter values without lossy quantization. The parameter manifest records
individual file checksums. The heat-index raster is regenerated from the 12 original
1951–2025 temperature climatologies and compared to the existing baseline raster.

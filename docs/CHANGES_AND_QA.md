# Differences from the experimental notebooks

| Issue | Release behavior |
|---|---|
| Different years and inconsistent month formatting | One required year/month pair; standardized output names |
| Absolute user-specific paths | All locations supplied as arguments or manifest-relative paths |
| 1990 test heat index | Regenerated 1951–2025 climatological heat index |
| Missing precipitation/temperature becoming zero anomalies | Explicit joint validity; finite NoData recognized |
| Tiny precipitation standard deviation | Configurable conservative screening; separate QA |
| PET cap applied before daylight correction | Guarded profile caps the final month total |
| Missing heat index becoming zero PET | Missing remains missing |
| Duplicate SPEI notebook cells and silent overwrites | Single CLI; refuse existing and partial output directories |
| Global fine-grid arrays / latitude-day cubes | Tiled fine-grid arithmetic; row-wise daylight |
| x≤0 silently discarded in quick SPEI | Explicit historical lower-tail convention with QA |
| Unclear precipitation units | Required total-vs-daily-mean unit selection |

## QA bitmask

Multiple flags can occur together; use bitwise AND, not equality. For example,
`(qa & 4) != 0` selects cells affected by low precipitation standard deviation.
First exclude NoData=65535. Zero means none of these flags, not perfect accuracy.

| Bit value | Name | Interpretation |
|---|---|---|
| 1 | MISSING_FORCING | Missing/unavailable forcing anomaly affects this land cell |
| 2 | INVALID_PARAMETER | Missing or physically invalid required parameter |
| 4 | LOW_PRECIP_STD | Coarse precipitation standard deviation below threshold or ≤0 |
| 8 | PRECIP_FLOORED | Negative reconstructed precipitation was set to zero |
| 16 | BELOW_GAMMA_SUPPORT | P−PET+1000≤0; SPEI assigned lower bound |
| 32 | PET_CAPPED | Low-temperature PET limit applied (profile dependent) |
| 64 | SPEI_CLIPPED | SPEI reached ±3.09 after tail clipping |
| 128 | COASTAL_EXTENSION | Fine interpolation uses extrapolated coastal anomaly |
| 256 | PRECIP_ABOVE_5000_MM | Screening indicator; precipitation retained, not capped |
| 512 | NUMERICAL_FAILURE | Non-finite PET or SPEI despite finite, admissible inputs |

QA combines information across precipitation, temperature, PET and SPEI. A flag
does not necessarily invalidate all four outputs. For example, a low precipitation
standard deviation masks precipitation and SPEI but can leave temperature/PET valid.

## Guarded versus reference

The guarded default uses sigma≥0.1 mm/month, actual-calendar daylight, a final
0<T≤5 °C PET cap, and an I=0 warm-month floor. The reference profile accepts any
positive sigma, uses a fixed 365-day month-day list, caps unadjusted PET for 0<T<5,
and forces PET=0 when I=0, as in the original rapid PET formula.

Both profiles retain repaired missing-data handling and the climatological heat
index. `reference` is a diagnostic comparison, not exact reproduction of annual-PET
historical products. No arbitrary ceiling is used to make implausible precipitation
appear valid. Examine flagged values and investigate input/climatology compatibility.

The sigma threshold is not fitted against stations, and the changed PET convention
has not been used to refit the shipped Gamma maps. Full global execution verifies
software behavior and numerical coverage; it does not establish independent
scientific accuracy or seamless temporal homogeneity with historical G1SPEI.

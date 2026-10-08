"""Numerical kernels. All precipitation/PET in mm/month; temperature in degrees C."""

import calendar
from enum import IntFlag

import numpy as np
from scipy.special import gammainc, ndtri


class QA(IntFlag):
    MISSING_FORCING = 1
    INVALID_PARAMETER = 2
    LOW_PRECIP_STD = 4
    PRECIP_FLOORED = 8
    BELOW_GAMMA_SUPPORT = 16
    PET_CAPPED = 32
    SPEI_CLIPPED = 64
    COASTAL_EXTENSION = 128
    PRECIP_ABOVE_5000_MM = 256
    NUMERICAL_FAILURE = 512


def precipitation_mm(values, unit, year, month):
    factors = {
        "mm_month": 1,
        "m_month": 1000,
        "mm_day": calendar.monthrange(year, month)[1],
        "m_day": 1000 * calendar.monthrange(year, month)[1],
    }
    return np.asarray(values, dtype=np.float64) * factors[unit]


def daylight_hours(latitude, year, month, legacy=False):
    """Mean daily astronomical day length; rows only, including polar night/day.

    The empirical declination denominator remains 365, as in Thornthwaite
    implementations. Actual day-of-year and month length include leap days.
    Legacy mode reproduces the original fixed non-leap monthly day list.
    """
    ref_year = 2001 if legacy else year
    first = sum(calendar.monthrange(ref_year, m)[1] for m in range(1, month)) + 1
    n = calendar.monthrange(ref_year, month)[1]
    days = np.arange(first, first + n, dtype=np.float64)
    declination = 0.409 * np.sin(2 * np.pi * days / 365 - 1.39)
    latitude = np.asarray(latitude, dtype=np.float64)
    angle = -np.tan(np.deg2rad(latitude))[..., None] * np.tan(declination)
    return np.mean(24 / np.pi * np.arccos(np.clip(angle, -1, 1)), axis=-1)


def pet_thornthwaite(temperature, heat_index, latitude, year, month, legacy=False):
    t, index = np.broadcast_arrays(
        np.asarray(temperature, dtype=np.float64), np.asarray(heat_index, dtype=np.float64)
    )
    valid = np.isfinite(t) & np.isfinite(index) & (index >= 0)
    i = np.maximum(index, 0.1)
    a = 6.75e-7 * i**3 - 7.71e-5 * i**2 + 1.792e-2 * i + 0.49239
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        pet = 16 * np.power(10 * np.maximum(t, 0) / i, a)
    qa = np.zeros(t.shape, dtype=np.uint16)
    cold = (t > 0) & ((t < 5) if legacy else (t <= 5))
    if legacy:
        capped = valid & cold & (pet > 50)
        pet = np.where(capped, 50, pet)
    correction = daylight_hours(latitude, year, month, legacy)
    if t.ndim == 2 and correction.ndim == 1:
        correction = correction[:, None]
    pet *= correction / 12 * calendar.monthrange(year, month)[1] / 30
    if not legacy:
        capped = valid & cold & (pet > 50)
        pet = np.where(capped, 50, pet)
    pet = np.where(t <= 0, 0, pet)
    if legacy:
        pet = np.where(index == 0, 0, pet)
    qa[capped] |= int(QA.PET_CAPPED)
    qa[~np.isfinite(index) | (index < 0)] |= int(QA.INVALID_PARAMETER)
    qa[valid & ~np.isfinite(pet)] |= int(QA.NUMERICAL_FAILURE)
    pet[~valid | ~np.isfinite(pet)] = np.nan
    return pet.astype(np.float32), qa


def spei_gamma(precipitation, pet, alpha, beta, offset=1000.0, limit=3.09):
    p, e, a, b = np.broadcast_arrays(
        *[np.asarray(v, dtype=np.float64) for v in (precipitation, pet, alpha, beta)]
    )
    valid_parameters = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    valid = valid_parameters & np.isfinite(p) & np.isfinite(e)
    x = p - e + offset
    qa = np.zeros(x.shape, dtype=np.uint16)
    qa[~valid_parameters] |= int(QA.INVALID_PARAMETER)
    below = valid & (x <= 0)
    qa[below] |= int(QA.BELOW_GAMMA_SUPPORT)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        probability = gammainc(a, np.maximum(x, 0) / b)
        z = ndtri(probability)
    clipped = valid & ((z < -limit) | (z > limit))
    qa[clipped] |= int(QA.SPEI_CLIPPED)
    z = np.clip(z, -limit, limit)
    qa[valid & ~np.isfinite(z)] |= int(QA.NUMERICAL_FAILURE)
    z[~valid] = np.nan
    return z.astype(np.float32), qa

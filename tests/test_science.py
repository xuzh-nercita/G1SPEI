import numpy as np
import pytest
from scipy.stats import gamma, norm

from g1spei.science import QA, daylight_hours, pet_thornthwaite, precipitation_mm, spei_gamma


def test_input_units_and_leap_month():
    assert precipitation_mm([1], "m_day", 2024, 2)[0] == 29000
    assert precipitation_mm([1], "m_day", 2023, 2)[0] == 28000
    assert precipitation_mm([0.07], "m_month", 2024, 2)[0] == 70


def test_daylight_hemispheres_and_poles():
    np.testing.assert_allclose(daylight_hours([0], 2024, 6), [12])
    northern, southern = daylight_hours([89, -89], 2024, 6)
    assert northern == 24 and southern == 0
    assert daylight_hours([50], 2024, 6)[0] > daylight_hours([50], 2024, 12)[0]


def test_pet_final_cap_and_nodata():
    t = np.array([[2, 5, -1, np.nan, 2]], float)
    hi = np.array([[0.1, 0.1, 10, 10, np.nan]], float)
    pet, qa = pet_thornthwaite(t, hi, np.array([75]), 2024, 6)
    assert pet[0, 0] == 50 and pet[0, 1] == 50
    assert qa[0, 0] & QA.PET_CAPPED
    assert pet[0, 2] == 0
    assert np.isnan(pet[0, 3]) and np.isnan(pet[0, 4])
    prior, _ = pet_thornthwaite(t, hi, np.array([75]), 2024, 6, legacy=True)
    assert prior[0, 0] > 50


def test_zero_heat_index_warm_month_explicit_convention():
    result, _ = pet_thornthwaite(np.array([[2.0]]), np.array([[0.0]]), [50], 2025, 7)
    assert 0 < result[0, 0] <= 50


def test_gamma_reference_support_and_invalid_parameters():
    p = np.array([[100, 0, np.nan, 100, 100]], float)
    pet = np.array([[50, 1001, 50, 50, 50]], float)
    a = np.array([[20, 20, 20, 0, 20]], float)
    b = np.array([[50, 50, 50, 50, -1]], float)
    z, qa = spei_gamma(p, pet, a, b)
    assert z[0, 0] == pytest.approx(norm.ppf(gamma.cdf(1050, 20, scale=50)), abs=1e-6)
    assert z[0, 1] == pytest.approx(-3.09)
    assert qa[0, 1] & QA.BELOW_GAMMA_SUPPORT
    assert np.isnan(z[0, 2:]).all()


def test_extreme_gamma_parameters_do_not_underflow_to_missing():
    z, _ = spei_gamma(
        np.array([0, 0, 100000.0]),
        np.array([0, 2000, 0.0]),
        np.array([1e6, 1e6, 1e6]),
        np.array([0.001, 0.001, 0.001]),
    )
    assert np.isfinite(z).all()
    assert z[1] == pytest.approx(-3.09)
    assert z[2] == pytest.approx(3.09)

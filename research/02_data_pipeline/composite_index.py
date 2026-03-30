"""
Composite Index Calculators for Digital Columbus Immune Care Pipeline.

Implements the derived composite indices specified in the data pipeline
architecture document, mapping environmental and lifelog measurements to
normalised 0-100 immune-relevant scores.

All functions accept numpy arrays or scalar values and return normalised
0-100 scores.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _to_array(x: ArrayLike) -> np.ndarray:
    """Coerce scalar or array-like to ndarray."""
    return np.atleast_1d(np.asarray(x, dtype=np.float64))


def _normalise_minmax(
    x: np.ndarray,
    x_min: float,
    x_max: float,
) -> np.ndarray:
    """Min-max normalise *x* to [0, 1], clamping to [x_min, x_max]."""
    clamped = np.clip(x, x_min, x_max)
    denom = x_max - x_min
    if denom == 0:
        return np.zeros_like(clamped)
    return (clamped - x_min) / denom


# ---------------------------------------------------------------------------
# Oxidative Stress Load (OSL)
# ---------------------------------------------------------------------------

def oxidative_stress_load(
    pm25: ArrayLike,
    voc_index: ArrayLike,
    o3: ArrayLike,
    *,
    w_pm25: float = 0.50,
    w_voc: float = 0.30,
    w_o3: float = 0.20,
) -> np.ndarray:
    """Compute Oxidative Stress Load (OSL).

    Ontology mapping
    ----------------
    ico:OxidativeStressLoad  (rdfs:subClassOf ico:CompositeEnvironmentalIndex)

    Formula
    -------
    OSL = w_pm25 * norm(PM2.5) + w_voc * norm(VOC_index) + w_o3 * norm(O3)

    Normalisation ranges (WHO guideline-based):
      - PM2.5: 0-250 ug/m3  (WHO 24-h guideline 15 ug/m3 = low end)
      - VOC index: 0-500     (Sensirion SGP41 scale)
      - O3: 0-200 ppb        (WHO 8-h guideline ~50 ppb)

    Parameters
    ----------
    pm25 : array-like
        PM2.5 concentration in ug/m3.
    voc_index : array-like
        SGP41 VOC index (0-500).
    o3 : array-like
        Ozone concentration in ppb.
    w_pm25, w_voc, w_o3 : float
        Component weights (must sum to 1).

    Returns
    -------
    np.ndarray
        OSL score normalised to 0-100.
    """
    pm25_n = _normalise_minmax(_to_array(pm25), 0.0, 250.0)
    voc_n = _normalise_minmax(_to_array(voc_index), 0.0, 500.0)
    o3_n = _normalise_minmax(_to_array(o3), 0.0, 200.0)

    osl = w_pm25 * pm25_n + w_voc * voc_n + w_o3 * o3_n
    return np.clip(osl * 100.0, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Allergen Exposure Score (AES)
# ---------------------------------------------------------------------------

def _humidity_risk(rh: np.ndarray) -> np.ndarray:
    """Non-linear humidity risk.

    Risk rises sharply above 60% RH (dust mite / mold threshold).
    Uses a logistic curve centred at 65% RH.
    """
    return 1.0 / (1.0 + np.exp(-0.3 * (rh - 65.0)))


def _mold_risk_score(rh: np.ndarray) -> np.ndarray:
    """Mold growth risk from ASHRAE model proxy.

    Risk is negligible below 60% RH and increases rapidly above 70%.
    """
    return np.clip((rh - 55.0) / 35.0, 0.0, 1.0) ** 2


def _dust_mite_risk_score(rh: np.ndarray) -> np.ndarray:
    """Dust mite proliferation risk.

    Optimal dust mite conditions: 70-80% RH. Minimal below 50%.
    """
    return np.clip((rh - 50.0) / 30.0, 0.0, 1.0)


def allergen_exposure_score(
    rh: ArrayLike,
    mold_risk: ArrayLike | None = None,
    dust_mite_risk: ArrayLike | None = None,
    *,
    w_humidity: float = 0.40,
    w_mold: float = 0.35,
    w_dust: float = 0.25,
) -> np.ndarray:
    """Compute Allergen Exposure Score (AES).

    Ontology mapping
    ----------------
    ico:AllergenExposureScore  (rdfs:subClassOf ico:CompositeEnvironmentalIndex)

    Formula
    -------
    AES = w_humidity * humidity_risk(RH) + w_mold * mold_risk + w_dust * dust_mite_risk

    If mold_risk or dust_mite_risk are not provided, they are derived
    from relative humidity using built-in proxy models.

    Parameters
    ----------
    rh : array-like
        Relative humidity in %.
    mold_risk : array-like or None
        External mold risk score (0-1). Derived from RH if None.
    dust_mite_risk : array-like or None
        External dust mite risk score (0-1). Derived from RH if None.

    Returns
    -------
    np.ndarray
        AES score normalised to 0-100.
    """
    rh_arr = _to_array(rh)

    hr = _humidity_risk(rh_arr)
    mr = _to_array(mold_risk) if mold_risk is not None else _mold_risk_score(rh_arr)
    dr = _to_array(dust_mite_risk) if dust_mite_risk is not None else _dust_mite_risk_score(rh_arr)

    aes = w_humidity * hr + w_mold * mr + w_dust * dr
    return np.clip(aes * 100.0, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Ventilation Index (VI)
# ---------------------------------------------------------------------------

def ventilation_index(
    co2_series: ArrayLike,
    *,
    reference_decay_rate: float = 15.0,
    window_size: int = 30,
) -> np.ndarray:
    """Compute Ventilation Index (VI) from CO2 time series.

    Ontology mapping
    ----------------
    ico:VentilationIndex  (rdfs:subClassOf ico:CompositeEnvironmentalIndex)

    Formula
    -------
    VI = 100 * clamp(decay_rate / reference_decay_rate, 0, 1)

    Where decay_rate is the negative slope (ppm/min) of CO2 within a
    rolling window when CO2 is decreasing, indicating active ventilation.

    A perfect VI of 100 means ventilation is at or above the reference
    air-change rate (default 0.5 ACH ~ 15 ppm/min decay).

    Parameters
    ----------
    co2_series : array-like
        CO2 concentration time series in ppm (1-min intervals assumed).
    reference_decay_rate : float
        Expected CO2 decay rate at 0.5 ACH (ppm/min).
    window_size : int
        Rolling window size in samples for slope estimation.

    Returns
    -------
    np.ndarray
        VI score normalised to 0-100 (100 = excellent ventilation).
    """
    co2 = _to_array(co2_series)
    n = len(co2)

    if n < window_size:
        # Not enough data — return neutral score
        return np.full(n, 50.0)

    # Rolling slope via least-squares (vectorised)
    vi = np.full(n, 50.0)
    x = np.arange(window_size, dtype=np.float64)
    x_mean = x.mean()
    x_var = np.sum((x - x_mean) ** 2)

    for i in range(window_size, n):
        y = co2[i - window_size : i]
        slope = np.sum((x - x_mean) * (y - y.mean())) / (x_var + 1e-12)
        if slope < 0:
            # Decay detected — measure how fast
            decay = -slope  # ppm/min (positive)
            vi[i] = min(100.0, 100.0 * decay / reference_decay_rate)
        else:
            # CO2 rising or flat — poor ventilation
            vi[i] = max(0.0, 50.0 - 50.0 * slope / reference_decay_rate)

    return np.clip(vi, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Immune Risk Score (IRS)
# ---------------------------------------------------------------------------

def immune_risk_score(
    osl: ArrayLike,
    aes: ArrayLike,
    hrv_sdnn: ArrayLike,
    sleep_quality: ArrayLike,
    spo2: ArrayLike,
    *,
    w_osl: float = 0.25,
    w_aes: float = 0.15,
    w_hrv: float = 0.25,
    w_sleep: float = 0.20,
    w_spo2: float = 0.15,
) -> np.ndarray:
    """Compute multi-layer Immune Risk Score (IRS).

    Ontology mapping
    ----------------
    ico:ImmuneRiskScore

    Formula
    -------
    IRS = w_osl * OSL/100
        + w_aes * AES/100
        + w_hrv * (1 - norm_hrv)     # low HRV = high risk
        + w_sleep * (1 - sleep/100)  # low sleep = high risk
        + w_spo2 * (1 - norm_spo2)   # low SpO2 = high risk

    HRV normalisation: SDNN 0-150 ms (WHO/clinical range).
    SpO2 normalisation: 85-100% (clinical range).

    Returns
    -------
    np.ndarray
        IRS score normalised to 0-100 (100 = highest risk).
    """
    osl_n = _normalise_minmax(_to_array(osl), 0.0, 100.0)
    aes_n = _normalise_minmax(_to_array(aes), 0.0, 100.0)
    hrv_n = _normalise_minmax(_to_array(hrv_sdnn), 0.0, 150.0)
    sleep_n = _normalise_minmax(_to_array(sleep_quality), 0.0, 100.0)
    spo2_n = _normalise_minmax(_to_array(spo2), 85.0, 100.0)

    irs = (
        w_osl * osl_n
        + w_aes * aes_n
        + w_hrv * (1.0 - hrv_n)
        + w_sleep * (1.0 - sleep_n)
        + w_spo2 * (1.0 - spo2_n)
    )
    return np.clip(irs * 100.0, 0.0, 100.0)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick smoke test with scalar and array inputs
    print("=== Composite Index Smoke Test ===\n")

    osl_val = oxidative_stress_load(pm25=35.0, voc_index=180.0, o3=45.0)
    print(f"OSL (PM2.5=35, VOC=180, O3=45):  {osl_val[0]:.1f}")

    aes_val = allergen_exposure_score(rh=72.0)
    print(f"AES (RH=72%):                    {aes_val[0]:.1f}")

    co2 = np.concatenate([
        np.linspace(1200, 1200, 20),   # stable high
        np.linspace(1200, 500, 40),    # ventilation decay
        np.linspace(500, 500, 20),     # stable low
    ])
    vi = ventilation_index(co2)
    print(f"VI  peak (during decay):         {vi.max():.1f}")

    irs_val = immune_risk_score(
        osl=osl_val, aes=aes_val, hrv_sdnn=35.0, sleep_quality=40.0, spo2=94.0,
    )
    print(f"IRS (stressed scenario):         {irs_val[0]:.1f}")

    # Array test
    pm25_arr = np.array([10, 50, 100, 200])
    voc_arr = np.array([80, 150, 300, 450])
    o3_arr = np.array([20, 40, 80, 150])
    osl_arr = oxidative_stress_load(pm25_arr, voc_arr, o3_arr)
    print(f"\nOSL array: {np.round(osl_arr, 1)}")

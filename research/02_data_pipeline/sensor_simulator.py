"""
Sensor Data Simulator for Digital Columbus Immune Care Pipeline.

Generates realistic time-series data for Layer 1 (Environmental) and
Layer 2 (Lifelog) sensors with circadian rhythms, cross-layer correlations,
and configurable anomaly scenarios.

Ontology reference: ico:EnvironmentalFactor, ico:LifelogObservation
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ScenarioName = Literal["normal", "pollution_event", "sleep_deprived", "allergic_flare"]


@dataclass
class SensorConfig:
    """Physical range and normal baseline for a single signal."""
    name: str
    unit: str
    range_min: float
    range_max: float
    normal_mean: float
    normal_std: float
    circadian_amplitude: float = 0.0   # fraction of normal_mean
    circadian_phase_hr: float = 0.0    # peak hour (0-24)


LAYER1_SENSORS: list[SensorConfig] = [
    SensorConfig("pm25",        "ug/m3", 0,   500,  25.0,  8.0,   0.20, 14.0),
    SensorConfig("pm10",        "ug/m3", 0,   600,  45.0,  15.0,  0.20, 14.0),
    SensorConfig("voc_index",   "",      0,   500,  125.0, 30.0,  0.15, 10.0),
    SensorConfig("co2",         "ppm",   400, 5000, 600.0, 120.0, 0.25, 22.0),
    SensorConfig("temperature", "degC",  15,  35,   23.0,  2.0,   0.10, 15.0),
    SensorConfig("humidity",    "%RH",   30,  80,   55.0,  8.0,   0.12, 5.0),
    SensorConfig("btex",        "ppb",   0,   100,  8.0,   4.0,   0.10, 10.0),
    SensorConfig("o3",          "ppb",   0,   100,  25.0,  10.0,  0.30, 14.0),
]

LAYER2_SENSORS: list[SensorConfig] = [
    SensorConfig("hrv_sdnn",       "ms",        0,   200,  65.0,  15.0, 0.20, 3.0),
    SensorConfig("spo2",           "%",         70,  100,  97.5,  0.8,  0.02, 4.0),
    SensorConfig("sleep_quality",  "score",     0,   100,  72.0,  10.0, 0.0,  0.0),
    SensorConfig("activity_level", "steps/hr",  0,   1000, 250.0, 120.0, 0.60, 12.0),
    SensorConfig("skin_temp",      "degC",      30.0, 37.0, 33.5,  0.5,  0.05, 4.0),
]


# ---------------------------------------------------------------------------
# Core generation helpers
# ---------------------------------------------------------------------------

def _circadian(
    timestamps: pd.DatetimeIndex,
    amplitude: float,
    phase_hr: float,
) -> np.ndarray:
    """Return a circadian modulation curve (unitless, centered at 0)."""
    hours = timestamps.hour + timestamps.minute / 60.0
    return amplitude * np.sin(2 * np.pi * (hours - phase_hr + 6) / 24.0)


def _generate_signal(
    cfg: SensorConfig,
    timestamps: pd.DatetimeIndex,
    rng: np.random.Generator,
    spike_prob: float = 0.002,
    spike_magnitude: float = 3.0,
) -> np.ndarray:
    """Generate a single realistic sensor signal.

    Components:
      1. Baseline mean
      2. Circadian modulation
      3. Gaussian noise
      4. Random spikes (Poisson-triggered)
    """
    n = len(timestamps)
    base = cfg.normal_mean * np.ones(n)

    # Circadian
    circ = _circadian(timestamps, cfg.circadian_amplitude * cfg.normal_mean, cfg.circadian_phase_hr)
    base += circ

    # Noise
    noise = rng.normal(0, cfg.normal_std, n)
    signal = base + noise

    # Spikes
    spike_mask = rng.random(n) < spike_prob
    spikes = spike_mask * rng.uniform(spike_magnitude * 0.5, spike_magnitude, n) * cfg.normal_std
    signal += spikes

    # Clamp to physical range
    return np.clip(signal, cfg.range_min, cfg.range_max)


# ---------------------------------------------------------------------------
# Cross-layer correlation
# ---------------------------------------------------------------------------

def _apply_cross_layer_correlation(
    df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply physiologically plausible cross-layer correlations.

    Key relationships (from domain analysis):
      - PM2.5 up  ->  HRV down  (r=-0.42, lag ~6 h)
      - PM2.5 up  ->  SpO2 down (r=-0.35, lag ~4 h)
      - High humidity -> mold risk -> sleep quality down
    """
    interval_min = (df.index[1] - df.index[0]).total_seconds() / 60.0
    lag_6h = int(round(360 / interval_min))
    lag_4h = int(round(240 / interval_min))

    # Normalised PM2.5 perturbation (0-1 scale)
    pm25_norm = (df["pm25"] - df["pm25"].min()) / (df["pm25"].max() - df["pm25"].min() + 1e-9)
    pm25_shifted_6h = pm25_norm.shift(lag_6h).fillna(0.0).values
    pm25_shifted_4h = pm25_norm.shift(lag_4h).fillna(0.0).values

    # HRV depression when PM2.5 was high 6 h ago
    df["hrv_sdnn"] -= pm25_shifted_6h * 20.0
    df["hrv_sdnn"] = df["hrv_sdnn"].clip(lower=5.0)

    # SpO2 depression when PM2.5 was high 4 h ago
    df["spo2"] -= pm25_shifted_4h * 2.0
    df["spo2"] = df["spo2"].clip(lower=85.0, upper=100.0)

    return df


# ---------------------------------------------------------------------------
# Scenario modifiers
# ---------------------------------------------------------------------------

def _apply_scenario(
    df: pd.DataFrame,
    scenario: ScenarioName,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Overlay scenario-specific patterns onto the baseline data."""

    if scenario == "normal":
        return df

    n = len(df)
    hours = df.index.hour + df.index.minute / 60.0

    if scenario == "pollution_event":
        # A 4-hour PM2.5/VOC spike on each simulated day between 11:00-15:00
        spike_window = (hours >= 11) & (hours <= 15)
        spike_envelope = np.where(spike_window, np.sin(np.pi * (hours - 11) / 4.0), 0.0)
        df["pm25"] += spike_envelope * 180.0   # peak ~200 ug/m3
        df["pm10"] += spike_envelope * 120.0
        df["voc_index"] += spike_envelope * 150.0
        df["o3"] += spike_envelope * 30.0
        df["btex"] += spike_envelope * 25.0
        # Clamp
        for col in ["pm25", "pm10", "voc_index", "o3", "btex"]:
            cfg = next(c for c in LAYER1_SENSORS if c.name == col)
            df[col] = df[col].clip(cfg.range_min, cfg.range_max)

    elif scenario == "sleep_deprived":
        # Sleep quality drops to 20-40 during night windows
        night = (hours >= 22) | (hours <= 6)
        df.loc[night, "sleep_quality"] = rng.uniform(20, 40, night.sum())
        # Next-day HRV suppression (entire day following poor sleep)
        day_mask = (hours >= 6) & (hours <= 22)
        df.loc[day_mask, "hrv_sdnn"] *= 0.65
        df.loc[day_mask, "spo2"] -= 1.0
        df["spo2"] = df["spo2"].clip(85.0, 100.0)
        df["hrv_sdnn"] = df["hrv_sdnn"].clip(5.0)

    elif scenario == "allergic_flare":
        # Sustained high humidity + mold/dust risk -> immune response
        df["humidity"] = df["humidity"].clip(lower=65.0)
        df["humidity"] += rng.uniform(0, 10, n)
        df["humidity"] = df["humidity"].clip(upper=95.0)
        # Prolonged low HRV, lower SpO2
        df["hrv_sdnn"] *= 0.75
        df["spo2"] -= 1.5
        df["hrv_sdnn"] = df["hrv_sdnn"].clip(5.0)
        df["spo2"] = df["spo2"].clip(85.0, 100.0)

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_sensor_data(
    duration_hours: int = 24,
    interval_minutes: int = 1,
    scenario: ScenarioName = "normal",
    seed: int = 42,
    start_time: str | None = None,
) -> pd.DataFrame:
    """Generate a DataFrame of simulated sensor data.

    Parameters
    ----------
    duration_hours : int
        Total simulation duration in hours.
    interval_minutes : int
        Sampling interval in minutes.
    scenario : ScenarioName
        One of "normal", "pollution_event", "sleep_deprived", "allergic_flare".
    seed : int
        Random seed for reproducibility.
    start_time : str or None
        ISO-format start timestamp. Defaults to "2026-03-30T00:00:00".

    Returns
    -------
    pd.DataFrame
        Columns for every sensor signal, indexed by UTC timestamps.
    """
    rng = np.random.default_rng(seed)
    if start_time is None:
        start_time = "2026-03-30T00:00:00"

    timestamps = pd.date_range(
        start=start_time,
        periods=int(duration_hours * 60 / interval_minutes),
        freq=f"{interval_minutes}min",
    )

    data: dict[str, np.ndarray] = {}

    for cfg in LAYER1_SENSORS:
        data[cfg.name] = _generate_signal(cfg, timestamps, rng)

    for cfg in LAYER2_SENSORS:
        data[cfg.name] = _generate_signal(cfg, timestamps, rng)

    df = pd.DataFrame(data, index=timestamps)
    df.index.name = "timestamp"

    # Apply scenario modifications
    df = _apply_scenario(df, scenario, rng)

    # Apply cross-layer physiological correlations
    df = _apply_cross_layer_correlation(df, rng)

    return df


def generate_scenario(
    scenario: ScenarioName,
    duration_hours: int = 48,
    interval_minutes: int = 1,
    seed: int = 42,
) -> pd.DataFrame:
    """Convenience wrapper to generate data for a named scenario.

    Preset scenarios
    ----------------
    - "normal"          : Typical day with baseline fluctuations.
    - "pollution_event" : PM2.5/VOC spike (11:00-15:00) with lagged immune response.
    - "sleep_deprived"  : Poor sleep quality with next-day biomarker elevation.
    - "allergic_flare"  : High allergen exposure triggering Th2 response proxy.

    Returns
    -------
    pd.DataFrame
        Sensor data for the requested scenario.
    """
    return generate_sensor_data(
        duration_hours=duration_hours,
        interval_minutes=interval_minutes,
        scenario=scenario,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    for name in ("normal", "pollution_event", "sleep_deprived", "allergic_flare"):
        df = generate_scenario(name, duration_hours=24)  # type: ignore[arg-type]
        print(f"\n=== Scenario: {name} ({len(df)} samples) ===")
        print(df.describe().round(2).to_string())

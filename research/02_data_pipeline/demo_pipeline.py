#!/usr/bin/env python3
"""
Demo Pipeline for Digital Columbus Immune Care Data Pipeline.

Demonstrates the end-to-end flow:
  1. Generate 48 hours of simulated sensor data (pollution_event scenario)
  2. Compute composite environmental and immune risk indices
  3. Map a sample window to RDF triples (Turtle format)
  4. Print summary statistics and example triples

Usage:
    python3 demo_pipeline.py
"""

from __future__ import annotations

import sys
from datetime import datetime

import numpy as np
import pandas as pd

from sensor_simulator import generate_scenario
from composite_index import (
    oxidative_stress_load,
    allergen_exposure_score,
    ventilation_index,
    immune_risk_score,
)
from ontology_mapper import map_dataframe_to_rdf, graph_to_turtle


def compute_indices(df: pd.DataFrame) -> pd.DataFrame:
    """Add composite index columns to the sensor DataFrame."""
    df = df.copy()

    df["osl"] = oxidative_stress_load(
        pm25=df["pm25"].values,
        voc_index=df["voc_index"].values,
        o3=df["o3"].values,
    )

    df["aes"] = allergen_exposure_score(
        rh=df["humidity"].values,
    )

    df["vi"] = ventilation_index(
        co2_series=df["co2"].values,
    )

    df["irs"] = immune_risk_score(
        osl=df["osl"].values,
        aes=df["aes"].values,
        hrv_sdnn=df["hrv_sdnn"].values,
        sleep_quality=df["sleep_quality"].values,
        spo2=df["spo2"].values,
    )

    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print human-readable summary statistics."""
    separator = "=" * 72

    print(f"\n{separator}")
    print("  DIGITAL COLUMBUS - Immune Care Data Pipeline Demo")
    print(f"{separator}\n")

    print(f"Time range : {df.index[0]} -> {df.index[-1]}")
    print(f"Samples    : {len(df):,}")
    print(f"Columns    : {', '.join(df.columns)}\n")

    # Environmental summary
    env_cols = ["pm25", "pm10", "voc_index", "co2", "temperature", "humidity", "btex", "o3"]
    print("--- Layer 1: Environmental Sensors ---")
    print(df[env_cols].describe().round(2).to_string())

    # Lifelog summary
    lifelog_cols = ["hrv_sdnn", "spo2", "sleep_quality", "activity_level", "skin_temp"]
    print("\n--- Layer 2: Lifelog / Biosignals ---")
    print(df[lifelog_cols].describe().round(2).to_string())

    # Composite indices summary
    index_cols = ["osl", "aes", "vi", "irs"]
    print("\n--- Composite Indices ---")
    print(df[index_cols].describe().round(2).to_string())

    # Key correlations
    print("\n--- Cross-Layer Correlations ---")
    pairs = [
        ("pm25", "hrv_sdnn"),
        ("pm25", "spo2"),
        ("osl", "irs"),
        ("humidity", "aes"),
    ]
    for a, b in pairs:
        r = df[a].corr(df[b])
        print(f"  {a:>15s} <-> {b:<20s}  r = {r:+.3f}")

    # Peak pollution event detection
    peak_osl_idx = df["osl"].idxmax()
    peak_irs_idx = df["irs"].idxmax()
    print(f"\n--- Peak Events ---")
    print(f"  Highest OSL: {df.loc[peak_osl_idx, 'osl']:.1f}  at {peak_osl_idx}")
    print(f"  Highest IRS: {df.loc[peak_irs_idx, 'irs']:.1f}  at {peak_irs_idx}")

    # Lag analysis: find IRS peak relative to OSL peak
    lag_minutes = (peak_irs_idx - peak_osl_idx).total_seconds() / 60.0
    print(f"  IRS peak lag vs OSL peak: {lag_minutes:.0f} minutes ({lag_minutes / 60:.1f} hours)")


def print_rdf_sample(df: pd.DataFrame, n_rows: int = 5) -> None:
    """Generate and print RDF triples for a small sample window."""
    separator = "=" * 72

    print(f"\n{separator}")
    print(f"  RDF Triple Generation (first {n_rows} rows)")
    print(f"{separator}\n")

    graph = map_dataframe_to_rdf(df, patient_id="P001", max_rows=n_rows)

    turtle_str = graph_to_turtle(graph)
    triple_count = len(graph)

    print(f"Generated {triple_count} triples from {n_rows} observation rows.\n")

    # Print first ~3000 chars of Turtle output
    max_chars = 3000
    if len(turtle_str) > max_chars:
        print(turtle_str[:max_chars])
        print(f"\n... ({len(turtle_str) - max_chars} more characters) ...")
    else:
        print(turtle_str)


def main() -> None:
    """Run the full demo pipeline."""
    print("Generating 48 hours of simulated sensor data (pollution_event scenario)...")
    df = generate_scenario("pollution_event", duration_hours=48, seed=42)
    print(f"  -> {len(df):,} samples generated.")

    print("Computing composite indices...")
    df = compute_indices(df)
    print("  -> OSL, AES, VI, IRS columns added.")

    # Summary statistics
    print_summary(df)

    # RDF generation for a sample around the peak pollution event
    peak_idx = df["osl"].idxmax()
    window_start = peak_idx - pd.Timedelta(minutes=2)
    window_end = peak_idx + pd.Timedelta(minutes=2)
    sample_window = df.loc[window_start:window_end]

    print_rdf_sample(sample_window, n_rows=5)

    print("\nDemo pipeline completed successfully.")


if __name__ == "__main__":
    main()

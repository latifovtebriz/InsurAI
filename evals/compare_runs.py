"""Compares metrics between two evaluation report JSON files to evaluate iterations."""

import argparse
import json
import sys
from pathlib import Path


def compare_reports(file_a: Path, file_b: Path) -> dict[str, dict[str, float]]:
    with open(file_a, encoding="utf-8") as f:
        data_a = json.load(f)
    with open(file_b, encoding="utf-8") as f:
        data_b = json.load(f)

    metrics_a = data_a.get("metrics", data_a)
    metrics_b = data_b.get("metrics", data_b)

    deltas: dict[str, dict[str, float]] = {}
    all_keys = set(metrics_a.keys()).union(set(metrics_b.keys()))

    for k in sorted(all_keys):
        val_a = metrics_a.get(k, 0.0)
        val_b = metrics_b.get(k, 0.0)
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            diff = val_b - val_a
            deltas[k] = {"run_a": float(val_a), "run_b": float(val_b), "delta": float(diff)}

    return deltas


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two eval runs.")
    parser.add_argument("run_a", type=Path, help="Path to baseline run JSON")
    parser.add_argument("run_b", type=Path, help="Path to new iteration run JSON")
    args = parser.parse_args()

    if not args.run_a.exists() or not args.run_b.exists():
        print("One or both input files do not exist.")
        sys.exit(1)

    deltas = compare_reports(args.run_a, args.run_b)
    print("\n--- EVALUATION RUN COMPARISON ---")
    print(f"{'Metric':30s} | {'Baseline':10s} | {'New Run':10s} | {'Delta':10s}")
    print("-" * 68)
    for k, v in deltas.items():
        sign = "+" if v["delta"] > 0 else ""
        print(f"{k:30s} | {v['run_a']:10.2f} | {v['run_b']:10.2f} | {sign}{v['delta']:10.2f}")


if __name__ == "__main__":
    main()

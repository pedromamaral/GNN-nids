#!/usr/bin/env python3
"""Aggregate decomposition runs and apply the Phase 1 go/no-go criteria.

Reads every ``decomposition.csv`` under ``--results-dir`` (default
``results/decomposition``) and writes:

    decomposition_summary.csv  mean ± std of each condition, per scenario
    decomposition_effects.csv  feature / structure / combined / interaction effects
    go_no_go.csv               the two kill-experiment tests, per scenario

Go/no-go (docs/PAPER_ROADMAP.md, Phase 1). For each scenario
(dataset, model, k, hidden_layers, epsilon) the coupling is considered
material if EITHER holds, consistently across seeds:

  1. Induced structure hurts:  ΔF1 under condition B of ``pgd``
     >= --structure-threshold (default 0.05), one-sided Wilcoxon p < --alpha.
  2. Adaptive attacker gains:  F1(pgd, A) - F1(pgd_rebuild, C)
     >= --adaptive-threshold (default 0.03), paired over (training_seed,
     attack_seed), one-sided Wilcoxon p < --alpha.

go_no_go.csv also splits test 2 into the deployment gap (pgd: A vs C) and the
extra gain from anticipating the rebuild (pgd C vs pgd_rebuild C).

Usage:
    python experiments/05b_decomposition_report.py
    python experiments/05b_decomposition_report.py --results-dir results/decomposition --out-dir results/reports
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon
except ModuleNotFoundError:  # pragma: no cover
    wilcoxon = None

SCENARIO = ["dataset", "model", "k", "hidden_layers", "epsilon"]
PAIR = ["training_seed", "attack_seed"]


def load_runs(results_dir: Path) -> pd.DataFrame:
    files = sorted(results_dir.rglob("decomposition.csv"))
    if not files:
        raise FileNotFoundError(f"No decomposition.csv files under {results_dir}")
    frames = [pd.read_csv(f).assign(source=str(f.parent.name)) for f in files]
    return pd.concat(frames, ignore_index=True)


def one_sided_wilcoxon(values: np.ndarray) -> float:
    """p-value for H1: median(values) > 0. Returns nan when undefined."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if wilcoxon is None or values.size < 2 or np.allclose(values, 0.0):
        return float("nan")
    try:
        return float(wilcoxon(values, alternative="greater").pvalue)
    except ValueError:
        return float("nan")


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(SCENARIO + ["attack", "condition"])
    out = grouped.agg(
        n=("f1", "size"),
        clean_f1=("clean_f1", "mean"),
        f1_mean=("f1", "mean"),
        f1_std=("f1", "std"),
        delta_f1_mean=("delta_f1", "mean"),
        delta_f1_std=("delta_f1", "std"),
        ncr_malicious_mean=("ncr_malicious", "mean"),
        ncr_global_mean=("ncr_global", "mean"),
    )
    return out.reset_index()


def effects(df: pd.DataFrame) -> pd.DataFrame:
    wide = df.pivot_table(index=SCENARIO + ["attack"] + PAIR, columns="condition", values="delta_f1").reset_index()
    for cond in ("A", "B", "C"):
        if cond not in wide:
            wide[cond] = np.nan
    wide = wide.rename(columns={"A": "feature", "B": "structure", "C": "combined"})
    wide["interaction"] = wide["combined"] - wide["feature"] - wide["structure"]
    agg = wide.groupby(SCENARIO + ["attack"])[["feature", "structure", "combined", "interaction"]].agg(["mean", "std"])
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    return agg.reset_index()


def go_no_go(df: pd.DataFrame, structure_threshold: float, adaptive_threshold: float, alpha: float) -> pd.DataFrame:
    rows = []
    for key, scenario in df.groupby(SCENARIO):
        record = dict(zip(SCENARIO, key))

        b = scenario[(scenario.attack == "pgd") & (scenario.condition == "B")]["delta_f1"].to_numpy()
        record["structure_effect_mean"] = float(np.mean(b)) if b.size else float("nan")
        record["structure_effect_p"] = one_sided_wilcoxon(b - structure_threshold) if b.size else float("nan")
        record["structure_n"] = int(b.size)

        a = scenario[(scenario.attack == "pgd") & (scenario.condition == "A")].set_index(PAIR)["f1"]
        c_star = scenario[(scenario.attack == "pgd_rebuild") & (scenario.condition == "C")].set_index(PAIR)["f1"]
        paired = pd.concat([a.rename("A"), c_star.rename("C_star")], axis=1, join="inner")
        gain = (paired["A"] - paired["C_star"]).to_numpy()
        record["adaptive_gain_mean"] = float(np.mean(gain)) if gain.size else float("nan")
        record["adaptive_gain_p"] = one_sided_wilcoxon(gain - adaptive_threshold) if gain.size else float("nan")
        record["adaptive_n"] = int(gain.size)

        # Informative split of the gain (not used in the verdict):
        #   deployment_gap  = F1(pgd, A) - F1(pgd, C)          evaluating on the rebuilt graph
        #   adaptive_over_C = F1(pgd, C) - F1(pgd_rebuild, C)  anticipating the rebuild while attacking
        c_plain = scenario[(scenario.attack == "pgd") & (scenario.condition == "C")].set_index(PAIR)["f1"]
        three = pd.concat([a.rename("A"), c_plain.rename("C"), c_star.rename("C_star")], axis=1, join="inner")
        record["deployment_gap_mean"] = float((three["A"] - three["C"]).mean()) if len(three) else float("nan")
        record["adaptive_over_C_mean"] = float((three["C"] - three["C_star"]).mean()) if len(three) else float("nan")

        structure_go = (
            record["structure_effect_mean"] >= structure_threshold and record["structure_effect_p"] < alpha
        )
        adaptive_go = record["adaptive_gain_mean"] >= adaptive_threshold and record["adaptive_gain_p"] < alpha
        record["structure_go"] = bool(structure_go)
        record["adaptive_go"] = bool(adaptive_go)
        record["verdict"] = "GO" if (structure_go or adaptive_go) else "no-go"
        rows.append(record)
    return pd.DataFrame(rows)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results-dir", type=Path, default=Path("results") / "decomposition")
    parser.add_argument("--out-dir", type=Path, default=None, help="Default: --results-dir.")
    parser.add_argument("--structure-threshold", type=float, default=0.05)
    parser.add_argument("--adaptive-threshold", type=float, default=0.03)
    parser.add_argument("--alpha", type=float, default=0.05)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    out_dir = args.out_dir or args.results_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_runs(args.results_dir)
    summary = summarise(df)
    eff = effects(df)
    verdict = go_no_go(df, args.structure_threshold, args.adaptive_threshold, args.alpha)

    summary.to_csv(out_dir / "decomposition_summary.csv", index=False)
    eff.to_csv(out_dir / "decomposition_effects.csv", index=False)
    verdict.to_csv(out_dir / "go_no_go.csv", index=False)

    with pd.option_context("display.max_columns", None, "display.width", 200, "display.float_format", "{:.4f}".format):
        print("\nDecomposition effects (ΔF1, mean over seeds):")
        cols = SCENARIO + ["attack", "feature_mean", "structure_mean", "combined_mean", "interaction_mean"]
        print(eff[cols].to_string(index=False))
        print("\nGo / no-go:")
        print(verdict.to_string(index=False))

    overall = "GO" if (verdict["verdict"] == "GO").any() else "no-go"
    print(f"\nOverall Phase 1 verdict: {overall}  (GO if any scenario passes either test)")
    print(f"Tables written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

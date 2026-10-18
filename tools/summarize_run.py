#!/usr/bin/env python3
"""Raw run directories -> .mem/results/E###.json + a short table.

    python tools/summarize_run.py E015 GPUserver2:results/runs/<dir> [more specs] [--labels ip ...]

A spec is a local directory or HOST:DIR (DIR relative to ~/GNN-nids unless
absolute). For a remote spec this script is piped to the server's python3
(`--extract`), so only the compact summary crosses the network.

Understood layouts:
    gnn      results/runs/<run>/metrics.json (01_baseline_training.py)
    tabular  results/tabular/<run>/summary.csv + config.json (00_tabular_baselines.py)
    generic  any other dir with *.json: numeric leaves, at most 40
A dir without its final file is reported as `incomplete`.

Runs already in E###.json are replaced by (host, dir); others are kept, so a
seed grid can be added as its runs finish. Standard library only.
"""

import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REMOTE_REPO = "~/GNN-nids"
TEST_KEYS = ("f1", "roc_auc", "precision", "recall")
# Report CSVs: file -> (row key columns, value columns); rows sharing a key are averaged.
CSV_SPECS = {
    "graph_ablation.csv": (("dataset", "model", "node_key", "graph"), ("f1", "changed")),
    "go_no_go.csv": (("dataset", "model", "epsilon"), ("structure_effect_mean", "adaptive_gain_mean")),
    # E017/E020 (08): per detector x attack seed x beta; Delta = clean recall - attacked recall at 1% FPR
    "summary.csv": (("detector", "origin", "attack_seed", "delay", "beta"), ("delta_A", "delta_B", "delta_Cstar", "G", "S_max_abs")),
    "summary_hostwin.csv": (("detector", "attack_seed", "delay", "beta"), ("delta_A", "delta_B", "delta_Cstar", "G", "S_max_abs")),
    "rows.csv": (("detector", "attack_seed", "delay", "beta", "rho", "condition"),
                 ("recall", "fpr", "recall_05", "decoy_alarm_rate", "hostwin_recall", "hostwin_recall_dec")),
}
SHORT = {"nf-unsw-nb15-v3": "unsw", "nf-ton-iot-v3": "ton"}


def git_sha_before(repo, started):
    """Last commit before the run started (runs do not record their sha)."""
    if not started:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%h", f"--before={started}"],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def started_from_name(name):
    m = re.match(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", name)
    return "{}-{}-{} {}:{}:{}".format(*m.groups()) if m else None


def numeric_leaves(obj, prefix="", out=None, limit=40):
    out = {} if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            numeric_leaves(v, f"{prefix}{k}/" if not isinstance(v, (int, float)) else f"{prefix}{k}", out, limit)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix.rstrip("/")] = {"final": obj}
    return out


def table_metrics(path, keys, values):
    groups = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            key = "/".join(SHORT.get(row.get(k, ""), row.get(k, "")) or "-" for k in keys)
            for v in values:
                try:
                    groups.setdefault(f"{key}/{v}", []).append(float(row[v]))
                except (KeyError, TypeError, ValueError):
                    pass
    return {k: {"final": sum(v) / len(v), "n": len(v)} for k, v in list(groups.items())[:20000]}


def extract(run_dir):
    """Compact record for one run directory (runs where the data lives)."""
    d = Path(os.path.expanduser(run_dir))
    rec = {"dir": run_dir, "started": started_from_name(d.name), "status": "missing",
           "kind": None, "config": {}, "metrics": {}, "artifacts": [], "log_tail": None}
    if not d.is_dir():
        return rec
    rec["artifacts"] = sorted(
        f"{p.name} ({p.stat().st_size // 1024} KB)" for p in d.iterdir() if p.is_file()
    )[:12]
    metrics_path, summary_path = d / "metrics.json", d / "summary.csv"

    if metrics_path.exists():
        m = json.loads(metrics_path.read_text())
        if "fit" in m and "metrics" in m:
            rec["kind"], rec["status"] = "gnn", "finished"
            cfg = m.get("config", {})
            rt = cfg.get("runtime_config", {})
            rec["config"] = {"dataset": cfg.get("dataset"), "model": cfg.get("model"), "run_id": m.get("run_id"),
                             **{k: rt.get(k) for k in ("seed", "window_size", "hidden_layers", "epochs",
                                                       "learning_rate", "k", "max_flows")}}
            for split in ("test", "train"):
                for key in TEST_KEYS if split == "test" else ("f1",):
                    val = m["metrics"].get(split, {}).get(key)
                    if val is not None:
                        rec["metrics"][f"{split}_{key}"] = {"final": val}
            hist = m["fit"].get("history", [])
            vals = [(h.get("val_metrics") or {}).get("f1") for h in hist]
            vals = [(i, v) for i, v in enumerate(vals) if v is not None]
            if vals:
                best_i, best_v = max(vals, key=lambda t: t[1])
                rec["metrics"]["val_f1"] = {"final": vals[-1][1], "best": best_v,
                                            "best_step": hist[best_i].get("epoch", best_i)}
            rec["metrics"]["epochs_run"] = {"final": len(hist)}
        else:
            rec["kind"], rec["status"] = "generic", "finished"
            rec["metrics"] = numeric_leaves(m)
    elif summary_path.exists() and (d / "config.json").exists() and not (d / "rows.csv").exists():
        rec["kind"], rec["status"] = "tabular", "finished"
        cfg = json.loads((d / "config.json").read_text())
        args = cfg.get("args", {})
        rec["config"] = {k: args.get(k) for k in ("dataset", "context", "node_key", "context_window",
                                                  "seeds", "models", "max_flows", "device")}
        rec["config"]["num_features"] = cfg.get("num_features")
        with summary_path.open() as fh:
            for row in csv.DictReader(fh):
                for key in ("f1", "roc_auc"):
                    mean = row.get(f"{key}_mean")
                    if mean not in (None, "", "None"):
                        std = row.get(f"{key}_std")
                        rec["metrics"][f"{row['model']}/test_{key}"] = {
                            "final": float(mean),
                            "std": float(std) if std not in (None, "", "None") else None,
                            "n": int(row.get("seeds") or 0)}
    elif any((d / f).exists() for f in CSV_SPECS):
        rec["kind"], rec["status"] = "table", "finished"
        for f, (keys, values) in CSV_SPECS.items():
            if (d / f).exists():
                rec["metrics"].update(table_metrics(d / f, keys, values))
    else:
        jsons = sorted(d.glob("*.json"))
        if jsons:
            rec["kind"], rec["status"] = "generic", "finished"
            for p in jsons[:3]:
                try:
                    numeric_leaves(json.loads(p.read_text()), f"{p.stem}/", rec["metrics"])
                except ValueError:
                    pass
        else:
            rec["status"] = "incomplete"
    log = d / "training_log.txt"
    if log.exists():
        lines = [l for l in log.read_text(errors="replace").replace("\r", "\n").splitlines() if l.strip()]
        rec["log_tail"] = lines[-1][-200:] if lines else None
    return rec


def fetch(spec):
    host, path = (spec.split(":", 1) if re.match(r"^[\w.-]+:", spec) and not os.path.exists(spec) else (None, spec))
    if host is None:
        rec = extract(path)
        rec["host"], rec["sha"] = "local", git_sha_before(".", rec["started"])
        return rec
    remote = f"cd {REMOTE_REPO} && python3 - --extract {path}"
    with open(__file__, "rb") as fh:
        out = subprocess.run(["ssh", "-o", "ConnectTimeout=10", host, remote], stdin=fh,
                             capture_output=True, timeout=120)
    if out.returncode != 0:
        sys.exit(f"{host}: {out.stderr.decode()[-400:]}")
    return json.loads(out.stdout)


def label_of(rec):
    name = Path(rec["dir"].rstrip("/")).name
    return re.sub(r"^\d{8}_\d{6}_", "", name)


def fmt(v):
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def main(argv):
    if argv and argv[0] == "--extract":
        rec = extract(argv[1])
        rec["sha"] = git_sha_before(".", rec["started"])
        rec["host"] = os.uname().nodename
        print(json.dumps(rec))
        return
    if len(argv) < 2 or not re.match(r"^E\d{3}$", argv[0]):
        sys.exit(__doc__)
    eid, rest = argv[0], argv[1:]
    labels = []
    if "--labels" in rest:
        i = rest.index("--labels")
        labels, rest = rest[i + 1:], rest[:i]
    out_path = Path(__file__).resolve().parent.parent / ".mem" / "results" / f"{eid}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(out_path.read_text()) if out_path.exists() else {"id": eid, "runs": []}

    for i, spec in enumerate(rest):
        rec = fetch(spec)
        rec["spec"] = spec
        rec["label"] = labels[i] if i < len(labels) else label_of(rec)
        existing["runs"] = [r for r in existing["runs"] if r.get("spec") != spec] + [rec]

    runs = existing["runs"]
    first = runs[0]
    existing.update({
        "id": eid,
        "sha": first.get("sha"),
        "host": ",".join(sorted({r.get("host") or "?" for r in runs})),
        "started": min((r["started"] for r in runs if r.get("started")), default=None),
        "status": "finished" if all(r["status"] == "finished" for r in runs) else
                  ",".join(sorted({r["status"] for r in runs})),
        "config": first["config"] if len(runs) == 1 else {"runs": len(runs)},
        "metrics": first["metrics"] if len(runs) == 1 else
                   {f"{r['label']}/{k}": v for r in runs for k, v in r["metrics"].items()},
        "artifacts": [f"{r['host']}:{r['dir']}" for r in runs],
    })
    out_path.write_text(json.dumps(existing, indent=1))

    # Short table: one line per run, key metrics only.
    print(f"{eid} -> {out_path.relative_to(Path.cwd()) if out_path.is_relative_to(Path.cwd()) else out_path}")
    for r in runs[:14]:
        keys = [k for k in r["metrics"] if k.endswith(("test_f1", "test_roc_auc", "/f1", "_mean")) or k == "val_f1"]
        parts = []
        for k in keys[:6]:
            m = r["metrics"][k]
            s = fmt(m["final"]) + (f"±{m['std']:.4f}" if m.get("std") is not None else "")
            if m.get("best") is not None:
                s += f" (best {fmt(m['best'])}@{m['best_step']})"
            parts.append(f"{k}={s}")
        print(f"  {r['label'][:48]:48s} {r['status']:10s} {' '.join(parts)}"[:230])


if __name__ == "__main__":
    main(sys.argv[1:])

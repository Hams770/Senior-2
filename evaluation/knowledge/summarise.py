"""Collect the six runs and apply the success criteria fixed in train_knowledge.py."""
import json
import sys
from pathlib import Path

import numpy as np

runs = [json.loads(p.read_text()) for p in sorted(Path(sys.argv[1]).rglob("knowledge_run_*.json"))]
M = ["accuracy", "macro_f1", "good_fit_recall", "good_fit_precision", "potential_fit_recall"]
L = ["# Knowledge line vs matched control: M0/512, validation only (1,162 pairs; test not read)", "",
     "Same CS4085 code and frozen configuration, trained on CPU in CI. Only difference: the knowledge line in front of the job text.", "",
     "| Variant | Seed | Accuracy % | Macro-F1 % | Good Fit recall % | Good Fit precision % | Potential Fit recall % | Best step |",
     "|---|---|---|---|---|---|---|---|"]
for r in sorted(runs, key=lambda r: (r["variant"], r["seed"])):
    L.append(f"| {r['variant']} | {r['seed']} | " + " | ".join(f"{r[m]:.2f}" for m in M) + f" | {r['best_step']} |")
mean = {v: {m: float(np.mean([r[m] for r in runs if r["variant"] == v])) for m in M} for v in ("control", "knowledge")}
for v in ("control", "knowledge"):
    L.append(f"| **{v} mean** | | " + " | ".join(f"{mean[v][m]:.2f}" for m in M) + " | |")
d = {m: mean["knowledge"][m] - mean["control"][m] for m in M}
crit = {"Good Fit recall >= +2.0": d["good_fit_recall"] >= 2.0, "Accuracy >= +1.0": d["accuracy"] >= 1.0,
        "Macro-F1 >= -1.0": d["macro_f1"] >= -1.0}
L += ["", "| Difference (knowledge - control) | Value | Criterion met |", "|---|---|---|",
      f"| Good Fit recall | {d['good_fit_recall']:+.2f} | {crit['Good Fit recall >= +2.0']} |",
      f"| Accuracy | {d['accuracy']:+.2f} | {crit['Accuracy >= +1.0']} |",
      f"| Macro-F1 | {d['macro_f1']:+.2f} | {crit['Macro-F1 >= -1.0']} |",
      f"| Good Fit precision | {d['good_fit_precision']:+.2f} | (reported) |", "",
      f"**Verdict: {'PROMISING, all criteria met' if all(crit.values()) else 'NOT IMPROVED, criteria not met'}** (n = {len(runs)} runs)"]
Path("knowledge_training.md").write_text("\n".join(L) + "\n")
Path("knowledge_training.json").write_text(json.dumps({"runs": runs, "mean": mean, "difference": d, "criteria": crit}, indent=2))
print("\n".join(L))

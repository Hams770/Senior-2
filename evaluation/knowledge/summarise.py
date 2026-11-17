"""Summarise the arms of evaluation/knowledge/experiment.json against its reference arm.

Criteria fixed in advance (same for every comparison, mean over the seeds the two arms share):
Good Fit recall >= +2.0 points, accuracy >= +1.0 point, macro-F1 >= -1.0 point.
"""
import json
import sys
from pathlib import Path

import numpy as np

exp = json.loads(Path(sys.argv[2]).read_text())
runs = [json.loads(p.read_text()) for p in sorted(Path(sys.argv[1]).rglob("knowledge_run_*.json"))]
M = ["accuracy", "macro_f1", "good_fit_recall", "good_fit_precision", "potential_fit_recall"]
T = ["train_accuracy", "train_macro_f1", "train_good_fit_recall"]
has_train = any(T[0] in r for r in runs)
L = [f"# {exp['name']}", "", "M0 at 512 tokens, CS4085 code and configuration, validation only (1,162 pairs; test never read).", "",
     "| Arm | Seed | Val accuracy % | Val macro-F1 % | Val Good Fit recall % | Val Good Fit precision % | Val Potential Fit recall % |"
     + (" Train accuracy % | Train macro-F1 % | Train Good Fit recall % |" if has_train else ""),
     "|---|---|---|---|---|---|---|" + ("---|---|---|" if has_train else "")]
arms = list(exp["arms"])
for v in arms:
    for r in sorted((r for r in runs if r["variant"] == v), key=lambda r: r["seed"]):
        L.append(f"| {v} | {r['seed']} | " + " | ".join(f"{r[m]:.2f}" for m in M)
                 + ("".join(f" {r.get(t, float('nan')):.2f} |" for t in T) if has_train else ""))
mean = {}
for v in arms:
    rs = [r for r in runs if r["variant"] == v]
    if rs:
        mean[v] = {m: float(np.mean([r[m] for r in rs])) for m in M + [t for t in T if t in rs[0]]}
        L.append(f"| **{v} mean** | {len(rs)} | " + " | ".join(f"{mean[v][m]:.2f}" for m in M)
                 + ("".join(f" {mean[v].get(t, float('nan')):.2f} |" for t in T) if has_train else ""))
ref = exp["reference"]
by = {(r["variant"], r["seed"]): r for r in runs}
verdicts = {}
for v in arms:
    if v == ref or v not in mean:
        continue
    seeds = sorted(s for (a, s) in by if a == v and (ref, s) in by)
    d = {m: float(np.mean([by[(v, s)][m] - by[(ref, s)][m] for s in seeds])) for m in M}
    ok = {"Good Fit recall >= +2.0": d["good_fit_recall"] >= 2.0, "Accuracy >= +1.0": d["accuracy"] >= 1.0,
          "Macro-F1 >= -1.0": d["macro_f1"] >= -1.0}
    wins = {m: sum(by[(v, s)][m] > by[(ref, s)][m] for s in seeds) for m in ("good_fit_recall", "accuracy", "macro_f1")}
    verdicts[v] = {"difference": d, "criteria": ok, "seeds": seeds, "wins": wins}
    L += ["", f"## {v} vs {ref} (seeds {', '.join(map(str, seeds))})", "", "| Metric | Difference | Criterion met | Seeds better |", "|---|---|---|---|",
          f"| Good Fit recall | {d['good_fit_recall']:+.2f} | {ok['Good Fit recall >= +2.0']} | {wins['good_fit_recall']}/{len(seeds)} |",
          f"| Accuracy | {d['accuracy']:+.2f} | {ok['Accuracy >= +1.0']} | {wins['accuracy']}/{len(seeds)} |",
          f"| Macro-F1 | {d['macro_f1']:+.2f} | {ok['Macro-F1 >= -1.0']} | {wins['macro_f1']}/{len(seeds)} |",
          f"| Good Fit precision | {d['good_fit_precision']:+.2f} | (reported) | |", "",
          f"**{'PROMISING: all criteria met' if all(ok.values()) else 'NOT IMPROVED: criteria not met'}**"]
Path("knowledge_training.md").write_text("\n".join(L) + "\n")
Path("knowledge_training.json").write_text(json.dumps({"experiment": exp, "runs": runs, "mean": mean, "verdicts": verdicts}, indent=2))
print("\n".join(L))

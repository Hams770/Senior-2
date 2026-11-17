"""Tool 4, error analysis (CS4085 Chapter 4): where does the knowledge model miss Good Fit, and why?

Reads val_predictions_*.csv (validation only) written with --save-preds and reports, averaged over seeds,
how Good Fit recall and the errors split by candidate causes. The biggest bucket is where to work next.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

files = sorted(Path(sys.argv[1]).rglob("val_predictions_*.csv"))
P = pd.concat([pd.read_csv(f).assign(seed=f.stem.split("_s")[-1]) for f in files])
G = P[P.label == 2].copy()
L = [f"# Error analysis: Good Fit misses of the knowledge model (validation, {P.seed.nunique()} seeds, {G.row_uid.nunique()} Good Fit pairs)", ""]


def bucket_table(title, key, order=None):
    g = G.groupby(key, dropna=False)
    t = pd.DataFrame({"Good Fit pairs": g.row_uid.nunique(), "share of all Good Fit %": 100 * g.size() / len(G),
                      "recall %": 100 * g.apply(lambda d: (d.pred == 2).mean()),
                      "share of all misses %": 100 * g.apply(lambda d: (d.pred != 2).sum()) / (G.pred != 2).sum()})
    if order:
        t = t.reindex([o for o in order if o in t.index])
    L.extend([f"## {title}", "", t.round(1).to_markdown(), ""])


miss = G[G.pred != 2]
L += ["## Where the missed Good Fit go", "",
      f"- predicted Potential Fit: {100 * (miss.pred == 1).mean():.1f}% of misses",
      f"- predicted No Fit: {100 * (miss.pred == 0).mean():.1f}% of misses", ""]
G["knowledge"] = np.select([G.n_job_skills == 0, G.n_found == 0, G.match_ratio < 0.5], 
                           ["no skill recognised in job", "0 required skills found in CV", "under half found"], "half or more found")
bucket_table("By the knowledge line", "knowledge",
             ["no skill recognised in job", "0 required skills found in CV", "under half found", "half or more found"])
G["length"] = pd.cut(G.cv_tokens + G.job_tokens, [0, 512, 1024, 2048, 10**6],
                     labels=["fits in 512", "512-1024", "1024-2048", "> 2048"])
bucket_table("By input length (CV + job tokens; everything beyond 512 is cut)", "length")
G["margin"] = pd.cut(G.p_good - G[["p_no", "p_potential"]].max(axis=1), [-1, -0.3, -0.1, 0, 1],
                     labels=["far (< -0.3)", "mid", "close (-0.1..0)", "predicted Good"])
bucket_table("By how close the model was (P(Good) minus the top other class)", "margin")
jg = G.groupby("job_group").apply(lambda d: pd.Series({"Good Fit pairs": d.row_uid.nunique(),
                                                      "misses (all seeds)": int((d.pred != 2).sum()),
                                                      "recall %": 100 * (d.pred == 2).mean(),
                                                      "title": d.job_title.iloc[0]}))
jg = jg.sort_values("misses (all seeds)", ascending=False)
L += ["## Job groups with the most missed Good Fit", "",
      f"{(jg['recall %'] == 0).sum()} of {len(jg)} job groups with Good Fit pairs have recall 0 on every seed.", "",
      jg.head(12).round(1).to_markdown(), ""]
fp = P[(P.pred == 2) & (P.label != 2)]
L += ["## False Good Fit", "", f"- true Potential Fit: {100 * (fp.label == 1).mean():.1f}%",
      f"- true No Fit: {100 * (fp.label == 0).mean():.1f}%", ""]
Path("error_analysis.md").write_text("\n".join(L) + "\n")
print("\n".join(L))

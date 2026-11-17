"""Step 2: does the knowledge separate the classes? Train and validation only; the test split is never read.

Decision rule fixed before running: continue to training only if a features-only model reaches validation
macro-F1 >= 38 (clearly above chance, 33) or the Good Fit vs Potential Fit AUC of the best feature is >= 0.60.
Otherwise the knowledge carries too little signal to help BERT and we stop here.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knowledge import features, knowledge_line  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LABELS = ["No Fit", "Potential Fit", "Good Fit"]


def words(t):
    return {w for w in pd.Series([t]).str.lower().str.findall(r"[a-z][a-z+#.]{2,}")[0] if w not in ENGLISH_STOP_WORDS}


def table(d, tfidf):
    rows = []
    cvm, jbm = tfidf.transform(d.resume_text), tfidf.transform(d.job_description_text)
    cos = np.asarray(cvm.multiply(jbm).sum(1)).ravel()
    for i, (cv, job) in enumerate(zip(d.resume_text, d.job_description_text)):
        f = features(cv, job)
        jw, cw = words(job), words(cv)
        rows.append({"match_ratio": f["match_ratio"], "n_found": f["n_found"], "n_job_skills": f["n_job_skills"],
                     "n_missing": f["n_job_skills"] - f["n_found"], "meets_years": f["meets_years"],
                     "cv_years": f["cv_years"], "job_years": f["job_years"],
                     "word_overlap": len(jw & cw) / max(len(jw), 1), "tfidf_cosine": float(cos[i]),
                     "cv_words": len(cv.split()), "line_words": len(knowledge_line(f).split())})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dl", required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.dl).resolve() / "src"))
    from hiremind_dl import load_config
    from hiremind_dl.data import download_raw, load_manifest, read_raw, split_frame
    cfg = load_config(Path(a.dl) / "configs" / "experiment.json")
    raw = {"train": read_raw(download_raw(cfg, "train"))}
    man = load_manifest(cfg)
    tr = split_frame(raw, man, "train", cfg["dataset"]["rows"]["train"])
    va = split_frame(raw, man, "validation", cfg["dataset"]["rows"]["validation"])
    tfidf = TfidfVectorizer(stop_words="english", min_df=2, sublinear_tf=True).fit(
        pd.concat([tr.resume_text, tr.job_description_text]))
    F = {"train": table(tr, tfidf), "validation": table(va, tfidf)}
    y = {"train": tr.label_id.to_numpy(), "validation": va.label_id.to_numpy()}

    rep = {"rows": {k: len(v) for k, v in y.items()}}
    ft = F["train"]
    rep["coverage"] = {"jobs_with_a_recognised_skill_pct": 100 * float((ft.n_job_skills > 0).mean()),
                       "pairs_with_years_on_both_sides_pct": 100 * float(ft.meets_years.notna().mean()),
                       "knowledge_line_words_median": float(ft.line_words.median())}
    feats = ["match_ratio", "n_found", "n_missing", "meets_years", "word_overlap", "tfidf_cosine", "cv_words"]
    rep["means_by_label_train"] = {f: {LABELS[c]: float(ft[f][y["train"] == c].mean()) for c in range(3)} for f in feats}
    gp = np.isin(y["train"], [1, 2])
    rep["auc_good_vs_potential_train"] = {}
    rep["auc_good_vs_no_train"] = {}
    for f in feats:
        col = ft[f].fillna(ft[f].median())
        rep["auc_good_vs_potential_train"][f] = float(roc_auc_score(y["train"][gp] == 2, col[gp]))
        gn = np.isin(y["train"], [0, 2])
        rep["auc_good_vs_no_train"][f] = float(roc_auc_score(y["train"][gn] == 2, col[gn]))

    def X(df):
        d = df[feats].copy()
        for c in feats:
            d[c + "_missing"] = d[c].isna().astype(float)
            d[c] = d[c].fillna(F["train"][c].median())
        return d.to_numpy(float)
    sc = StandardScaler().fit(X(F["train"]))
    lr = LogisticRegression(max_iter=2000).fit(sc.transform(X(F["train"])), y["train"])
    p = lr.predict(sc.transform(X(F["validation"])))
    cm = confusion_matrix(y["validation"], p, labels=[0, 1, 2])
    rep["features_only_model_validation"] = {
        "accuracy": 100 * float((p == y["validation"]).mean()),
        "macro_f1": 100 * float(f1_score(y["validation"], p, average="macro")),
        "good_fit_recall": 100 * float(cm[2, 2] / cm[2].sum()), "confusion": cm.tolist()}
    best_auc = max(rep["auc_good_vs_potential_train"].values())
    go = rep["features_only_model_validation"]["macro_f1"] >= 38 or best_auc >= 0.60
    rep["decision"] = {"best_good_vs_potential_auc": best_auc, "continue_to_training": bool(go)}
    rep["example_lines"] = [knowledge_line(features(cv, job))
                            for cv, job in zip(va.resume_text[:5], va.job_description_text[:5])]

    out = ROOT / "test-results"
    out.mkdir(exist_ok=True)
    (out / "knowledge_signal.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()

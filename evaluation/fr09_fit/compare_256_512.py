"""Validation-only comparison of M0 at 256 and 512 tokens (seeds 42, 43, 44). Never opens the test split.

1. Checks every weights file against its SHA-256.
2. Runs each model with the platform's inference path (pinned tokenizer, longest_first truncation) and checks that
   the validation confusion matrices equal the recorded ones (CS4085 for 256, Mervat's run for 512).
3. Good Fit review rules on validation: P(Good Fit) threshold sweep and the top-2 rule, per seed and as a mean.
4. CPU latency (1 thread, batch 1), model only and including tokenization.
Writes test-results/compare_256_512.md and .json.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import confusion_matrix, f1_score
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "eval_weights"
BASE, REV = "google/bert_uncased_L-2_H-128_A-2", "30b0a37ccaaa32f332884b96992754e246e48c5f"
MODELS = {  # name: (file, max_len, sha256, recorded validation confusion or None)
    "256_s42": (ROOT / "backend/models/M0_s42_lr0.0001.pt", 256, "6ac7862edea03cba6c9f7854c45f7c7fc470b0c54518ebb8791f571f08997d71"),
    "256_s43": (W / "M0_s43_lr0.0001.pt", 256, "08fd438d0393d724787e95f9c1e72d9e689065cd6944d1fd87e2ad3f57ffe4d7"),
    "256_s44": (W / "M0_s44_lr0.0001.pt", 256, "9cce30b993ec289e8f94620405740c1857db91269030284344b38b6fd71f6d2b"),
    "512_s42": (W / "M0_L512_s42.pt", 512, "dcae9c17d21b2b8e3d9f4d687d19980ee8cce45e40f508ff328ee3a4454e0a0f"),
    "512_s43": (W / "M0_L512_s43.pt", 512, "4dce28e17eaeb43771f5b7469524b5bc12ed23fb4cb8848c30723dd18c3bc5ed"),
    "512_s44": (W / "M0_L512_s44.pt", 512, "28d1ccbe486ee111dc6afb75794781bca82a4903b21b009ca740f911ebff5c68"),
    "512_w1.5_s42": (W / "M0_L512_w1p5_s42.pt", 512, "04869a9fb71e9501997d83d30a4e87078ae88221f02b6c045d8354f88780205b"),
}
RECORDED_256 = {"256_s42": (55.59380378657487, 46.536276922018175, 23.875432525951556),  # accuracy, macro-F1, GF recall
                "256_s43": (51.54905335628227, 37.646805064438716, 21.10726643598616),
                "256_s44": (50.34423407917383, 35.85511233790764, 5.88235294117647)}
WEIGHTED_CONFUSION = [[477, 58, 44], [162, 103, 29], [122, 74, 93]]
THRESHOLDS = [round(t, 3) for t in np.arange(0.10, 0.501, 0.025)]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(path):
    cfg = AutoConfig.from_pretrained(BASE, revision=REV, num_labels=3)
    m = AutoModelForSequenceClassification.from_config(cfg, attn_implementation="eager")
    m.load_state_dict(torch.load(path, map_location="cpu", weights_only=True), strict=True)
    return m.eval()


def probs(model, tok, pairs, max_len, batch=32):
    out = []
    with torch.inference_mode():
        for i in range(0, len(pairs), batch):
            p = pairs[i:i + batch]
            enc = tok([a for a, _ in p], [b for _, b in p], truncation="longest_first", max_length=max_len,
                      padding="max_length", return_tensors="pt")
            out.append(model(**enc).logits.softmax(-1))
    return torch.cat(out).numpy()


def flag_stats(y, flagged):
    good = y == 2
    return {"review_pct": 100 * float(flagged.mean()), "good_fit_caught_pct": 100 * float(flagged[good].mean()),
            "good_fit_among_flagged_pct": 100 * float(good[flagged].mean()) if flagged.any() else 0.0}


def latency(model, tok, pairs, max_len, n=50):
    torch.set_num_threads(1)
    model_ms, total_ms = [], []
    with torch.inference_mode():
        for cv, job in pairs[:n]:
            t0 = time.perf_counter()
            enc = tok(cv, job, truncation="longest_first", max_length=max_len, padding="max_length", return_tensors="pt")
            t1 = time.perf_counter()
            model(**enc)
            t2 = time.perf_counter()
            model_ms.append(1000 * (t2 - t1))
            total_ms.append(1000 * (t2 - t0))
    torch.set_num_threads(torch.get_num_threads())
    return {"model_only_median_ms": float(np.median(model_ms)), "with_tokenization_median_ms": float(np.median(total_ms))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dl", required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.dl).resolve() / "src"))
    from hiremind_dl import load_config
    from hiremind_dl.data import download_raw, load_manifest, read_raw, split_frame
    cfg = load_config(Path(a.dl) / "configs" / "experiment.json")
    raw = {"train": read_raw(download_raw(cfg, "train"))}  # validation rows come from the train file; test is never read
    val = split_frame(raw, load_manifest(cfg), "validation", cfg["dataset"]["rows"]["validation"])
    pairs = list(zip(val.resume_text, val.job_description_text))
    y = val.label_id.to_numpy()
    tok = AutoTokenizer.from_pretrained(BASE, revision=REV)
    mervat = json.loads((W / "mervat_validation_confusions.json").read_text())

    rep = {"validation_rows": len(y), "models": {}, "checks": {}}
    P = {}
    for name, (path, L, digest) in MODELS.items():
        rep["checks"][f"{name}: SHA-256 matches"] = sha(path) == digest
        m = load(path)
        p = probs(m, tok, pairs, L)
        P[name] = p
        pred = p.argmax(1)
        cm = confusion_matrix(y, pred, labels=[0, 1, 2])
        r = {"max_len": L, "accuracy": 100 * float((pred == y).mean()),
             "macro_f1": 100 * float(f1_score(y, pred, labels=[0, 1, 2], average="macro", zero_division=0)),
             "good_fit_recall": 100 * float(cm[2, 2] / cm[2].sum()),
             "good_fit_precision": 100 * float(cm[2, 2] / max(cm[:, 2].sum(), 1)), "confusion": cm.tolist(),
             **latency(m, tok, pairs, L)}
        rep["models"][name] = r
        if name in RECORDED_256:
            rec = RECORDED_256[name]
            rep["checks"][f"{name}: reproduces the CS4085 validation result"] = all(
                abs(x - y_) < 0.05 for x, y_ in zip((r["accuracy"], r["macro_f1"], r["good_fit_recall"]), rec))
        elif name == "512_w1.5_s42":
            rep["checks"][f"{name}: reproduces Mervat's confusion matrix"] = r["confusion"] == WEIGHTED_CONFUSION
        else:
            rep["checks"][f"{name}: reproduces Mervat's confusion matrix"] = r["confusion"] == mervat[f"M0_s{name[-2:]}"]

    rules = {}
    for L in (256, 512):
        names = [f"{L}_s{s}" for s in (42, 43, 44)]
        for t in THRESHOLDS:
            per = [flag_stats(y, P[n][:, 2] >= t) for n in names]
            rules[f"{L} | P(Good Fit) >= {t:.3f}"] = {"length": L, "rule": f"threshold {t:.3f}", "per_seed": per,
                                                       **{k: float(np.mean([s[k] for s in per])) for k in per[0]},
                                                       "caught_sd": float(np.std([s["good_fit_caught_pct"] for s in per], ddof=1))}
        per = [flag_stats(y, np.argsort(-P[n], 1)[:, :2].__eq__(2).any(1)) for n in names]
        rules[f"{L} | top-2"] = {"length": L, "rule": "top-2", "per_seed": per,
                                 **{k: float(np.mean([s[k] for s in per])) for k in per[0]},
                                 "caught_sd": float(np.std([s["good_fit_caught_pct"] for s in per], ddof=1))}
        per = [flag_stats(y, P[n].argmax(1) == 2) for n in names]
        rules[f"{L} | predicted Good Fit"] = {"length": L, "rule": "argmax", "per_seed": per,
                                              **{k: float(np.mean([s[k] for s in per])) for k in per[0]},
                                              "caught_sd": float(np.std([s["good_fit_caught_pct"] for s in per], ddof=1))}
    rep["rules"] = rules

    out = ROOT / "test-results"
    out.mkdir(exist_ok=True)
    (out / "compare_256_512.json").write_text(json.dumps(rep, indent=2))
    L = ["# M0 at 256 vs 512 tokens: validation only (1,162 pairs; test not opened)", "",
         "| Model | Accuracy % | Macro-F1 % | Good Fit recall % | Good Fit precision % | CPU ms (model / with tokenizer) |",
         "|---|---|---|---|---|---|"]
    for n, r in rep["models"].items():
        L.append(f"| {n} | {r['accuracy']:.2f} | {r['macro_f1']:.2f} | {r['good_fit_recall']:.2f} | {r['good_fit_precision']:.2f} | "
                 f"{r['model_only_median_ms']:.1f} / {r['with_tokenization_median_ms']:.1f} |")
    for Ln in (256, 512):
        ms = [rep["models"][f"{Ln}_s{s}"] for s in (42, 43, 44)]
        L.append(f"| **{Ln} mean of 3 seeds** | {np.mean([m['accuracy'] for m in ms]):.2f} | {np.mean([m['macro_f1'] for m in ms]):.2f} | "
                 f"{np.mean([m['good_fit_recall'] for m in ms]):.2f} | {np.mean([m['good_fit_precision'] for m in ms]):.2f} | |")
    L += ["", "| Check | Result |", "|---|---|"] + [f"| {k} | {'passed' if v else 'FAILED'} |" for k, v in rep["checks"].items()]
    L += ["", "## Good Fit review rules (mean of seeds 42, 43, 44)", "",
          "| Length | Rule | Review % of applicants | Good Fit caught % (SD) | Good Fit among flagged % |", "|---|---|---|---|---|"]
    for k, r in rules.items():
        L.append(f"| {r['length']} | {r['rule']} | {r['review_pct']:.1f} | {r['good_fit_caught_pct']:.1f} ({r['caught_sd']:.1f}) | {r['good_fit_among_flagged_pct']:.1f} |")
    (out / "compare_256_512.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    if not all(rep["checks"].values()):
        sys.exit("Some checks failed")


if __name__ == "__main__":
    main()

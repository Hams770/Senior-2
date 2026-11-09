"""FR-09 integration check: the platform's own classifier code must reproduce the CS4085 results of M0 seed 42.

    git clone https://github.com/Hams770/HireMind-DL ../HireMind-DL
    pip install -r backend/requirements.txt -r backend/requirements-model.txt pandas==2.2.3 scikit-learn==1.6.1 huggingface-hub==0.30.2
    python evaluation/fr09_fit/verify_fit_model.py --dl ../HireMind-DL

It downloads the pinned dataset, rebuilds the frozen validation and test splits with the DL repository's code,
runs every pair through backend/app/fit_model.py (the code the platform uses), and compares the result with the
numbers recorded in backend/models/fit_model.json. It then shows how the Good Fit review threshold behaves on the
validation split (where the threshold is chosen) and reports the configured threshold once on the test split.
Writes test-results/fit_model_report.md and fit_model_report.json; exits with an error if the numbers differ.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def run(pairs, fit_model, batch=32):
    probs = []
    for i in range(0, len(pairs), batch):
        probs.extend(fit_model.predict_batch(pairs[i:i + batch]))
    return np.array(probs)


def metrics(y, probs):
    pred = probs.argmax(1)
    cm = confusion_matrix(y, pred, labels=[0, 1, 2])
    return {"rows": int(len(y)), "accuracy": 100 * float((pred == y).mean()),
            "macro_f1": 100 * float(f1_score(y, pred, labels=[0, 1, 2], average="macro", zero_division=0)),
            "good_fit_recall": 100 * float(cm[2, 2] / max(cm[2].sum(), 1)), "confusion": cm.tolist()}


def flag_stats(y, probs, t):
    flagged = probs[:, 2] >= t
    good = y == 2
    return {"threshold": round(float(t), 3), "flagged_share": 100 * float(flagged.mean()),
            "good_fit_caught": 100 * float(flagged[good].mean()),
            "good_fit_among_flagged": 100 * float(good[flagged].mean()) if flagged.any() else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dl", required=True, help="path to a clone of github.com/Hams770/HireMind-DL")
    ap.add_argument("--out", default=str(ROOT / "test-results"))
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.dl).resolve() / "src"))
    from hiremind_dl import load_config
    from hiremind_dl.data import download_raw, load_manifest, read_raw, split_frame

    from app import config, fit_model
    config.FIT_ENABLED = True
    st = fit_model.status()
    if not st["available"]:
        sys.exit(f"Classifier not available: {st['reason']}")
    card = fit_model.CARD
    cfg = load_config(Path(a.dl) / "configs" / "experiment.json")
    raw = {p: read_raw(download_raw(cfg, p)) for p in ("train", "test")}
    manifest = load_manifest(cfg)
    rec = card["recorded_results"]
    report = {"model": fit_model.model_version(), "review_threshold": card["review_threshold"]}
    probs_by_split = {}
    for split in ("validation", "test"):
        d = split_frame(raw, manifest, split, cfg["dataset"]["rows"][split])
        pairs = list(zip(d.resume_text, d.job_description_text))
        started = time.perf_counter()
        probs = run(pairs, fit_model)
        secs = time.perf_counter() - started
        y = d.label_id.to_numpy()
        probs_by_split[split] = (y, probs)
        report[split] = {**metrics(y, probs), "seconds": round(secs, 1), "ms_per_pair": round(1000 * secs / len(y), 2)}
    val, test = report["validation"], report["test"]
    checks = {
        "validation macro-F1 equals the recorded value": abs(val["macro_f1"] - rec["validation_macro_f1"]) < 0.05,
        "validation confusion matrix equals the recorded one": val["confusion"] == rec["validation_confusion"],
        "test macro-F1 equals the recorded value": abs(test["macro_f1"] - rec["test_macro_f1"]) < 0.05,
        "test Good Fit recall equals the recorded value": abs(test["good_fit_recall"] - rec["test_good_fit_recall"]) < 0.05,
    }
    yv, pv = probs_by_split["validation"]
    report["threshold_curve_validation"] = [flag_stats(yv, pv, t) for t in np.arange(0.10, 0.501, 0.025)]
    yt, pt = probs_by_split["test"]
    report["configured_threshold_test"] = flag_stats(yt, pt, card["review_threshold"])
    report["checks"] = checks

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "fit_model_report.json").write_text(json.dumps(report, indent=2))
    lines = [f"# FR-09 fit classifier: integration check ({report['model']})", "",
             "The platform's classifier code was run on the frozen CS4085 splits and compared with the recorded results.", "",
             "| Split | Pairs | Accuracy % | Macro-F1 % | Good Fit recall % | ms per pair (CPU, batch 32) |", "|---|---|---|---|---|---|"]
    for s in ("validation", "test"):
        r = report[s]
        lines.append(f"| {s} | {r['rows']} | {r['accuracy']:.2f} | {r['macro_f1']:.2f} | {r['good_fit_recall']:.2f} | {r['ms_per_pair']} |")
    lines += ["", "| Check | Result |", "|---|---|"] + [f"| {k} | {'passed' if v else 'FAILED'} |" for k, v in checks.items()]
    lines += ["", "## Good Fit review flag on the validation split (threshold chosen here)", "",
              "| P(Good Fit) ≥ | Flagged % of all | Good Fit caught % | Good Fit among flagged % |", "|---|---|---|---|"]
    for r in report["threshold_curve_validation"]:
        lines.append(f"| {r['threshold']:.3f} | {r['flagged_share']:.1f} | {r['good_fit_caught']:.1f} | {r['good_fit_among_flagged']:.1f} |")
    c = report["configured_threshold_test"]
    lines += ["", f"Configured threshold {c['threshold']} on the test split (reported once, not used for choosing): "
              f"{c['flagged_share']:.1f}% flagged, {c['good_fit_caught']:.1f}% of Good Fit caught, "
              f"{c['good_fit_among_flagged']:.1f}% of flagged are Good Fit (argmax recall alone: {test['good_fit_recall']:.1f}%)."]
    (out / "fit_model_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if not all(checks.values()):
        sys.exit("The platform does not reproduce the recorded results")


if __name__ == "__main__":
    main()

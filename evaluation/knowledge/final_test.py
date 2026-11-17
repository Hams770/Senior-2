"""FINAL held-out test, run once after every choice was fixed on validation.

Fixed before opening the test split:
  final model   M0, 512 tokens, knowledge line (v1), 3 epochs, seed 42 (trained in the same CI run on CPU)
  compared with M0-256 seed 42 (platform today) and M0-512 seed 42 (Mervat), on the same test pairs
  review flag   P(Good Fit) >= 0.25 for the 512 models (team decision of 11 Nov), 0.225 for M0-256 (platform today)
Writes test-results/final_test.md and .json.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch
from sklearn.metrics import confusion_matrix, f1_score
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knowledge import features, knowledge_line  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE, REV = "google/bert_uncased_L-2_H-128_A-2", "30b0a37ccaaa32f332884b96992754e246e48c5f"


def run(path, pairs, max_len):
    m = AutoModelForSequenceClassification.from_config(AutoConfig.from_pretrained(BASE, revision=REV, num_labels=3),
                                                       attn_implementation="eager")
    m.load_state_dict(torch.load(path, map_location="cpu", weights_only=True), strict=True)
    m.eval()
    tok = AutoTokenizer.from_pretrained(BASE, revision=REV)
    out = []
    with torch.inference_mode():
        for i in range(0, len(pairs), 32):
            b = pairs[i:i + 32]
            enc = tok([c for c, _ in b], [j for _, j in b], truncation="longest_first", max_length=max_len,
                      padding="max_length", return_tensors="pt")
            out.append(m(**enc).logits.softmax(-1))
    return torch.cat(out).numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dl", required=True)
    ap.add_argument("--final", required=True, help="weights.pt of the final model")
    ap.add_argument("--m512", required=True, help="Mervat's M0-512 seed 42 weights")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.dl).resolve() / "src"))
    from hiremind_dl import load_config
    from hiremind_dl.data import download_raw, load_manifest, read_raw, split_frame
    cfg = load_config(Path(a.dl) / "configs" / "experiment.json")
    raw = {"test": read_raw(download_raw(cfg, "test"))}
    te = split_frame(raw, load_manifest(cfg), "test", cfg["dataset"]["rows"]["test"])
    y = te.label_id.to_numpy()
    plain = list(zip(te.resume_text, te.job_description_text))
    know = [(cv, knowledge_line(features(cv, job)) + "\n" + job) for cv, job in plain]
    models = {
        "M0-256 seed 42 (platform today)": (ROOT / "backend/models/M0_s42_lr0.0001.pt", plain, 256, 0.225,
                                            "6ac7862edea03cba6c9f7854c45f7c7fc470b0c54518ebb8791f571f08997d71"),
        "M0-512 seed 42 (Mervat)": (Path(a.m512), plain, 512, 0.25,
                                    "dcae9c17d21b2b8e3d9f4d687d19980ee8cce45e40f508ff328ee3a4454e0a0f"),
        "M0-512 + knowledge seed 42 (final)": (Path(a.final), know, 512, 0.25, None),
    }
    rep = {"test_pairs": len(y), "good_fit_pairs": int((y == 2).sum()), "models": {}}
    for name, (path, pairs, max_len, t, sha) in models.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha is None or digest == sha, f"{name}: SHA-256 mismatch"
        p = run(path, pairs, max_len)
        pred = p.argmax(1)
        cm = confusion_matrix(y, pred, labels=[0, 1, 2])
        flag = p[:, 2] >= t
        rep["models"][name] = {
            "sha256": digest, "max_len": max_len, "accuracy": 100 * float((pred == y).mean()),
            "macro_f1": 100 * float(f1_score(y, pred, average="macro")),
            "good_fit_recall": 100 * float(cm[2, 2] / cm[2].sum()),
            "good_fit_precision": 100 * float(cm[2, 2] / max(cm[:, 2].sum(), 1)), "confusion": cm.tolist(),
            "review_threshold": t, "review_pct": 100 * float(flag.mean()),
            "good_fit_reaching_hr_pct": 100 * float(flag[y == 2].mean()),
            "good_fit_among_flagged_pct": 100 * float((y[flag] == 2).mean())}
    lines = [f"# Final held-out test (opened once): {rep['test_pairs']} pairs, {rep['good_fit_pairs']} Good Fit", "",
             "| Model | Accuracy % | Macro-F1 % | Good Fit recall % | Good Fit precision % | Review flag | HR reviews % | Good Fit reaching HR % |",
             "|---|---|---|---|---|---|---|---|"]
    for n, r in rep["models"].items():
        lines.append(f"| {n} | {r['accuracy']:.2f} | {r['macro_f1']:.2f} | {r['good_fit_recall']:.2f} | "
                     f"{r['good_fit_precision']:.2f} | P(Good) >= {r['review_threshold']} | {r['review_pct']:.1f} | "
                     f"{r['good_fit_reaching_hr_pct']:.1f} |")
    lines += ["", "Confusion matrices (rows: true No / Potential / Good):", ""]
    lines += [f"- {n}: {r['confusion']}" for n, r in rep["models"].items()]
    out = ROOT / "test-results"
    out.mkdir(exist_ok=True)
    (out / "final_test.json").write_text(json.dumps(rep, indent=2))
    (out / "final_test.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

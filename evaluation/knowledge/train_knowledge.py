"""Step 4: matched training of M0/512 with and without the knowledge line (validation only; test never read).

    HIREMIND_MAX_LEN=512 python evaluation/knowledge/train_knowledge.py --dl ../HireMind-DL --seed 42 --variant knowledge

Both variants use the CS4085 training code and frozen configuration unchanged (BERT-Tiny, lr 1e-4, 3 epochs,
939 updates, best validation macro-F1 checkpoint). The only difference: in 'knowledge' the job description
starts with one line from evaluation/knowledge/knowledge.py, e.g.
    "Skills check: 2 of 3 required skills found; found: python, sql; missing: excel."

Success criteria, fixed before any result (mean of seeds 42, 43, 44, knowledge minus control):
    Good Fit recall  >= +2.0 points
    Accuracy         >= +1.0 point
    Macro-F1         >= -1.0 point (no meaningful drop)
"""
import argparse
import json
import os
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knowledge import features, knowledge_line  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dl", required=True)
    ap.add_argument("--seed", type=int, required=True, choices=[42, 43, 44])
    ap.add_argument("--variant", required=True, choices=["control", "knowledge"])
    a = ap.parse_args()
    assert os.getenv("HIREMIND_MAX_LEN") == "512", "set HIREMIND_MAX_LEN=512"
    sys.path.insert(0, str(Path(a.dl).resolve() / "src"))
    from transformers import AutoTokenizer
    from hiremind_dl import load_config
    from hiremind_dl.data import as_dataset, download_raw, load_manifest, read_raw, split_frame, tokenize
    from hiremind_dl.training import train_run

    cfg = load_config(Path(a.dl) / "configs" / "experiment.json")
    assert cfg["tokenization"]["max_len"] == 512
    raw = {"train": read_raw(download_raw(cfg, "train"))}  # test file is never downloaded
    man = load_manifest(cfg)
    tok = AutoTokenizer.from_pretrained(cfg["student"]["name"], revision=cfg["student"]["revision"])
    ds = {}
    for part in ("train", "validation"):
        d = split_frame(raw, man, part, cfg["dataset"]["rows"][part])
        if a.variant == "knowledge":
            d["job_description_text"] = [knowledge_line(features(cv, job)) + "\n" + job
                                         for cv, job in zip(d.resume_text, d.job_description_text)]
        ds[part] = as_dataset(tokenize(d, tok, 512))
    torch.set_num_threads(os.cpu_count() or 4)
    info, _ = train_run("M0", cfg["selected"]["M0"]["lr"], a.seed, cfg, ds["train"], ds["validation"], "cpu")
    b = info["best"]
    out = {"variant": a.variant, "seed": a.seed, "best_step": b["step"], "updates": info["updates"],
           "seconds": round(info["seconds"]), "accuracy": b["accuracy"], "macro_f1": b["macro_f1"],
           "good_fit_recall": b["good_fit_recall"],
           "good_fit_precision": 100 * b["per_class"]["Good Fit"]["precision"],
           "potential_fit_recall": 100 * b["per_class"]["Potential Fit"]["recall"],
           "confusion": b["confusion"], "history": info["history"]}
    res = ROOT / "test-results"
    res.mkdir(exist_ok=True)
    (res / f"knowledge_run_{a.variant}_s{a.seed}.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "history"}, indent=2))


if __name__ == "__main__":
    main()

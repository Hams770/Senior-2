"""Score the CV parser against the agreed annotations (AT-01 / NFR-07) and write AT-01_report.md.

    python evaluation/at01_extraction/score_extraction.py
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.parser import ParseError, parse_cv  # noqa: E402
from app.skills import SKILLS  # noqa: E402

TARGET = 0.85


def read_sheet(wb, name):
    ws = wb[name]
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            out[row[0]] = {s.strip().lower() for s in str(row[2] or "").split(",") if s.strip()}
    return out


def prf(gold: dict, pred: dict):
    tp = sum(len(gold[k] & pred.get(k, set())) for k in gold)
    fp = sum(len(pred.get(k, set()) - gold[k]) for k in gold)
    fn = sum(len(gold[k] - pred.get(k, set())) for k in gold)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return tp, fp, fn, p, r, f


def main():
    from openpyxl import load_workbook
    wb = load_workbook(HERE / "AT-01_annotation.xlsx", read_only=True)
    gold = read_sheet(wb, "Agreed")
    if not any(gold.values()):
        sys.exit("The 'Agreed' sheet is empty: finish the annotation first.")
    unknown = sorted({s for v in gold.values() for s in v} - set(SKILLS))
    pred, failed = {}, []
    for name in gold:
        f = HERE / "cvs" / name
        try:
            pred[name] = {s["skill"] for s in parse_cv(f.read_bytes(), f.suffix.lower()).skills}
        except (ParseError, FileNotFoundError) as e:
            pred[name] = set()
            failed.append(f"{name}: {e}")
    tp, fp, fn, p, r, f1 = prf(gold, pred)
    lines = ["# AT-01: skill extraction accuracy", "",
             f"CVs: {len(gold)} · gold skills: {tp + fn} · parser skills: {tp + fp}", "",
             "| Measure | Value |", "|---|---|",
             f"| True positives | {tp} |", f"| False positives | {fp} |", f"| False negatives | {fn} |",
             f"| Micro precision | {p:.3f} |", f"| Micro recall | {r:.3f} |", f"| **Micro-F1** | **{f1:.3f}** |",
             f"| NFR-07 target (≥ {TARGET}) | {'met' if f1 >= TARGET else 'not met'} |", ""]
    if {"Annotator A", "Annotator B"} <= set(wb.sheetnames):
        a, b = read_sheet(wb, "Annotator A"), read_sheet(wb, "Annotator B")
        if any(a.values()) and any(b.values()):
            agree = prf(a, b)[5]
            lines += [f"Agreement between the two annotators before discussion (pairwise F1): {agree:.3f}", ""]
    missed = Counter(s for k in gold for s in gold[k] - pred[k])
    extra = Counter(s for k in gold for s in pred[k] - gold[k])
    lines += ["## Most missed skills (false negatives)", ""] + [f"- {s}: {n}" for s, n in missed.most_common(10)] + [""]
    lines += ["## Most frequent wrong skills (false positives)", ""] + [f"- {s}: {n}" for s, n in extra.most_common(10)] + [""]
    lines += ["## Per CV", "", "| CV | Gold | Parser | Missed | Extra |", "|---|---|---|---|---|"]
    for k in gold:
        lines.append(f"| {k} | {len(gold[k])} | {len(pred[k])} | {', '.join(sorted(gold[k] - pred[k])) or '—'} | {', '.join(sorted(pred[k] - gold[k])) or '—'} |")
    if unknown:
        lines += ["", f"Note: annotated skills not on the skill list (the parser cannot find them): {', '.join(unknown)}"]
    if failed:
        lines += ["", "Files the parser could not read:"] + [f"- {x}" for x in failed]
    (HERE / "AT-01_report.md").write_text("\n".join(lines))
    print("\n".join(lines[:14]))
    print("Full report:", HERE / "AT-01_report.md")


if __name__ == "__main__":
    main()

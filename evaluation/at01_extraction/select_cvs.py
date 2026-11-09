"""Pick 30 CVs for AT-01 (NFR-07) and create the annotation workbook.

Source: the public dataset used in the DL project (cnamuangtoun/resume-job-description-fit, pinned revision),
official test file, 10 CVs per label, distinct CVs, seed 42. Each CV is saved as DOCX so it goes through the
same parser path as an uploaded CV. Files are written to evaluation/at01_extraction/cvs/ (git-ignored).
To use your own CVs instead, put PDF/DOCX files in cvs/ and run with --own.

    pip install huggingface_hub pandas openpyxl
    python evaluation/at01_extraction/select_cvs.py           # dataset CVs
    python evaluation/at01_extraction/select_cvs.py --own     # your own files already in cvs/
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
sys.path.insert(0, str(HERE.parents[1] / "backend" / "tests"))
from app.skills import SKILLS  # noqa: E402

CVS = HERE / "cvs"
REPO, REV = "cnamuangtoun/resume-job-description-fit", "08978e21714984bb417547d2c0f9b477f5298163"


def from_dataset(n_per_label: int):
    import pandas as pd
    from huggingface_hub import hf_hub_download

    from cvfiles import make_docx
    df = pd.read_csv(hf_hub_download(REPO, "test.csv", repo_type="dataset", revision=REV), keep_default_na=False)
    df = df.drop_duplicates("resume_text")
    picked = pd.concat(g.sample(n=n_per_label, random_state=42) for _, g in df.groupby("label"))
    CVS.mkdir(exist_ok=True)
    names = []
    for i, text in enumerate(picked.resume_text, 1):
        name = f"cv{i:02d}.docx"
        (CVS / name).write_bytes(make_docx(text.splitlines() or [text]))
        names.append((name, text))
    return names


def from_folder():
    from app.parser import ParseError, extract_text
    names = []
    for f in sorted(CVS.iterdir()):
        if f.suffix.lower() in (".pdf", ".docx"):
            try:
                names.append((f.name, extract_text(f.read_bytes(), f.suffix.lower())))
            except ParseError as e:
                names.append((f.name, f"[could not read: {e}]"))
    return names


def workbook(cvs):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    info = wb.active
    info.title = "Instructions"
    lines = [
        "AT-01 skill extraction accuracy (NFR-07: micro-F1 of at least 0.85 on 30 annotated CVs)",
        "",
        "1. Two team members annotate independently: one uses 'Annotator A', the other 'Annotator B'. Do not look at each other's sheet or at the parser output.",
        "2. For each CV, read the text and list every skill from the 'Skill list' sheet that the CV clearly shows the person has, separated by commas (use the names in column A of 'Skill list').",
        "3. Only skills on the list count, because the parser can only find those. Write nothing for a CV with none.",
        "4. Compare A and B, discuss every difference, and write the agreed list in 'Agreed'. This is the gold standard.",
        "5. Run: python evaluation/at01_extraction/score_extraction.py  (it reads 'Agreed' and writes AT-01_report.md).",
    ]
    for i, t in enumerate(lines, 1):
        info.cell(row=i, column=1, value=t)
    info["A1"].font = Font(bold=True)
    info.column_dimensions["A"].width = 150
    for title in ("Annotator A", "Annotator B", "Agreed"):
        ws = wb.create_sheet(title)
        for c, h in enumerate(["CV file", "CV text", "Skills (comma-separated)"], 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="DCE0E8")
        for r, (name, text) in enumerate(cvs, 2):
            ws.cell(row=r, column=1, value=name)
            ws.cell(row=r, column=2, value=text[:32000]).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=r, column=3).font = Font(color="0000FF")
            ws.row_dimensions[r].height = 150
        ws.column_dimensions["A"].width = 12
        ws.column_dimensions["B"].width = 100
        ws.column_dimensions["C"].width = 45
    sk = wb.create_sheet("Skill list")
    sk.append(["Skill (write this)", "Also written as"])
    for k, v in sorted(SKILLS.items()):
        sk.append([k, ", ".join(x for x in v if x != k)])
    sk.column_dimensions["A"].width = 24
    sk.column_dimensions["B"].width = 60
    out = HERE / "AT-01_annotation.xlsx"
    wb.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--own", action="store_true", help="use the PDF/DOCX files already in cvs/")
    ap.add_argument("--per-label", type=int, default=10)
    a = ap.parse_args()
    cvs = from_folder() if a.own else from_dataset(a.per_label)
    print(f"{len(cvs)} CVs in {CVS}")
    print("Annotation workbook:", workbook(cvs))


if __name__ == "__main__":
    main()

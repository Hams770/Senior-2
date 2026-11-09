# AT-01 skill extraction accuracy (NFR-07)

**Target (midterm report):** skill extraction micro-F1 of at least 0.85 on 30 annotated CVs.

1. `pip install huggingface_hub pandas openpyxl` (in the backend environment), then
   `python evaluation/at01_extraction/select_cvs.py`. It picks 30 CVs from the public dataset of the DL project
   (official test file, 10 per label, seed 42), saves them as DOCX in `cvs/`, and creates `AT-01_annotation.xlsx`.
   To use your own CVs instead, put 30 PDF/DOCX files (shared with permission) in `cvs/` and add `--own`.
2. Two team members annotate independently (sheets *Annotator A* and *Annotator B*), then agree on one list per
   CV in *Agreed*. Instructions are in the workbook. Annotate without looking at the parser output.
3. `python evaluation/at01_extraction/score_extraction.py` writes `AT-01_report.md`: micro precision, recall and F1,
   the agreement between annotators, the most missed and wrong skills, and a per-CV table.

`cvs/`, the workbook and the report hold CV text and stay out of Git (see `.gitignore`); put only the numbers in the report.

"""Builds realistic test CVs in memory (no personal data)."""
import io

CV_LINES = [
    "Sara Ahmed", "Jeddah, Saudi Arabia | sara@example.com",
    "Summary", "Data analyst with two years of experience turning business data into clear reports.",
    "Experience", "Data Analyst, Retail Co. (2023 - present)",
    "Built Power BI dashboards used by 40 store managers each week.",
    "Wrote SQL queries in PostgreSQL to clean and join sales data. Automated reports with Python and pandas.",
    "Education", "BSc Computer Science, Effat University, 2023",
    "Skills", "Python, SQL, Excel, Tableau, Git", "Communication, teamwork, English and Arabic",
    "Projects", "Customer churn prediction with scikit-learn and machine learning models.",
]


def make_pdf(lines=CV_LINES) -> bytes:
    """A minimal valid text PDF (Helvetica), one line per text row."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "BT /F1 11 Tf 50 800 Td 14 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1"))
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def make_docx(lines=CV_LINES) -> bytes:
    import docx
    d = docx.Document()
    for line in lines:
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def scanned_pdf() -> bytes:
    """A PDF page with no text layer, like a scanned CV."""
    return make_pdf([])

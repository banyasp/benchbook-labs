"""PDF -> page texts as JSON on stdout. Run as a subprocess by `normalize` with an interpreter that has pypdf
(`BENCHBOOK_PDF_PYTHON`; the main venv has no PDF library and must not be modified). Usage: pdf_text.py <file.pdf>"""
import json
import sys

from pypdf import PdfReader

reader = PdfReader(sys.argv[1])
json.dump([{"page": i + 1, "text": p.extract_text() or ""} for i, p in enumerate(reader.pages)], sys.stdout, ensure_ascii=False)

import io
from typing import List
from pypdf import PdfReader

def extract_text_from_pdf(file_bytes: bytes, max_pages: int = 50) -> str:
    """
    Extract text (first max_pages) from a PDF byte blob.
    Returns a single UTF-8 string; blank pages are skipped.
    """
    with io.BytesIO(file_bytes) as buf:
        reader = PdfReader(buf)
        out: List[str] = []
        for i, page in enumerate(reader.pages[:max_pages]):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            t = t.strip()
            if t:
                out.append(t)
    return "\n\n".join(out)
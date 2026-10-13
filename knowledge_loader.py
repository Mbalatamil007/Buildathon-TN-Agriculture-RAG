"""Validate the PDF's companion source records without calling an API."""
import hashlib
import json
from pypdf import PdfReader

def load_source_records(pdf_path):
    sidecar = pdf_path.with_suffix('.sources.json')
    if not sidecar.is_file():
        return None
    payload = json.loads(sidecar.read_text(encoding='utf-8'))
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if payload.get('pdf_sha256') != digest:
        raise ValueError('PDF and source sidecar differ. Rebuild both before indexing.')
    page_count = len(PdfReader(pdf_path).pages)
    records = payload.get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('Source sidecar must contain nonempty records.')
    for record in records:
        if not isinstance(record.get('text'), str) or not record['text'].strip():
            raise ValueError('Source record has empty text.')
        page = record.get('page')
        end = record.get('page_end', page)
        if type(page) is not int or type(end) is not int or not 1 <= page <= end <= page_count:
            raise ValueError('Source page range is outside the PDF.')
        record.setdefault('knowledge_scope', payload.get('knowledge_scope', 'Collected document dataset; coverage must be reviewed.'))
    return records

"""Normalize collected text without removing scheme numbers/dates.
Chromium shapes Tamil text using locally installed fonts. JSON sidecar preserves
exact source text and combined-PDF page ranges for reliable Tamil retrieval.
"""
import argparse
import hashlib
import html
import json
import unicodedata
from io import BytesIO
from pathlib import Path
from config import DATA_DIR, PDF_PATH
from pypdf import PdfReader, PdfWriter
from playwright.sync_api import sync_playwright

def build_pdf(input_path, output_path):
    payload = json.loads(input_path.read_text(encoding='utf-8'))
    records = payload['records']
    if not records:
        raise ValueError('Collected records are empty.')
    writer, mapped = PdfWriter(), []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for record in records:
            text = unicodedata.normalize('NFC', record['text']).replace('\x00', '').strip()
            if not text:
                raise ValueError('An empty source record cannot be published.')
            source = record.get('source', '')
            url = record.get('source_url', '')
            content = f'''<!doctype html><meta charset="utf-8"><style>
                body {{ font-family: 'Nirmala UI', 'Noto Sans Tamil', sans-serif;
                font-size: 12px; line-height: 1.6; }}
                pre {{ white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; }}
                </style><h2>{html.escape(source)}</h2><p>{html.escape(url)}</p>
                <p>Original GO page: {record.get('go_page', 'N/A')}</p>
                <pre>{html.escape(text)}</pre>'''
            page.set_content(content)
            page.evaluate('document.fonts.ready')
            blob = page.pdf(format='A4', margin={'top':'15mm', 'bottom':'15mm', 'left':'15mm', 'right':'15mm'})
            start = len(writer.pages) + 1
            for pdf_page in PdfReader(BytesIO(blob)).pages:
                writer.add_page(pdf_page)
            mapped.append({**record, 'text': text, 'page': start, 'page_end': len(writer.pages)})
        browser.close()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as handle:
        writer.write(handle)
    sidecar = {'pdf_sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
               'collected_at': payload.get('collected_at'),
               'knowledge_scope': payload.get('knowledge_scope', 'Live portal collection; district applicability must be reviewed.'), 'records': mapped}
    output_path.with_suffix('.sources.json').write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved combined PDF:', output_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=str(DATA_DIR / 'collected.json'))
    parser.add_argument('--output', default=str(PDF_PATH))
    args = parser.parse_args()
    build_pdf(Path(args.input), Path(args.output))

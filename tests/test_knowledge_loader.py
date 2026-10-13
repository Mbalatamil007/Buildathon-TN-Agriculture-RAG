import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from pypdf import PdfWriter
from knowledge_loader import load_source_records

class KnowledgeLoaderTests(unittest.TestCase):
    def fixture(self, folder, record=None):
        pdf = Path(folder) / 'source.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=400)
        with pdf.open('wb') as f:
            writer.write(f)
        payload = {'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
                   'knowledge_scope': 'Starter summary',
                   'records': [record or {'text': 'A verified source summary.', 'page': 1, 'page_end': 1}]}
        pdf.with_suffix('.sources.json').write_text(json.dumps(payload), encoding='utf-8')
        return pdf
    def test_valid_records_keep_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = load_source_records(self.fixture(folder))
            self.assertEqual(rows[0]['knowledge_scope'], 'Starter summary')
    def test_changed_pdf_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = self.fixture(folder)
            pdf.write_bytes(pdf.read_bytes() + b'\nchanged')
            with self.assertRaisesRegex(ValueError, 'differ'):
                load_source_records(pdf)
    def test_invalid_page_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = self.fixture(folder, {'text': 'source text', 'page': 2})
            with self.assertRaisesRegex(ValueError, 'range'):
                load_source_records(pdf)
    def test_empty_record_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = self.fixture(folder, {'text': '', 'page': 1})
            with self.assertRaisesRegex(ValueError, 'empty'):
                load_source_records(pdf)
    def test_no_sidecar_returns_none(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(load_source_records(Path(folder) / 'other.pdf'))

if __name__ == '__main__':
    unittest.main()

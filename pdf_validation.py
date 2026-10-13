import argparse
from pathlib import Path
from config import PDF_PATH
from pypdf import PdfReader

def validate_pdf(path):
    if not path.is_file():
        raise FileNotFoundError(f'PDF missing: {path}')
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError('Use an unencrypted government PDF.')
    if not reader.pages:
        raise ValueError('PDF has no pages.')
    weak = [i for i, page in enumerate(reader.pages, 1) if len((page.extract_text() or '').strip()) < 80]
    print(f'PDF pages: {len(reader.pages)}. Low-text pages: {weak}')
    print('Review Tamil glyphs, tables, numbers and source coverage manually. OCR is not guaranteed exact.')
    return len(reader.pages)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', default=str(PDF_PATH))
    args = parser.parse_args()
    validate_pdf(Path(args.pdf))

import hashlib
import json
from config import PDF_PATH, DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ocr import read_pdf
from knowledge_loader import load_source_records

def split_pdf(path=PDF_PATH):
    if not path.is_file():
        raise FileNotFoundError(f'Place your official agriculture PDF at {path}')
    records = load_source_records(path)
    if records is None:
        # Existing PDF mode: exact combined-PDF page numbers; no invented source URL.
        records = read_pdf(path)
        records = [{**r, 'page': r['go_page'], 'page_end': r['go_page']} for r in records]
    documents = [Document(page_content=r['text'], metadata={
        key: value for key, value in r.items() if key != 'text'}) for r in records if r['text'].strip()]
    if not documents:
        raise ValueError('No text to index.')
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=['\n\n', '\n', '. ', '।', ' ', ''])
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata['document_id'] = hashlib.sha256(
            f'{i}:{chunk.page_content}:{chunk.metadata}'.encode('utf-8')).hexdigest()
        chunk.metadata['chunk_id'] = i + 1
    return chunks

if __name__ == '__main__':
    chunks = split_pdf()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / 'chunks.json').write_text(json.dumps([
        {'text': d.page_content, 'metadata': d.metadata} for d in chunks], ensure_ascii=False, indent=2), encoding='utf-8')
    print('Chunks:', len(chunks))

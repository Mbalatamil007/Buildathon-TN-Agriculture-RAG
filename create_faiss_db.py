"""Versioned snapshots plus atomic CURRENT pointer avoid half-built indexes."""
import argparse
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from config import PDF_PATH, INDEX_ROOT, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
import faiss
from langchain_community.vectorstores import FAISS
from embeddings import get_embeddings
from text_splitter import split_pdf

def build_index(pdf_path=PDF_PATH, publish=True):
    initial_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    chunks = split_pdf(pdf_path)
    ids = [doc.metadata['document_id'] for doc in chunks]
    store = FAISS.from_documents(chunks, get_embeddings(), ids=ids)
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    version = uuid.uuid4().hex
    snapshot = INDEX_ROOT / version
    snapshot.mkdir()
    try:
        faiss.write_index(store.index, str(snapshot / 'index.faiss'))
        shutil.copy2(pdf_path, snapshot / 'TN_Agriculture_Schemes.pdf')
        if hashlib.sha256((snapshot / 'TN_Agriculture_Schemes.pdf').read_bytes()).hexdigest() != initial_hash:
            raise ValueError('PDF changed during indexing. Retry with a stable PDF.')
        sidecar = pdf_path.with_suffix('.sources.json')
        if sidecar.exists():
            shutil.copy2(sidecar, snapshot / 'TN_Agriculture_Schemes.sources.json')
        manifest = {'embedding_model': EMBEDDING_MODEL, 'embedding_dimension': store.index.d,
            'chunk_size': CHUNK_SIZE, 'chunk_overlap': CHUNK_OVERLAP,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'pdf_sha256': initial_hash,
            'knowledge_scope': chunks[0].metadata.get('knowledge_scope', 'User-supplied PDF; verify source and coverage.'),
            'index_sha256': hashlib.sha256((snapshot / 'index.faiss').read_bytes()).hexdigest(),
            'documents': [{'id': doc_id, 'text': doc.page_content, 'metadata': doc.metadata}
                          for doc_id, doc in zip(ids, chunks)]}
        (snapshot / 'documents.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        if publish:
            publish_snapshot(snapshot)
    except Exception:
        shutil.rmtree(snapshot, ignore_errors=True)
        raise
    print(f'Built {len(chunks)} chunks: {snapshot}')
    return snapshot

def publish_snapshot(snapshot):
    temporary = INDEX_ROOT / ('CURRENT.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(snapshot.name, encoding='utf-8')
    os.replace(temporary, INDEX_ROOT / 'CURRENT')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', default=str(PDF_PATH))
    args = parser.parse_args()
    build_index(Path(args.pdf))

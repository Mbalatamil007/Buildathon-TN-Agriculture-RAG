import hashlib
import json
from pathlib import Path
from config import (INDEX_ROOT, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP,
                    SEARCH_K, TOP_K, RRF_K, BM25_WEIGHT, FAISS_WEIGHT)
import faiss
from langchain_core.documents import Document
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi
from langsmith import traceable
from embeddings import get_embeddings
from retrieval_utils import tokenize_text, fuse_results
from districts import ALL_DISTRICTS, validate_district, eligible_positions

def current_snapshot():
    pointer = INDEX_ROOT / 'CURRENT'
    if not pointer.is_file():
        raise FileNotFoundError('Run python create_faiss_db.py first.')
    version = pointer.read_text(encoding='utf-8').strip()
    if len(version) != 32 or any(c not in '0123456789abcdef' for c in version):
        raise ValueError('Invalid CURRENT snapshot identifier.')
    return INDEX_ROOT / version

def load_knowledge(snapshot=None):
    snapshot = Path(snapshot) if snapshot else current_snapshot()
    payload = json.loads((snapshot / 'documents.json').read_text(encoding='utf-8'))
    if (payload['embedding_model'], payload['chunk_size'], payload['chunk_overlap']) != (EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP):
        raise ValueError('Embedding/chunk settings changed. Rebuild the index.')
    for filename, key in [('TN_Agriculture_Schemes.pdf', 'pdf_sha256'), ('index.faiss', 'index_sha256')]:
        if hashlib.sha256((snapshot / filename).read_bytes()).hexdigest() != payload[key]:
            raise ValueError(f'Snapshot checksum mismatch: {filename}')
    records = payload['documents']
    documents = [Document(page_content=r['text'], metadata={**r['metadata'], 'document_id': r['id']}) for r in records]
    index = faiss.read_index(str(snapshot / 'index.faiss'))
    if not documents or index.ntotal != len(documents) or len({r['id'] for r in records}) != len(records) or index.d != payload['embedding_dimension']:
        raise ValueError('Invalid index/document mapping.')
    store = FAISS(get_embeddings(), index,
        InMemoryDocstore({r['id']: d for r, d in zip(records, documents)}),
        {i: r['id'] for i, r in enumerate(records)})
    tokenized = [tokenize_text(doc.page_content) for doc in documents]
    if not any(tokenized):
        raise ValueError('No words found for BM25.')
    return {'store': store, 'documents': documents, 'bm25': BM25Okapi(tokenized),
            'snapshot': str(snapshot), 'created_at': payload['created_at'], 'chunk_count': len(documents),
            'knowledge_scope': payload.get('knowledge_scope', 'Verify source coverage.')}

def scope_resources(resources, district=ALL_DISTRICTS):
    """Create a district-only semantic index from existing vectors: no re-embedding."""
    district = validate_district(district)
    positions = eligible_positions(resources['documents'], district)
    documents = [resources['documents'][i] for i in positions]
    scoped = {**resources, 'documents': documents, 'chunk_count': len(documents), 'district': district}
    if not documents:
        scoped.update(store=None, bm25=None)
        return scoped
    import numpy as np
    vectors = np.vstack([resources['store'].index.reconstruct(i) for i in positions]).astype('float32')
    index = faiss.IndexFlatL2(resources['store'].index.d)
    index.add(vectors)
    ids = [d.metadata['document_id'] for d in documents]
    scoped['store'] = FAISS(get_embeddings(), index,
        InMemoryDocstore(dict(zip(ids, documents))), dict(enumerate(ids)))
    tokens = [tokenize_text(d.page_content) for d in documents]
    scoped['bm25'] = BM25Okapi(tokens) if any(tokens) else None
    return scoped

@traceable(name='BM25KeywordSearch', run_type='retriever')
def search_bm25(query, resources):
    tokens = tokenize_text(query)
    if not tokens or resources['bm25'] is None:
        return []
    scores = resources['bm25'].get_scores(tokens)
    # Order all overlap candidates; BM25 scores may be zero/negative on tiny corpora.
    overlap = [i for i, doc in enumerate(resources['documents'])
               if set(tokens).intersection(tokenize_text(doc.page_content))]
    ids = sorted(overlap, key=lambda i: (-float(scores[i]), i))[:SEARCH_K]
    return [resources['documents'][i] for i in ids]

@traceable(name='FAISSSemanticSearch', run_type='retriever')
def search_faiss(query, resources):
    if resources['store'] is None:
        return []
    return resources['store'].similarity_search(query, k=min(SEARCH_K, resources['chunk_count']))

@traceable(name='HybridRetrieval', run_type='retriever')
def retrieve(queries, resources):
    rankings, bm_ids, fa_ids = [], set(), set()
    for query in queries:
        bm, semantic = search_bm25(query, resources), search_faiss(query, resources)
        bm_ids.update(d.metadata['document_id'] for d in bm)
        fa_ids.update(d.metadata['document_id'] for d in semantic)
        rankings.extend([('BM25', bm, BM25_WEIGHT / len(queries)), ('FAISS', semantic, FAISS_WEIGHT / len(queries))])
    results = fuse_results(rankings, TOP_K, RRF_K)
    sources = [{'label': f'S{i}', **r['document'].metadata, 'text': r['document'].page_content,
                'rrf_score': r['rrf_score'], 'retrieved_by': r['retrieved_by']}
               for i, r in enumerate(results, 1)]
    return {'sources': sources, 'bm25_count': len(bm_ids), 'faiss_count': len(fa_ids)}

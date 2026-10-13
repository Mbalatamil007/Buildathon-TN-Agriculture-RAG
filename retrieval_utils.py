"""Dependency-free Unicode tokenization and reciprocal rank fusion."""
import unicodedata

def tokenize_text(text):
    # Keep combining vowel/virama marks with Tamil letters. Python \\w drops them.
    result, word = [], []
    for char in unicodedata.normalize('NFC', text).casefold():
        if unicodedata.category(char)[0] in {'L', 'N', 'M'}:
            word.append(char)
        elif word:
            result.append(''.join(word)); word = []
    if word:
        result.append(''.join(word))
    return result

def fuse_results(ranked_lists, top_k=6, rrf_k=60):
    scores, docs, methods = {}, {}, {}
    for method, documents, weight in ranked_lists:
        seen = set()
        for rank, document in enumerate(documents, 1):
            doc_id = document.metadata['document_id']
            if doc_id in seen:
                continue
            seen.add(doc_id)
            docs[doc_id] = document
            scores[doc_id] = scores.get(doc_id, 0) + weight / (rrf_k + rank)
            methods.setdefault(doc_id, set()).add(method)
    ids = sorted(scores, key=lambda key: (-scores[key], key))[:top_k]
    return [{'document': docs[key], 'rrf_score': scores[key],
             'retrieved_by': sorted(methods[key])} for key in ids]

import unittest
from types import SimpleNamespace
from retrieval_utils import tokenize_text, fuse_results

class RetrievalTests(unittest.TestCase):
    def doc(self, key):
        return SimpleNamespace(metadata={'document_id': key})
    def test_tamil_combining_marks_preserved(self):
        self.assertEqual(tokenize_text('விவசாய மானியம்!'), ['விவசாய', 'மானியம்'])
    def test_case_and_numbers(self):
        self.assertEqual(tokenize_text('GO 123/2025'), ['go', '123', '2025'])
    def test_shared_document_ranks_first(self):
        a, b, c = map(self.doc, ['a', 'b', 'c'])
        result = fuse_results([('BM25', [a, b], .5), ('FAISS', [b, c], .5)])
        self.assertEqual(result[0]['document'].metadata['document_id'], 'b')
        self.assertEqual(result[0]['retrieved_by'], ['BM25', 'FAISS'])
    def test_duplicates_do_not_inflate_scores(self):
        a = self.doc('a')
        result = fuse_results([('BM25', [a, a], 1)])
        self.assertAlmostEqual(result[0]['rrf_score'], 1 / 61)
    def test_no_results(self):
        self.assertEqual(fuse_results([]), [])

if __name__ == '__main__':
    unittest.main()

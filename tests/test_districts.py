import unittest
from types import SimpleNamespace
from districts import DISTRICTS, ALL_DISTRICTS, normalize_district, record_applies, eligible_positions, validate_district
from answer_utils import language_instruction, missing_answer

class DistrictTests(unittest.TestCase):
    def test_all_38_districts(self):
        self.assertEqual(len(DISTRICTS),38)
    def test_aliases(self):
        self.assertEqual(normalize_district('Thiruvallur'),'Tiruvallur')
        self.assertEqual(normalize_district('Villupuram'),'Viluppuram')
        self.assertEqual(normalize_district('The Nilgiris'),'Nilgiris')
    def test_tamil_selection(self):
        self.assertEqual(normalize_district('மதுரை'),'Madurai')
    def test_selected_district_only(self):
        self.assertTrue(record_applies({'district':'Madurai'},'Madurai'))
        self.assertFalse(record_applies({'district':'Coimbatore'},'Madurai'))
    def test_unlabelled_not_treated_statewide(self):
        self.assertFalse(record_applies({'source':'general scheme'},'Madurai'))
    def test_explicit_statewide(self):
        self.assertTrue(record_applies({'scope':'statewide'},'Madurai'))
    def test_multi_district_scope(self):
        self.assertTrue(record_applies({'districts':['Madurai','Salem']},'Salem'))
        self.assertFalse(record_applies({'districts':['Madurai','Salem']},'Erode'))
    def test_all_districts(self):
        self.assertTrue(record_applies({'district':'Coimbatore'},ALL_DISTRICTS))
    def test_unknown_rejected(self):
        with self.assertRaises(ValueError):validate_district('Unknown')
    def test_filter_before_candidate_limit(self):
        docs=[SimpleNamespace(metadata={'district':'Coimbatore'}) for _ in range(12)]
        docs.append(SimpleNamespace(metadata={'district':'Madurai'}))
        self.assertEqual(eligible_positions(docs,'Madurai'),[12])
    def test_bilingual_missing_evidence(self):
        answer=missing_answer('English + Tamil','Madurai')
        self.assertIn('## English',answer)
        self.assertIn('## தமிழ்',answer)
    def test_bilingual_instructions(self):
        instruction=language_instruction('English + Tamil')
        self.assertIn('faithfully translate',instruction)
        self.assertIn('[S#]',instruction)

if __name__=='__main__':unittest.main()

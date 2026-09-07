import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
import nighthawk_bilingual as pub

class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs=json.loads((pub.OUT/'payload.json').read_text())['pairs']
        cls.original=json.loads((pub.OUT/'inventory.json').read_text())['nl']
    def test_ten_complete_pairs(self):
        self.assertEqual([p['part'] for p in self.pairs],list(range(10)))
        self.assertEqual(len({p[lang]['url'] for p in self.pairs for lang in ['en','nl']}),20)
    def test_dutch_body_preserved(self):
        for pair,old in zip(self.pairs,self.original):
            changed=pair['nl']['html']
            changed=changed.replace(pub.switch(pair['nl']['url'],pair['en']['url'],'nl'),'')
            changed=changed.replace(' lang="nl"','',1)
            self.assertEqual(changed,old['html'])
    def test_every_switch_matches_counterpart(self):
        for pair in self.pairs:
            for lang in ['nl','en']:
                parsed=pub.Inspect(); parsed.feed(pair[lang]['html'])
                self.assertEqual({a['hreflang']:a['href'] for a in parsed.switches},{code:pair[code]['url'] for code in ['nl','en']})
                self.assertEqual([a['hreflang'] for a in parsed.switches if a.get('aria-current')=='page'],[lang])
                self.assertTrue(all(url.startswith(pub.EN_URLS[0]) for url in parsed.series) if lang=='en' else True)
    def test_table_cells_and_math_unchanged(self):
        for pair in self.pairs:
            nl=pair['nl']['html']; en=pair['en']['html']
            cells_nl=re.findall(r'<td>(.*?)</td>',nl,re.S); cells_en=re.findall(r'<td>(.*?)</td>',en,re.S)
            self.assertEqual(len(cells_nl),len(cells_en))
            for a,b in zip(cells_nl,cells_en): self.assertEqual(pub.numbers(a,'nl'),pub.numbers(b,'en'))
            self.assertEqual(re.findall(r'\[latex.*?\[/latex\]',nl,re.S),re.findall(r'\[latex.*?\[/latex\]',en,re.S))
    def test_clock_and_accuracy_boundaries(self):
        timing=self.pairs[7]['en']['html']; mitigation=self.pairs[5]['en']['html']
        for value in ['150.819180','156.905497','181','18.85x','21.55x','did not run chi128','predefined error tolerances']: self.assertIn(value,timing)
        self.assertIn('holdouts failed',mitigation)
        self.assertIn('ZNE, PEC, postselection and DD were not enabled',mitigation)
        self.assertIn('repository remains private',self.pairs[0]['en']['html'])
    def test_numeric_sentence_punctuation(self):
        self.assertEqual(pub.numbers('21,55. 20.736 CZ.','nl'),pub.numbers('21.55. 20,736 CZ.','en'))

if __name__=='__main__': unittest.main()

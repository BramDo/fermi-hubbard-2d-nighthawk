"""Fail-closed scope and byte-preserving copy tests for the one-arm resumption."""
from pathlib import Path
import copy,tempfile,unittest
from lmpf_2d.resume_twirl1_zz import missing_spec,copy_verified,REUSED
from lmpf_2d.model import digest

class TestResumeZZ(unittest.TestCase):
    def plan(self):
        return {'twirl':1,'observable':22,'chi':[128,256],'support':{'8':'Z','9':'Z'},
            'shot_allocation':[43,7,14],'eta':1.,'max_contraction_flops':3e9,
            'max_contraction_elements':2**22,'inputs':[{'factor':3,'record_index':2,'twirl':1}]}

    def test_exactly_one_missing_arm_and_seven_reuses(self):
        spec=missing_spec(self.plan())
        self.assertEqual((spec['chi'],spec['arm'],spec['factor']),(256,3,3))
        self.assertEqual(len(REUSED),7);self.assertEqual(len(set(REUSED)),7)
        self.assertNotIn((256,3),REUSED)

    def test_reject_scope_changes(self):
        for field,value in [('twirl',0),('observable',9),('chi',[64,128]),
                            ('shot_allocation',[64,7,14]),('eta',2.),('max_contraction_flops',2e9)]:
            p=self.plan();p[field]=value
            with self.assertRaises(ValueError):missing_spec(p)
        p=self.plan();p['inputs'][0]['record_index']=23
        with self.assertRaises(ValueError):missing_spec(p)

    def test_copy_is_exact_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source';dest=Path(directory)/'dest'
            source.write_bytes(b'fixed numeric artifact\x00\xff')
            h=digest(source);copy_verified(source,dest,h)
            self.assertEqual(source.read_bytes(),dest.read_bytes())
            with self.assertRaises(FileExistsError):copy_verified(source,dest,h)
            with self.assertRaises(ValueError):copy_verified(source,Path(directory)/'bad','0'*64)

if __name__=='__main__':unittest.main()

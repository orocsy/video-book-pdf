import importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'skills/video-book-pdf/scripts'))
from pack_pdf import build

class PackTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.rows=[dict(sequence=i,candidate=n,video_pts=float(i)) for i,n in [(1,9),(2,2)]]
  for n,color in [(9,'#ffeef4'),(2,'#fffacd')]:
   im=Image.new('RGB',(320,400),color);draw=ImageDraw.Draw(im);draw.text((20,40),'SYNTHETIC 123 0.6 6 < 5',fill='black');draw.line((30,160,250,160),fill='red',width=3);im.save(self.root/f'cand_{n:04d}.png')
  self.mapping=self.root/'pages.json';self.mapping.write_text(json.dumps(self.rows))
 def tearDown(self):self.tmp.cleanup()
 def test_lossless_native_pixels_order_and_independent_pdf_decoder(self):
  out=self.root/'out.pdf';r=build(self.mapping,self.root,out,mode='lossless');self.assertEqual(r['pages'],2)
  pdf=PdfReader(out);self.assertEqual(len(pdf.pages),2)
  for page,n in zip(pdf.pages,[9,2]):
   obj=page['/Resources']['/XObject']['/Im0'].get_object();self.assertEqual(obj['/Filter'],'/JPXDecode')
   actual=Image.open(io.BytesIO(obj._data)).convert('RGB');original=Image.open(self.root/f'cand_{n:04d}.png').convert('RGB');self.assertEqual(actual.tobytes(),original.tobytes())
 def test_compact_preserves_geometry_and_passes_recorded_baseline_checks(self):
  r=build(self.mapping,self.root,self.root/'compact.pdf')
  self.assertFalse(r['lossless']);self.assertFalse(r['readability_verified'])
  for p in r['page_checks']:self.assertLessEqual(p['mse'],p['baseline']['mse']);self.assertLessEqual(p['edge_error'],p['baseline']['edge_error'])
 def test_no_overwrite(self):
  out=self.root/'out.pdf';out.write_bytes(b'keep')
  with self.assertRaises(ValueError):build(self.mapping,self.root,out)
  self.assertEqual(out.read_bytes(),b'keep')
 def test_missing_reversed_or_duplicate_page_fails(self):
  for rows in [[],[self.rows[0],self.rows[0]],[self.rows[1],{**self.rows[0],'sequence':3}],[{**self.rows[0],'video_pts':10},self.rows[1]]]:
   self.mapping.write_text(json.dumps(rows))
   with self.assertRaises(ValueError):build(self.mapping,self.root,self.root/'none.pdf')
if __name__=='__main__':unittest.main()

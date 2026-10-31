import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/video-book-pdf/scripts'))
from recover_pages import sample,propose,export

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg/ffprobe required')
class RecoveryTests(unittest.TestCase):
 def test_numbered_pages_small_text_changes_exact_source_frames_and_no_clobber(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);frames=root/'frames';frames.mkdir();font=ImageFont.load_default(size=18)
   for n in range(1,5):
    im=Image.new('RGB',(384,512),'white');d=ImageDraw.Draw(im)
    d.text((20,20),f'SYNTHETIC PAGE {n}',font=font,fill='black')
    if n==2:d.rectangle((20,90,350,300),fill='teal');d.line((30,350,300,350),fill='red',width=5)
    else:
     for j in range(9):d.text((20,90+j*28),f'Value {n*11+j}; NOT {n}.25 mm',font=font,fill='black')
    d.text((150,470),f'{n:03d}',font=font,fill='black')
    for j in range(4):im.save(frames/f'f_{(n-1)*4+j:03d}.png')
   video=root/'source.mp4';subprocess.run(['ffmpeg','-v','error','-framerate','2','-i',str(frames/'f_%03d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(video)],check=True)
   work=root/'work';sample(video,work,width=384);mapping=root/'pages.json';result=propose(work,mapping)
   self.assertEqual(result['proposed_pages'],4)
   rows=json.loads(mapping.read_text());self.assertEqual([int(r['video_pts'])//2+1 for r in rows],[1,2,3,4])
   out=root/'export';export(video,work,mapping,out)
   for r in rows:
    direct=root/f"direct-{r['candidate']}.png";n=round(r['video_pts']*2)
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-vf',f"select='eq(n,{n})'",'-frames:v','1',str(direct)],check=True)
    self.assertEqual(Image.open(direct).tobytes(),Image.open(out/f"cand_{r['candidate']:04d}.png").tobytes())
   with self.assertRaises(FileExistsError):export(video,work,mapping,out)

"""Embed native-size page images in PDF. Never edits evidence or overwrites output.

lossless: reversible JPEG 2000, decoded RGB equality required for every page.
compact: irreversible JPEG 2000; increase bitrate if PSNR/edge error is worse
than a native-resolution JPEG quality=82, 4:2:0 baseline. This is STILL LOSSY.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import time

import numpy as np
from PIL import Image


def load_pages(page_map: Path, pages_dir: Path):
    rows = sorted(json.loads(page_map.read_text()), key=lambda x: x['sequence'])
    if not rows or [r['sequence'] for r in rows] != list(range(1, len(rows)+1)):
        raise ValueError('Sequence must be nonempty, unique and contiguous')
    if len({r['candidate'] for r in rows}) != len(rows):
        raise ValueError('Repeated candidate')
    times = [float(r['video_pts']) for r in rows]
    if any(not math.isfinite(t) or t < 0 for t in times) or any(b <= a for a,b in zip(times,times[1:])):
        raise ValueError('Source PTS must be strictly increasing, finite and nonnegative')
    for row in rows:
        n = row['candidate']
        if type(n) is not int or n < 1: raise ValueError('Invalid candidate number')
        path = (pages_dir / f'cand_{n:04d}.png').resolve()
        if not path.is_relative_to(pages_dir.resolve()): raise ValueError('Evidence path escapes pages')
        if not path.is_file(): raise ValueError(f'Missing source page: {n}')
        yield row, path


def errors(original, decoded):
    a, b = np.asarray(original, dtype=np.float32), np.asarray(decoded, dtype=np.float32)
    if a.shape != b.shape: raise ValueError('Codec changed image dimensions')
    mse = float(np.mean((a-b)**2))
    # First-difference error measures thin strokes better than global PSNR alone.
    gray_a, gray_b = a.mean(axis=2), b.mean(axis=2)
    edge = float((np.mean(np.abs(np.diff(gray_a,axis=0)-np.diff(gray_b,axis=0))) +
                  np.mean(np.abs(np.diff(gray_a,axis=1)-np.diff(gray_b,axis=1)))) / 2)
    return {'mse': mse, 'psnr': None if mse == 0 else 10*math.log10(255**2/mse),
            'edge_error': edge, 'pixel_exact': bool(np.array_equal(a,b))}


def encode(image, mode, rate, quality_policy="baseline"):
    if quality_policy not in ("baseline","review"):raise ValueError("Unknown quality policy")
    base = io.BytesIO(); image.save(base, 'JPEG',quality=82,subsampling=2,optimize=True)
    baseline = errors(image, Image.open(io.BytesIO(base.getvalue())).convert('RGB'))
    if mode == 'jpeg': return base.getvalue(), 'DCTDecode', {'baseline':baseline,**baseline,'rate':None}
    rates = [None] if mode == 'lossless' else list(dict.fromkeys([rate, max(1,rate*.875), max(1,rate*.75),max(1,rate*.5),1]))
    for r in rates:
        buf=io.BytesIO(); options=dict(irreversible=mode!='lossless',mct=1)
        if r is not None: options.update(quality_mode='rates',quality_layers=[r])
        image.save(buf,'JPEG2000',**options); data=buf.getvalue()
        check=errors(image,Image.open(io.BytesIO(data)).convert('RGB'))
        if mode=='lossless':
            if not check['pixel_exact']: raise ValueError('Lossless encoder failed exact RGB equality')
            return data,'JPXDecode',dict(baseline=baseline,rate=None,**check)
        if quality_policy=='review' or (check['mse'] <= baseline['mse'] and check['edge_error'] <= baseline['edge_error']):
            return data,'JPXDecode',dict(baseline=baseline,rate=r,**check)
    raise ValueError('No compact candidate passed baseline pixel/edge check')


class PDFWriter:
    def __init__(self, stream, count):
        self.stream=stream;self.offsets={};self.count=count
        stream.write(b'%PDF-1.5\n%\xe2\xe3\xcf\xd3\n')
        self.obj(1,b'<< /Type /Catalog /Pages 2 0 R >>')
        kids=' '.join(f'{3+3*i} 0 R' for i in range(count))
        self.obj(2,f'<< /Type /Pages /Count {count} /Kids [{kids}] >>'.encode())
    def obj(self,n,body):
        self.offsets[n]=self.stream.tell();self.stream.write(f'{n} 0 obj\n'.encode()+body+b'\nendobj\n')
    def page(self,i,data,codec,width,height,ppi):
        n=3+3*i;w,h=width*72/ppi,height*72/ppi
        self.obj(n,f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w:.8f} {h:.8f}] /Resources << /XObject << /Im0 {n+1} 0 R >> >> /Contents {n+2} 0 R >>'.encode())
        self.obj(n+1,f'<< /Type /XObject /Subtype /Image /Width {width} /Height {height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /{codec} /Length {len(data)} >>\nstream\n'.encode()+data+b'\nendstream')
        content=f'q {w:.8f} 0 0 {h:.8f} 0 0 cm /Im0 Do Q\n'.encode()
        self.obj(n+2,f'<< /Length {len(content)} >>\nstream\n'.encode()+content+b'endstream')
    def finish(self):
        size=3+3*self.count;xref=self.stream.tell();self.stream.write(f'xref\n0 {size}\n0000000000 65535 f \n'.encode())
        for n in range(1,size):self.stream.write(f'{self.offsets[n]:010d} 00000 n \n'.encode())
        self.stream.write(f'trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())


def build(page_map,pages_dir,output,*,mode='compact',rate=40,ppi=144,quality_policy='baseline'):
    if mode not in ('compact','lossless','jpeg') or not 1<=rate<=100 or not 72<=ppi<=300: raise ValueError('Invalid compression settings')
    if output.exists():raise ValueError('Output exists; choose a new filename')
    pages=list(load_pages(page_map,pages_dir));output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.pdf-',suffix='.tmp',dir=output.parent);tmp=Path(name);proof=[];started=time.monotonic()
    try:
        with os.fdopen(fd,'wb') as f:
            pdf=PDFWriter(f,len(pages))
            for i,(row,path) in enumerate(pages):
                with Image.open(path) as original:
                    # Lossless means equality to the RGB decoded frame, not original YUV/video/PDF.
                    rgb=original.convert('RGB');data,codec,stats=encode(rgb,mode,rate,quality_policy)
                    pdf.page(i,data,codec,*rgb.size,ppi)
                    proof.append(dict(sequence=row['sequence'],candidate=row['candidate'],video_pts=row['video_pts'],width=rgb.width,height=rgb.height,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),encoded_bytes=len(data),codec=codec,**stats))
                if (i+1)%10==0: print(f'encoded {i+1}/{len(pages)}',flush=True)
            pdf.finish();f.flush();os.fsync(f.fileno())
        os.link(tmp,output) # Atomic no-clobber publication, including concurrent processes.
    finally:tmp.unlink(missing_ok=True)
    report=dict(quality_policy=quality_policy,readability_verified=False,mode=mode,lossless=mode=='lossless',native_pixels=True,ppi=ppi,requested_rate=rate,pages=len(pages),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),seconds=round(time.monotonic()-started,3),page_checks=proof)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--page-map',type=Path,required=True);p.add_argument('--pages-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['compact','lossless','jpeg'],default='compact');p.add_argument('--rate',type=float,default=40);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--quality-policy',choices=['baseline','review'],default='baseline',help='review disables baseline acceptance: renders/OCR/human review are mandatory')
    a=p.parse_args()
    if a.report.exists():p.error('Report exists; choose a new filename')
    report=build(a.page_map,a.pages_dir,a.output,mode=a.mode,rate=a.rate,quality_policy=a.quality_policy)
    with a.report.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='page_checks'}))
if __name__=='__main__':main()

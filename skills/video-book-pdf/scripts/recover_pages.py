"""Offline screen-recorded book recovery. Proposals require page-order/folio review."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

from page_metrics import measure,segment


def run(args,log):
    with log.open('x') as f:subprocess.run(args,stdout=f,stderr=f,check=True)


def samples(log):
    found=[]
    for line in log.read_text(errors='replace').splitlines():
        m=re.search(r'\bn:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:\s*([\d.]+)',line)
        if m:found.append(dict(index=int(m[1])+1,pts_ticks=int(m[2]),video_pts=float(m[3]),source_frame=f'f_{int(m[1])+1:05d}.png'))
    if not found or [r['index'] for r in found]!=list(range(1,len(found)+1)):raise ValueError('Missing/duplicate source timestamps')
    return found


def sample(video,work,interval=.5,width=1000):
    if not video.is_file() or not .05<=interval<=5 or not 320<=width<=2000:raise ValueError('Invalid source/sample options')
    work.mkdir(parents=True,exist_ok=False);frames=work/'frames';frames.mkdir()
    raw=subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)])
    with video.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    source=dict(video_sha256=digest,probe=json.loads(raw),interval=interval,preview_width=width)
    (work/'source.json').write_text(json.dumps(source,indent=2))
    expr=f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{interval})',showinfo,scale={width}:-2"
    run(['ffmpeg','-hide_banner','-threads','2','-i',str(video),'-an','-sn','-vf',expr,'-fps_mode','vfr',str(frames/'f_%05d.png')],work/'showinfo.log')
    data=samples(work/'showinfo.log')
    if len(list(frames.glob('*.png')))!=len(data):raise ValueError('Preview/timestamp count mismatch')
    (work/'samples.json').write_text(json.dumps(data,indent=2))
    with (work/'pts.csv').open('x') as f:
        writer=csv.writer(f);writer.writerow(['n','pts_time'])
        writer.writerows((r['index']-1,r['video_pts']) for r in data)
    return {'samples':len(data),'seconds':data[-1]['video_pts'],'work':str(work)}


def propose(work,output,change=6,same=3,min_seconds=.75):
    if output.exists():raise ValueError('Proposal file exists')
    source=json.loads((work/'source.json').read_text());sample_rows=json.loads((work/'samples.json').read_text());lookup={r['source_frame']:r for r in sample_rows}
    rows=measure(work/'frames',1/source['interval'],work/'pts.csv')
    pages=segment(rows,1/source['interval'],change,same,min_seconds,0)
    result=[]
    for i,p in enumerate(pages,1):
        exact=lookup[Path(p['best_frame']).name]
        result.append(dict(sequence=i,candidate=i,video_pts=exact['video_pts'],pts_ticks=exact['pts_ticks'],source_frame=exact['source_frame'],review='proposed',printed_page=None,sharpness=p['sharpness']))
    diagnostics=output.with_suffix('.diagnostics.json')
    if diagnostics.exists():raise ValueError('Diagnostics file exists')
    all_views=segment(rows,1/source['interval'],change,same,0,0)
    chosen={r['source_frame'] for r in result}
    short=[dict(video_pts=x['best_t'],source_frame=Path(x['best_frame']).name,reason='short_view_requires_review') for x in all_views if Path(x['best_frame']).name not in chosen]
    with diagnostics.open('x') as f:json.dump({'unretained_views':short,'complete_book_verified':False},f,indent=2)
    with output.open('x') as f:json.dump(result,f,indent=2)
    return {'proposed_pages':len(result),'unretained_views_to_review':len(short),'complete':False,'next':'Review contact sheets and printed-page gaps before export'}


def export(video,work,page_map,output):
    source=json.loads((work/'source.json').read_text())
    with video.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    if source['video_sha256']!=digest:raise ValueError('Source video changed')
    rows=sorted(json.loads(page_map.read_text()),key=lambda x:x['sequence'])
    if not rows or [r['sequence'] for r in rows]!=list(range(1,len(rows)+1)):raise ValueError('Invalid sequence')
    ticks=[r['pts_ticks'] for r in rows];candidates=[r['candidate'] for r in rows]
    if any(type(x)is not int or x<0 for x in ticks) or any(b<=a for a,b in zip(ticks,ticks[1:])) or len(set(candidates))!=len(rows) or any(type(x)is not int or x<1 for x in candidates):raise ValueError('Invalid PTS/candidate list')
    known={r['pts_ticks']:r for r in json.loads((work/'samples.json').read_text())}
    if any(t not in known or abs(r['video_pts']-known[t]['video_pts'])>1e-6 for r,t in zip(rows,ticks)):raise ValueError('PTS is not a recorded source sample')
    output.mkdir(parents=True,exist_ok=False) # Never clears a prior export.
    expr="select='"+'+'.join(f'eq(pts,{t})' for t in ticks)+"'"
    run(['ffmpeg','-hide_banner','-threads','2','-i',str(video),'-an','-sn','-vf',expr,'-fps_mode','vfr',str(output/'raw_%05d.png')],output/'export.log')
    files=sorted(output.glob('raw_*.png'))
    if len(files)!=len(rows):raise ValueError('Exact export count mismatch; incomplete directory retained for inspection')
    report=[]
    for f,r in zip(files,rows):
        target=output/f"cand_{r['candidate']:04d}.png";f.rename(target)
        report.append({'sequence':r['sequence'],'candidate':r['candidate'],'pts_ticks':r['pts_ticks'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    (output/'export-proof.json').write_text(json.dumps(report,indent=2))
    return {'exported':len(report),'native_pixels':True,'lossless_to_decoded_rgb':True,'complete_book_verified':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('sample');s.add_argument('video',type=Path);s.add_argument('work',type=Path);s.add_argument('--interval',type=float,default=.5);s.add_argument('--width',type=int,default=1000)
    s=sub.add_parser('propose');s.add_argument('work',type=Path);s.add_argument('output',type=Path);s.add_argument('--change',type=float,default=6);s.add_argument('--same',type=float,default=3);s.add_argument('--min-seconds',type=float,default=.75)
    s=sub.add_parser('export');s.add_argument('video',type=Path);s.add_argument('work',type=Path);s.add_argument('page_map',type=Path);s.add_argument('output',type=Path)
    a=p.parse_args()
    if a.cmd=='sample':result=sample(a.video,a.work,a.interval,a.width)
    elif a.cmd=='propose':result=propose(a.work,a.output,a.change,a.same,a.min_seconds)
    else:result=export(a.video,a.work,a.page_map,a.output)
    print(json.dumps(result))
if __name__=='__main__':main()

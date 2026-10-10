#!/usr/bin/env python3
"""Convert a local video to a standalone ASCII player and H.264 MP4."""
import argparse, base64, io, json, os, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

CHARS = ' .,:;i+*ox%#@'
PRESETS = {'tiny': (48, 6, 43, False), 'small': (128, 12, 34, True), 'detail': (256, 20, 38, True), 'ultra': (320, 24, 38, True)}

def run(cmd):
    return subprocess.check_output(cmd)

def convert(src, out, preset='ultra', seconds=None, audio=False, proxy_source=None):
    src, out = Path(src).resolve(), Path(out).resolve()
    if not src.is_file(): raise ValueError('Input file does not exist')
    if out.exists(): raise ValueError('Choose a new output directory to avoid replacing files')
    if proxy_source is not None and (audio or seconds is not None):
        raise ValueError("Cached video reuse supports full-length silent conversions only")
    cols, fps, crf, color = PRESETS[preset]
    vivid = preset == "ultra"
    probe = json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(src)]))
    stream = next(s for s in probe['streams'] if s['codec_type']=='video')
    w, h = stream['width'], stream['height']
    # FFmpeg autorotates phone footage; match the displayed dimensions.
    rotation = next((s.get('rotation',0) for s in stream.get('side_data_list',[]) if 'rotation' in s),0)
    if int(rotation) % 180: w,h = h,w
    cw, ch = (6, 10) if cols >= 128 else (8, 16)
    rows = max(2, round(cols*h/w*cw/ch)); rows += rows % 2
    out.mkdir(parents=True)
    fontpath = os.environ.get('ASCII_FONT') or run(['fc-match','monospace','-f','%{file}']).decode()
    if vivid:
        boldpath = Path(fontpath).with_name("DejaVuSansMono-Bold.ttf")
        if boldpath.exists(): fontpath = str(boldpath)
    font = ImageFont.truetype(fontpath, 10 if cw==6 else 13)
    glyphs = []
    palette = ['#000000','#b0b0ad','#d6d3c9','#fff7df','#bfa880','#e2bc80','#ffe0a2','#c89375','#e4a38c','#a0aa70','#b6d38e','#def2b2','#88b7ce','#add7e9','#b9a3cc','#e0c2e9']
    rgb = [tuple(bytes.fromhex(c[1:])) for c in palette]
    for c in rgb:
        for char in CHARS:
            tile = Image.new('RGB',(cw,ch)); ImageDraw.Draw(tile).text((0,-2 if cw==6 else -1),char,font=font,fill=(255,255,255) if vivid else c); glyphs.append(tile)
    atlas = np.zeros((256,ch,cw,3),dtype=np.uint8)
    for ci in range(16):
        for gi in range(len(CHARS)): atlas[(ci<<4)|gi] = np.asarray(glyphs[ci*len(CHARS)+gi])
    atlas_image = Image.fromarray(atlas.transpose(1,0,2,3).reshape(ch,256*cw,3))
    atlas_buf=io.BytesIO(); atlas_image.save(atlas_buf,format='PNG',optimize=True)
    pal = Image.new('P',(1,1)); pal.putpalette([v for c in rgb for v in c] + [0]*(768-48))
    limit = ['-t',str(seconds)] if seconds else []
    dec = subprocess.Popen(['ffmpeg','-v','error','-i',str(proxy_source or src),*limit,'-vf',f'fps={fps},scale={cols}:{rows}:flags=area','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
    audioargs = ['-i',str(src),'-map','0:v:0','-map','1:a:0?','-c:a','aac','-b:a','24k','-ac','1','-shortest'] if audio else ['-an']
    enc = subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{cols*cw}x{rows*ch}','-r',str(fps),'-i','pipe:0',*audioargs,'-c:v','libx264','-preset','fast' if vivid else 'medium','-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(out/'ascii.mp4')],stdin=subprocess.PIPE)
    count = 0; size = cols*rows*3
    try:
        while True:
            buf = dec.stdout.read(size)
            if not buf: break
            if len(buf)!=size: raise RuntimeError('Incomplete decoded frame')
            im = Image.frombytes('RGB',(cols,rows),buf)
            im = im.filter(ImageFilter.UnsharpMask(radius=1,percent=110,threshold=2))
            pixels = np.asarray(im,dtype=np.float32)
            peak = np.maximum(pixels.max(axis=2,keepdims=True),1)
            if vivid:
                # Preserve the source hues, brighten the ink, and use heavier glyphs.
                ink = pixels * (np.minimum(peak*1.4,255)/peak)
                indices = np.minimum(len(CHARS)-1,np.rint(np.power(peak[:,:,0]/255,0.4)*(len(CHARS)-1))).astype(np.uint8)
                tiles = (atlas[indices].astype(np.float32)/255 * ink[:,:,None,None,:]).astype(np.uint8)
            else:
                ink = np.clip(pixels * (235 / peak),0,255).astype(np.uint8)
                colors = np.asarray(Image.fromarray(ink).quantize(palette=pal,dither=Image.Dither.NONE),dtype=np.uint8) if color else np.full((rows,cols),3,dtype=np.uint8)
                lum = np.asarray(im.convert('L'),dtype=np.float32)/255
                indices = np.minimum(len(CHARS)-1,np.rint(np.power(lum,0.62)*(len(CHARS)-1))).astype(np.uint8)
                tiles = atlas[indices | ((colors % 16)<<4)]
            canvas = tiles.transpose(0,2,1,3,4).reshape(rows*ch,cols*cw,3)
            enc.stdin.write(canvas.tobytes()); count+=1
            if count % (fps*30)==0: print(f'{count/fps:.0f}s converted',flush=True)
    finally:
        dec.stdout.close(); enc.stdin.close()
        dr, er = dec.wait(), enc.wait()
    if dr or er or not count: raise RuntimeError('Video decoding or encoding failed')
    # Store a tiny spatial proxy. The browser rebuilds the dense ASCII grid live.
    proxyargs = ['-c:a','aac','-b:a','24k','-ac','1'] if audio else ['-an']
    if proxy_source is not None:
        shutil.copy2(proxy_source,out/'proxy.mp4')
    else:
        subprocess.run(['ffmpeg','-v','error','-i',str(src),*limit,'-vf',f'fps={fps},scale={cols}:{rows}:flags=area',*proxyargs,'-c:v','libx264','-preset','slow','-crf','30','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'proxy.mp4')],check=True)
    meta = dict(cols=cols,rows=rows,fps=fps,count=count,chars=CHARS,palette=palette,cw=cw,ch=ch,color=color,audio=audio,vivid=vivid,atlas=base64.b64encode(atlas_buf.getvalue()).decode())
    template = (Path(__file__).parent/'player-video.html').read_text()
    (out/'index.html').write_text(template.replace('__META__',json.dumps(meta)).replace('__DATA__',base64.b64encode((out/'proxy.mp4').read_bytes()).decode()))
    report = {'source_bytes':src.stat().st_size,'duration_seconds':count/fps,'preset':preset,'vivid':vivid,'columns':cols,'rows':rows,'fps':fps,'audio':audio,'files':{p.name:p.stat().st_size for p in out.iterdir()}}
    (out/'report.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2)); return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input'); p.add_argument('-o','--output',required=True); p.add_argument('--preset',choices=PRESETS,default='ultra'); p.add_argument('--seconds',type=float); p.add_argument('--audio',action='store_true'); a=p.parse_args()
    if a.seconds is not None and a.seconds<=0: p.error('--seconds must be positive')
    convert(a.input,a.output,a.preset,a.seconds,a.audio)

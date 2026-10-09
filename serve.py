#!/usr/bin/env python3
"""Local upload UI. Videos stay on this computer."""
import json, threading, uuid
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from ascii_video import convert
ROOT=Path(__file__).parent.resolve(); JOBS={}; LOCK=threading.Lock()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kw): super().__init__(*args,directory=str(ROOT),**kw)
    def reply(self,status,data):
        body=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path.startswith('/status/'):
            return self.reply(200,JOBS.get(self.path.split('/')[-1],{'state':'missing'}))
        if self.path=='/':self.path='/upload.html'
        super().do_GET()
    def do_POST(self):
        u=urlparse(self.path)
        if u.path!='/convert':return self.reply(404,{'error':'Unknown endpoint'})
        q=parse_qs(u.query); ext=q.get('ext',[''])[0].lower(); preset=q.get('preset',['ultra'])[0]
        if ext not in ['mp4','mov'] or preset not in ['tiny','small','detail','ultra']:return self.reply(400,{'error':'Choose an MP4 or MOV and a valid preset'})
        try: size=int(self.headers.get('Content-Length','0'))
        except ValueError:return self.reply(400,{'error':'Invalid upload size'})
        if size<=0 or size>2*1024**3:return self.reply(413,{'error':'Upload must be between 1 byte and 2 GB'})
        if not LOCK.acquire(blocking=False):return self.reply(409,{'error':'A conversion is already running'})
        job=uuid.uuid4().hex; folder=ROOT/'uploads';folder.mkdir(exist_ok=True); src=folder/(job+'.'+ext)
        try:
            with src.open('xb') as f:
                remaining=size
                while remaining:
                    chunk=self.rfile.read(min(1024**2,remaining))
                    if not chunk:raise ValueError('Upload interrupted')
                    f.write(chunk);remaining-=len(chunk)
        except Exception as e:LOCK.release();return self.reply(400,{'error':str(e)})
        JOBS[job]={'state':'converting'}
        def work():
            try:
                report=convert(src,ROOT/'outputs'/job,preset,audio=q.get('audio',['0'])[0]=='1')
                JOBS[job]={'state':'done','url':f'/outputs/{job}/index.html','report':report}
            except Exception as e:JOBS[job]={'state':'error','error':str(e)}
            finally:LOCK.release()
        threading.Thread(target=work,daemon=True).start();self.reply(202,{'job':job})
if __name__=='__main__':
    print('Open http://localhost:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()

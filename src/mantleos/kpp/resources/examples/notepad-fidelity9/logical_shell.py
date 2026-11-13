"""Local preview shell for the independent Anchor/Gate logical interpreter.

Run: python logical_shell.py --port 8765
Open: http://127.0.0.1:8765/

Single-user, in-memory experiment. No model API, filesystem save, cross-site
requests, or OS clipboard effects are made by the interpreter. The browser may
read an explicitly chosen file and offer a download on a user click.
"""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse
from logical_engine import LogicalMachine, Rejected, virtual_path

ROOT=Path(__file__).resolve().parent
MAX_BODY = 262144


class LocalHost(ThreadingHTTPServer):
    allow_reuse_address=True
    daemon_threads=True
    def __init__(self, address, *args):
        super().__init__(address, *args)
        self.machine=LogicalMachine('Hello, Anchor!')
        self.lock=RLock()


class Handler(BaseHTTPRequestHandler):
    server: LocalHost
    def log_message(self, fmt, *args):
        pass

    def _send(self, status, content, media):
        self.send_response(status)
        self.send_header('Content-Type',media)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'")
        self.send_header('Content-Length',str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, data, status=200):
        self._send(status,json.dumps(data,ensure_ascii=False).encode('utf-8'),'application/json; charset=utf-8')

    def _body(self):
        size=self.headers.get('Content-Length')
        if size is None or not size.isdigit() or int(size)>MAX_BODY:
            raise ValueError('Expected bounded JSON request')
        if self.headers.get('Content-Type','').split(';')[0].strip().lower() != 'application/json':
            raise ValueError('JSON content type required')
        origin=self.headers.get('Origin')
        if origin is not None and origin != f'http://{self.headers.get("Host")}':
            raise ValueError('Cross-origin request denied')
        data=json.loads(self.rfile.read(int(size)))
        if type(data) is not dict:raise ValueError('Expected JSON object')
        return data

    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':path='/shell.html'
        if path in ('/shell.html','/shell.css','/shell.js'):
            suffix=path.rsplit('.',1)[-1]
            media={'html':'text/html; charset=utf-8', 'css':'text/css; charset=utf-8',
                   'js':'application/javascript; charset=utf-8'}[suffix]
            self._send(200,(ROOT/path[1:]).read_bytes(),media)
            return
        with self.server.lock:
            if path=='/api/state':
                self._json({'outcome':'VIEW_ONLY','state':self.server.machine.state(),
                            'gate_family_count':self.server.machine.economy['gate_family_count'],
                            'anchor_count':self.server.machine.economy['anchor_count'],
                            'condition_clause_count':self.server.machine.economy['source_condition_count'],
                            'effect_profile':'VIRTUAL_ONLY'})
                return
            if path=='/api/packet':
                try:self._json({'prompt':self.server.machine.reasoning_prompt()})
                except Rejected as e:self._json({'error':str(e)},400)
                return
        self._json({'error':'Unknown route'},404)

    def do_POST(self):
        try:
            args=self._body()
            path=urlparse(self.path).path
            with self.server.lock:
                if path=='/api/command':
                    if set(args)!={'action','payload'}:raise ValueError('Action and payload required')
                    response=self.server.machine.send(args['action'],args['payload'])
                elif path=='/api/reset':
                    if args:raise ValueError('reset accepts empty object')
                    self.server.machine=LogicalMachine('Hello, Anchor!')
                    response={'outcome':'VIEW_ONLY','state':self.server.machine.state()}
                elif path=='/api/seed-file':
                    if set(args)!={'path','text'}:raise ValueError('Virtual file path and text required')
                    name=virtual_path(args['path'])
                    if type(args['text']) is not str:raise ValueError('Virtual file text must be a string')
                    self.server.machine.files[name]=args['text'].encode('utf-8')
                    response={'outcome':'VIRTUAL_FILE_SEEDED','state':self.server.machine.state()}
                else:
                    self._json({'error':'Unknown route'},404);return
            self._json(response)
        except (ValueError,Rejected,UnicodeError,json.JSONDecodeError) as error:
            self._json({'error':str(error)},400)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8765)
    args=p.parse_args(argv)
    if not (1024<=args.port<=65535):p.error('Port must be 1024..65535')
    server=LocalHost(('127.0.0.1',args.port),Handler)
    print(f'Anchor Notepad logical shell — http://127.0.0.1:{args.port}/')
    print('Virtual-only host effects; no model API. Press Ctrl+C to stop.')
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()

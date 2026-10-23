"""Localhost-only preview bridge with append-only live modules and consented coarse activity."""
import json
import re
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from .core import KPPError
from .module_revisions import source_path
from urllib.parse import parse_qs, urlsplit
from .workshop import load, record_activity, inspection, priorities, preview_fingerprint

ID=re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

def serve(workspace,host="127.0.0.1",port=8765):
    if host!="127.0.0.1":raise KPPError("Preview binds to loopback only")
    workspace=Path(workspace).resolve()
    _,state=load(workspace)
    if state.get("preview_kind") != "progressive-web":
        raise KPPError("No live browser preview configured for this recipe")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args):
            # Avoid logging URLs and request bodies; no telemetry beyond consented areas.
            pass
        def send(self,data,kind="application/json",status=200):
            self.send_response(status)
            self.send_header("Content-Type",kind+"; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data if isinstance(data,bytes) else data.encode("utf-8"))
        def do_GET(self):
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self.send('{"error":"wrong host"}',status=403);return
            try:
                recipe,state=load(workspace)
                path=self.path.split("?",1)[0]
                if path in ("/","/index.html"):
                    self.send((workspace/"app"/"index.html").read_bytes(),"text/html");return
                if path=="/runtime.js":
                    self.send((workspace/"app"/"runtime.js").read_bytes(),"text/javascript");return
                if state.get("preview_kind")=="progressive-web" and path in ("/base.js","/style.css"):
                    kind="text/javascript" if path.endswith(".js") else "text/css"
                    self.send((workspace/"app"/path[1:]).read_bytes(),kind);return
                if path=="/snapshot":
                    self.send(json.dumps({"revision":state["revision"],"phase":state["phase"],"modules":state["modules"],
                                         "fingerprint":preview_fingerprint(recipe,state),"recipe_sha256":state["recipe_hash"],"report":inspection(workspace)}));return
                if path=="/body-state":
                    if state.get("initial_body_sha256"):
                        self.send((workspace/"app"/"body-state.json").read_bytes());return
                    self.send('{"schema":"kpp.browser-state/1","body":null}');return
                if path=="/priority":
                    self.send(json.dumps({"chase":priorities(workspace)}));return
                if path.startswith("/modules/") and path.endswith(".js"):
                    mid=path[len("/modules/"):-3]
                    if ID.fullmatch(mid) and mid in {m["id"] for m in state["modules"]}:
                        module=next(m for m in state['modules'] if m['id']==mid)
                        requested=parse_qs(urlsplit(self.path).query).get('sha256')
                        if requested is not None and requested != [module['sha256']]:
                            self.send('{"error":"stale module revision"}',status=409);return
                        self.send((workspace/source_path(module)).read_bytes(),"text/javascript");return
                self.send('{"error":"not found"}',status=404)
            except (KPPError,OSError,ValueError) as err:
                self.send(json.dumps({"error":str(err)}),status=409)
        def do_POST(self):
            if self.headers.get("Host") != f"127.0.0.1:{port}":
                self.send('{"error":"wrong host"}',status=403);return
            if self.path!="/activity":
                self.send('{"error":"not found"}',status=404);return
            if self.headers.get("Origin") != f"http://127.0.0.1:{port}":
                self.send('{"error":"wrong origin"}',status=403);return
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length<1 or length>128:raise KPPError("Invalid event size")
                payload=json.loads(self.rfile.read(length))
                if set(payload)!={"area"}:raise KPPError("Only coarse area is accepted")
                record_activity(workspace,payload["area"])
                self.send('{"ok":true}')
            except (ValueError,KPPError) as err:
                self.send(json.dumps({"error":str(err)}),status=400)
    server=ThreadingHTTPServer((host,port),Handler)
    print(f"KPP preview: http://{host}:{port}   (Ctrl+C to stop)",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

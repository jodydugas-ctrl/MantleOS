"""Immutable local/Google Drive snapshots; credentials belong to external NEST."""
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from .transactions import atomic_bytes, body_lock, write_json

SCOPE = 'https://www.googleapis.com/auth/drive.file'
MAX_SNAPSHOT = 512 * 1024 * 1024


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def _nest(value):
    if not value:
        raise ValueError('Cloud operations require an external --nest directory')
    path = Path(value).resolve(); path.mkdir(parents=True,exist_ok=True)
    return path


def _protect(data, decrypt=False):
    if os.name != 'nt':
        return data
    import ctypes
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32',use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise OSError(ctypes.get_last_error(),'Windows credential protection failed')
    try:
        return ctypes.string_at(target.data,target.size)
    finally:
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.LocalFree.argtypes=[ctypes.c_void_p]; kernel.LocalFree.restype=ctypes.c_void_p
        kernel.LocalFree(target.data)


def save_tokens(nest, tokens):
    path = _nest(nest)/'oauth-token.bin'
    atomic_bytes(path,_protect(json.dumps(tokens,allow_nan=False).encode()))
    if os.name != 'nt': path.chmod(0o600)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Unexpected HTTP redirect refused')


def request(method, url, *, data=None, headers=None, timeout=30, max_bytes=MAX_SNAPSHOT):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in {'www.googleapis.com','oauth2.googleapis.com'} or parsed.username:
        raise ValueError('Untrusted cloud endpoint')
    req = urllib.request.Request(url,data=data,headers=headers or {},method=method)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(req,timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code!=308:
            raise ValueError('Cloud HTTP failure: '+str(error.code)) from None
        response = error
    with response:
        payload = response.read(max_bytes+1)
        if len(payload)>max_bytes: raise ValueError('Cloud response exceeds size limit')
        return response.code,dict(response.headers),payload


def _json_request(method,url,**kwargs):
    status,headers,payload = request(method,url,**kwargs)
    from .compiled import _unique
    return status,headers,json.loads(payload,object_pairs_hook=_unique)


def authorize(nest, client_id, *, timeout=180, client_secret=None):
    """Explicit CLI login using system browser, loopback redirect, state, and PKCE."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import webbrowser
    nest = _nest(nest)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state = secrets.token_urlsafe(32)
    result = {}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            values = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            valid = values.get('state')==[state] and len(values.get('code',[]))==1
            if valid: result['code']=values['code'][0]
            self.send_response(200 if valid else 400); self.end_headers()
            self.wfile.write(b'MantleOS sign-in received. Return to the terminal.' if valid else b'Invalid sign-in response.')
        def log_message(self,*args): pass
    with HTTPServer(('127.0.0.1',0),Handler) as server:
        redirect = 'http://127.0.0.1:'+str(server.server_port)+'/'
        params = {'client_id':client_id,'redirect_uri':redirect,'response_type':'code',
                  'scope':SCOPE,'state':state,'code_challenge':challenge,
                  'code_challenge_method':'S256','access_type':'offline','prompt':'consent'}
        webbrowser.open('https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode(params))
        deadline = time.monotonic()+timeout
        while not result and time.monotonic()<deadline:
            server.timeout=min(1,deadline-time.monotonic()); server.handle_request()
    if not result: raise TimeoutError('Cloud sign-in timed out')
    fields={'client_id':client_id,'code':result['code'],
        'redirect_uri':redirect,'grant_type':'authorization_code','code_verifier':verifier}
    if client_secret:fields['client_secret']=client_secret
    form = urllib.parse.urlencode(fields).encode()
    _,_,token = _json_request('POST','https://oauth2.googleapis.com/token',data=form,
        headers={'Content-Type':'application/x-www-form-urlencoded'},max_bytes=65536)
    token['expires_at']=time.time()+token.get('expires_in',3600)
    if client_secret:token['client_secret']=client_secret
    save_tokens(nest,token); write_json(nest/'oauth-client.json',{'client_id':client_id})
    return {'result':'AUTHORIZED','scope':SCOPE,'credentials_portable':False}


class LocalSnapshots:
    def put(self, snapshot, destination):
        snapshot, target = Path(snapshot),Path(destination).resolve()
        if snapshot.stat().st_size>MAX_SNAPSHOT: raise ValueError('Snapshot exceeds size limit')
        with body_lock(target):
            atomic_bytes(target,snapshot.read_bytes(),replace=False)
            if sha(target)!=sha(snapshot): raise ValueError('Published snapshot digest mismatch')
        return {'result':'SAVED','destination':str(target),'sha256':sha(target),'bytes':target.stat().st_size,'download_verified':True}

    def get(self, source, output, *, expected_sha256=None):
        source=Path(source)
        if source.stat().st_size>MAX_SNAPSHOT: raise ValueError('Snapshot exceeds size limit')
        digest=sha(source)
        if expected_sha256 is not None and digest!=expected_sha256: raise ValueError('Snapshot digest mismatch')
        atomic_bytes(output,source.read_bytes(),replace=False)
        if sha(output)!=digest: raise ValueError('Restored snapshot digest mismatch')
        return {'sha256':digest,'source':str(source)}


class GoogleDriveSnapshots:
    def __init__(self,nest,*,transport=request):
        self.nest=_nest(nest); self.transport=transport

    def _token(self):
        token=json.loads(_protect((self.nest/'oauth-token.bin').read_bytes(),decrypt=True))
        if token.get('expires_at',0)>time.time()+60: return token['access_token']
        client=json.loads((self.nest/'oauth-client.json').read_text('utf-8'))
        fields={'client_id':client['client_id'],'grant_type':'refresh_token','refresh_token':token['refresh_token']}
        if token.get('client_secret'):fields['client_secret']=token['client_secret']
        form=urllib.parse.urlencode(fields).encode()
        _,_,raw=self.transport('POST','https://oauth2.googleapis.com/token',data=form,
            headers={'Content-Type':'application/x-www-form-urlencoded'},max_bytes=65536)
        new=json.loads(raw); token.update(new); token['expires_at']=time.time()+new.get('expires_in',3600)
        save_tokens(self.nest,token); return token['access_token']

    def _request(self,method,url,*,data=None,headers=None,max_bytes=MAX_SNAPSHOT):
        return self.transport(method,url,data=data,headers={**(headers or {}),'Authorization':'Bearer '+self._token()},
                              timeout=30,max_bytes=max_bytes)

    def put(self,snapshot,destination):
        snapshot=Path(snapshot); size=snapshot.stat().st_size
        if not 0<size<=MAX_SNAPSHOT: raise ValueError('Invalid snapshot size')
        parsed=urllib.parse.urlsplit(destination)
        parent=parsed.netloc; name=urllib.parse.unquote(parsed.path.lstrip('/'))
        if not re.fullmatch(r'[A-Za-z0-9_-]+',parent) or not name or '/' in name or '\\' in name or parsed.query or parsed.fragment:
            raise ValueError('Use gdrive://folder-id/snapshot-name')
        digest=sha(snapshot)
        key=hashlib.sha256((parent+'\n'+name+'\n'+digest).encode()).hexdigest()
        state_path=self.nest/'uploads'/(key+'.json')
        with body_lock(state_path):
            if state_path.exists():
                session=json.loads(state_path.read_text('utf-8'))
                if 'receipt' in session: return session['receipt']
            else:
                metadata={'name':name,'parents':[parent],'appProperties':{'mantle_sha256':digest,'mantle_snapshot':key}}
                _,headers,_=self._request('POST','https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',
                    data=json.dumps(metadata).encode(),headers={'Content-Type':'application/json; charset=UTF-8',
                    'X-Upload-Content-Type':'application/octet-stream','X-Upload-Content-Length':str(size)},max_bytes=65536)
                location=next((v for k,v in headers.items() if k.lower()=='location'),None)
                if not location: raise ValueError('Cloud did not return an upload session')
                parsed_location=urllib.parse.urlsplit(location)
                if parsed_location.scheme!='https' or parsed_location.hostname!='www.googleapis.com':
                    raise ValueError('Untrusted upload session')
                session={'url':location,'offset':0,'sha256':digest}
                write_json(state_path,session)
            # Query server state on every resume; a failed final response must not duplicate files.
            status,headers,raw=self._request('PUT',session['url'],data=b'',headers={'Content-Range':f'bytes */{size}'},max_bytes=65536)
            attempts=0
            with snapshot.open('rb') as stream:
                while status==308:
                    range_value=next((v for k,v in headers.items() if k.lower()=='range'),'')
                    match=re.fullmatch(r'bytes=0-(\d+)',range_value)
                    offset=int(match[1])+1 if match else 0
                    if not 0<=offset<size: raise ValueError('Invalid resumable upload offset')
                    stream.seek(offset); chunk=stream.read(1024*1024)
                    try:
                        status,headers,raw=self._request('PUT',session['url'],data=chunk,
                            headers={'Content-Type':'application/octet-stream','Content-Range':f'bytes {offset}-{offset+len(chunk)-1}/{size}'},max_bytes=65536)
                        if status==308:
                            acknowledged=next((v for k,v in headers.items() if k.lower()=='range'),'')
                            if acknowledged==range_value: raise ValueError('Upload made no progress')
                    except (OSError,ValueError):
                        attempts+=1
                        if attempts>=3: raise
                        time.sleep(min(attempts,2))
                        status,headers,raw=self._request('PUT',session['url'],data=b'',headers={'Content-Range':f'bytes */{size}'},max_bytes=65536)
            if status not in {200,201}: raise ValueError('Upload did not complete')
            info=json.loads(raw); file_id=info['id']
            import tempfile
            with tempfile.TemporaryDirectory(prefix='mantle-cloud-check-') as td:
                self.get('gdrive://'+file_id,Path(td)/'verified',expected_sha256=digest)
            receipt={'result':'SAVED','destination':'gdrive://'+file_id,'name':name,'sha256':digest,'bytes':size,'download_verified':True}
            session['receipt']=receipt; write_json(state_path,session)
            return receipt

    def get(self,source,output,*,expected_sha256=None):
        parsed=urllib.parse.urlsplit(source); file_id=parsed.netloc
        if not re.fullmatch(r'[A-Za-z0-9_-]+',file_id) or parsed.path not in {'','/'} or parsed.query or parsed.fragment:
            raise ValueError('Restore requires gdrive://file-id')
        url='https://www.googleapis.com/drive/v3/files/'+file_id
        _,_,raw=self._request('GET',url+'?fields=id,size,appProperties',max_bytes=65536)
        metadata=json.loads(raw)
        if int(metadata.get('size',0))>MAX_SNAPSHOT: raise ValueError('Cloud snapshot exceeds size limit')
        expected=expected_sha256 or metadata.get('appProperties',{}).get('mantle_sha256')
        if not expected or not re.fullmatch('[0-9a-f]{64}',expected): raise ValueError('Snapshot digest required')
        _,_,payload=self._request('GET',url+'?alt=media')
        if hashlib.sha256(payload).hexdigest()!=expected: raise ValueError('Cloud snapshot digest mismatch')
        atomic_bytes(output,payload,replace=False)
        return {'source':source,'sha256':expected,'download_verified':True}


def publish(snapshot,destination,*,nest=None,store=None):
    adapter=store or (GoogleDriveSnapshots(nest) if str(destination).startswith('gdrive://') else LocalSnapshots())
    return adapter.put(snapshot,destination)


def fetch(source,output,*,nest=None,expected_sha256=None,store=None):
    adapter=store or (GoogleDriveSnapshots(nest) if str(source).startswith('gdrive://') else LocalSnapshots())
    return adapter.get(source,output,expected_sha256=expected_sha256)

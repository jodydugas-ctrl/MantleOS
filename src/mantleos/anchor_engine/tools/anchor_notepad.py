"""NOTEPAD_LLM/1.3 host implementation of the embedded, LLM-readable rules.

No eval, dynamic imports, PC reads, system clipboard, or implicit external I/O.
An optional explicitly supplied ArtifactHost exports into its authorized root.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path
import re
import uuid
from mantleos.anchor_engine.tools.unicode_fold import fold_scalar, TABLE_JSON as FOLD_TABLE_JSON

PROFILE = 'NOTEPAD_LLM/1.3'
MAX_TEXT = 65536
MAX_JSON_BYTES = 1048576
MAX_STATE_JSON_BYTES = 8388608
MAX_DISPLAY_NUMBER = 1.7976931348623157e308
PRIMER_SHA256 = 'f85e0beaa8023c80103741268f91fdcd3936a904dd63fa99f1df52e2a8008837'
MOLECULES_SHA256 = '0882c960df82ba087401aa683e49605f3278522ee8bf8a4a970214e07d032488'
ROUTES = {op: module for module, ops in {
    'Editing': 'INSERT SELECT SELECT_ALL DELETE COPY CUT PASTE UNDO TIME_DATE',
    'Searching': 'FIND FIND_NEXT REPLACE',
    'Display': 'WORD_WRAP STATUS_BAR GOTO FONT',
    'Files': 'NEW OPEN SAVE SAVE_AS EXIT CONFIRM',
}.items() for op in ops.split()}
DOC_FIELDS = 'text saved_text filename encoding codepage dirty caret selection undo find pending'.split()
ALLOWED_KEYS = {
    'INSERT': {'text'}, 'SELECT': {'start','end'}, 'TIME_DATE': {'source','stamp'},
    'FIND': {'query','match_case','direction'}, 'REPLACE': {'find','with','all','match_case'},
    'WORD_WRAP': {'value'}, 'STATUS_BAR': {'value'}, 'GOTO': {'line'},
    'FONT': {'family','size','style'}, 'OPEN': {'filename','text'},
    'SAVE_AS': {'filename','encoding','codepage'}, 'CONFIRM': {'choice','filename','encoding','codepage'},
}

class Rejection(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def reject(code):
    raise Rejection(code)

def strict_json(source, max_bytes=MAX_JSON_BYTES):
    try:
        if len(source if isinstance(source,bytes) else source.encode('utf-8')) > max_bytes: reject('LIMIT_EXCEEDED')
    except UnicodeEncodeError: reject('INVALID_TEXT')
    def object_pairs(pairs):
        result = {}
        for name, value in pairs:
            if name in result: reject('DUPLICATE_JSON_KEY')
            result[name] = value
        return result
    def constant(_): reject('NONFINITE_JSON_NUMBER')
    def decimal(value):
        result=float(value)
        if not math.isfinite(result): reject('NONFINITE_JSON_NUMBER')
        return result
    def check(value, depth=0):
        if isinstance(value,(dict,list)):
            depth+=1
            if depth>16: reject('LIMIT_EXCEEDED')
        if isinstance(value,str): scalar(value)
        elif isinstance(value,dict):
            for key,item in value.items(): scalar(key); check(item,depth)
        elif isinstance(value,list):
            for item in value: check(item,depth)
    try:
        result=json.loads(source, object_pairs_hook=object_pairs, parse_constant=constant,parse_float=decimal)
        check(result)
        return result
    except Rejection: raise
    except (ValueError,RecursionError,UnicodeDecodeError) as error:
        raise Rejection('INVALID_JSON') from error

def scalar(value, nonempty=False, code='INVALID_TEXT'):
    if type(value) is not str or (nonempty and not value) or any(0xD800 <= ord(c) <= 0xDFFF for c in value): reject(code)
    return value

def text(value, nonempty=False):
    value = scalar(value, nonempty)
    if '\r' in value.replace('\r\n',''): reject('INVALID_TEXT')
    value = value.replace('\r\n','\n')
    if len(value) > MAX_TEXT: reject('LIMIT_EXCEEDED')
    return value

def integer(value, code='INVALID_ARGUMENT'):
    if type(value) is not int: reject(code)
    return value

def boolean(value):
    if type(value) is not bool: reject('INVALID_ARGUMENT')
    return value

def filename(value):
    value = scalar(value, True, 'INVALID_FILENAME')
    if value in ('.','..') or value[-1] in ' .' or any(ord(c) < 32 or 0x7F<=ord(c)<=0x9F or c in '/\\<>:"|?*' for c in value): reject('INVALID_FILENAME')
    stem = value.split('.',1)[0].upper()
    if stem in {'CON','PRN','AUX','NUL'} or re.fullmatch(r'(?:COM|LPT)[1-9]', stem): reject('INVALID_FILENAME')
    return value

def initial_state():
    return dict(text='', saved_text='', filename=None, encoding=None, codepage=None,
        dirty=False, caret=0, selection=[0,0], clipboard='', undo=None,
        word_wrap=False, status_bar=False, font=dict(family='Lucida Console',size=10,style='Regular'),
        find=None, pending=None, closed=False)

def offsets(buffer, caret, selection):
    if type(selection) is not list or len(selection) != 2: reject('INVALID_SELECTION')
    a,b = (integer(x,'INVALID_SELECTION') for x in selection)
    integer(caret,'INVALID_SELECTION')
    if not 0 <= a <= b <= len(buffer) or caret != b: reject('INVALID_SELECTION')

def command_shape(command):
    if type(command) is not dict or type(command.get('op')) is not str: reject('INVALID_ARGUMENT')
    op = command['op']
    if op not in ROUTES: reject('UNKNOWN_COMMAND')
    if set(command) - ({'op'} | ALLOWED_KEYS.get(op,set())): reject('INVALID_ARGUMENT')
    return op

def validate_font(value):
    if type(value) is not dict or set(value) != {'family','size','style'}: reject('INVALID_ARGUMENT')
    scalar(value['family'],True,'INVALID_ARGUMENT'); scalar(value['style'],True,'INVALID_ARGUMENT')
    size = value['size']
    if type(size) not in (int,float) or size <= 0 or size > MAX_DISPLAY_NUMBER or (type(size) is float and not math.isfinite(size)): reject('INVALID_ARGUMENT')

def validate_file_action(command):
    op = command_shape(command)
    if op not in {'NEW','OPEN','EXIT'}: reject('INVALID_ARGUMENT')
    result = deepcopy(command)
    if op == 'OPEN':
        filename(command.get('filename'))
        result['text'] = text(command.get('text'))
    return result

def validate_state(state):
    if type(state) is not dict or set(state) != set(initial_state()): reject('INVALID_STATE')
    for name in ('text','saved_text','clipboard'):
        if text(state[name]) != state[name]: reject('INVALID_STATE')
    for name in ('dirty','word_wrap','status_bar','closed'): boolean(state[name])
    if state['dirty'] != (state['text'] != state['saved_text']): reject('INVALID_STATE')
    if state['word_wrap'] and state['status_bar']: reject('INVALID_STATE')
    offsets(state['text'],state['caret'],state['selection'])
    if state['filename'] is not None: filename(state['filename'])
    if state['encoding'] not in (None,'UTF-8','UTF-16LE','UTF-16BE','ANSI'): reject('INVALID_STATE')
    if state['encoding'] == 'ANSI':
        if state['codepage'] not in ('cp1251','cp1252'): reject('INVALID_STATE')
    elif state['codepage'] is not None: reject('INVALID_STATE')
    validate_font(state['font'])
    if state['undo'] is not None:
        undo=state['undo']
        if type(undo) is not list or len(undo)!=3: reject('INVALID_STATE')
        if text(undo[0]) != undo[0]: reject('INVALID_STATE')
        offsets(undo[0],undo[1],undo[2])
    if state['find'] is not None:
        find=state['find']
        if type(find) is not dict or set(find) != {'query','match_case','direction'}: reject('INVALID_STATE')
        if text(find['query'],True) != find['query']: reject('INVALID_STATE')
        boolean(find['match_case'])
        if find['direction'] not in ('up','down'): reject('INVALID_STATE')
    if state['pending'] is not None:
        if validate_file_action(state['pending']) != state['pending'] or not state['dirty']: reject('INVALID_STATE')
    return state

def compare_text(buffer, query, match_case):
    boolean(match_case)
    if match_case: return buffer,query
    values=[[fold_scalar(c) for c in value] for value in (buffer,query)]
    if any(c is None for value in values for c in value): reject('UNSUPPORTED_CASE_MAPPING')
    return tuple(''.join(value) for value in values)

def encode_export(buffer, encoding, codepage=None):
    if type(encoding) is not str: reject('INVALID_ENCODING')
    if codepage is not None and type(codepage) is not str: reject('INVALID_ARGUMENT')
    value = buffer.replace('\n','\r\n')
    if encoding == 'ANSI':
        if codepage is None: reject('NEEDS_CODEPAGE')
        if codepage not in ('cp1251','cp1252'): reject('UNSUPPORTED_CODEPAGE')
        try: return value.encode(codepage)
        except UnicodeEncodeError: reject('UNENCODABLE_TEXT')
    if codepage is not None: reject('INVALID_ARGUMENT')
    choices={'UTF-8':(b'\xef\xbb\xbf','utf-8'),'UTF-16LE':(b'\xff\xfe','utf-16le'),'UTF-16BE':(b'\xfe\xff','utf-16be')}
    if encoding not in choices: reject('INVALID_ENCODING')
    bom,codec=choices[encoding]
    return bom+value.encode(codec)

@dataclass(frozen=True)
class Receipt:
    artifact_id: str
    filename: str
    byte_count: int
    sha256: str
    path: str

class NoExportHost:
    available=False
    simulated=False

class MockExportHost:
    available=True
    simulated=True
    def export(self, name, payload):
        # Intentionally returns no external receipt and performs no I/O.
        return None

class ArtifactHost:
    """Explicit host binding: export only inside an authorized artifact directory.

    It creates a distinct identity, verifies bytes, and never overwrites a file.
    This is task-host artifact I/O, not an implied Windows document path.
    """
    available=True
    simulated=False
    def __init__(self, root):
        self.root=Path(root).resolve(strict=True)
        if not self.root.is_dir(): raise ValueError('Artifact root must already exist')
    def export(self, name, payload):
        filename(name)
        identity=uuid.uuid4().hex
        directory=self.root/identity
        directory.mkdir()
        temporary=directory/'payload.part'
        target=directory/name
        receipt=Receipt(identity,name,len(payload),hashlib.sha256(payload).hexdigest(),str(target))
        try:
            with temporary.open('xb') as stream:
                stream.write(payload)
                stream.flush()
            if temporary.read_bytes() != payload: raise OSError('Export readback mismatch')
            temporary.rename(target)
            return receipt
        except OSError:
            # Do not guess whether a live operation partially completed.
            raise
    def verify(self, receipt, name, payload):
        if type(receipt) is not Receipt: return False
        target=Path(receipt.path).resolve(strict=True)
        if target.parent.parent != self.root or target.parent.name != receipt.artifact_id or target.name != name or receipt.filename != name: return False
        raw=target.read_bytes()
        return raw==payload and receipt.byte_count==len(payload) and receipt.sha256==hashlib.sha256(payload).hexdigest()

class Session:
    def __init__(self, state=None, routes=None, host=None, clock_observation=None):
        self._state=deepcopy(validate_state(initial_state() if state is None else state))
        self.routes=deepcopy(ROUTES if routes is None else routes)
        self.host=NoExportHost() if host is None else host
        self.clock_observation=deepcopy(clock_observation)
        self.uncertain_effect=False
        self._held_export=None
    @property
    def state(self): return deepcopy(self._state)
    def _edit(self, before, after, new_text, position):
        new_text=text(new_text)
        if new_text == before['text']: return
        after.update(text=new_text,caret=position,selection=[position,position],
            undo=[before['text'],before['caret'],deepcopy(before['selection'])])
    def _insert(self, before, after, addition):
        a,b=before['selection']
        self._edit(before,after,before['text'][:a]+addition+before['text'][b:],a+len(addition))
    def _file(self, after, command):
        op=command['op']
        if op=='EXIT': after['closed']=True; after['pending']=None; return
        base=initial_state()
        for name in DOC_FIELDS: after[name]=deepcopy(base[name])
        if op=='OPEN': after.update(text=command['text'],saved_text=command['text'],filename=command['filename'])
    def _verify_receipt(self,receipt,name,payload):
        if type(receipt) is not Receipt: return False
        if (receipt.filename!=name or type(receipt.byte_count) is not int or receipt.byte_count!=len(payload)
                or receipt.sha256!=hashlib.sha256(payload).hexdigest()): return False
        scalar(receipt.artifact_id,True); scalar(receipt.path,True)
        return self.host.verify(receipt,name,payload) is True
    def step(self, command):
        before=self.state
        after=deepcopy(before)
        result='OK'; effect='NONE'; receipt=None; provenance=None; export=None
        if self.uncertain_effect:
            return dict(result='HOST_EFFECT_UNRESOLVED',state=before,effect_claim='UNKNOWN_EFFECT')
        try:
            if before['closed']: reject('SESSION_CLOSED')
            # Apply the same JSON limits to direct API inputs as to JSONL inputs.
            if type(command) is not dict: reject('INVALID_ARGUMENT')
            try:
                strict_json(json.dumps(command,ensure_ascii=False,allow_nan=False,separators=(',',':')))
            except (TypeError,ValueError,RecursionError) as error:
                if isinstance(error,Rejection): raise
                reject('INVALID_ARGUMENT')
            op=command_shape(command)
            if before['pending'] is not None and op!='CONFIRM': reject('PENDING_CONFIRMATION')
            if self.routes.get(op) != ROUTES[op]: reject('UNROUTED_COMMAND')
            if op in {'NEW','OPEN','EXIT'}:
                action=validate_file_action(command)
                if before['dirty']: after['pending']=action; result='NEEDS_CONFIRMATION'
                else: self._file(after,action)
            elif op=='CONFIRM':
                choice=command.get('choice')
                if choice not in ('save','discard','cancel'): reject('INVALID_ARGUMENT')
                if choice!='save' and set(command)-{'op','choice'}: reject('INVALID_ARGUMENT')
                if before['pending'] is None: reject('NO_PENDING_ACTION')
                if choice=='cancel': after['pending']=None; result='CANCELLED'
                elif choice=='discard': self._file(after,before['pending'])
                else:
                    name=command.get('filename',before['filename']); encoding=command.get('encoding',before['encoding'])
                    codepage=command.get('codepage',before['codepage'] if encoding=='ANSI' else None)
                    if name is None or encoding is None: reject('NEEDS_SAVE_AS')
                    export=(name,encoding,codepage,before['text'])
                    after.update(filename=name,encoding=encoding,codepage=codepage,saved_text=before['text'],dirty=False)
                    self._file(after,before['pending'])
            elif op in {'SAVE','SAVE_AS'}:
                if op=='SAVE':
                    name,encoding,codepage=before['filename'],before['encoding'],before['codepage']
                    if name is None or encoding is None: reject('NEEDS_SAVE_AS')
                else: name,encoding,codepage=command.get('filename'),command.get('encoding'),command.get('codepage')
                export=(name,encoding,codepage,before['text'])
                after.update(filename=name,encoding=encoding,codepage=codepage,saved_text=before['text'],dirty=False)
            elif op in {'INSERT','PASTE','TIME_DATE'}:
                if op=='INSERT': addition=text(command.get('text'))
                elif op=='PASTE': addition=before['clipboard']
                else:
                    source=command.get('source')
                    if source=='user':
                        if command.get('stamp') is None or command.get('stamp')=='': reject('NEEDS_TIME')
                        addition=text(command.get('stamp'),True); provenance='USER_SUPPLIED'
                    elif source=='verified_host_clock':
                        observed=self.clock_observation
                        if type(observed) is not dict or set(observed)!={'stamp','receipt_id'}: reject('NEEDS_TIME')
                        addition=text(observed['stamp'],True); scalar(observed['receipt_id'],True)
                        if 'stamp' in command and command['stamp'] != addition: reject('NEEDS_TIME')
                        provenance={'source':'VERIFIED_HOST_CLOCK','receipt_id':observed['receipt_id']}
                    else: reject('NEEDS_TIME')
                    if source=='user' and not command.get('stamp'): reject('NEEDS_TIME')
                self._insert(before,after,addition)
            elif op in {'SELECT','SELECT_ALL'}:
                a,b=(0,len(before['text'])) if op=='SELECT_ALL' else (command.get('start'),command.get('end'))
                offsets(before['text'],b,[a,b]); after.update(caret=b,selection=[a,b])
            elif op=='UNDO':
                if before['undo'] is None: reject('NO_UNDO')
                after.update(text=before['undo'][0],caret=before['undo'][1],selection=deepcopy(before['undo'][2]),undo=None)
            elif op in {'DELETE','CUT','COPY'}:
                a,b=before['selection']
                if op=='COPY': after['clipboard']=before['text'][a:b]
                elif op=='CUT':
                    if a!=b:
                        after['clipboard']=before['text'][a:b]
                        self._edit(before,after,before['text'][:a]+before['text'][b:],a)
                else:
                    end=b if a!=b else min(b+1,len(before['text']))
                    self._edit(before,after,before['text'][:a]+before['text'][end:],a)
            elif op in {'FIND','FIND_NEXT'}:
                if op=='FIND':
                    query=text(command.get('query'),True); match=boolean(command.get('match_case')); direction=command.get('direction')
                    if direction not in ('up','down'): reject('INVALID_ARGUMENT')
                    find=dict(query=query,match_case=match,direction=direction)
                else:
                    if before['find'] is None: reject('NO_FIND')
                    find=before['find']; query=find['query']; match=find['match_case']; direction=find['direction']
                buffer,needle=compare_text(before['text'],query,match)
                index=buffer.find(needle,before['selection'][1]) if direction=='down' else buffer.rfind(needle,0,before['selection'][0])
                if op=='FIND': after['find']=deepcopy(find)
                if index<0: result='NOT_FOUND'
                else: end=index+len(query); after.update(selection=[index,end],caret=end)
            elif op=='REPLACE':
                query=text(command.get('find'),True); replacement=text(command.get('with')); all_=boolean(command.get('all'))
                buffer,needle=compare_text(before['text'],query,command.get('match_case'))
                start=0 if all_ else before['caret']; positions=[]
                while True:
                    index=buffer.find(needle,start)
                    if index<0: break
                    positions.append(index); start=index+len(query)
                    if not all_: break
                if not positions: result='NOT_FOUND'
                else:
                    pieces=[]; start=0
                    for index in positions:
                        pieces.extend([before['text'][start:index],replacement]); start=index+len(query)
                    pieces.append(before['text'][start:]); new=''.join(pieces)
                    self._edit(before,after,new,len(new) if all_ else positions[0]+len(replacement))
            elif op in {'WORD_WRAP','STATUS_BAR'}:
                value=boolean(command.get('value'))
                if op=='WORD_WRAP':
                    after['word_wrap']=value
                    if value: after['status_bar']=False
                else:
                    if before['word_wrap']: reject('DISABLED')
                    after['status_bar']=value
            elif op=='GOTO':
                if before['word_wrap']: reject('DISABLED')
                line=integer(command.get('line')); lines=before['text'].split('\n')
                if not 1<=line<=len(lines): reject('INVALID_LINE')
                index=sum(len(value)+1 for value in lines[:line-1]); after.update(caret=index,selection=[index,index])
            elif op=='FONT':
                font={name:command.get(name) for name in ('family','size','style')}
                validate_font(font); after['font']=font
            if after['text'] != before['text']: after['dirty']=(after['text']!=after['saved_text'])
            if export is not None:
                if not self.host.available: reject('NEEDS_EXPORT')
                name,encoding,codepage,buffer=export
                filename(name); payload=encode_export(buffer,encoding,codepage)
            validate_state(after)
        except Rejection as error:
            return dict(result=error.code,state=before,effect_claim='NONE')
        if export is not None:
            try:
                receipt=self.host.export(name,payload)
                if self.host.simulated:
                    if receipt is not None: raise ValueError('A mock host cannot supply a real receipt')
                    effect='SIMULATED_ONLY'
                else:
                    if not self._verify_receipt(receipt,name,payload): raise ValueError('Unverified export receipt')
                    effect='ACTUAL_RECEIPT'
            except Exception:
                self.uncertain_effect=True
                self._held_export=(deepcopy(after),name,payload)
                return dict(result='EXPORT_UNCERTAIN',state=before,effect_claim='UNKNOWN_EFFECT')
        self._state=deepcopy(after)
        outcome=dict(result=result,state=self.state,effect_claim=effect)
        if receipt is not None: outcome['receipt']=asdict(receipt)
        if provenance is not None: outcome['time_provenance']=provenance
        return outcome

    def resolve_export(self, receipt):
        """Trusted host reconciliation, outside COMMAND; never repeats the effect."""
        if not self.uncertain_effect or self._held_export is None:
            return dict(result='NO_UNRESOLVED_EFFECT',state=self.state,effect_claim='NONE')
        after,name,payload=self._held_export
        try:
            verified=not self.host.simulated and self._verify_receipt(receipt,name,payload)
        except Exception:
            verified=False
        if not verified:
            return dict(result='HOST_EFFECT_UNRESOLVED',state=self.state,effect_claim='UNKNOWN_EFFECT')
        validate_state(after)
        self._state=deepcopy(after)
        self.uncertain_effect=False
        self._held_export=None
        return dict(result='OK',state=self.state,effect_claim='ACTUAL_RECEIPT',receipt=asdict(receipt))

    def view(self):
        state=self.state; prefix=state['text'][:state['caret']]
        return dict(title=(state['filename'] or 'Untitled')+' - Notepad',text=state['text'],
            dirty=state['dirty'],word_wrap=state['word_wrap'],status_bar=state['status_bar'],
            line=prefix.count('\n')+1,column=len(prefix.rsplit('\n',1)[-1])+1)

def load_blueprint(source, primer=None, molecules=None):
    source=scalar(source)
    pattern=(r'ANCHOR BLUEPRINT: ([A-Za-z][A-Za-z0-9_]*)\n'
        r'STATUS: RELEASE CANDIDATE NOTEPAD_LLM/1\.3\n\n'
        r'BEGIN ANCHOR EXECUTION PRIMER\n([\s\S]*?)\nEND ANCHOR EXECUTION PRIMER\n\n'
        r'BEGIN STATE\n([^\n]+)\nEND STATE\n\n'
        r'BEGIN FUNCTION MAP\n([^\n]+)\nEND FUNCTION MAP\n\n'
        r'([\s\S]*?)BEGIN EXECUTION\nRUN ([A-Za-z][A-Za-z0-9_]*)\nAWAIT USER COMMAND\nEND EXECUTION\n')
    match=re.fullmatch(pattern,source)
    if match is None: reject('INVALID_BLUEPRINT')
    name,embedded,state_json,map_json,declared,run=match.groups()
    if name!=run: reject('RUN_TARGET_MISMATCH')
    embedded+='\n'
    if hashlib.sha256(embedded.encode('utf-8')).hexdigest()!=PRIMER_SHA256: reject('PROFILE_PRIMER_MISMATCH')
    if hashlib.sha256(declared.encode('utf-8')).hexdigest()!=MOLECULES_SHA256: reject('PROFILE_MOLECULE_MISMATCH')
    if primer is not None and embedded!=primer: reject('PROFILE_PRIMER_MISMATCH')
    if molecules is not None and declared!=molecules: reject('PROFILE_MOLECULE_MISMATCH')
    if '\n'+FOLD_TABLE_JSON+'\n' not in embedded: reject('PROFILE_CASE_MAPPING_MISMATCH')
    mapping=strict_json(map_json)
    expected=dict(dispatcher='Dispatch',entry='Boundary',routes=ROUTES,state_owner='Document')
    if mapping!=expected: reject('PROFILE_ROUTE_MISMATCH')
    state=validate_state(strict_json(state_json,MAX_STATE_JSON_BYTES))
    return name,state

# COMPILER_HOST_ONLY
def compile_python(source, primer, molecules):
    load_blueprint(source,primer,molecules)
    implementation=Path(__file__).read_text('utf-8')
    implementation=implementation.rsplit('\n# COMPILER_HOST_ONLY\n',1)[0]
    fold_module=(Path(__file__).parent/'unicode_fold.py').read_text('utf-8')
    # Generated thoughts keep their own complete table; repository copies share one.
    before, resource = fold_module.split('# BEGIN TABLE RESOURCE\n', 1)
    _, after = resource.split('# END TABLE RESOURCE\n', 1)
    fold_module = before + 'TABLE_JSON=' + repr(FOLD_TABLE_JSON) + '\n' + after
    implementation=implementation.replace('from mantleos.anchor_engine.tools.unicode_fold import fold_scalar, TABLE_JSON as FOLD_TABLE_JSON',fold_module+'\nFOLD_TABLE_JSON=TABLE_JSON',1)
    journal=(Path(__file__).parent/'anchor_journal.py').read_text('utf-8')
    journal=journal.replace('from mantleos.anchor_engine.tools.anchor_notepad import Session, MockExportHost, Receipt, filename, strict_json, validate_state','',1)
    license_text=(Path(__file__).resolve().parents[1]/'reference_materials/unicode/LICENSE.txt').read_text('utf-8')
    attribution='\n'.join('# '+line for line in license_text.splitlines())+'\n'
    return attribution+implementation+'\n'+journal+'\nBLUEPRINT='+repr(source)+'''\n
if __name__ == '__main__':
    import argparse, sys
    parser=argparse.ArgumentParser(description='Execute the pinned LLM-first Blueprint on JSONL COMMAND inputs')
    parser.add_argument('--mock-export',action='store_true',help='Explicit simulated export; never creates files')
    parser.add_argument('--export-dir',type=Path,help='Explicit existing authorized task-host artifact directory')
    parser.add_argument('--journal-dir',type=Path,help='Explicit existing authorized process-recovery journal directory; required for real export')
    parser.add_argument('--recover',action='store_true',help='Trusted host reconciliation of a pending effect, without replaying COMMAND')
    args=parser.parse_args()
    if args.mock_export and args.export_dir: parser.error('Choose one export mode')
    if bool(args.export_dir)!=bool(args.journal_dir): parser.error('Real export requires both --export-dir and --journal-dir')
    if args.recover and not args.journal_dir: parser.error('--recover requires a durable host binding')
    name,state=load_blueprint(BLUEPRINT)
    host=ArtifactHost(args.export_dir) if args.export_dir else MockExportHost() if args.mock_export else NoExportHost()
    session=DurableSession(args.journal_dir,args.export_dir,hashlib.sha256(BLUEPRINT.encode('utf-8')).hexdigest(),state=state) if args.journal_dir else Session(state,host=host)
    sys.stdout.reconfigure(encoding='utf-8')
    if args.recover:
        try: print(json.dumps(session.recover(),ensure_ascii=False,allow_nan=False,separators=(',',':')))
        finally: session.close()
        raise SystemExit(0)
    while True:
        line=sys.stdin.buffer.readline(MAX_JSON_BYTES+1)
        if not line: break
        if len(line)>MAX_JSON_BYTES:
            held=getattr(session,'unresolved',False) or getattr(session,'uncertain_effect',False)
            print(json.dumps(dict(result='HOST_EFFECT_UNRESOLVED' if held else 'SESSION_CLOSED' if session.state['closed'] else 'LIMIT_EXCEEDED',state=session.state,effect_claim='UNKNOWN_EFFECT' if held else 'NONE')))
            break
        try:
            if getattr(session,'unresolved',False) or getattr(session,'uncertain_effect',False):
                outcome=dict(result='HOST_EFFECT_UNRESOLVED',state=session.state,effect_claim='UNKNOWN_EFFECT')
            elif session.state['closed']:
                outcome=dict(result='SESSION_CLOSED',state=session.state,effect_claim='NONE')
            else: outcome=session.step(strict_json(line))
        except Rejection as error: outcome=dict(result=error.code,state=session.state,effect_claim='NONE')
        print(json.dumps(outcome,ensure_ascii=False,allow_nan=False,separators=(',',':')))
    if isinstance(session,DurableSession): session.close()
'''

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='Translate a self-contained NOTEPAD_LLM/1.3 Blueprint to standalone Python')
    parser.add_argument('blueprint',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    primer=(root/'templates/primer_notepad_llm_v1.txt').read_text('utf-8')
    molecules=(root/'templates/notepad_llm_v1_molecules.txt').read_text('utf-8')
    try:
        output=compile_python(args.blueprint.read_text('utf-8'),primer,molecules)
        with args.output.open('x',encoding='utf-8',newline='\n') as stream: stream.write(output)
    except (Rejection,OSError) as error: parser.exit(1,f'FAIL: {error}\n')
    return 0

if __name__=='__main__': raise SystemExit(main())

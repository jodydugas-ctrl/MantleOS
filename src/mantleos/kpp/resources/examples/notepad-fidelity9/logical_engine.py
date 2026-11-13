"""Independent, bounded logical reference interpreter for the Notepad Anchor contracts.

This is a deterministic *test oracle / preview backend*, NOT an LLM and NOT native
Anchor execution. It deliberately imports no notepad_*.py application modules.
Filesystem and clipboard effects are simulated in memory. There is NO external
filesystem write in dispatch(), and a virtual save is NEVER claimed as a real save.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / 'LOGICAL-CONTRACT.json'
ECONOMY_PATH = ROOT / 'GATE-ECONOMY.json'


class Rejected(Exception):
    pass


class Undetermined(Exception):
    pass


def require(test, why):
    if not test:
        raise Rejected(why)


def exact_object(value, fields):
    require(type(value) is dict and set(value) == set(fields),
            'Payload must be an object with exactly: ' + ', '.join(fields))


def index(value, upper, name):
    require(type(value) is int and 0 <= value <= upper,
            f'{name} must be an integer in [0, {upper}] (bool is not an integer)')


def virtual_path(path):
    require(type(path) is str and len(path) > 1 and path.startswith('/') and '\x00' not in path,
            'Virtual file path must be a nonempty absolute path')
    require('..' not in path.split('/'), 'Parent traversal is not supported by the virtual host')
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


@dataclass
class ViewResult:
    kind: str = 'snapshot'
    selection: list[int] | None = None
    count: int | None = None

    def as_dict(self):
        d = {'kind': self.kind}
        if self.selection is not None:
            d['selection'] = self.selection
        if self.count is not None:
            d['count'] = self.count
        return d


class LogicalMachine:
    """Rule-driven admission + independently implemented transitions.

    Runtime action admission, action-specific text clauses and participating Gate
    families are always read from declarative JSON. The procedure implementations
    below make it a reference interpreter, not a magical compiler of prose.
    """
    def __init__(self, text='', *, clipboard='', files=None, history_limit=100):
        require(type(text) is str and type(clipboard) is str, 'Initial text/clipboard must be text')
        require(type(history_limit) is int and history_limit > 0, 'Invalid history limit')
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
        self.economy = json.loads(ECONOMY_PATH.read_text(encoding='utf-8'))
        self.clauses = {c['action']: c for c in self.contract['gate_conditions'] if c['phase']=='RUNTIME'}
        self.gates_for = {a: [] for a in self.clauses}
        for g in self.economy['gate_families']:
            for a in g['actions']:
                self.gates_for[a].append(g['id'])
        self.text = text
        self.baseline = text
        self.revision = 0
        self.undo = []
        self.redo = []
        self.history_limit = history_limit
        self.expected_revision = 0
        self.active_path = None
        self.expected_digest = None
        self.clipboard = clipboard
        self.files = dict(files or {})  # virtual path -> bytes
        self.fail_effects = set()  # deliberately simulated test faults
        self.last_packet = None
        self.last_trace = None
        self._check_contract_integrity()

    def _check_contract_integrity(self):
        ids = [a['id'] for a in self.contract['anchors']]
        require(len(ids)==len(set(ids))==9, 'Not exactly nine distinct Anchor applications')
        require(set(self.clauses)==set(self.contract['conformance']['expected_actions']),
                'Action clauses do not cover the declared command vocabulary')
        all_clauses = {g['gate_id'] for g in self.contract['gate_conditions']}
        covered = [cl for g in self.economy['gate_families'] for cl in g['clauses']]
        require(set(covered)==all_clauses and len(covered)==len(set(covered)),
                'Each original rule clause must have one unique owning Gate family')
        require(all(self.gates_for.values()), 'A command has no gate protection')
        require(all(set(g['participants']).issubset(ids) for g in self.economy['gate_families']),
                'A Gate refers to an unknown Anchor')

    @property
    def dirty(self):
        return self.text != self.baseline

    def state(self):
        return {
            'text': self.text,
            'revision': self.revision,
            'dirty': self.dirty,
            'undo_count': len(self.undo),
            'redo_count': len(self.redo),
            'path': self.active_path,
            'clipboard': self.clipboard,
            'virtual_file_count': len(self.files),
        }

    def logical_state(self):
        """Complete known state for a blind LLM stimulus packet; no source code."""
        return {
            'text': self.text, 'clean_baseline': self.baseline,
            'revision': self.revision,
            'undo_stack': deepcopy(self.undo), 'redo_stack': deepcopy(self.redo),
            'history_expected_revision': self.expected_revision,
            'history_limit': self.history_limit,
            'active_path': self.active_path,
            'expected_digest': self.expected_digest,
            'virtual_clipboard': self.clipboard,
            'virtual_files': {p: {'bytes_hex': b.hex(), 'sha256': digest(b)} for p,b in self.files.items()},
            'simulated_effect_failures': sorted(self.fail_effects),
        }

    def _set(self, value, *, track=True):
        require(type(value) is str, 'Document text must be a string')
        if value == self.text:
            return False
        before = self.text
        self.text = value
        self.revision += 1
        if track:
            self.undo.append([before, value])
            if len(self.undo)>self.history_limit:
                del self.undo[:-self.history_limit]
            self.redo.clear()
        self.expected_revision = self.revision
        return True

    def _history_current(self):
        require(self.expected_revision == self.revision, 'History is stale')

    def _range(self, payload, *, nonempty=False):
        exact_object(payload, ('start','end'))
        start, end = payload['start'], payload['end']
        index(start, len(self.text), 'start'); index(end, len(self.text), 'end')
        require(start < end if nonempty else start <= end,
                'Selection boundaries are invalid')
        return start, end

    def _clipboard_read(self):
        if 'CLIPBOARD_READ' in self.fail_effects:
            raise Rejected('Simulated clipboard read failure')
        return self.clipboard

    def _clipboard_write(self, value):
        if 'CLIPBOARD_WRITE' in self.fail_effects:
            raise Rejected('Simulated clipboard write failure')
        self.clipboard = value

    def _read_file(self, path):
        if 'FS_READ' in self.fail_effects:
            raise Rejected('Simulated file read failure')
        require(path in self.files, 'Virtual file not found')
        b = self.files[path]
        try:
            return b.decode('utf-8'), digest(b)
        except UnicodeDecodeError:
            raise Rejected('Virtual file is not UTF-8') from None

    def _write_file(self, path, data):
        if 'FS_WRITE' in self.fail_effects:
            raise Rejected('Simulated file write failure')
        self.files[path] = data
        return digest(data)

    def _match_pattern(self, query, match_case):
        require(type(query) is str and len(query)>0, 'Search query must be nonempty text')
        require(type(match_case) is bool, 'match_case must be Boolean')
        return re.compile(re.escape(query), 0 if match_case else re.IGNORECASE)

    def _dispatch(self, action, payload):
        self._history_current()
        if action == 'read':
            require(payload is None, 'read payload must be null')
            return ViewResult()
        if action == 'edit':
            require(type(payload) is str, 'edit payload must be text')
            self._set(payload)
            return ViewResult()
        if action == 'insert':
            exact_object(payload, ('offset','text'))
            off=payload['offset'];index(off,len(self.text),'offset')
            require(type(payload['text']) is str,'insert text must be a string')
            self._set(self.text[:off]+payload['text']+self.text[off:]); return ViewResult()
        if action == 'delete':
            start,end=self._range(payload)
            self._set(self.text[:start]+self.text[end:]); return ViewResult()
        if action == 'undo':
            require(payload is None,'undo payload must be null')
            require(bool(self.undo),'No undo history')
            before,after=self.undo[-1]
            require(self.text==after,'History text mismatch')
            self.undo.pop()
            self._set(before,track=False)
            self.redo.append([before,after])
            return ViewResult()
        if action == 'redo':
            require(payload is None,'redo payload must be null')
            require(bool(self.redo),'No redo history')
            before,after=self.redo[-1]
            require(self.text==before,'History text mismatch')
            self.redo.pop()
            self._set(after,track=False)
            self.undo.append([before,after])
            return ViewResult()
        if action == 'new':
            exact_object(payload,('discard',))
            require(type(payload['discard']) is bool,'discard must be Boolean')
            require(not self.dirty or payload['discard'],'Unsaved changes: discard not confirmed')
            self._set('',track=False)
            self.baseline=''; self.undo.clear();self.redo.clear()
            self.active_path=None;self.expected_digest=None
            return ViewResult()
        if action == 'open':
            exact_object(payload,('path','discard'))
            require(type(payload['discard']) is bool,'discard must be Boolean')
            path=virtual_path(payload['path'])
            require(not self.dirty or payload['discard'],'Unsaved changes: discard not confirmed')
            value,d=self._read_file(path)
            self._set(value,track=False)
            self.baseline=value;self.undo.clear();self.redo.clear()
            self.active_path=path;self.expected_digest=d
            return ViewResult()
        if action == 'save':
            require(payload is None,'save payload must be null')
            require(self.active_path is not None,'Save requires an associated file')
            if self.active_path in self.files:
                require(digest(self.files[self.active_path])==self.expected_digest,
                        'Virtual file changed outside this session')
            raw=self.text.encode('utf-8')
            self.expected_digest=self._write_file(self.active_path,raw)
            self.baseline=self.text
            return ViewResult()
        if action == 'save-as':
            exact_object(payload,('path','overwrite'))
            path=virtual_path(payload['path'])
            require(type(payload['overwrite']) is bool,'overwrite must be Boolean')
            require(path not in self.files or payload['overwrite'], 'Virtual file exists; overwrite not approved')
            if path==self.active_path and path in self.files:
                require(digest(self.files[path])==self.expected_digest,'Virtual file changed outside session')
            raw=self.text.encode('utf-8')
            d=self._write_file(path,raw)
            self.expected_digest=d;self.active_path=path;self.baseline=self.text
            return ViewResult()
        if action=='copy':
            start,end=self._range(payload,nonempty=True)
            self._clipboard_write(self.text[start:end]); return ViewResult()
        if action=='cut':
            start,end=self._range(payload,nonempty=True)
            self._clipboard_write(self.text[start:end])
            self._set(self.text[:start]+self.text[end:]);return ViewResult()
        if action=='paste':
            start,end=self._range(payload)
            content=self._clipboard_read()
            require(type(content) is str,'Clipboard observation must contain text')
            self._set(self.text[:start]+content+self.text[end:]);return ViewResult()
        if action=='select-all':
            require(payload is None,'select-all payload must be null')
            return ViewResult(kind='selection',selection=[0,len(self.text)])
        if action=='find':
            exact_object(payload,('query','start','match_case','wrap','backwards'))
            start=payload['start'];index(start,len(self.text),'start')
            require(type(payload['wrap']) is bool and type(payload['backwards']) is bool,'Search flags must be Boolean')
            pattern=self._match_pattern(payload['query'],payload['match_case'])
            matches=list(pattern.finditer(self.text))
            if payload['backwards']:
                choices=[m for m in matches if m.end()<=start]
                match=choices[-1] if choices else (matches[-1] if payload['wrap'] and matches else None)
            else:
                choices=[m for m in matches if m.start()>=start]
                match=choices[0] if choices else (matches[0] if payload['wrap'] and matches else None)
            return ViewResult(kind='match',selection=[match.start(),match.end()]) if match else ViewResult(kind='none')
        if action=='replace-one':
            exact_object(payload,('query','replacement','start','end','match_case'))
            require(type(payload['replacement']) is str,'replacement must be text')
            start=payload['start'];end=payload['end']
            index(start,len(self.text),'start');index(end,len(self.text),'end')
            require(start<end,'Selected range must be nonempty')
            p=self._match_pattern(payload['query'],payload['match_case'])
            require(p.fullmatch(self.text[start:end]) is not None,'Selection does not match query')
            self._set(self.text[:start]+payload['replacement']+self.text[end:])
            return ViewResult(kind='replace',count=1)
        if action=='replace-all':
            exact_object(payload,('query','replacement','match_case'))
            require(type(payload['replacement']) is str,'replacement must be text')
            p=self._match_pattern(payload['query'],payload['match_case'])
            value,count=p.subn(lambda _:payload['replacement'],self.text)
            self._set(value)
            return ViewResult(kind='replace',count=count)
        raise Rejected('Unrecognized command')

    def send(self, action, payload=None):
        """Apply one stimulus, return projection + provenance. No physical effects."""
        before = self.logical_state()
        rule = self.clauses.get(action) if type(action) is str else None
        packet = {
            'contract_schema': self.contract['schema'],
            'gate_economy_schema': self.economy['schema'],
            'known_state_before': before,
            'stimulus': {'action':action, 'payload':payload},
            'action_clause': rule,
            'gate_families': self.gates_for.get(action,[]),
            'host_profile': 'VIRTUAL_ONLY: effects run in memory; no OS filesystem/clipboard effects',
        }
        self.last_packet = packet
        try:
            require(rule is not None,'Unsupported action')
            output=self._dispatch(action,payload)
            result={'outcome':'PREDICTED_FROM_ANCHORS',
                    'result':output.as_dict(), 'state':self.state(),
                    'trace':{'received_by':'BH-EDITOR-INPUT',
                             'authorized_by':'WH-COMMAND-GUARD',
                             'action_clause':rule['gate_id'],
                             'gate_families':self.gates_for[action],
                             'participants':rule['participants'],
                             'external_effects':rule['external_effects'],
                             'effect_scope':'VIRTUAL_IN_MEMORY_ONLY'}}
        except (Rejected,Undetermined) as err:
            result={'outcome':'REJECTED_BY_GATE' if isinstance(err,Rejected) else 'UNDETERMINED',
                    'reason':str(err), 'state':self.state(),
                    'trace':{'received_by':'BH-EDITOR-INPUT',
                             'authorized_by':'WH-COMMAND-GUARD',
                             'action_clause':rule['gate_id'] if rule else None,
                             'gate_families':self.gates_for.get(action,[]),
                             'effect_scope':'NO_EXTERNAL_EFFECT'}}
        self.last_trace = result
        return result

    def reasoning_prompt(self):
        """A portable prompt for an *independent* LLM; contains no Python source."""
        require(self.last_packet is not None, 'Send an action first')
        p=self.last_packet
        return ('You are an Anchor logical interpreter, NOT a code runner. Do not execute code. '
                'Given the canonical Anchor meanings, the Gate rules, the COMPLETE known state, '
                'and one stimulus, predict the resulting state and observable response. '
                'Return JSON with outcome (PREDICTED_FROM_ANCHORS, REJECTED_BY_GATE, or UNDETERMINED), '
                'reason, updated state, action result and the Gate IDs applied. '
                'Host effects are SIMULATED, not real. Missing observations yield UNDETERMINED. '
                'Apply atomic mutation, revision, dirty, undo/redo, and rejection invariants. '
                'This is a blind interpretation task: do not use Python implementation source, '
                'a known answer, or executable tools.\n\n'
                'CANONICAL TYPES:\n'+json.dumps(self.contract['anchor_definition_types'],ensure_ascii=False,indent=2)+'\n\n'
                'SHARED SEMANTICS:\n'+json.dumps(self.contract['semantics'],ensure_ascii=False,indent=2)+'\n\n'
                'STIMULUS PACKET:\n'+json.dumps(p,ensure_ascii=False,indent=2)+'\n')

"""Trusted process-restart storage for NOTEPAD_LLM; no new language commands.

The journal and artifact directories must be explicitly authorized, existing,
local directories. Checksums detect damage, not malicious privileged editing.
The contract covers process termination; hardware power-loss guarantees depend
on the filesystem and are not asserted here.
"""
from copy import deepcopy
from dataclasses import asdict
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from mantleos.anchor_engine.tools.anchor_notepad import Session, MockExportHost, Receipt, filename, strict_json, validate_state

class JournalError(RuntimeError):
    pass

def canonical(value):
    return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def binding(root):
    root=Path(root).resolve(strict=True)
    if not root.is_dir(): raise JournalError('Authorized root must be a directory')
    stat=root.stat()
    return dict(path=str(root),device=stat.st_dev,inode=stat.st_ino)

def sync_directory(root):
    if os.name!='nt':
        descriptor=os.open(root,os.O_RDONLY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)

class DirectoryLock:
    """OS-owned lock: released even when its process is forcibly terminated."""
    def __init__(self,root):
        self.stream=None
        path=Path(root)/'.anchor.lock'
        if path.is_symlink(): raise JournalError('Invalid lock path')
        stream=path.open('a+b')
        try:
            if stream.seek(0,2)==0:
                stream.write(b'\0'); stream.flush()
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            stream.close()
            raise JournalError('Journal is already owned by another process') from error
        self.stream=stream
    def close(self):
        if self.stream is not None:
            self.stream.close(); self.stream=None

class JournalArtifactHost:
    available=True
    simulated=False
    def __init__(self,root,checkpoint_hook=None):
        self.identity=binding(root)
        self.root=Path(self.identity['path'])
        self.hook=checkpoint_hook or (lambda stage:None)
    def check(self):
        if binding(self.root)!=self.identity: raise JournalError('Artifact root identity changed')
    def location(self,operation,name):
        self.check(); filename(name)
        if not re.fullmatch('[0-9a-f]{32}',operation): raise JournalError('Invalid operation identity')
        directory=self.root/operation
        if directory.exists() and (directory.is_symlink() or directory.resolve()!=directory):
            raise JournalError('Artifact identity is redirected')
        return directory,directory/name
    def export(self,operation,name,payload):
        directory,target=self.location(operation,name)
        directory.mkdir() # create only; an existing identity must be reconciled
        temporary=directory/('.anchor-private.part' if name!='.anchor-private.part' else '.anchor-private-2.part')
        with temporary.open('xb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        if temporary.read_bytes()!=payload: raise JournalError('Export readback mismatch')
        self.hook('staged')
        # Atomic create-only publication on the same local filesystem. No rename
        # that could overwrite an unexpected existing target on POSIX.
        if os.name == 'nt':
            os.rename(temporary,target)
        else:
            os.link(temporary,target)
        sync_directory(directory)
        self.hook('linked')
        temporary.unlink(missing_ok=True)
        return self.inspect(operation,name,payload)
    def inspect(self,operation,name,payload):
        directory,target=self.location(operation,name)
        if target.is_symlink(): raise JournalError('Published artifact is redirected')
        if target.exists():
            if not target.is_file() or target.stat().st_size!=len(payload) or target.read_bytes()!=payload:
                raise JournalError('Published artifact does not match prepared bytes')
            if target.resolve()!=target: raise JournalError('Published artifact path changed')
            return Receipt(operation,name,len(payload),hashlib.sha256(payload).hexdigest(),str(target))
        if directory.exists():
            entries=list(directory.iterdir())
            private='.anchor-private.part' if name!='.anchor-private.part' else '.anchor-private-2.part'
            if any(x.name!=private or x.is_symlink() or not x.is_file() for x in entries):
                raise JournalError('Unexpected artifact contents; absence is not proven')
        return None # only unpublished private work, or no directory

class RecordingMock(MockExportHost):
    def __init__(self): self.exported=None
    def export(self,name,payload): self.exported=(name,payload)

class DurableSession:
    """One serialized durable state and at most one prepared external effect.

    The model supplies COMMAND only. Source hash, roots, recovery and the clock
    are trusted host configuration. Reopening never automatically repeats I/O.
    """
    def __init__(self,journal_root,artifact_root,source_sha256,state=None,clock_observation=None,checkpoint_hook=None):
        if not re.fullmatch('[0-9a-f]{64}',source_sha256): raise JournalError('Invalid source hash')
        self.journal_binding=binding(journal_root)
        self.root=Path(self.journal_binding['path'])
        self.lock=DirectoryLock(self.root)
        self.closed=False; self.storage_fault=False
        try:
            self.host=JournalArtifactHost(artifact_root,checkpoint_hook)
            self.source_sha256=source_sha256
            self.clock_observation=deepcopy(clock_observation)
            self.hook=checkpoint_hook or (lambda stage:None)
            self.path=self.root/'checkpoint.json'
            if self.path.is_symlink(): raise JournalError('Checkpoint is redirected')
            if self.path.exists():
                envelope=strict_json(self.path.read_bytes(),12*1024*1024)
                if type(envelope) is not dict or set(envelope)!={'record','sha256'}:
                    raise JournalError('Invalid checkpoint envelope')
                record=envelope['record']
                if hashlib.sha256(canonical(record)).hexdigest()!=envelope['sha256']:
                    raise JournalError('Checkpoint checksum mismatch')
                self._validate(record)
                self.record=record
            else:
                self.record=dict(schema='anchor.host-journal/1',source_sha256=source_sha256,
                    journal_binding=self.journal_binding,artifact_binding=self.host.identity,
                    state=deepcopy(validate_state(state)) if state is not None else Session().state,
                    pending=None,last_outcome=None,sequence=0)
                self._write(self.record)
        except Exception:
            self.lock.close(); raise
    def _open(self):
        if self.closed: raise JournalError('Durable session is closed')
        if self.storage_fault: raise JournalError('Storage acknowledgement uncertain; reopen the journal')
        if binding(self.root)!=self.journal_binding: raise JournalError('Journal root identity changed')
        self.host.check()
    def _validate(self,record):
        if type(record) is not dict or set(record)!={'schema','source_sha256','journal_binding','artifact_binding','state','pending','last_outcome','sequence'}:
            raise JournalError('Invalid checkpoint schema')
        if (record['schema']!='anchor.host-journal/1' or record['source_sha256']!=self.source_sha256
                or record['journal_binding']!=self.journal_binding or record['artifact_binding']!=self.host.identity):
            raise JournalError('Checkpoint does not match this source and authorized roots')
        if type(record['sequence']) is not int or record['sequence']<0: raise JournalError('Invalid journal sequence')
        validate_state(record['state'])
        pending=record['pending']
        if pending is not None:
            if type(pending) is not dict or set(pending)!={'operation','command','after','filename','payload','payload_sha256','outcome'}:
                raise JournalError('Invalid prepared effect')
            raw=base64.b64decode(pending['payload'],validate=True)
            if hashlib.sha256(raw).hexdigest()!=pending['payload_sha256']: raise JournalError('Prepared payload checksum mismatch')
            self.host.location(pending['operation'],pending['filename'])
            planner=RecordingMock()
            outcome=Session(record['state'],host=planner).step(pending['command'])
            if (planner.exported!=(pending['filename'],raw) or outcome!=pending['outcome']
                    or outcome['state']!=pending['after'] or outcome['effect_claim']!='SIMULATED_ONLY'):
                raise JournalError('Prepared effect does not match source transition')
        outcome=record['last_outcome']
        if outcome is not None:
            if type(outcome) is not dict or outcome.get('state')!=record['state']:
                raise JournalError('Acknowledged state does not match checkpoint')
            if outcome.get('effect_claim') not in {'NONE','ACTUAL_RECEIPT','UNKNOWN_EFFECT'}:
                raise JournalError('Invalid checkpoint effect claim')
    def _write(self,record):
        self._validate(record)
        raw=canonical(dict(record=record,sha256=hashlib.sha256(canonical(record)).hexdigest()))+b'\n'
        if len(raw)>12*1024*1024: raise JournalError('Journal limit exceeded')
        temporary=self.root/('checkpoint-'+uuid.uuid4().hex+'.part')
        try:
            with temporary.open('xb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,self.path)
            sync_directory(self.root)
        except Exception:
            self.storage_fault=True
            raise
        self.record=deepcopy(record)
    @property
    def state(self): return deepcopy(self.record['state'])
    @property
    def unresolved(self): return self.record['pending'] is not None
    @property
    def last_outcome(self): return deepcopy(self.record['last_outcome'])
    def step(self,command):
        self._open()
        if self.unresolved:
            return dict(result='HOST_EFFECT_UNRESOLVED',state=self.state,effect_claim='UNKNOWN_EFFECT')
        planner=RecordingMock()
        outcome=Session(self.state,host=planner,clock_observation=self.clock_observation).step(command)
        record=deepcopy(self.record); record['sequence']+=1
        if planner.exported is None:
            record.update(state=deepcopy(outcome['state']),last_outcome=deepcopy(outcome))
            self._write(record); self.hook('committed'); return outcome
        name,payload=planner.exported
        operation=uuid.uuid4().hex
        directory,_=self.host.location(operation,name)
        if directory.exists(): raise JournalError('New operation identity already exists; no effect attempted')
        record['pending']=dict(operation=operation,command=deepcopy(command),after=deepcopy(outcome['state']),
            filename=name,payload=base64.b64encode(payload).decode('ascii'),payload_sha256=hashlib.sha256(payload).hexdigest(),outcome=deepcopy(outcome))
        self._write(record); self.hook('prepared')
        try:
            pending=self.record['pending']
            receipt=self.host.export(pending['operation'],name,payload)
            if receipt is None: raise JournalError('No published artifact')
            self.hook('published')
            completed=deepcopy(outcome); completed.update(effect_claim='ACTUAL_RECEIPT',receipt=asdict(receipt))
            record=deepcopy(self.record); record.update(state=deepcopy(completed['state']),pending=None,last_outcome=completed)
            self._write(record)
        except Exception:
            return dict(result='EXPORT_UNCERTAIN',state=self.state,effect_claim='UNKNOWN_EFFECT')
        self.hook('committed')
        return deepcopy(completed)
    def recover(self):
        self._open()
        if not self.unresolved:
            return dict(result='NO_UNRESOLVED_EFFECT',state=self.state,effect_claim='NONE',
                sequence=self.record['sequence'],last_outcome=self.last_outcome)
        pending=self.record['pending']; payload=base64.b64decode(pending['payload'],validate=True)
        try: receipt=self.host.inspect(pending['operation'],pending['filename'],payload)
        except (OSError,ValueError,JournalError):
            return dict(result='HOST_EFFECT_UNRESOLVED',state=self.state,effect_claim='UNKNOWN_EFFECT')
        record=deepcopy(self.record); record['pending']=None; record['sequence']+=1
        if receipt is None:
            outcome=dict(result='NO_PUBLISHED_EFFECT',state=self.state,effect_claim='NONE')
        else:
            outcome=deepcopy(pending['outcome']); outcome.update(effect_claim='ACTUAL_RECEIPT',receipt=asdict(receipt))
            record['state']=deepcopy(outcome['state'])
        record['last_outcome']=deepcopy(outcome)
        self._write(record); self.hook('recovered')
        return outcome
    def close(self):
        if not self.closed: self.lock.close(); self.closed=True
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

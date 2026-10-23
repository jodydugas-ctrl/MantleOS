"""Durable writes, process locks and recoverable Body replacement (stdlib only)."""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import shutil
import tempfile
import threading
import uuid
from functools import wraps

_locks = {}
_guard = threading.Lock()
_held = threading.local()


def locked_body(function):
    @wraps(function)
    def wrapper(body,*args,**kwargs):
        with body_lock(body):
            ensure_clean(body)
            return function(Path(body),*args,**kwargs)
    return wrapper


def locked_host(function):
    @wraps(function)
    def wrapper(self,*args,**kwargs):
        with body_lock(self.root):
            ensure_clean(self.root)
            from . import cartridge, compiled
            if (self.root/'COMPILED.json').is_file():
                compiled.load(self.root)
            else:
                cartridge.verify(self.root)
            return function(self,*args,**kwargs)
    return wrapper


def atomic_bytes(path, data, *, replace=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'.', dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temp, path)
        else:
            # Windows rename refuses an existing destination; POSIX rename replaces
            # it, so use an atomic no-clobber hard link there instead.
            if os.name == 'nt':
                os.rename(temp, path)
            else:
                os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_json(path, value):
    atomic_bytes(path, (json.dumps(value, sort_keys=True, ensure_ascii=False,
                                  indent=2, allow_nan=False)+'\n').encode('utf-8'))


@contextmanager
def body_lock(body):
    body = Path(body).resolve()
    key = str(body).casefold() if os.name == 'nt' else str(body)
    with _guard:
        lock = _locks.setdefault(key, threading.RLock())
    with lock:
        held = getattr(_held, 'keys', set())
        if key in held:
            yield
            return
        path = body.parent / ('.'+body.name+'.mantle-lock')
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = path.open('a+b')
        try:
            if path.stat().st_size == 0:
                stream.write(b'\0'); stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _held.keys = held | {key}
            try:
                yield
            finally:
                _held.keys = held
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)
        finally:
            stream.close()


def journal_path(body):
    body = Path(body).resolve()
    return body.parent / ('.'+body.name+'.transaction.json')


def ensure_clean(body):
    if journal_path(body).exists():
        raise ValueError('Interrupted Body transaction; run recover before use')


def stage_body(body):
    body = Path(body).resolve()
    stage = body.parent / ('.'+body.name+'.stage-'+uuid.uuid4().hex)
    shutil.copytree(body, stage, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return stage


def publish_body(stage, body, *, interrupt=None):
    """Caller holds body_lock; recovery retains the previous verified generation."""
    body, stage = Path(body).resolve(), Path(stage).resolve()
    if stage.parent != body.parent or not stage.name.startswith('.'+body.name+'.stage-'):
        raise ValueError('Invalid staging directory')
    from .cartridge import verify
    verify(stage)
    ensure_clean(body)
    backup = body.parent / ('.'+body.name+'.rollback-'+uuid.uuid4().hex)
    before = (body/'MANIFEST.json').read_bytes()
    after = (stage/'MANIFEST.json').read_bytes()
    import hashlib
    journal = {'schema':'mantle.body-transaction/1', 'body':body.name,
               'stage':stage.name, 'backup':backup.name,
               'before':hashlib.sha256(before).hexdigest(),
               'after':hashlib.sha256(after).hexdigest()}
    write_json(journal_path(body), journal)
    os.replace(body, backup)
    if interrupt == 'after-backup':
        raise RuntimeError('Simulated interruption after backup')
    os.replace(stage, body)
    if interrupt == 'after-publish':
        raise RuntimeError('Simulated interruption after publish')
    journal_path(body).unlink()
    return {'result':'COMMITTED', 'body':str(body), 'rollback':str(backup)}


def recover(body):
    body = Path(body).resolve()
    with body_lock(body):
        path = journal_path(body)
        if not path.exists():
            return {'result':'CLEAN'}
        from .json_contract import loads
        import hashlib
        journal = loads(path.read_text('utf-8'))
        if journal.get('schema') != 'mantle.body-transaction/1' or journal.get('body') != body.name:
            raise ValueError('Invalid recovery journal')
        locations = {}
        for field, prefix in [('stage','stage'),('backup','rollback')]:
            name = journal.get(field, '')
            if Path(name).name != name or not name.startswith('.'+body.name+'.'+prefix+'-'):
                raise ValueError('Unsafe recovery path')
            locations[field] = body.parent/name
            if locations[field].is_symlink():
                raise ValueError('Unsafe recovery symlink')
        backup, stage = locations['backup'], locations['stage']
        from .cartridge import verify
        if backup.exists():
            verify(backup)
            if hashlib.sha256((backup/'MANIFEST.json').read_bytes()).hexdigest() != journal['before']:
                raise ValueError('Recovery backup changed')
            if body.exists():
                verify(body)
                if hashlib.sha256((body/'MANIFEST.json').read_bytes()).hexdigest() != journal['after']:
                    raise ValueError('Recovery conflict: active Body changed')
                retained = body.parent/('.'+body.name+'.uncommitted-'+uuid.uuid4().hex)
                os.replace(body, retained)
            os.replace(backup, body)
        else:
            verify(body)
            if hashlib.sha256((body/'MANIFEST.json').read_bytes()).hexdigest() != journal['before']:
                raise ValueError('Recovery conflict: original Body changed')
        path.unlink()
        return {'result':'RECOVERED', 'body':str(body), 'staging_retained':str(stage) if stage.exists() else None}

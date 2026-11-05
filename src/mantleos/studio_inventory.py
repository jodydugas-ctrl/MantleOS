"""Owner-local editor resource descriptors, separate from credential secrets.

An inventory entry never establishes a usable credential, an executable node,
or a workflow grant. Browser routes may read this index; only independently
reviewed host code can register descriptors. No provider configuration is read.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from urllib.parse import quote
import uuid

from . import json_contract as c

APPLICATION=0x4153494E
COLLECTIONS={'credentials':{'id','name','type'},'tags':{'id','name'},
             'favorites':{'id','resourceId','resourceType','resourceName'}}
MAX_ENTRIES=2048


def descriptor(collection,value):
    c.require(collection in COLLECTIONS,'Unsupported editor inventory')
    c.shape(value,COLLECTIONS[collection])
    c.identifier(value['id'])
    for key in COLLECTIONS[collection]:c.text(value[key],maximum=512)
    if collection=='favorites':
        c.identifier(value['resourceId'])
        c.require(value['resourceType'] in ('workflow','project','folder','dataTable','agent'),
                  'Invalid favorite resource type')
    return c.loads(c.canonical(value,limit=65536))


class EditorInventory:
    def __init__(self,nest):
        self.nest=Path(nest).absolute()
        self.path=self.nest/'editor-inventory.sqlite'

    @contextmanager
    def _db(self,write=False):
        for path in (self.nest,self.path):
            c.require(not path.is_symlink() and not getattr(path,'is_junction',lambda:False)(),
                      'Linked editor inventory unavailable')
        c.require(self.nest.is_dir(),'Editor inventory parent unavailable')
        if not write:c.require(self.path.is_file(),'Editor inventory is not initialized')
        uri='file:'+quote(self.path.as_posix(),safe='/:')+'?mode='+('rwc' if write else 'ro')
        db=sqlite3.connect(uri,uri=True,timeout=10)
        try:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            app=db.execute('PRAGMA application_id').fetchone()[0]
            version=db.execute('PRAGMA user_version').fetchone()[0]
            empty=not db.execute("SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone()
            if write and app==version==0 and empty:
                db.execute('CREATE TABLE versions(revision TEXT PRIMARY KEY,collection TEXT,id TEXT,content TEXT,sha256 TEXT,created TEXT,parent TEXT)')
                db.execute('CREATE TABLE current(collection TEXT,id TEXT,revision TEXT NOT NULL REFERENCES versions(revision),PRIMARY KEY(collection,id))')
                db.execute('PRAGMA application_id='+str(APPLICATION));db.execute('PRAGMA user_version=1')
            else:c.require(app==APPLICATION and version==1,'Unsupported editor inventory')
            yield db
            db.commit()
        except BaseException:
            db.rollback();raise
        finally:db.close()

    def initialize(self,*,reviewed=False):
        if reviewed is not True:raise PermissionError('Owner inventory review required')
        with self._db(write=True):pass

    def register(self,collection,value,*,revision=None,reviewed=False):
        """Trusted operator/library surface; not a browser or MIND operation."""
        if reviewed is not True:raise PermissionError('Owner inventory review required')
        value=descriptor(collection,value)
        with self._db(write=True) as db:
            old=db.execute('SELECT revision FROM current WHERE collection=? AND id=?',(collection,value['id'])).fetchone()
            c.require((old[0] if old else None)==revision,'Stale inventory descriptor')
            count=db.execute('SELECT count(*) FROM current WHERE collection=?',(collection,)).fetchone()[0]
            c.require(old is not None or count<MAX_ENTRIES,'Editor inventory limit exceeded')
            token=str(uuid.uuid4());at=datetime.now(timezone.utc).isoformat()
            db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?,?)',
                       (token,collection,value['id'],c.canonical(value),c.digest(value),at,revision))
            db.execute('INSERT OR REPLACE INTO current VALUES (?,?,?)',(collection,value['id'],token))
        return {'revision':token,'id':value['id']}

    def list(self,collection):
        c.require(collection in COLLECTIONS,'Unsupported editor inventory')
        with self._db() as db:
            rows=db.execute('SELECT v.content,v.sha256,v.created,v.revision,c.id,v.id,v.collection FROM current c '
                'JOIN versions v ON c.revision=v.revision WHERE c.collection=? ORDER BY c.id LIMIT ?',
                (collection,MAX_ENTRIES+1)).fetchall()
            count=db.execute('SELECT count(*) FROM current WHERE collection=?',(collection,)).fetchone()[0]
            c.require(count==len(rows) and count<=MAX_ENTRIES,'Editor inventory index invalid')
            result=[]
            for raw,digest,at,revision,index_id,record_id,kind in rows:
                value=descriptor(collection,c.loads(raw))
                c.require(kind==collection and value['id']==index_id==record_id and c.digest(value)==digest,
                          'Editor inventory descriptor changed')
                result.append({**value,'createdAt':at,'updatedAt':at,'revision':revision})
        return result

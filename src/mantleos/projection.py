"""Shared deterministic Engram retrieval, active memory and settled evidence.

The Raven reference supplies the behavioral target: phrase-first ranking,
supersession, historical heads, bounded excerpts, and terminal effect evidence.
This implementation handles both Raven and Mantle record forms.
"""
import hashlib
import json
import re

TOKEN = re.compile(r"[\w'-]+",re.UNICODE)
ZERO = '0'*64


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def _effect_key(record):
    body=record['body']
    return body.get('effect_id') or body.get('binding_sha256') or body.get('request_id')


def build(records):
    texts=[];postings={};superseded=set();terminals={};faces=[]
    for i,record in enumerate(records):
        body=record['body'];text=canonical({'source':record['source'],'body':body})
        texts.append(text)
        for token in set(TOKEN.findall(text.casefold())):postings.setdefault(token,[]).append(i)
        if record['type'] in {'memory','soft','face'} and body.get('supersedes'):
            superseded.add(body['supersedes'])
        if record['type']=='effect' and _effect_key(record):terminals[_effect_key(record)]=i
        if record['type']=='face':faces.append(i)
    active_faces=[i for i in faces if records[i]['id'] not in superseded]
    return {'schema':'mantle.engram-index/1','texts':texts,'postings':postings,
            'superseded':sorted(superseded),'effect_terminals':terminals,
            'active_face':active_faces[-1] if active_faces else None}


def rank(records,index,query,*,limit=8,types=None,include_superseded=False):
    if not isinstance(query,str) or len(query.encode('utf-8'))>8192:
        raise ValueError('Invalid query')
    if type(limit) is not int or not 1<=limit<=100:raise ValueError('Invalid query limit')
    if types is not None and (not isinstance(types,(list,tuple,set,frozenset)) or not types or any(not isinstance(t,str) for t in types)):
        raise ValueError('Invalid query types')
    terms=set(TOKEN.findall(query.casefold()));candidates=set()
    for term in terms:candidates.update(index['postings'].get(term,[]))
    phrase=query.strip().casefold();ranked=[]
    for i in candidates:
        record=records[i]
        if types is not None and record['type'] not in types:continue
        if not include_superseded:
            if record['id'] in index['superseded']:continue
            if record['type']=='face' and i!=index['active_face']:continue
        text=index['texts'][i].casefold()
        matched=sorted(t for t in terms if i in index['postings'].get(t,[]))
        ranked.append((bool(phrase and phrase in text),len(matched),record['seq'],i,matched))
    return sorted(ranked,reverse=True)[:limit]


def _reference(record):
    return {'id':record['id'],'seq':record['seq'],'type':record['type'],'source':record['source'],
            'record_sha256':record['sha256'],
            'body_sha256':hashlib.sha256(canonical(record['body']).encode()).hexdigest()}


def query(records,index,text,*,limit=8,types=None,include_superseded=False):
    matches=[]
    for exact,count,_,i,terms in rank(records,index,text,limit=limit,types=types,include_superseded=include_superseded):
        source=index['texts'][i];position=source.casefold().find(text.strip().casefold())
        start=max(0,position-300);excerpt=source[start:start+1600]
        matches.append({**_reference(records[i]),'exact_phrase':exact,'matched_terms':terms,'score':count,
                        'excerpt':excerpt,'excerpt_truncated':len(source)>len(excerpt)})
    return {'schema':'mantle.engram-query/2','ledger_head':records[-1]['sha256'] if records else ZERO,
            'query':text,'matches':matches,'authoritative':False,'model_calls':0}


def evidence(records,index,text,*,limit=6):
    selected=[];seen=set()
    for exact,count,_,i,terms in rank(records,index,text,limit=100,types=['effect','pulse']):
        record=records[i]
        if record['type']=='effect':
            key=_effect_key(record)
            terminal_index=index['effect_terminals'].get(key)
            if key in seen or terminal_index is None:continue
            terminal=records[terminal_index]
            if terminal['body'].get('stage') not in {'VERIFIED','FAILED','UNKNOWN'}:continue
            seen.add(key)
            selected.append({'kind':'effect','id':key,'status':terminal['body']['stage'],
                             'terminal_record':_reference(terminal),'match_record':_reference(record)})
        else:selected.append({'kind':'pulse','status':'COMMITTED','record':_reference(record)})
        if len(selected)>=limit:break
    return {'schema':'mantle.evidence-projection/1','ledger_head':records[-1]['sha256'] if records else ZERO,
            'items':selected,'authoritative':False}


def context(records,*,depth='FAST',query_text=None,max_bytes=131072):
    index=build(records)
    active=[r for r in records if r['type'] in {'memory','soft'} and r['id'] not in index['superseded']]
    turns=[r for r in records if r['type']=='turn']
    if depth=='FAST':chosen=active+turns[-6:]
    elif depth=='DEEP':chosen=records
    elif depth=='TARGETED':
        if not query_text:raise ValueError('TARGETED context requires a query')
        chosen=[records[row[3]] for row in rank(records,index,query_text,limit=8,types=['turn','memory','soft'])]+turns[-2:]
    else:raise ValueError('Unknown context depth')
    chosen=sorted({r['id']:r for r in chosen}.values(),key=lambda r:r['seq'])
    evidence_view=evidence(records,index,query_text or '') if depth=='TARGETED' else {'items':[]}
    # Bound derived context explicitly; the canonical records are never truncated.
    result=[];used=0
    for record in reversed(chosen):
        size=len(canonical(record).encode())
        if used+size<=max_bytes:result.append(record);used+=size
    return {'records':list(reversed(result)),'evidence':evidence_view['items'],
            'omitted_records':len(chosen)-len(result),'source_records':len(records)}

"""M3 candidate binding. Evidence hashes record submitted bytes, not test truth."""
import hashlib
import re
from .canonical import dumps, loads, sha256
from .bytecode import decode
from .checker import exact
from .errors import refuse

CANDIDATE_SCHEMA = 'mantle.reflex-candidate/0.2-experimental'
HEX = re.compile(r'^[a-f0-9]{64}$')
NAME = re.compile(r'^[a-z][a-z0-9_.-]{0,63}$')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    if type(value) is not str or not HEX.fullmatch(value):
        refuse('E_EVIDENCE', 'digest must be lowercase 64-character sha256')


def _baselines(versions):
    if type(versions) is not dict or len(versions) > 16:
        refuse('E_EVIDENCE', 'baseline_versions must be an object with <=16 entries')
    for name, digest in versions.items():
        if type(name) is not str or not NAME.fullmatch(name):
            refuse('E_EVIDENCE', 'invalid baseline identifier')
        _digest(digest)


def _refs(refs):
    if type(refs) is not list or len(refs)>32 or any(type(x) is not str or
            not x.startswith('synthetic:') or len(x)>128 for x in refs) or len(set(refs))!=len(refs):
        refuse('E_EVIDENCE','evidence references must be distinct bounded synthetic labels')


def _candidate_fields():
    return {'schema','book','program_id','program_sha256','binary_sha256','vm_abi','compiler_version','predecessor_sha256',
            'input_schema','output_schema','capabilities','limits','test_receipt_sha256',
            'evidence_refs','baseline_versions','proposed_by','scope','candidate_sha256'}


def make_candidate(binary, test_receipt, *, evidence_refs, baseline_versions, proposed_by,
                   predecessor_sha256=None):
    if type(binary) is not bytes or type(test_receipt) is not bytes or not 1 <= len(test_receipt) <= 65536:
        refuse('E_EVIDENCE','binary and bounded nonempty receipt bytes required')
    _baselines(baseline_versions);_refs(evidence_refs)
    if predecessor_sha256 is not None: _digest(predecessor_sha256)
    if type(proposed_by) is not str or not NAME.fullmatch(proposed_by):
        refuse('E_EVIDENCE','invalid candidate proposer')
    bc=decode(binary)
    ir=bc['ir']
    item={'schema':CANDIDATE_SCHEMA,'book':ir['book'],'program_id':ir['id'],
          'program_sha256':bc['program_sha256'],'binary_sha256':_sha(binary),
          'vm_abi':bc['abi'],'compiler_version':'reflex-python-compiler/0.1',
          'predecessor_sha256':predecessor_sha256,'input_schema':ir['inputs'],
          'output_schema':'mantle.reflex-result/0.1',
          'capabilities':ir['capabilities'],'limits':ir['limits'],
          'test_receipt_sha256':_sha(test_receipt),'evidence_refs':evidence_refs,
          'baseline_versions':baseline_versions,'proposed_by':proposed_by,
          'scope':'isolated-reflex-registry/0.1'}
    item['candidate_sha256']=sha256(item)
    return loads(dumps(item))


def validate_candidate(candidate, binary, test_receipt):
    exact(candidate,_candidate_fields(),'candidate')
    _digest(candidate['candidate_sha256'])
    _digest(candidate['binary_sha256'])
    _digest(candidate['program_sha256'])
    _digest(candidate['test_receipt_sha256'])
    if candidate['predecessor_sha256'] is not None: _digest(candidate['predecessor_sha256'])
    _refs(candidate['evidence_refs']);_baselines(candidate['baseline_versions'])
    if type(candidate['proposed_by']) is not str or not NAME.fullmatch(candidate['proposed_by']):
        refuse('E_EVIDENCE','invalid proposer')
    if candidate['schema']!=CANDIDATE_SCHEMA or candidate['scope']!='isolated-reflex-registry/0.1':
        refuse('E_EDITION','unsupported candidate/scope')
    if sha256({k:v for k,v in candidate.items() if k!='candidate_sha256'})!=candidate['candidate_sha256']:
        refuse('E_INTEGRITY','candidate manifest digest mismatch')
    expected=make_candidate(binary,test_receipt,evidence_refs=candidate['evidence_refs'],
                            baseline_versions=candidate['baseline_versions'],proposed_by=candidate['proposed_by'],
                            predecessor_sha256=candidate['predecessor_sha256'])
    if dumps(expected)!=dumps(candidate):
        refuse('E_EVIDENCE','candidate does not bind supplied binary and evidence')
    return candidate

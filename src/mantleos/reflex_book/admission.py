"""M3 host-controlled *experimental* admission, not production BODY authority.

A trusted host supplies its own secret (never a program, manifest, or carrier).
HMAC authenticates a specific local key holder only; it is not an identity PKI.
The signer function belongs to the operator side of the demonstration.
"""
import hashlib
import hmac
import re
from .canonical import dumps,sha256
from .checker import exact
from .errors import refuse
from .types import timestamp
from .evidence import NAME

APPROVAL_SCHEMA='mantle.reflex-operator-receipt/0.1-experimental'
HEX=re.compile(r'^[0-9a-f]{64}$')
RECEIPT_FIELDS=frozenset({'schema','issuer','reviewed_by','candidate_sha256',
    'program_sha256','capabilities','baseline_versions','scope','decision',
    'not_before_utc','expires_utc','nonce','mac_sha256'})


def _body(candidate, *, issuer, reviewed_by, not_before_utc, expires_utc, nonce):
    if any(type(v) is not str or not NAME.fullmatch(v) for v in (issuer,reviewed_by,nonce)):
        refuse('E_APPROVAL','invalid issuer, reviewer or nonce')
    if reviewed_by==candidate['proposed_by']:
        refuse('E_AUTHORITY','proposer cannot approve own candidate')
    start=timestamp(not_before_utc)
    finish=timestamp(expires_utc)
    if finish<=start:
        refuse('E_APPROVAL','approval must have a positive validity interval')
    return {'schema':APPROVAL_SCHEMA,'issuer':issuer,'reviewed_by':reviewed_by,
            'candidate_sha256':candidate['candidate_sha256'],
            'program_sha256':candidate['program_sha256'],
            'capabilities':candidate['capabilities'],
            'baseline_versions':candidate['baseline_versions'],
            'scope':candidate['scope'],'decision':'APPROVE',
            'not_before_utc':not_before_utc,'expires_utc':expires_utc,'nonce':nonce}


def _key(key):
    if type(key) is not bytes or len(key)<32:
        refuse('E_AUTHORITY','operator credential must be at least 32 secret bytes')


def operator_issue_receipt(candidate, *, issuer, reviewed_by, secret, not_before_utc, expires_utc, nonce):
    """For a separately controlled host/operator only. Never call from reflex code."""
    _key(secret)
    body=_body(candidate,issuer=issuer,reviewed_by=reviewed_by,
               not_before_utc=not_before_utc,expires_utc=expires_utc,nonce=nonce)
    return {**body,'mac_sha256':hmac.new(secret,dumps(body),hashlib.sha256).hexdigest()}


def verify_approval(candidate,receipt,trusted_issuers,now_utc):
    if type(receipt) is not dict:
        refuse('E_APPROVAL','approval receipt must be an object')
    exact(receipt, RECEIPT_FIELDS,'operator receipt')
    if type(receipt['mac_sha256']) is not str or not HEX.fullmatch(receipt['mac_sha256']):
        refuse('E_APPROVAL','approval MAC must be lowercase sha256 hex')
    expected_fields=_body(candidate,issuer=receipt['issuer'],reviewed_by=receipt['reviewed_by'],
                          not_before_utc=receipt['not_before_utc'],expires_utc=receipt['expires_utc'],
                          nonce=receipt['nonce'])
    if any(receipt[k]!=value for k,value in expected_fields.items()):
        refuse('E_APPROVAL','approval does not match candidate or permitted scope')
    if type(trusted_issuers) is not dict or receipt['issuer'] not in trusted_issuers:
        refuse('E_AUTHORITY','issuer is not trusted by this host')
    secret=trusted_issuers[receipt['issuer']]
    _key(secret)
    expect=hmac.new(secret,dumps(expected_fields),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect,receipt['mac_sha256']):
        refuse('E_AUTHORITY','operator receipt MAC mismatch')
    now=timestamp(now_utc)
    if not timestamp(receipt['not_before_utc'])<=now<timestamp(receipt['expires_utc']):
        refuse('E_EXPIRED','operator receipt not currently valid')
    return {'result':'APPROVAL_VERIFIED','candidate_sha256':candidate['candidate_sha256'],
            'issuer':receipt['issuer'],'scope':candidate['scope'],
            'production_body_authorized':False}


def install(_candidate):
    """Legacy call remains permanently blocked: no caller may auto-install."""
    refuse('E_AUTHORITY','no production Body install path; use isolated registry with external receipt')

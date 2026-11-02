"""Private pilot's deterministic failure and quarantine boundary.

Only bounded reason codes and content digests cross into diagnostic records.
No raw exception, prompt, credential or private path is logged.
"""
import re
from .skin import sha

def evidence(reason, private_detail=b''):
    if not isinstance(reason,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',reason):
        raise ValueError('Immune reason code required')
    if not isinstance(private_detail,bytes): raise ValueError('Evidence bytes required')
    return {'reason':reason,'detail_sha256':sha(private_detail)}

def quarantine(skin, record_sha256, *, reason, expected_head):
    if not isinstance(record_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',record_sha256):
        raise ValueError('Canonical record digest required')
    return skin.append('private-quarantine',{'record_sha256':record_sha256,
        **evidence(reason)},expected_head=expected_head)

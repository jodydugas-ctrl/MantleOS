"""Explicitly synthetic offline host demonstration (NO MantleOS installation)."""
import json
import hashlib
from pathlib import Path
import tempfile
from mantleos.reflex_book.parser import parse_program
from mantleos.reflex_book.compiler import compile_ir
from mantleos.reflex_book.bytecode import encode
from mantleos.reflex_book.evidence import make_candidate
from mantleos.reflex_book.admission import operator_issue_receipt
from mantleos.reflex_book.registry import ExperimentalRegistry

from mantleos.reflex_book.fixtures import root
ROOT=root()
FIX=ROOT/'examples'/'reflex_book'
NOW='2026-10-24T12:00:00Z'
END='2026-11-24T12:00:00Z'
# An intentionally public, nonproduction demo key; do not use as an authority credential.
DEMO_KEY=b'NONPRODUCTION-EXAMPLE-ONLY-NEVER-USE-THIS-KEY'


def main():
    binary=encode(compile_ir(parse_program((FIX/'location_rule.json').read_bytes())))
    evidence=b'{"synthetic":true,"claimed_check":"demonstration-only"}'
    baselines={'synthetic.routine':hashlib.sha256(b'baseline-v1').hexdigest()}
    candidate=make_candidate(binary,evidence,evidence_refs=['synthetic:demo-fixture'],
                             baseline_versions=baselines,proposed_by='synthetic_model')
    # Separate, explicit host-operator action. Evidence bytes do not grant approval.
    receipt=operator_issue_receipt(candidate,issuer='test_host',reviewed_by='test_operator',
                                   secret=DEMO_KEY,not_before_utc=NOW,expires_utc=END,
                                   nonce='synthetic_review_01')
    with tempfile.TemporaryDirectory(prefix='reflex-m3-demo-') as directory:
        registry=ExperimentalRegistry(Path(directory)/'isolated.sqlite')
        installed=registry.install(candidate,binary,evidence,receipt,
                                   trusted_issuers={'test_host':DEMO_KEY},now_utc=NOW,
                                   current_baselines=baselines)
        activated=registry.activate(candidate['candidate_sha256'],
                                   trusted_issuers={'test_host':DEMO_KEY},now_utc=NOW,
                                   current_baselines=baselines)
        outcome=registry.run_active((FIX/'location_anomaly.json').read_bytes(),
                                   trusted_issuers={'test_host':DEMO_KEY},now_utc=NOW,
                                   current_baselines=baselines)
        disabled=registry.disable(now_utc=NOW)
        audit=registry.audit()
    print(json.dumps({'scope':'synthetic-offline-only',
                      'steps':[installed['state'],activated['state'],
                               outcome['state'],disabled['state']],
                      'result':outcome['trace']['result'],'audit':audit,
                      'production_body_authorized':False},sort_keys=True,indent=2))


if __name__=='__main__':main()

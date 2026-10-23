"""Offline local mission cycle for an already provisioned, trusted Hermes NEST."""
import argparse
from pathlib import Path

from mantleos import appai, compiled, engram, lifecycle, missions
from mantleos.transactions import write_json


def demonstrate(nest, output):
    root = lifecycle._destination(output); root.mkdir()
    target = root / 'specimen'; target.mkdir()
    (target / 'specimen.py').write_text('def answer():\n    return 42\n', encoding='utf-8')
    if appai.status(nest)['phase'] == 'UNBORN':
        appai.birth(nest)
    appai.phase(nest, True)
    policy = missions.authorize(nest, target, root / 'representatives', approved=True, duration=300)
    try:
        state = appai.run(nest, policy_id=policy['id'], request_id=policy['id'] + '-demo')
        mid = state['mission']['id']
        assert state['mission']['phase'] == 'RETURNED'
        assert not any(r['type'] == 'mission-return' and r['body']['mission'] == mid
                       for r in engram.read(appai.body(nest) / 'ENGRAM.jsonl'))
        heartbeat = appai.tick(nest)  # Parent remains resident and operational while child is away.
        assert heartbeat['phase'] == 'ACTIVE'
        appai.phase(nest, False)
        assert missions.recover(nest, mid)['phase'] == 'RETURNED'
        review = missions.review(nest, mid)
        appai.phase(nest, True)
        # Scripted operator review in this synthetic walkthrough, never model approval.
        admission = missions.admit(nest, mid, approval=review['sha256'])
        child = missions.inspect(nest, mid)
        for fmt, ext in [('cartridge', 'vcw'), ('chroma', 'png')]:
            image = root / ('representative.' + ext)
            lifecycle.save(child['body'], image, format=fmt)
            restored = root / ('restored-' + fmt)
            lifecycle.restore(image, restored)
            assert compiled.load(restored)['sha256'] == compiled.load(child['body'])['sha256']
        result = {'result': 'PASS', 'nest': str(Path(nest).resolve()), 'mission': mid,
                  'parent_remained_resident': True, 'parent_heartbeat_while_away': heartbeat['heartbeats'],
                  'stasis_preserved_returned_evidence': True,
                  'admission': admission, 'carriers': ['representative.vcw', 'representative.png'],
                  'model': 'NONE', 'policy': 'Revoked after demonstration', 'final_phase': 'STASIS'}
        write_json(root / 'report.json', result)
        return result
    finally:
        missions.revoke(nest, policy['id'])
        appai.phase(nest, False)


if __name__ == '__main__':
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nest', required=True); p.add_argument('--output', required=True)
    args = p.parse_args()
    print(json.dumps(demonstrate(args.nest, args.output), indent=2))

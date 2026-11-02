"""Executable journal ingredient specimen; scripted language is explicitly labeled."""
import argparse
from pathlib import Path
from mantleos import journal, specimens

def run(output):
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=False)
    specimens.fresh(root/'body',name='Synthetic Journal Specimen')
    journal.from_body(root/'body',root/'specimen.engram')
    with journal.Journal(root/'specimen.engram') as session:
        session.open('Remember the synthetic observation.',request_id='demo',model_id='SCRIPTED_FIXTURE')
        result=session.submit('demo',{'kind':'reply','reply':'The synthetic observation is recorded.','observation_sha256':None},broker=lambda a,n:a=='release')
        assert session.submit('demo',None,broker=lambda a,n:a=='release')['replayed']
        session.export(root/'saved.engram')
    return {'result':'PASS','live_model':False,'committed_reply':result['reply']}

if __name__=='__main__':
    import json
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    print(json.dumps(run(parser.parse_args().output),indent=2))

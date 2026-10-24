"""Create two clean encodings of one synthetic fresh Engram, never imported history."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from mantleos.kpp.engram_carriers import fresh_body, encode

def generate(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='raven-example-') as work:
        body=Path(work)/'body'
        fresh_body(body,identity='synthetic-raven-example')
        for name,encoding in [('raven-fresh.vcw','vcw'),('raven-fresh.vcw.png','chroma')]:
            encode(body,output/name,encoding)
    record={'schema':'kpp.reviewed-engram-examples/1','review':'PENDING',
            'scope':'Synthetic fresh birth only; public content review required before inventory inclusion',
            'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}}
    (output/'MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(generate(parser.parse_args().output),indent=2))

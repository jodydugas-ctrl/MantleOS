"""Supervised host handoff; uses the existing foreground Body, no inference API."""
import argparse
import base64
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
import urllib.request
from mantleos import studio, json_contract as c


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    parser=argparse.ArgumentParser();parser.add_argument('--nest',type=Path,required=True)
    parser.add_argument('--url',default='http://127.0.0.1:18880')
    sub=parser.add_subparsers(dest='op',required=True);sub.add_parser('next')
    p=sub.add_parser('submit');p.add_argument('--request-id',required=True);p.add_argument('--proposal',type=Path,required=True)
    args=parser.parse_args();url=urlparse(args.url)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or url.path not in ('','/') or url.username or url.password:raise ValueError('Use a local loopback origin')
    if args.op=='next':
        with studio.database(args.nest) as db:row=db.execute("SELECT id,frame FROM mind WHERE phase='AWAITING_MIND' ORDER BY rowid LIMIT 1").fetchone()
        result={'status':'IDLE'} if row is None else {'request_id':row[0],**c.loads(row[1])}
    else:
        auth=c.loads((args.nest/'operator.json').read_text('utf8'))
        headers={'Content-Type':'application/json','Authorization':'Basic '+base64.b64encode((auth['user']+':'+auth['password']).encode()).decode()}
        data=c.canonical({'request_id':args.request_id,'proposal':c.loads(args.proposal.read_text('utf8'))}).encode()
        request=urllib.request.Request(args.url.rstrip('/')+'/studio/mind-submit',data=data,headers=headers)
        with urllib.request.urlopen(request,timeout=30) as response:result=c.loads(response.read().decode())
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())

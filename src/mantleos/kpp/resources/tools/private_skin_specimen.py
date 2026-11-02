"""Synthetic private Skin specimen/benchmark. Does not establish OS isolation."""
import argparse
import json
import os
from pathlib import Path
import statistics
import time
from mantleos.skin import Skin, source_pin
from mantleos.private_appai import PrivateAppAI, signing_key, public_key, verify_release
from mantleos.private_mind import HostMind

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    report={'implementation_sha256':source_pin(),'evidence':'SYNTHETIC_NO_LIVE_LLM','os_isolation':'UNTESTED','cases':[]}
    for count in (0,100,1000):
        for cold in (0,20*1024*1024):
            key=os.urandom(32)
            path=root/f'{count}-{cold}.skin'
            start=time.perf_counter()
            skin=Skin.create(path,key,{'compiled':'Synthetic Finch founding PRIMER.'},persona='Finch')
            if cold: skin.put_object('cold-attachment',b'x'*cold)
            for i in range(count):skin.append('memory',{'text':'cedar synthetic '+str(i)},expected_head=skin.head)
            skin.close()
            start=time.perf_counter()
            skin=Skin(path,key)
            startup=time.perf_counter()-start
            frames=[]
            def generate(frame):
                frames.append(len(json.dumps(frame).encode()))
                return {'reply':'Finch confirms this synthetic encounter.'}
            mind=HostMind(generate,lambda:True,model='synthetic-fixture')
            signer=signing_key()
            body=PrivateAppAI(skin,signer,mind,policy={'id':'synthetic','expires':time.time()+600,
                'models':[mind.model],'conversation':True})
            samples=[]
            for i in range(20):
                body.admit_user('turn-'+str(i),'cedar')
                start=time.perf_counter()
                release=body.courier({'op':'encounter','args':{'request_id':'turn-'+str(i),'user':'cedar'}})
                samples.append(time.perf_counter()-start)
                assert verify_release(release,public_key(signer),identity=body.constitution['identity'],request_id='turn-'+str(i),user='cedar')
                assert body.result('turn-'+str(i),'cedar')==release
            start=time.perf_counter()
            exported=root/f'{count}-{cold}-saved.skin';skin.export(exported)
            export=time.perf_counter()-start
            checkpoint=skin.checkpoint();skin.close()
            with Skin(exported,key) as restored:
                restored.require_checkpoint(checkpoint)
                assert restored.object('constitution')
                if cold: assert len(restored.object('cold-attachment'))==cold
            report['cases'].append({'history':count,'cold_bytes':cold,'samples':20,
                'startup_ms':startup*1000,'median_ms':statistics.median(samples)*1000,
                'p95_ms':sorted(samples)[18]*1000,'export_ms':export*1000,
                'frame_bytes_max':max(frames),'model_calls':0,'fixture_generations':len(frames),
                'export_bytes':exported.stat().st_size})
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

import copy
from pathlib import Path
import secrets
import tempfile
import unittest
from mantleos.studio_mind_config import load_owner_file
from mantleos.studio_mind_budget import MindBudget
from mantleos.studio_mind_provider import StudioProvider


class StudioProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.owner=self.root/'owner.txt'
        self.owner.write_text('example/primary\nopenrouter/free\nMind:\n'
            +'sk-or-v1-'+secrets.token_hex(32)+'\nBudget: $1\nLimbs:\n'
            +'sk-or-v1-'+secrets.token_hex(32)+'\nBudget: $.50\n',encoding='utf8')
        self.config=load_owner_file(self.owner)
        self.budget=MindBudget(self.root/'cost.sqlite',create=True)
        self.calls=[];self.source_valid=True
        self.response={'model':'example/primary','provider':'Pinned Provider','id':'gen-synthetic',
            'choices':[{'finish_reason':'stop','message':{'content':
                '{"kind":"reply","reply":"hello","observation_sha256":null}'}}],
            'usage':{'prompt_tokens':100,'completion_tokens':12,'cost':0.0001}}
        self.wrapper={'frame':{'primer':'Complete synthetic founding PRIMER.\nNo compression.',
                              'response_contract':{'kind':['reply','action']}}}
        self.provider=self.make()

    def check_source(self):
        if not self.source_valid:raise PermissionError('Source changed')

    def transport(self,key,payload):
        self.calls.append((key,payload))
        return copy.deepcopy(self.response)

    def make(self):
        return StudioProvider(config=self.config,accounting=self.budget,
            source_sha256='a'*64,policy_sha256='b'*64,
            allowed={'example/primary':['Pinned Provider'],'example/free':['Free Provider']},
            provider_slugs=['pinned-provider','free-provider'],
            free_models=['example/free'],source_check=self.check_source,transport=self.transport)

    def generate(self):
        return self.provider.generate(wrapper=self.wrapper,request_id='frame-one')

    def test_full_frame_once_durable_recovery_and_secret_free_proposal(self):
        result=self.generate()
        self.assertEqual(len(self.calls),1)
        key,payload=self.calls[0]
        self.assertEqual(key,self.config.mind_key)
        self.assertIn(self.wrapper['frame']['primer'].replace('\n','\\n'),payload['messages'][1]['content'])
        self.assertNotIn(key,str(payload));self.assertNotIn(str(self.owner),str(payload))
        self.assertEqual(payload['models'],['example/primary','openrouter/free'])
        self.assertEqual(payload['provider']['max_price'],{'prompt':0.5,'completion':2,'request':0})
        self.assertEqual(result['value']['body_validation'],'REQUIRED')
        self.provider=self.make()
        self.assertEqual(self.generate(),result)
        self.assertEqual(len(self.calls),1)

    def test_timeout_retains_claim_and_never_retries(self):
        def fail(key,payload):
            self.calls.append(1);raise TimeoutError('private diagnostic '+key)
        self.provider.transport=fail
        with self.assertRaises(RuntimeError) as raised:self.generate()
        self.assertNotIn(self.config.mind_key,str(raised.exception))
        self.assertEqual(self.generate()['status'],'NEEDS_REVIEW')
        self.assertEqual(len(self.calls),1)

    def test_free_physical_model_requires_pinned_provider_and_zero_cost(self):
        self.response.update(model='example/free',provider='Free Provider')
        self.response['usage']['cost']=0
        self.assertEqual(self.generate()['value']['model'],'example/free')
        self.response['usage']['cost']=0.01
        with self.assertRaises(ValueError):
            self.provider.generate(wrapper=self.wrapper,request_id='second-frame')
        self.response['usage']['cost']=0
        self.response['provider']='Unknown Provider'
        with self.assertRaises(ValueError):
            self.provider.generate(wrapper=self.wrapper,request_id='third-frame')

    def test_stale_owner_or_source_cannot_call_provider(self):
        self.source_valid=False
        with self.assertRaises(PermissionError):self.generate()
        self.source_valid=True
        self.owner.write_text(self.owner.read_text()+'\nchanged')
        with self.assertRaises(PermissionError):self.generate()
        self.assertEqual(self.calls,[])

    def test_malformed_result_is_retained_rejection_without_retry(self):
        self.response['choices'][0]['finish_reason']='length'
        with self.assertRaises(ValueError):self.generate()
        saved=self.generate()
        self.assertEqual(saved['value']['error'],'PROVIDER_RESULT_REJECTED')
        self.assertEqual(len(self.calls),1)

    def test_privileged_looking_usage_metadata_not_admitted(self):
        self.response['usage']['private_transcript']='should not persist'
        self.assertNotIn('should not persist',str(self.generate()))

    def test_nonfinite_or_unbounded_cost_cannot_escape_accounting_limits(self):
        for index,cost in enumerate(('NaN','1e99999999','-1')):
            self.response['usage']['cost']=cost
            with self.assertRaises(ValueError):
                self.provider.generate(wrapper=self.wrapper,request_id='invalid-cost-'+str(index))


if __name__=='__main__':unittest.main()

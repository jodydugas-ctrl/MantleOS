"""Actual Journal encounters with a synthetic provider; not live LLM evidence."""
import json
from contextlib import chdir
from pathlib import Path
import secrets
import shutil
import tempfile
import unittest
from mantleos.studio_mind_budget import MindBudget
from mantleos import studio, specimens, journal, studio_auto_mind as auto
from mantleos.limbs import LimbSet


def bindings(value='a'):
    return {name:value*64 for name in ('frame_sha256','source_sha256',
            'config_sha256','route_sha256','policy_sha256')}


class AutoMindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        base=Path(cls.temp.name)
        specimens.fresh(base/'body',name='Complete synthetic automatic Studio persona')
        cls.seed=base/'seed.engram'
        journal.from_body(base/'body',cls.seed)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.temp_case=tempfile.TemporaryDirectory();self.addCleanup(self.temp_case.cleanup)
        self.nest=Path(self.temp_case.name)/'nest'
        studio.initialize_heart(self.nest,b'Synthetic founding bytes\r\n')
        shutil.copyfile(self.seed,self.nest/'prime.engram')
        LimbSet.create(self.nest/'limb-runtime',[],worker_limit=0,approved=True)
        self.owner=self.nest/'owner-key-file.txt'
        self.owner.write_text('example/primary\nMind:\n'+'sk-or-v1-'+secrets.token_hex(32)
            +'\nBudget: $1\nLimbs:\n'+'sk-or-v1-'+secrets.token_hex(32)+'\nBudget: $.50\n')
        self.catalog={'allowed':{'example/primary':['Pinned Provider']},
                      'provider_slugs':['pinned-provider'],'free_models':[],
                      'provenance':{'kind':'synthetic test fixture'}}
        self.addCleanup(self.close)
        self.calls=[]

    def close(self):
        session=studio._sessions.pop(str((self.nest/'prime.engram').resolve()),None)
        if session:session.close()

    def configure(self):
        return auto.configure(self.nest,owner_file=self.owner,catalog=self.catalog,reviewed=True)

    def transport(self,key,payload):
        self.calls.append(payload)
        return {'model':'example/primary','provider':'Pinned Provider','id':'synthetic-generation',
            'choices':[{'finish_reason':'stop','message':{'content':json.dumps(self.proposal)}}],
            'usage':{'prompt_tokens':100,'completion_tokens':10,'cost':0.0001}}

    def start(self):
        self.configure();studio.phase(self.nest,True)
        return studio.conversation(self.nest,'Remember amber.','user-one','OPENROUTER_OWNER_CONFIGURED')

    def test_explicit_configuration_no_calls_and_no_private_status_fields(self):
        with self.assertRaises(PermissionError):
            auto.configure(self.nest,owner_file=self.owner,catalog=self.catalog)
        status=self.configure()
        self.assertEqual(self.calls,[])
        self.assertNotIn(str(self.owner),str(status))
        self.assertNotIn('sk-or-',str(status))
        self.assertEqual(status['budget']['accounts']['limbs']['cap_micro_usd'],500000)
        studio.phase(self.nest,True)
        with self.assertRaises(PermissionError):self.configure()

    def test_new_nests_share_owner_budget_and_do_not_replenish_it(self):
        self.configure()
        route=json.loads((self.nest/'mind-route.json').read_text('utf8'))
        accounting=MindBudget(route['accounting_file'])
        accounting.reserve(purpose='mind',request_id='earlier-nest',binding=bindings(),
                           maximum_micro_usd=600000,cap_micro_usd=1000000)
        other=self.nest.parent/'another-nest'
        studio.initialize_heart(other,b'Synthetic second Body')
        status=auto.configure(other,owner_file=self.owner,catalog=self.catalog,reviewed=True)
        another=json.loads((other/'mind-route.json').read_text('utf8'))
        self.assertEqual(route['accounting_file'],another['accounting_file'])
        self.assertEqual(route['accounting_identity'],another['accounting_identity'])
        self.assertEqual(status['budget']['accounts']['mind']['remaining_micro_usd'],400000)
        with self.assertRaises(PermissionError):
            MindBudget(another['accounting_file']).reserve(purpose='mind',request_id='new-nest',
                binding=bindings('b'),maximum_micro_usd=600000,cap_micro_usd=1000000)
        self.assertEqual(self.calls,[])

    def test_missing_or_substituted_account_fails_closed_even_on_reconfigure(self):
        self.configure()
        route=json.loads((self.nest/'mind-route.json').read_text('utf8'))
        account=Path(route['accounting_file'])
        backup=account.with_suffix('.preserved')
        account.rename(backup)
        with self.assertRaises(PermissionError):auto.public_status(self.nest)
        with self.assertRaises(FileNotFoundError):self.configure()
        self.assertFalse(account.exists())
        replacement=MindBudget(account,create=True)
        self.assertNotEqual(replacement.identity(),route['accounting_identity'])
        with self.assertRaises(PermissionError):auto.public_status(self.nest)
        with self.assertRaises(PermissionError):self.configure()
        with self.assertRaises(PermissionError):
            auto.configure(self.nest,owner_file=self.owner,catalog=self.catalog,
                           accounting_file=self.nest/'another.sqlite',reviewed=True)
        self.assertEqual(self.calls,[])

    def test_legacy_exposure_must_be_retained_and_can_be_shared_explicitly(self):
        path=self.nest/'mind-accounting.sqlite'
        legacy=MindBudget(path,create=True)
        legacy.reserve(purpose='mind',request_id='historical',binding=bindings(),
                       maximum_micro_usd=900000,cap_micro_usd=1000000)
        with self.assertRaisesRegex(PermissionError,'Retain existing'):
            self.configure()
        status=auto.configure(self.nest,owner_file=self.owner,catalog=self.catalog,
                              accounting_file=path,reviewed=True)
        self.assertEqual(status['budget']['accounts']['mind']['remaining_micro_usd'],100000)
        self.assertEqual(self.configure()['budget'],status['budget'])
        other=self.nest.parent/'new-nest'
        studio.initialize_heart(other,b'Synthetic third Body')
        shared=auto.configure(other,owner_file=self.owner,catalog=self.catalog,
                             accounting_file=path,reviewed=True)
        self.assertEqual(shared['budget'],status['budget'])

    def test_relative_account_path_spelling_retains_identity_and_exposure(self):
        before=self.configure()
        route=json.loads((self.nest/'mind-route.json').read_text('utf8'))
        account=Path(route['accounting_file'])
        nested=account.parent/'operator-path';nested.mkdir()
        # Windows runners keep their checkout and temporary files on different
        # drives. Relative paths are meaningful within the account's drive.
        with chdir(account.parent):
            for spelling in (Path(account.name),Path('operator-path')/'..'/account.name):
                status=auto.configure(self.nest,owner_file=self.owner,catalog=self.catalog,
                                      accounting_file=spelling,reviewed=True)
                changed=json.loads((self.nest/'mind-route.json').read_text('utf8'))
                self.assertEqual(changed['accounting_identity'],route['accounting_identity'])
                self.assertEqual(status['budget'],before['budget'])
        self.assertEqual(self.configure()['budget'],before['budget'])

    def test_actual_journal_full_primer_commit_exact_replay_without_regeneration(self):
        wrapper=self.start()
        self.proposal={'kind':'reply','reply':'Amber retained.','observation_sha256':None}
        result=auto.generate(self.nest,'user-one',transport=self.transport)
        with self.assertRaises(PermissionError):
            studio.submit(self.nest,'user-one',{**self.proposal,'reply':'Forged courier reply'})
        frame=json.loads(self.calls[0]['messages'][1]['content'])
        self.assertEqual(frame['frame']['payload']['primer'],wrapper['frame']['payload']['primer'])
        self.assertNotIn('claim',result)
        self.assertEqual(studio.committed_result(self.nest,'user-one')['status'],'AWAITING_MIND')
        recovered=auto.generate(self.nest,'user-one',transport=self.transport)
        self.assertEqual(recovered,result)
        committed=studio.submit(self.nest,'user-one',result['value']['proposal'])
        self.assertEqual(committed['reply'],'Amber retained.')
        self.assertEqual(auto.generate(self.nest,'user-one',transport=self.transport)['status'],'ALREADY_COMMITTED')
        self.assertEqual(studio.committed_result(self.nest,'user-one')['reply'],committed['reply'])
        self.assertEqual(len(self.calls),1)

    def test_missing_owner_configuration_redacts_paths_at_body_boundary(self):
        self.start()
        self.owner.unlink()
        with self.assertRaises(PermissionError) as error:
            studio.submit(self.nest,'user-one',{'kind':'reply','reply':'Unavailable.','observation_sha256':None})
        self.assertNotIn(str(self.owner),str(error.exception))
        self.assertNotIn('sk-or-',str(error.exception))

    def test_action_uses_second_distinct_frame_and_requires_checked_observation(self):
        self.start()
        self.proposal={'kind':'action','capability':'body.status','arguments':{}}
        action=auto.generate(self.nest,'user-one',transport=self.transport)
        checked=studio.submit(self.nest,'user-one',action['value']['proposal'])
        digest=checked['frame']['payload']['observation_sha256']
        self.proposal={'kind':'reply','reply':'Verified observation.','observation_sha256':digest}
        response=auto.generate(self.nest,'user-one',transport=self.transport)
        self.assertNotEqual(action['attempt_id'],response['attempt_id'])
        observed=json.loads(self.calls[1]['messages'][1]['content'])
        self.assertEqual(observed['frame']['payload']['observation_sha256'],digest)
        with self.assertRaises(PermissionError):
            studio.submit(self.nest,'user-one',{**self.proposal,'observation_sha256':'0'*64})
        self.assertEqual(studio.submit(self.nest,'user-one',response['value']['proposal'])['status'],'COMMITTED')
        self.assertEqual(len(self.calls),2)

    def test_provider_cannot_forge_checked_observation(self):
        self.start()
        self.proposal={'kind':'action','capability':'body.status','arguments':{}}
        action=auto.generate(self.nest,'user-one',transport=self.transport)
        studio.submit(self.nest,'user-one',action['value']['proposal'])
        self.proposal={'kind':'reply','reply':'Forged observation.','observation_sha256':'0'*64}
        response=auto.generate(self.nest,'user-one',transport=self.transport)
        with self.assertRaises(ValueError):
            studio.submit(self.nest,'user-one',response['value']['proposal'])
        self.assertEqual(studio.committed_result(self.nest,'user-one')['status'],'AWAITING_MIND')

    def test_route_change_during_inference_prevents_result_admission(self):
        self.start()
        self.proposal={'kind':'reply','reply':'Must not release.','observation_sha256':None}
        def changed(key,payload):
            value=self.transport(key,payload)
            self.owner.write_text(self.owner.read_text()+'\nchanged')
            return value
        with self.assertRaises(PermissionError):auto.generate(self.nest,'user-one',transport=changed)
        with self.assertRaises(PermissionError):studio.submit(self.nest,'user-one',self.proposal)
        self.assertEqual(studio.committed_result(self.nest,'user-one')['status'],'AWAITING_MIND')
        with self.assertRaises(PermissionError):auto.generate(self.nest,'user-one',transport=self.transport)
        self.assertEqual(len(self.calls),1)

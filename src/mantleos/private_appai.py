"""Opt-in controller-side AppAI pilot. Courier never receives private MIND frames.

Public RPC has no caller-supplied policy, MIND, keys, paths or approval operations.
The controller owns instances; do not expose its Python process to model tools.
"""
from __future__ import annotations
import base64
import json
import time
from . import anchor_design, anchor_language, engram
from .skin import Skin, canon, sha, source_pin

def signing_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.generate()

def public_key(key):
    from cryptography.hazmat.primitives import serialization
    return base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw,
        serialization.PublicFormat.Raw)).decode()

def verify_release(release, public, *, identity, request_id, user):
    """Trusted display checks exact reply, input, request and independently pinned key."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        receipt = release['receipt']
        payload = receipt['payload']
        if (release['status'] != 'COMMITTED' or payload['identity'] != identity or payload['request_id'] != request_id or
            payload['input_sha256'] != sha(user.encode()) or
            payload['reply_sha256'] != sha(release['reply'].encode())):
            return False
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public,validate=True)).verify(
            base64.b64decode(receipt['signature'],validate=True),canon(payload).encode())
        return True
    except Exception: return False

def design():
    value = anchor_design.journal_design()
    value['id'] = 'Private-AppAI'
    value['purpose'] = 'Private constitution and memory; isolated proposal cognition; exact verified release.'
    for a in value['applications']:
        if a['id']=='N-HOST':
            a['attributes']['responsibility']='Coordinate private MIND frames, checked operations and sealed export; disclose only committed public replies.'
            # Canonical application hashes cover contextual attributes too.
            from .anchors import application
            value['applications'][value['applications'].index(a)] = application(a['id'],definition_id='Neutral',attributes=a['attributes'])
            break
    return anchor_design.validate(value)

class PrivateAppAI:
    def __init__(self, skin, signer, mind, *, policy, broker=None, checkpoint=None):
        self.skin,self.signer,self.mind = skin,signer,mind
        self.broker = broker
        self.constitution = json.loads(skin.object('constitution'))
        if self.constitution['source_pin'] != source_pin():
            raise ValueError('Private Body source changed; explicit reviewed upgrade required')
        self.policy = None
        self.set_policy(policy)
        if checkpoint is not None: skin.require_checkpoint(checkpoint)
        self.replies = {}
        self.quarantined = set()
        self.admitted_users = {}
        # Replay bindings derive exclusively from authenticated canonical records.
        for seq in sorted(skin.index.get(skin._token('kind:private-quarantine'),set())):
            r = skin.record(seq)
            if r['type']=='private-quarantine':
                self.quarantined.add(r['body']['record_sha256'])

    def _prior(self, request_id):
        if request_id not in self.replies:
            matches = self.skin.index.get(self.skin._token('request:'+request_id),set())
            if len(matches)>1: raise ValueError('Duplicate committed request binding')
            if matches:
                record = self.skin.record(next(iter(matches)))
                compatible = record['type']=='private-turn' or (record['type']=='turn' and record['source'] in {'journal-bridge','prototype-bridge'})
                if not compatible or record['body']['request_id']!=request_id:
                    raise ValueError('Invalid replay binding')
                self.replies[request_id] = record
        return self.replies.get(request_id)

    def admit_user(self, request_id, user):
        """Trusted UI/controller intake; this method is never courier-callable."""
        self._authority()
        old = self.admitted_users.get(request_id)
        if old is not None and old != user: raise PermissionError('User intake binding changed')
        self.admitted_users[request_id] = user

    def set_policy(self, policy):
        if (not isinstance(policy,dict) or set(policy) != {'id','expires','models','conversation'} or
            not isinstance(policy['id'],str) or not policy['id'] or
            type(policy['expires']) not in (int,float) or
            not isinstance(policy['models'],list) or not policy['models'] or
            not all(isinstance(m,str) and m for m in policy['models']) or
            type(policy['conversation']) is not bool):
            raise ValueError('Owner conversation policy required')
        self.policy = json.loads(canon(policy))

    def _authority(self):
        self.skin._fresh()
        if source_pin() != self.constitution['source_pin']:
            raise ValueError('Private Body source changed; reopen after reviewed upgrade')
        if (not self.policy['conversation'] or self.policy['expires'] <= time.time() or
            self.mind.model not in self.policy['models']):
            raise PermissionError('Private conversation policy denied or expired')

    def status(self):
        return {'schema':'mantle.private-appai-status/1','identity':self.constitution['identity'],
                'persona':self.constitution['persona'],'head':self.skin.head,
                'records':self.skin.count,'private_context':'BODY_ONLY'}

    def _release(self, record):
        body = record['body']
        payload = {'schema':'mantle.private-release/1','identity':self.constitution['identity'],
            'request_id':body['request_id'],'input_sha256':sha(body['user'].encode()),
            'reply_sha256':sha(body['reply'].encode()),'commit_head':record['sha256'],
            'policy_sha256':body.get('policy_sha256',sha(canon(self.policy).encode())),
            'model':body.get('model',body.get('model_id','historical-declared')),
            'observation_sha256':body.get('observation_sha256')}
        return {'status':'COMMITTED','reply':body['reply'],'receipt':{'payload':payload,
            'signature':base64.b64encode(self.signer.sign(canon(payload).encode())).decode()}}

    def result(self, request_id, user):
        self._authority()
        r = self._prior(request_id)
        if r is None: return {'status':'UNKNOWN'}
        if r['body']['user'] != user: raise PermissionError('Request binding mismatch')
        return self._release(r)

    def encounter(self, request_id, user):
        self._authority()
        if (not isinstance(request_id,str) or not 1<=len(request_id)<=96 or
            not isinstance(user,str) or not user.strip() or len(user.encode())>4096):
            raise ValueError('Invalid encounter')
        if self._prior(request_id) is not None: return self.result(request_id,user)
        head = self.skin.head
        policy_pin = sha(canon(self.policy).encode())
        recent_turns = self.skin.index.get(self.skin._token('kind:private-turn'),set()) | self.skin.index.get(self.skin._token('kind:turn'),set())
        recent = sorted(recent_turns,reverse=True)[:2]
        memory = [self.skin.record(seq) for seq in recent]
        for record in self.skin.recall(user):
            if not any(r['sha256']==record['sha256'] for r in memory): memory.append(record)
        memory = [r for r in memory if r['sha256'] not in self.quarantined]
        while memory and len(canon(memory).encode()) > 16384:
            memory.pop()
        frame = {'protocol':'mantle.private-encounter/1','request_id':request_id,'head':head,
            'primer':self.constitution['primer'],'design':anchor_design.projection(design()),
            'memory':memory,'memory_omitted':max(0,self.skin.count-len(memory)),
            'user':user,'contract':{'reply':{'reply':'text'},
                'action':{'action':'body.status or engram.query','text':'bounded query for engram.query'},'observation_reply':{'reply':'text','observation_sha256':'digest'}}}
        saved = self.skin.index.get(self.skin._token('observation:'+request_id),set())
        action_binding=self.skin.index.get(self.skin._token('action-user:'+request_id),set())
        if action_binding:
            if len(action_binding)!=1 or self.skin.record(next(iter(action_binding)))['body']['user']!=user:
                raise PermissionError('Checked action request/input binding mismatch')
        observation = None
        if saved:
            if len(saved)!=1:raise ValueError('Duplicate checked observation')
            bound=self.skin.record(next(iter(saved)))['body']
            if bound['user']!=user:raise PermissionError('Observation belongs to another user input')
            observation=bound['checked']
            frame['observation']=observation
            frame['observation_sha256']=sha(canon(observation).encode())
        if len(canon(frame).encode()) > 131072: raise ValueError('Private frame budget exceeded')
        proposal = self.mind(frame)
        if isinstance(proposal,dict) and 'action' in proposal:
            if observation is not None or action_binding or self.skin.index.get(self.skin._token('action:'+request_id)):
                raise PermissionError('One checked action per encounter; incomplete attempts require review')
            capability=proposal['action']
            if capability=='body.status' and set(proposal)=={'action'}:
                arguments={}
                provider=lambda a:self.status()
            elif (capability=='engram.query' and set(proposal)=={'action','text'} and
                  isinstance(proposal['text'],str) and 2<=len(proposal['text'])<=160):
                arguments={'text':proposal['text']}
                def provider(a):
                    matches=[r for r in self.skin.recall(a['text']) if r['sha256'] not in self.quarantined]
                    while matches and len(canon(matches).encode())>16384:matches.pop()
                    return {'matches':matches,'head':self.skin.head}
            else:raise PermissionError('Unsupported bounded private action')
            from .effects import Capability,CapabilityRegistry,CheckedActionExecutor
            bound=self.skin.append('private-action-binding',{'request_id':request_id,'user':user},expected_head=head)
            head=bound['sha256']
            registry=CapabilityRegistry()
            registry.register(Capability(capability,'READ','read','mantle.private-skin/1',provider,lambda value:isinstance(value,dict)))
            skin=self.skin
            class EffectStore:
                def append_record(self,kind,source,payload,*,expected_head):
                    return skin.append(kind,payload,source=source,expected_head=expected_head)
            observation=CheckedActionExecutor(registry,self.broker or (lambda a,n:False),EffectStore()).execute(
                capability,arguments,request_id=request_id,expected_head=head)
            if observation['stage']!='VERIFIED':raise PermissionError('Private action was not verified')
            saved=self.skin.append('private-observation',{'request_id':request_id,'user':user,'checked':observation},expected_head=self.skin.head)
            head=saved['sha256']
            frame['head']=head
            frame['observation'] = observation
            frame['observation_sha256'] = sha(canon(observation).encode())
            proposal = self.mind(frame)
            if not isinstance(proposal,dict) or proposal.get('observation_sha256') != frame['observation_sha256']:
                raise PermissionError('Reply must bind checked observation')
        if observation is not None and (not isinstance(proposal,dict) or proposal.get('observation_sha256')!=sha(canon(observation).encode())):
            raise PermissionError('Reply must bind the retained checked observation')
        expected = {'reply','observation_sha256'} if observation is not None else {'reply'}
        if (not isinstance(proposal,dict) or set(proposal)!=expected or
            not isinstance(proposal['reply'],str) or not proposal['reply'].strip() or
            len(proposal['reply'].encode())>16384):
            raise ValueError('Invalid private MIND proposal')
        def private_strings(value):
            if isinstance(value,str) and len(value)>=16:
                yield value
            elif isinstance(value,dict):
                for v in value.values(): yield from private_strings(v)
            elif isinstance(value,list):
                for v in value: yield from private_strings(v)
        if any(text in proposal['reply'] for text in private_strings(self.constitution['primer'])):
            raise PermissionError('Raw founding material cannot be released')
        # Apply shared Anchor communication validation. Envelopes are host-created.
        anchor_language.validate_message(anchor_language.make_message('private-mind','body','encounter-'+sha(request_id.encode()),proposal))
        self._authority()
        if sha(canon(self.policy).encode()) != policy_pin or source_pin()!=self.constitution['source_pin']:
            raise ValueError('Preparation invalidated')
        record = self.skin.append('private-turn',{'request_id':request_id,'user':user,
            'reply':proposal['reply'],'model':self.mind.model,'policy_sha256':policy_pin,
            'observation_sha256':sha(canon(observation).encode()) if observation else None},expected_head=head)
        self.replies[request_id] = record
        return self._release(record)

    def courier(self, packet):
        """Narrow data-only facade. Errors contain no private exception messages."""
        try:
            if not isinstance(packet,dict) or set(packet)!={'op','args'} or not isinstance(packet['args'],dict):
                raise ValueError()
            op,args = packet['op'],packet['args']
            if op=='status' and not args: return self.status()
            if op in {'encounter','result'} and set(args)=={'request_id','user'}:
                if self.admitted_users.get(args['request_id']) != args['user']:
                    raise PermissionError('No trusted user-origin binding')
                return getattr(self,op)(**args)
            raise PermissionError()
        except PermissionError: return {'status':'DENIED'}
        except Exception: return {'status':'REVIEW_REQUIRED'}

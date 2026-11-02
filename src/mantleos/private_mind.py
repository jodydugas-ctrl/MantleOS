"""Private cognition ports. Constructed only by a trusted controller, never RPC input."""
import json
import urllib.request
import urllib.error
from .skin import canon

class HostMind:
    """Host-owned private worker. A checker must exercise the actual OS boundary.

    No default checker or automatic same-transcript/subagent fallback is supplied.
    Synthetic tests may inject checks; that is not platform qualification.
    """
    def __init__(self, generate, isolation_check, *, model):
        self.generate = generate
        self.check = isolation_check
        self.model = model

    def __call__(self, frame):
        if self.check() is not True:
            raise PermissionError('Private MIND isolation unavailable; explicitly select a qualified route')
        return self.generate(json.loads(canon(frame)))

class OpenRouterMind:
    """Explicit provider route with private credentials; no network on import/init."""
    model = None
    def __init__(self, *, key, model, providers, max_tokens, max_price, budget_calls,
                 provider_labels=None, transport=None):
        if (not key or not isinstance(model,str) or not model or not providers or
            not all(isinstance(p,str) and p for p in providers) or
            type(max_tokens) is not int or not 1 <= max_tokens <= 8192 or
            type(budget_calls) is not int or not 1 <= budget_calls <= 1000 or
            not isinstance(max_price,dict) or set(max_price) != {'prompt','completion'} or
            not all(type(v) in (int,float) and 0 < v <= 100 for v in max_price.values())):
            raise ValueError('Explicit bounded OpenRouter route required')
        self.key,self.model,self.providers = key,model,list(providers)
        self.provider_labels = list(provider_labels or providers)
        if not self.provider_labels or not all(isinstance(p,str) and p for p in self.provider_labels):
            raise ValueError('Explicit provider response labels required')
        self.max_tokens,self.max_price,self.remaining = max_tokens,max_price,budget_calls
        self.transport = transport or self._send

    def _send(self, payload):
        request = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
            data=canon(payload).encode(),headers={'Authorization':'Bearer '+self.key,
            'Content-Type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=30) as response:
                raw = response.read(262145)
            if len(raw)>262144: raise ValueError('Provider response budget exceeded')
            return json.loads(raw)
        except Exception:
            raise RuntimeError('Private provider request failed; no automatic retry or fallback') from None

    def __call__(self, frame):
        if self.remaining <= 0: raise PermissionError('Private MIND call budget exhausted')
        encoded = canon(frame)
        if len(encoded.encode()) > 131072: raise ValueError('Private frame budget exceeded')
        self.remaining -= 1  # Unknown provider outcome still consumes the authorized attempt.
        result = self.transport({'model':self.model,'messages':[{'role':'user','content':encoded}],
            'max_tokens':self.max_tokens,'stream':False,'response_format':{'type':'json_object'},
            'provider':{'only':self.providers,'allow_fallbacks':False,'require_parameters':True,
                        'data_collection':'deny','zdr':True,'max_price':self.max_price}})
        if result.get('model') != self.model or result.get('provider') not in self.provider_labels:
            raise ValueError('Unapproved model/provider result')
        return json.loads(result['choices'][0]['message']['content'])

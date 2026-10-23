"""One Anchor model: constant singularities, contextual attributes, no authority.

Definitions are trusted source constants. A model may propose an application of
a definition; it cannot redefine the singularity by editing or rehashing it.
"""
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from . import json_contract as contract

SCHEMA = 'anchor.application/1'
TYPES = ('BlackHole', 'WhiteHole', 'Neutral')
RULE_ECONOMY = 'Use as few rules as possible while still covering all needed variables.'


@dataclass(frozen=True)
class Definition:
    id: str
    type: str
    singularity: str


DEFINITIONS = MappingProxyType({
    'BlackHole': Definition('BlackHole', 'BlackHole', 'Receive the declared input.'),
    'WhiteHole': Definition('WhiteHole', 'WhiteHole', 'Enforce the declared boundary.'),
    'Neutral': Definition('Neutral', 'Neutral', 'Apply the declared relationship.'),
    'N-RULE-ECONOMY': Definition('N-RULE-ECONOMY', 'Neutral', RULE_ECONOMY),
})


def definition(identifier):
    if not isinstance(identifier, str) or identifier not in DEFINITIONS:
        raise ValueError('Unknown Anchor definition; model-created singularities are not admitted')
    return DEFINITIONS[identifier]


def validate_binding(value):
    """Validate a register/project view against the same source constants."""
    base = definition(value.get('definition_id'))
    contract.require(value.get('type') == base.type and value.get('singularity') == base.singularity,
                     'Anchor singularity and type are immutable')
    return base


def application(identifier, *, definition_id='Neutral', attributes=None):
    base = definition(definition_id)
    value = {'schema': SCHEMA, 'id': identifier, 'definition': base.id,
             'type': base.type, 'singularity': base.singularity,
             'attributes': deepcopy(attributes if attributes is not None else {})}
    value['sha256'] = contract.digest(value)
    return validate(value)


def validate(value):
    contract.shape(value, {'schema', 'id', 'definition', 'type', 'singularity', 'attributes', 'sha256'})
    contract.require(value['schema'] == SCHEMA, 'Unsupported Anchor application version')
    contract.identifier(value['id'])
    base = definition(value['definition'])
    contract.require(value['type'] == base.type and value['singularity'] == base.singularity,
                     'Anchor singularity and type are immutable')
    contract.require(type(value['attributes']) is dict, 'Anchor attributes must be an object')
    contract.require(not {'singularity', 'type', 'definition'} & value['attributes'].keys(),
                     'Attributes cannot override an Anchor definition')
    contract.require(value['sha256'] == contract.digest({k: v for k, v in value.items() if k != 'sha256'}),
                     'Anchor application digest mismatch')
    return deepcopy(value)


def apply_attributes(value, attributes):
    """Return a proposed contextual application; this does not admit it anywhere."""
    old = validate(value)
    return application(old['id'], definition_id=old['definition'], attributes=attributes)

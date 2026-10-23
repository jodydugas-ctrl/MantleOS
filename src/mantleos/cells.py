"""Kernel-produced CELLs: the smallest unit of an organism for that kernel.

Pixel and append-segment representations share the CELL concept; their values
and units remain kernel-specific. Programs compose these units but are not CELLs.
"""
from copy import deepcopy
from . import json_contract as contract

SCHEMA = 'mantle.cell/2'
KERNELS = {'chroma.rgb/1': 'pixel', 'tape.segment/1': 'appended-record'}


def produce(kernel, payload):
    value = dict(schema=SCHEMA, kernel=kernel, payload=deepcopy(payload))
    value['sha256'] = contract.digest(value)
    return validate(value)


def validate(value):
    contract.shape(value, {'schema', 'kernel', 'payload', 'sha256'})
    contract.require(value['schema'] == SCHEMA, 'Unsupported CELL version')
    contract.require(value['kernel'] in KERNELS, 'Unsupported CELL kernel')
    payload = value['payload']
    if value['kernel'] == 'chroma.rgb/1':
        contract.require(type(payload) is list and len(payload) == 3 and
                         all(type(v) is int and 0 <= v <= 255 for v in payload),
                         'An RGB CELL is exactly one three-channel pixel')
    else:
        contract.shape(payload, {'sequence', 'record'})
        contract.require(type(payload['sequence']) is int and payload['sequence'] >= 1 and
                         type(payload['record']) is dict, 'A tape CELL is one append segment')
        contract.require(payload['record'].get('seq') == payload['sequence'], 'Tape CELL sequence mismatch')
    contract.require(value['sha256'] == contract.digest({k: v for k, v in value.items() if k != 'sha256'}),
                     'CELL digest mismatch')
    return deepcopy(value)


def rgb_tape(data):
    """Validate the producer's byte framing without materializing millions of objects."""
    contract.require(isinstance(data, (bytes, bytearray)) and len(data) % 3 == 0,
                     'RGB kernel output must contain complete pixel CELLs')
    return data


def pixels(data):
    rgb_tape(data)
    for offset in range(0, len(data), 3):
        yield produce('chroma.rgb/1', list(data[offset:offset + 3]))


def append_segment(record):
    contract.require(type(record) is dict and 'seq' in record, 'Append record needs its sequence')
    return produce('tape.segment/1', {'sequence': record['seq'], 'record': record})

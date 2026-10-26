"""Data-only REFLEX carrier transports; decoding is never adoption or execution.

These experimental codecs deliberately do not register with MantleOS Cartridge,
ChromaMem, VCW or BODY. No status here implies an approved native adapter.
"""
from .contract import make_manifest, verify_manifest
from .raw import RawCarrier
from .zip_reflex import ZipReflexCarrier

CARRIERS = {'raw': RawCarrier(), 'zip': ZipReflexCarrier()}


def carrier(name):
    from ..errors import refuse
    if type(name) is not str or name not in CARRIERS:
        refuse('E_CARRIER', 'unknown or unsupported experimental carrier')
    return CARRIERS[name]

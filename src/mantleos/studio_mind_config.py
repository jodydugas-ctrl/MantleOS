"""Owner-file data for Studio cognition. Loading never calls an inference API.

Keys remain controller-only fields. Public settings deliberately exclude keys,
their fingerprints, the source file and its digest. File prose is never executed
or interpreted as an authority grant. Spending caps do not reset on reload.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
from pathlib import Path
import re

MODEL = re.compile(r'[A-Za-z0-9_.+-]+/[A-Za-z0-9_.:+-]+')
KEY = re.compile(r'sk-or-[A-Za-z0-9_-]{16,256}')
BUDGET = re.compile(r'\s*\$?\s*(\d+(?:\.\d+)?|\.\d+)\s*(USD|dollars?|cents?)?\s*', re.I)


@dataclass(frozen=True)
class OwnerMindConfig:
    models: tuple[str, ...]
    mind_budget_micro_usd: int
    limbs_budget_micro_usd: int
    mind_key: str = field(repr=False)
    limbs_key: str = field(repr=False)
    source: Path = field(repr=False)
    source_sha256: str = field(repr=False)

    def public(self):
        return {'models': list(self.models),
                'budgets_micro_usd': {'mind': self.mind_budget_micro_usd, 'limbs': self.limbs_budget_micro_usd},
                'budget_period': 'TOTAL_NO_AUTOMATIC_RESET',
                'credentials': {'mind': 'AVAILABLE_IN_OWNER_FILE', 'limbs': 'AVAILABLE_IN_OWNER_FILE'},
                'inference': 'NOT_STARTED_BY_CONFIGURATION_LOAD'}

    def require_unchanged(self):
        with self.source.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != self.source_sha256:
            raise PermissionError('Owner MIND configuration changed; pending work requires review')


def _budget(text):
    match = BUDGET.fullmatch(text)
    if not match:
        raise ValueError('Explicit finite dollar/cent budget required')
    value = Decimal(match[1])
    if (match[2] or '').casefold().startswith('cent'):
        value /= 100
    micros = value*1_000_000
    if micros != micros.to_integral_value() or not 0 <= micros <= 2**63-1:
        raise ValueError('Budget is outside exact microdollar storage limits')
    return int(micros)


def load_owner_file(source):
    """Read the owner's models + Mind/Limbs key/budget sections as inert data.

    Model lines are ordered: primary, followed by explicitly listed backups.
    A backup/router selection is not a blanket permission for other models.
    Actual routing, provider constraints, accounting and release belong to Body.
    """
    source = Path(source).resolve()
    with source.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Owner MIND configuration exceeds 64 KiB')
    models, keys, budgets = [], {}, {}
    section = None
    for raw_line in raw.decode('utf-8-sig').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if MODEL.fullmatch(line):
            models.append(line)
            continue
        if KEY.fullmatch(line):
            if section not in ('mind', 'limbs') or section in keys:
                raise ValueError('Each private key needs one unambiguous Mind/Limbs section')
            keys[section] = line
            continue
        budget = re.fullmatch(r'Budget\s*[:=]\s*(.+)', line, re.I)
        if budget:
            if section not in ('mind', 'limbs') or section in budgets:
                raise ValueError('Each budget needs one unambiguous Mind/Limbs section')
            budgets[section] = _budget(budget[1])
            continue
        # Only section labels affect parsing. Other prose supplies no commands,
        # providers, policy changes, credential disclosure or callback code.
        if re.search(r'\blimbs?\b', line, re.I):
            section = 'limbs'
        elif re.fullmatch(r'[#*\s]*(?:mind|brain|prime)\s*:?[#*\s]*', line, re.I):
            section = 'mind'
    if (not 1 <= len(models) <= 8 or len(set(models)) != len(models)
            or set(keys) != {'mind', 'limbs'} or set(budgets) != {'mind', 'limbs'}):
        raise ValueError('Owner file must declare ordered models and separate Mind/Limbs keys and finite budgets')
    return OwnerMindConfig(tuple(models), budgets['mind'], budgets['limbs'], keys['mind'], keys['limbs'],
                           source, hashlib.sha256(raw).hexdigest())

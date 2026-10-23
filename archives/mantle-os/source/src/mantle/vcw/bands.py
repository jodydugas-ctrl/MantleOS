#!/usr/bin/env python3
"""
mantle.vcw.bands  --  boot sectors, the driver registry, the standard genome,
                      and the capacity thresholds (Mantle OS)

Two-level encoding:
  level 1  boot-sector format  = fixed & universal (the Body always understands it)
  level 2  payload format      = programmable (the boot sector names a registered driver)

A band reserves a RANGE of `span` layers starting at `head`; physical layers materialize on
demand and reclaimed layers return to a per-band free pool. Every band declares a purpose.
The boot map is the cube's substrate bootloader: it decides which layers exist, who owns
them, what driver/profile interprets their four RGBA lanes, and which lanes are payload,
repair, index, tool, database, spatial, or Grimoire-semantic data.

CAPACITY DOCTRINE (executable): a band's *pressure* is the fraction of its reserved span
that is allocated. Crossing OVERFLOW (0.75) fires an `overflow` immune event and triggers
metabolism (compact/dedupe/reclaim). Crossing EMERGENCY (0.90) fires `emergency` and aggressive
metabolism. Capacity NEVER triggers rebirth: rebirth stays a separate, chosen reformat.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---- capacity thresholds (fractions of a band's reserved span) -------------
OVERFLOW_THRESHOLD  = 0.75   # metabolize: compact, dedupe, reclaim
EMERGENCY_THRESHOLD = 0.90   # aggressive metabolism + emergency immune event


def make_band_boot(band: str, head: int, encoding: str = "log-json",
                   params: Optional[Dict[str, Any]] = None,
                   private: bool = False, span: int = 1,
                   purpose: str = "") -> Dict[str, Any]:
    """A band's boot sector: head layer, reserved span, driver, params, veil flag, purpose."""
    return {
        "band": band,
        "head": head,
        "span": max(1, int(span)),
        "purpose": purpose or band,
        "encoding": encoding,
        "params": params or {},
        "private": bool(private),
        "v": 3,
    }


def make_cube_boot(generation: int, bands: Dict[str, Dict[str, Any]],
                   identity_in_body: bool = True) -> Dict[str, Any]:
    """The Cube Boot Sector: the authoritative band map for one generation.
    identity_in_body=True: the Primer lives in the BODY; the cube is pure experiential memory."""
    return {
        "format": "vcw-cube-png-v2",
        "generation": generation,
        "identity_in_body": identity_in_body,
        "bands": bands,
    }


def standard_genome() -> List[Dict[str, Any]]:
    """The reserved experiential bands (identity lives in the Body, never here). Spans are
    sized to each band's reserved range so metabolism can grow and reclaim layers."""
    return [
        make_band_boot("identity",    100, "log-json", span=50,  purpose="experiential self-state"),
        make_band_boot("facts",       150, "log-json", span=50,  purpose="durable truths"),
        make_band_boot("events",      200, "log-json", span=50,  purpose="event history"),
        make_band_boot("discoveries", 250, "log-json", span=50,  purpose="learned knowledge"),
        make_band_boot("senses",      300, "log-json", span=100, purpose="sensor intake"),
        make_band_boot("immune",      400, "log-json", span=50,  purpose="audit/defense"),
        make_band_boot("brain",       450, "log-json", span=50,  purpose="dispatch log"),
        make_band_boot("thoughts",    500, "log-json", span=50,  purpose="private reflection",
                       private=True),
    ]


def semantic_genome(semantic_bands=("thoughts", "brain")) -> List[Dict[str, Any]]:
    """The semantic-memory genome: the standard bands, but the selected MIND-surface
    bands boot the `grimoire-v0.10-entry` driver, so a MIND reflection is encoded into a
    Grimoire v0.10 statement at append time -- thought and storage are one step.

    Default scope: `thoughts` + `brain` (the MIND write surface). `identity` and
    `immune` intentionally stay `log-json` (identity lives in the Body; immune events
    stay plain records). The privacy veil on `thoughts` is preserved.

    Creating semantic-memory tissue requires the operator adoption receipt
    (`adopt_semantic_memory`); this function only builds the boot sectors.
    """
    allowed = {boot["band"] for boot in standard_genome()}
    unknown = [name for name in semantic_bands if name not in allowed]
    if unknown:
        raise ValueError("semantic_genome: unknown band(s) %s (have: %s)"
                         % (", ".join(sorted(unknown)), ", ".join(sorted(allowed))))
    encoding = "grimoire-v0.10-entry"
    get_driver(encoding)                                # registered or fail loudly
    genome = standard_genome()
    for boot in genome:
        if boot["band"] in semantic_bands:
            boot["encoding"] = encoding
            boot["params"] = {"profile": encoding}
    return genome


APP_BAND_RANGE = (550, 749)   # caller-defined application bands
TAIL_RANGE     = (750, 799)   # reserved scratch / future use

#: The app-band ATLAS: every framework-reserved range in 550-749, stated once (the
#: Reproduction organ is its keeper). Caller/egg/test bands live in the gaps
#: (600-637 and 676-699). A genome whose reserved ranges overlap is REFUSED at
#: genesis and at the compiler gate -- overlapping spans eventually stomp layers.
APP_BAND_ATLAS = {
    "host_state":       (550, 40),   # assimilator: mirrored host state
    "host_actions":     (590, 10),   # assimilator: wrapped host effectors
    #                   600-637      caller space (eggs, grafts, ganglia, tests)
    "vault":            (638, 2),    # the seed vault (Reproduction organ tissue)
    "phenotypes":       (640, 16),   # SELF-encrypted faces
    "symbiosis":        (656, 4),    # the energy ledger
    "phenotype_log":    (660, 2),    # append-only wear log
    "spore_vault":      (664, 12),   # the sealed origin spore (SPORE-DISTILLATION)
    #                   676-699      caller space
    "applets_manifest": (700, 4),    # VCW Applet Bodies (APPLET-BODY-CAPSULE)
    "applets_source":   (704, 24),
    "applets_state":    (728, 8),
    "applets_organs":   (736, 8),
    "applets_log":      (744, 4),
}


def _span_of(spec: Dict[str, Any]) -> Tuple[int, int, str]:
    head = int(spec["head"])
    span = max(1, int(spec.get("span", 1)))
    return head, head + span, str(spec.get("band", "?"))


def _ranges_overlap(a_head: int, a_end: int, b_head: int, b_end: int) -> bool:
    return a_head < b_end and b_head < a_end


def app_band_reserved_spans() -> List[Tuple[int, int, str]]:
    """Framework-reserved app-layer spans as half-open ranges.

    Returned shape is `(head, end, name)`, where `end` is exclusive. Caller bands
    should be allocated only in the gaps, not by hand-picking heads that may later
    collide with vault, phenotype, spore, or applet tissue.
    """
    spans = []
    for name, (head, span) in APP_BAND_ATLAS.items():
        spans.append((head, head + span, name))
    return sorted(spans)


def app_band_conflicts(specs: Iterable[Dict[str, Any]]) -> List[str]:
    """Return collisions between proposed app bands and the reserved atlas.

    Exact declarations of framework-owned atlas bands are allowed so built-in
    helpers such as `phenotype_bands()` and `applet_bands()` can self-validate.
    Any other overlap is refused: it would eventually stomp a physical VCW layer.
    """
    problems: List[str] = []
    reserved = app_band_reserved_spans()
    for spec in specs:
        head, end, band = _span_of(spec)
        if not (APP_BAND_RANGE[0] <= head <= APP_BAND_RANGE[1]):
            continue
        exact = APP_BAND_ATLAS.get(band)
        if exact is not None and exact == (head, end - head):
            continue
        for r_head, r_end, r_name in reserved:
            if _ranges_overlap(head, end, r_head, r_end):
                problems.append(
                    "band %r [%d-%d] overlaps reserved app band %r [%d-%d]"
                    % (band, head, end - 1, r_name, r_head, r_end - 1))
    return problems


def allocate_app_band(band: str, span: int, *,
                      encoding: str = "log-json",
                      params: Optional[Dict[str, Any]] = None,
                      private: bool = False,
                      purpose: str = "",
                      existing: Optional[Iterable[Dict[str, Any]]] = None
                      ) -> Dict[str, Any]:
    """Allocate the first free caller-owned app-band slice.

    This avoids the NotepadNext/calculator failure mode where a hand-picked span
    crossed the seed vault. The allocator treats APP_BAND_ATLAS plus any
    caller-supplied existing bands as occupied and returns a normal boot sector.
    """
    width = max(1, int(span))
    occupied = app_band_reserved_spans()
    for spec in existing or []:
        head, end, name = _span_of(spec)
        occupied.append((head, end, name))
    occupied.sort()

    head = APP_BAND_RANGE[0]
    for occ_head, occ_end, _name in occupied:
        if head + width <= occ_head:
            return make_band_boot(band, head, encoding, params=params,
                                  private=private, span=width, purpose=purpose)
        head = max(head, occ_end)
    if head + width <= APP_BAND_RANGE[1] + 1:
        return make_band_boot(band, head, encoding, params=params,
                              private=private, span=width, purpose=purpose)
    raise ValueError("no free app-band slice can fit band %r span %d" % (band, width))


def genome_overlaps(genome) -> List[str]:
    """Overlapping reserved ranges in a proposed genome ([] == coherent). Two bands
    whose [head, head+span) ranges intersect will eventually allocate the same physical
    layer and stomp each other -- so an overlapping genome is refused, never booted."""
    spans = sorted((int(b["head"]), int(b["head"]) + max(1, int(b.get("span", 1))),
                    b["band"]) for b in genome)
    problems: List[str] = []
    for (h1, e1, n1), (h2, e2, n2) in zip(spans, spans[1:]):
        if h2 < e1:
            problems.append("band %r [%d-%d] overlaps band %r [%d-%d]"
                            % (n2, h2, e2 - 1, n1, h1, e1 - 1))
    return problems


def code_hash(code: str) -> str:
    """The canonical hash binding an exec layer's boot sector to its code payload."""
    return "sha256:" + hashlib.sha256(code.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------
# Driver base + registry (drivers register themselves in mantle.vcw.drivers)
# ----------------------------------------------------------------------------
class Driver:
    """A payload protocol. `content` is the driver-native in-memory form of one layer:
      log-json -> list[entry dict] · keyvalue -> dict · calendar-spatial -> bytearray canvas
      exec     -> dict {code, code_hash, entry, signature, capabilities, limits, provenance}
    """
    name: str = "base"

    def empty(self, params: Dict[str, Any]) -> Any:
        raise NotImplementedError

    def read(self, content: Any, params: Dict[str, Any], reveal_private: bool = False) -> Any:
        raise NotImplementedError

    def retrieve(self, content: Any, params: Dict[str, Any], address: Any) -> Any:
        raise NotImplementedError

    def append(self, content: Any, params: Dict[str, Any], value: Any) -> Any:
        raise NotImplementedError


_REGISTRY: Dict[str, Driver] = {}


def register(driver):
    """Class decorator: stores an INSTANCE in the registry, returns the class unchanged."""
    inst = driver() if isinstance(driver, type) else driver
    _REGISTRY[inst.name] = inst
    return driver


def get_driver(encoding: str) -> Driver:
    if encoding not in _REGISTRY:
        raise KeyError("no driver registered for encoding %r (have: %s)"
                       % (encoding, ", ".join(sorted(_REGISTRY)) or "<none>"))
    return _REGISTRY[encoding]


def registered_encodings() -> List[str]:
    return sorted(_REGISTRY)

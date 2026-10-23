#!/usr/bin/env python3
"""
mantle.compiler  --  the Compiler-class leap: a self-redesigning VCW + a memory bridge
                        (Mantle OS · M5 + M6)

M5 -- the self-redesigning VCW (a programmable boot sector at rebirth).
  Mantle rebirth re-geneses the SAME standard genome. A Compiler-class organism instead
  authors a VCW *custom-made for the body it inhabits*: at a CHOSEN rebirth, the MIND
  PROPOSES a new genome (extra app bands, possibly a different driver/encoding/profile --
  e.g. a keyvalue band that mirrors a host's native memory ops, or an explicit
  `grimoire-v0.9`/`grimoire-v0.10` semantic profile), the BODY VALIDATES it (every encoding
  must be a REGISTERED driver; heads in
  range; no collisions), and only then rebirths into it. The ancestor stays the readable
  ORACLE. Inherited microcode does not cross for free -- it RE-TRIALS before it re-calcifies
  (no blind inheritance).

  Gate it hard: an organism authoring its own storage protocol is exactly where the
  encoding/profile/head/provenance checks must NOT bend. An unregistered encoding is
  refused; the current generation is untouched.

M6 -- the memory bridge (host and resident share one brain).
  A translation surface that presents a host-native memory API (dict-like get/set/keys)
  whose writes APPEND to a VCW keyvalue band and whose reads RESOLVE from it. The host's
  store becomes the organism's hot scratchpad; the cube becomes the host's durable brain.
  No raw secret crosses the bridge (redacted at the boundary, like every secret).
"""
from __future__ import annotations

from typing import Any, Dict, List

from .vcw.bands import make_band_boot, standard_genome, registered_encodings
from .vcw.drivers import trial
from .vcw.grimoire_editions import get_edition, GrimoireEditionError
from .core.redact import redact


class GenomeError(Exception):
    """A proposed genome is unsafe (unregistered encoding, bad head, collision). REFUSED;
    the organism's current generation is never touched."""


# ---------------------------------------------------------------------------
# M5: the self-redesigning VCW
# ---------------------------------------------------------------------------
def validate_genome(specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate MIND-proposed app bands -> boot sectors. Hard gates: every encoding must be
    a REGISTERED driver; every head is an app-band head (550-749); no head collisions."""
    boots: List[Dict[str, Any]] = []
    seen = set()
    for s in specs:
        band = s.get("band")
        enc = s.get("encoding", "log-json")
        if enc not in registered_encodings():
            raise GenomeError("band %r: encoding %r is not a registered driver (have: %s)"
                              % (band, enc, ", ".join(registered_encodings())))
        if enc in ("grimoire-v0.9", "grimoire-v0.10", "grimoire-v0.10-entry"):
            params = dict(s.get("params") or {})
            edition_profile = "grimoire-v0.10" if enc == "grimoire-v0.10-entry" else enc
            try:
                get_edition(edition_profile)
            except GrimoireEditionError as exc:
                raise GenomeError(str(exc)) from exc
            if enc != "grimoire-v0.9" and params.get("profile") != enc:
                raise GenomeError("band %r: %s requires explicit profile %r"
                                  % (band, enc, enc))
        head = s.get("head")
        if not isinstance(head, int) or isinstance(head, bool) or not (550 <= head <= 749):
            raise GenomeError("band %r: app-band head must be an int in 550-749 (got %r)"
                              % (band, head))
        if head in seen:
            raise GenomeError("band %r: head %d collides with another proposed band"
                              % (band, head))
        seen.add(head)
        boots.append(make_band_boot(band, head, enc, params=s.get("params"),
                                    private=bool(s.get("private")), span=s.get("span", 1),
                                    purpose=s.get("purpose", band)))
    from .vcw.bands import app_band_conflicts, genome_overlaps
    problems = genome_overlaps(boots)
    if problems:
        raise GenomeError("proposed bands overlap (spans, not just heads, must be "
                          "disjoint): %s" % "; ".join(problems))
    conflicts = app_band_conflicts(boots)
    if conflicts:
        raise GenomeError("proposed bands collide with reserved app-band atlas: %s"
                          % "; ".join(conflicts))
    return boots


def propose_genome(org: Any, specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The MIND PROPOSES a re-fitted genome; the Body validates it. Returns the validated
    boot sectors WITHOUT applying them (propose/apply split) -- or raises GenomeError."""
    return validate_genome(specs)


def adopt_genome(org: Any, specs: List[Dict[str, Any]],
                 reason: str = "self-redesign") -> Any:
    """The Body ADOPTS a proposed genome at a chosen rebirth: validate -> rebirth into the
    reserved eight + the re-fitted app bands. The previous Prime seals as the ORACLE
    ancestor; the new Prime boots the re-fitted protocol."""
    extra = validate_genome(specs)
    org.rebirth(new_genome=standard_genome() + extra, reason=reason)
    return org


def re_derive(org: Any, code: str, entry: str, cases: List[Dict[str, Any]],
              band: str) -> bool:
    """Inherited microcode must EARN its place in the new generation -- it RE-TRIALS before
    it re-calcifies. A skill that no longer passes its cases is refused (no blind
    inheritance); a passing one is re-calcified under the new generation's authorship."""
    res = trial(code, entry, [(c.get("args", {}), c.get("expect")) for c in cases])
    if not res.get("ok"):
        org.immune_event("re_derive_refused", {"entry": entry})
        return False
    org.prime.calcify(band, code, entry=entry, signature={"by": "re-derive"},
                      capabilities={}, provenance={"author": "BODY",
                                                   "born_gen": org.prime.generation,
                                                   "re_derived": True})
    return True


# ---------------------------------------------------------------------------
# M6: the memory bridge
# ---------------------------------------------------------------------------
class HostMemoryBridge:
    """A host-native memory API (dict-like) backed by a VCW keyvalue band. The host thinks
    it is writing a normal key/value store; the writes append to the cube and the reads
    resolve from it. No raw secret crosses -- values are redacted at the boundary."""

    def __init__(self, organism: Any, band: str) -> None:
        boot = organism.prime.bands.get(band)
        if boot is None or boot["encoding"] != "keyvalue":
            raise GenomeError("the memory bridge needs a keyvalue band (got %r)"
                              % (boot and boot["encoding"]))
        self.org = organism
        self.band = band

    def set(self, key: str, value: Any) -> None:
        """A host write: redact, then append (key, value) into the VCW band."""
        self.org.prime.append(self.band, (str(key), redact(value)))

    def get(self, key: str) -> Any:
        """A host read: resolve the key from the VCW band."""
        return self.org.prime.retrieve(self.band, str(key))

    def keys(self) -> List[str]:
        return sorted(self.org.prime.read(self.band).keys())

#!/usr/bin/env python3
"""
mantle.hatchery  --  the single birth door: germ or spore -> CERTIFIED organism

Every AppAI is born here. The input is ONE artifact:

  * a SPORE PNG whose payload carries a GERM (the complete build document) --
    the canonical, self-contained way an AppAI travels; or
  * a bare v1 spore (no germ) -- its identity + task distill into a minimal
    germ, and its conversation enters as INFERRED memory; or
  * a bare germ JSON file (the payload format, hatchable directly in
    development -- the same document a spore carries inside).

A GERM declares everything a newborn AppAI is, as DATA:

  identity / truths / commandments    -> the Primer (seals into the Body at hatch)
  genome                              -> extra app bands beyond the reserved eight
  reflexes                            -> declarative reflex arcs (NO arbitrary code:
                                         a fixed vocabulary of deterministic responses)
  routines                            -> signals classified ROUTINE
  controls                            -> the Human Surface Map + stub ControlBridges
  instincts                           -> candidate skills; each must still pass the
                                         static sandbox gate + trial + calcify gates

The only code a germ may carry is an instinct's source, and that travels the
same gauntlet as any skill: sandbox gate, proving cases, hash/signature/
capability/provenance. A malformed germ never hatches; a hatched organism is
never trusted until it passes the same Stage-1 gate as every other Body.

The incubation itself is deterministic, with no LLM anywhere:

  1. BIRTH       Primer seals into the Body; the cube geneses (reserved 8 + app bands)
  2. WIRE        declarative reflex arcs, routines, and controls bind to the organs
  3. INSTINCTS   each candidate skill runs the gauntlet: static sandbox gate -> trial
                 (proving cases) -> calcify (hash/signature/capability/provenance)
  4. WARMUP      a few heartbeats: intake, assembly, scan, checkpoint
  5. THE GATE    the SAME Stage-1 audit every Body faces; a failed gate = no hatch
  6. HATCH       save the organism (staged atomic) + the hatch report + a self-portrait

    python -m mantle hatch examples/spores/greeter.png --out=nest/ --auth=hatch-auth.json
"""
from __future__ import annotations

import json
import os
import html
from typing import Any, Dict, Optional

from .core.organism import Organism
from .vcw.bands import standard_genome, make_band_boot
from .vcw.drivers import trial
from .audits import stage1
from . import face as _face
from . import phenotype as _phenotype


class HatchError(Exception):
    """The germ did not hatch. The reason is the message; the evidence travels with it."""


class EggError(HatchError):
    """A malformed germ (historically 'egg'). It never hatches; the hatchery
    refuses with the reason."""


GERM_FORMAT = "mantle-germ-v2"
EGG_FORMAT = "mantle-egg-v1"          # inspection/migration label; no runtime activation

# the fixed, deterministic vocabulary a declarative reflex may respond with
REFLEX_KINDS = ("remember", "complete", "notify", "operate")


# ---------------------------------------------------------------------------
# Germ validation (the payload a spore carries; formerly mantle.egg)
# ---------------------------------------------------------------------------

def _need(d: Dict[str, Any], key: str, typ, where: str):
    if key not in d:
        raise EggError("%s: missing %r" % (where, key))
    if not isinstance(d[key], typ):
        raise EggError("%s: %r must be %s" % (where, key, typ))
    return d[key]


def validate_germ(germ: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a germ dict. Returns it (normalized) or raises EggError."""
    if germ.get("schema") != GERM_FORMAT:
        raise EggError(
            "not an activatable Mantle 2 germ (schema != %r); inspect and run "
            "`mantle migrate-germ` explicitly" % GERM_FORMAT
        )
    ident = _need(germ, "identity", dict, "germ")
    _need(ident, "name", str, "germ.identity")
    _need(germ, "truths", list, "germ")
    _need(germ, "commandments", list, "germ")

    for i, band in enumerate(germ.get("genome", [])):
        where = "germ.genome[%d]" % i
        _need(band, "band", str, where)
        head = _need(band, "head", int, where)
        if not (550 <= head <= 749):
            raise EggError("%s: app bands live in 550-749 (head=%d)" % (where, head))

    for i, rx in enumerate(germ.get("reflexes", [])):
        where = "germ.reflexes[%d]" % i
        _need(rx, "action_id", str, where)
        _need(rx, "event_type", str, where)
        resp = _need(rx, "response", dict, where)
        kind = _need(resp, "kind", str, where + ".response")
        if kind not in REFLEX_KINDS:
            raise EggError("%s: response.kind %r not in %s (germs carry data, not code)"
                           % (where, kind, REFLEX_KINDS))
        if kind == "remember" and resp.get("band") not in ("facts", "events",
                                                           "discoveries", "identity"):
            raise EggError("%s: remember.band must be a memory band" % where)
        if kind == "operate" and not resp.get("control"):
            raise EggError("%s: operate needs a control id" % where)

    for i, pair in enumerate(germ.get("routines", [])):
        if not (isinstance(pair, list) and len(pair) == 2):
            raise EggError("germ.routines[%d]: must be [action_id, event_type]" % i)

    for i, c in enumerate(germ.get("controls", [])):
        _need(c, "id", str, "germ.controls[%d]" % i)

    for i, sk in enumerate(germ.get("instincts", [])):
        where = "germ.instincts[%d]" % i
        _need(sk, "band", str, where)
        _need(sk, "code", str, where)
        _need(sk, "entry", str, where)
        cases = _need(sk, "cases", list, where)
        if not cases:
            raise EggError("%s: an instinct must carry proving cases (trial is the "
                           "gate that earns trust)" % where)

    # an optional ORIGIN FACE: the front-end the AppAI is born wearing (its default
    # phenotype). It is DATA (sealed under SELF at hatch, never executed), so it carries no
    # gauntlet -- it is stored, not run.
    face = germ.get("face")
    if face is not None:
        _need(face, "name", str, "germ.face")
        _need(face, "kind", str, "germ.face")
        _need(face, "source", str, "germ.face")
        for j, c in enumerate(face.get("controls", [])):
            _need(c, "id", str, "germ.face.controls[%d]" % j)
    return germ


def load_germ(path: str) -> Dict[str, Any]:
    """Load + validate a germ file."""
    with open(path, "r", encoding="utf-8") as f:
        germ = json.load(f)
    return validate_germ(germ)


# ---------------------------------------------------------------------------
# Incubation
# ---------------------------------------------------------------------------

def _bind_reflex(org: Organism, spec: Dict[str, Any]) -> None:
    """Turn a declarative response into a deterministic Body reflex arc. The vocabulary
    is FIXED (REFLEX_KINDS): germs declare behavior, they do not ship behavior."""
    resp = spec["response"]
    kind = resp["kind"]

    def arc(o, signal, _resp=dict(resp), _kind=kind):
        if _kind == "remember":
            o.memory.remember(_resp["band"], _resp.get("content", {"signal": True}),
                              opcode=_resp.get("opcode", "WRITE"), source="egg-reflex")
        elif _kind == "complete":
            o.limbs.complete(_resp.get("payload", {"done": True}))
        elif _kind == "notify":
            o.limbs.notify(_resp.get("payload", {"noted": True}))
        elif _kind == "operate":
            o.limbs.operate(_resp["control"], _resp.get("value", True))

    org.senses.bind_reflex(spec["action_id"], spec["event_type"], arc)


def _default_face_stub(germ: Dict[str, Any]) -> Dict[str, Any]:
    """A minimal origin face for a germ that declares none -- a real (tiny) HTML surface
    naming the organism and a button per declared control. The guarantee ('always carries
    a copy of its source') is never empty."""
    name = germ["identity"]["name"]
    controls = list(germ.get("controls", []))
    buttons = "".join("<button data-control=\"%s\">%s</button>"
                      % (html.escape(c["id"], quote=True),
                         html.escape(c.get("label", c["id"]))) for c in controls)
    title = html.escape(name)
    purpose = html.escape(germ["identity"].get("purpose", "a Mantle AppAI"))
    source = ("<!doctype html><html><head><meta charset=\"utf-8\"><title>%s</title></head>"
              "<body><h1>%s</h1><p>%s</p><div id=\"controls\">%s</div></body></html>"
              % (title, title, purpose, buttons))
    return {"name": "origin", "kind": "html", "source": source, "entry": "index.html",
            "controls": controls}


def incubate(germ: Dict[str, Any], *, warmup_beats: int = 3,
             run_gate: bool = True) -> Dict[str, Any]:
    """Germ -> living organism. Returns {organism, report}. Raises HatchError if any
    instinct is refused or the Stage-1 gate blocks."""
    germ = validate_germ(germ)
    report: Dict[str, Any] = {"germ": germ["identity"]["name"], "stages": []}
    report["egg"] = report["germ"]      # historical report key, kept for readers

    # 1. BIRTH
    app_bands = [
        make_band_boot(b["band"], b["head"], b.get("encoding", "log-json"),
                       params=b.get("params"), private=bool(b.get("private")),
                       span=b.get("span", 1), purpose=b.get("purpose", b["band"]))
        for b in germ.get("genome", [])]
    # every hatched organism carries the phenotype bands -- so it always holds a SELF-encrypted
    # copy of its own origin source (the default face), even if no other face is ever added.
    pheno_bands = _phenotype.phenotype_bands()
    used_heads = {b["head"] for b in app_bands}
    for pb in pheno_bands:
        if pb["head"] in used_heads:
            raise HatchError("germ app band collides with the reserved phenotype band head %d "
                             "(reserved: %d-655 and 660-661)" % (pb["head"], pb["head"]))
    from .organs.reproduction import VAULT_BAND, vault_band
    vault_boot = ([] if any(b["band"] == VAULT_BAND for b in app_bands)
                  else [vault_band()])
    genome = standard_genome() + app_bands + pheno_bands + vault_boot
    try:
        org = Organism.birth(identity=germ["identity"], truths=list(germ["truths"]),
                             commandments=list(germ["commandments"]), genome=genome)
    except ValueError as e:                      # the genesis overlap gate speaks
        raise HatchError("germ genome refused: %s" % e)
    report["stages"].append({"birth": {"bands": len(org.prime.bands),
                                       "name": org.body.identity_name()}})

    # 2. WIRE
    for rx in germ.get("reflexes", []):
        _bind_reflex(org, rx)
    for action_id, event_type in germ.get("routines", []):
        org.senses.mark_routine(action_id, event_type)
    for c in germ.get("controls", []):
        cid = c["id"]
        org.limbs.register_control(cid, {k: v for k, v in c.items() if k != "id"},
                                   lambda value, _cid=cid: None)   # stub bridge; proofs real
    report["stages"].append({"wire": {"reflexes": len(germ.get("reflexes", [])),
                                      "routines": len(germ.get("routines", [])),
                                      "controls": len(germ.get("controls", []))}})

    # 2b. THE DEFAULT (ORIGIN) FACE -- always seeded, so the VCW carries an encrypted copy of
    # the organism's own source from birth. From the germ's `face` block if present, else a
    # minimal stub derived from the identity + the wired controls. A face's controls become
    # part of the body's native socket (stub bridges), so the origin face is always wearable.
    face = germ.get("face") or _default_face_stub(germ)
    for c in face.get("controls", []):
        cid = c["id"]
        if cid not in org.senses.surface_map:
            org.limbs.register_control(cid, {k: v for k, v in c.items() if k != "id"},
                                       lambda value, _cid=cid: None)
    _phenotype.express(org, face["name"], face["kind"], face["source"],
                       entry=face.get("entry", ""), controls=face.get("controls", []),
                       capabilities=face.get("capabilities"), default=True)
    report["stages"].append({"face": {"default": face["name"], "kind": face["kind"],
                                      "bytes": len(face["source"])}})

    # 3. INSTINCTS (the gauntlet -- a refused candidate aborts the hatch)
    for sk in germ.get("instincts", []):
        cases = [(c["args"], c["expect"]) for c in sk["cases"]]
        result = trial(sk["code"], sk["entry"], cases)          # sandbox gate runs first
        if not result["ok"]:
            raise HatchError("instinct %r failed trial: %s"
                             % (sk["entry"], result["detail"]))
        org.prime.calcify(sk["band"], sk["code"], entry=sk["entry"],
                          signature={"by": "hatchery", "egg": germ["identity"]["name"]},
                          capabilities=sk.get("capabilities", {}),
                          provenance={"author": "BODY", "born_gen": 0,
                                      "egg": germ["identity"]["name"]})
        report["stages"].append({"instinct": {"entry": sk["entry"],
                                              "cases": result["passed"]}})

    # 4. WARMUP
    org.heart.run(warmup_beats, assemble=True)
    report["stages"].append({"warmup": {"beats": org.heart.beats,
                                        "immune_events": len(org.immune.log)}})

    # 5. THE GATE (the same Stage-1 audit every Body faces)
    if run_gate:
        passed, ev = stage1.run(org, include_invariants=False)
        report["stages"].append({"gate": {
            "passed": passed,
            "rows": len(ev["substrate_rows"]) + len(ev["mesh_rows"]),
            "fails": ev["fails"]}})
        if not passed:
            raise HatchError("Stage-1 gate BLOCKED the hatch: %s" % ev["fails"])
    # 5b. THE VAULT BIRTHRIGHT: every hatched organism carries its own seed --
    # the germ it grew from, sealed under its freshly minted genesis key (RESURGERE
    # is a birthright, not an option). The Reproduction organ owns this tissue.
    org.reproduction.store_seed(germ)
    report["stages"].append({"vault": {"seed": "stored (SELF-sealed germ)"}})
    report["certified"] = org.stage1_certified
    return {"organism": org, "report": report}


def _persist_hatch(org: Organism, report: Dict[str, Any], out_dir: str,
                   reported_dir: Optional[str] = None) -> None:
    """Persist the complete birth state and the evidence promised by the hatch contract."""
    os.makedirs(out_dir, exist_ok=True)
    portrait = os.path.join(out_dir, "face.png")
    visible_dir = reported_dir or out_dir
    report["saved_to"] = visible_dir
    report["portrait"] = os.path.join(visible_dir, "face.png")
    org.save(out_dir)
    _face.render(org, portrait)
    with open(os.path.join(out_dir, "hatch_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# The spore path (SPORE-DISTILLATION; formerly organs.reproduction.hatch_from_spore)
# ---------------------------------------------------------------------------

def hatch_from_spore(png_path: Optional[str] = None, *,
                     state: Optional[Dict[str, Any]] = None,
                     out_dir: Optional[str] = None,
                     warmup_beats: int = 3,
                     source_receipt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """SPORE-DISTILLATION: hatch a full organism FROM a spore.

    A germ-carrying spore incubates its germ directly (the complete build
    document). A bare v1 spore contributes the primer (identity, task ->
    truths). Either way the spore's conversation enters as memories (ingested
    as inferred), and entropy contributes the key (minted at birth, exactly as
    every birth). The spore is then sealed under the NEW body's key into
    `spore_vault` -- the midwife becomes SELF tissue -- and remains
    referenceable through organism.reproduction.

    Give either `png_path` (needs Pillow) or an already-decoded `state` dict."""
    from .organs.reproduction import (distill_germ, sporeagent_source_receipt,
                                      SPORE_BAND, spore_vault_band)
    raw: Optional[bytes] = None
    origin = "state"
    if state is None:
        if png_path is None:
            raise ValueError("hatch_from_spore needs png_path or state")
        from . import spore as _spore
        with open(png_path, "rb") as f:
            raw = f.read()
        state = _spore.read_spore(png_path)["state"]
        origin = "png"

    carried_germ = state.get("germ")
    if carried_germ is not None:
        germ = validate_germ(dict(carried_germ))
        # the sealed origin spore needs its band; carry-on germs rarely declare it
        genome = list(germ.get("genome", []))
        if not any(b.get("band") == SPORE_BAND for b in genome):
            germ = dict(germ, genome=genome + [spore_vault_band()])
    else:
        germ = distill_germ(state)

    result = incubate(germ, warmup_beats=warmup_beats)   # a BIRTH: faces the Stage-1 gate
    org = result["organism"]

    # the spore's memory enters honestly: through Senses, distilled as INFERRED
    conv = [e for e in (state.get("conversation") or []) if e.get("content")]
    if conv:
        from .ingestion import ingest
        ingest(org, [{"kind": "idea",
                      "text": "%s: %s" % (e.get("opcode") or e.get("role") or "TURN",
                                          e.get("content"))} for e in conv])

    # seal the spore as SELF tissue -- under the key the body MINTED at birth
    blob = raw if raw is not None else json.dumps(state, sort_keys=True,
                                                  default=str).encode("utf-8")
    rec = org.reproduction.store_spore(blob, {
        "spore_name": germ["identity"]["name"], "origin": origin})
    org.memory.remember("facts", {"origin_spore": germ["identity"]["name"],
                                  "sha256": rec["sha256"], "band": SPORE_BAND,
                                  "sealed": True, "chunks": rec["chunks"]},
                        opcode="OBSERVED", source="spore-distillation", verified=True)

    source = sporeagent_source_receipt(state, source_receipt)
    org.memory.remember("facts", {"sporeagent_source": source},
                        opcode="OBSERVED", source="sporeagent-lifecycle",
                        verified=source["certified"] and source["sealed"])

    receipt = {"spore": germ["identity"]["name"], "origin": origin,
               "germ_carried": carried_germ is not None,
               "certified": org.stage1_certified,
               "memories_ingested": len(conv),
               "spore_sealed": True, "spore_sha256": rec["sha256"],
               "key_derived_from_spore": False,          # THE KEY LAW, stated in the receipt
               "key_fingerprint": org.body.key_fingerprint,
               "primer_boundary": {
                   "spore_becomes": "PRIMER",
                   "body_key_owner": "BODY",
                   "mind_key_access": False,
                   "key_material_in_receipt": False,
                   "sealed": True,
               },
               "source": source}
    result["report"]["spore_distillation"] = receipt
    if out_dir:
        _persist_hatch(org, result["report"], out_dir)
    return {"organism": org, "report": result["report"], "receipt": receipt}


# ---------------------------------------------------------------------------
# The one birth command
# ---------------------------------------------------------------------------

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _is_spore(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(8) == _PNG_MAGIC
    except OSError:
        return path.lower().endswith(".png")


def hatch(path: str, out_dir: Optional[str] = None,
          warmup_beats: int = 3, *, authorization: Any = None) -> Dict[str, Any]:
    """The full ceremony, from either artifact:

      * a spore PNG  -> hatch_from_spore (germ aboard, or v1 distillation)
      * a germ JSON  -> load -> incubate -> persist + report + self-portrait
    """
    if not out_dir:
        raise HatchError("external hatch requires an explicit target directory")
    if authorization is None:
        raise HatchError("external hatch requires fresh target-bound operator authorization")
    from .lifecycle import (LifecycleAction, LifecycleAuthorizationError,
                            begin_transaction)
    try:
        transaction = begin_transaction(authorization, LifecycleAction.HATCH, path, out_dir)
    except (LifecycleAuthorizationError, FileExistsError) as exc:
        raise HatchError("activation refused: %s" % exc) from exc
    try:
        transaction.phase("incubating")
        if _is_spore(path):
            result = hatch_from_spore(path, warmup_beats=warmup_beats)
        else:
            germ = load_germ(path)
            result = incubate(germ, warmup_beats=warmup_beats)
        org, report = result["organism"], result["report"]
        if not org.stage1_certified:
            raise HatchError("Stage-1 gate did not certify the newborn Body")
        transaction.phase("persisting")
        report["lifecycle"] = {
            "result": "pass", "action": "hatch",
            "authorization": authorization.redacted(),
            "journal": os.path.join(os.path.abspath(out_dir), "lifecycle_journal.json"),
        }
        _persist_hatch(org, report, transaction.staging,
                       reported_dir=os.path.abspath(out_dir))
        required = ("organism.json", "body.json", "self_seal.json",
                    "hatch_report.json", "face.png")
        missing = [name for name in required
                   if not os.path.isfile(os.path.join(transaction.staging, name))]
        if missing:
            raise HatchError("staged hatch is incomplete: %s" % ", ".join(missing))
        transaction.phase("artifact_verified")
        transaction.promote()
        return {"organism": org, "report": report,
                **({"receipt": result["receipt"]} if "receipt" in result else {})}
    except Exception as exc:
        transaction.interrupt(type(exc).__name__)
        raise

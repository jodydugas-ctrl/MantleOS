#!/usr/bin/env python3
"""
mantle.cli  --  one command for the whole organism (Mantle OS)

    python -m mantle hatch <spore.png|germ.json> --out=DIR --auth=FILE
                                                    THE birth command: a germ spore (or
                                                      bare germ) -> certified AppAI
    python -m mantle teach [N]                      the Field Guide, RUNNING: each
                                                      chapter proves its claim live
    python -m mantle face <organism-dir> [out.png]  the organism paints its own state

  reproduction (two methods; everything else is a facet):
    python -m mantle reproduce                      the SEED vs GRAFT map, one screen
    python -m mantle spore create <png> "<name>" "<task>"   the smallest SEED: a whole
                                                      minimal agent in one PNG
    python -m mantle ghost selftest                 the cache-ghost substrate: a seed that
                                                      metabolises in the LLM prompt cache

  the gates and narrated tours:
    python -m mantle demo                           narrated Phase-1 life (no LLM)
    python -m mantle audit [--break-hash|--break-primer|--break-seal]
    python -m mantle prove                          the current security invariant suite
    python -m mantle mind                           narrated Phase-2 fusion (offline)
    python -m mantle audit-mind                     Stage-2 gate + Stage-1 regression
    python -m mantle assimilate <path> --dry-run    Path B read-only dissection
                                       --spore=out.png  ...and emit the host's germ spore
    python -m mantle check [--fast]                 EVERYTHING above that certifies, in
                                                      one command (the CI sequence, local)
"""
from __future__ import annotations

import json
import os
import sys

from .primer import appai_commandments, appai_truths

_USAGE = ("usage: python -m mantle "
          "[anchor <host> | ask <host> [--mind] <question> | feed <host> --credits=N "
          "[--key=NAME] | vitals <host> | hatch <spore.png|germ.json> --out=DIR --auth=FILE | "
          "teach [N] | "
          "face <dir> [out.png] | face-list <dir> | face-save <dir> <name> <src> [--default] | "
          "face-wear <dir> <name> | "
          "applet-create <dir> <source-dir> <name> [--entry=X] [--face=FILE] [--no-source] "
          "[--grow] | applet-list <dir> | applet-show <dir> <name> [--json] | "
          "applet-export <dir> <name> <dest> [--overwrite] | applet-wear <dir> <name> | "
          "applet-audit <dir> <name> | applet-clone <dir> <github-url>@<sha> <name> "
          "--allow-network | "
          "certify <nest> [--out=FILE] | reproduce | spore <op> ... | ghost <op> ... | "
          "demo | audit | prove | mind | audit-mind | "
          "check [--fast] | research-init/propose/trial/report/authorize/adopt | "
          "assimilate <path> [--dry-run] [--out=DIR] [--spore=out.png] | "
          "resident <nest> | lifecycle <authorize|status|resume|quarantine> ... | "
          "migrate-germ/migrate-resident/migrate-spore ... | rebind <host> ...]")

_COMMANDS = (
    "anchor", "ask", "feed", "vitals", "hatch", "graft", "spore", "ghost",
    "reproduce", "doctor", "teach", "face", "face-list", "face-save", "face-wear",
    "applet-create", "applet-list", "applet-show", "applet-export", "applet-wear",
    "applet-audit", "applet-clone", "demo", "audit", "prove", "mind", "audit-mind",
    "assimilate", "check", "certify", "research-init", "research-baseline",
    "research-propose", "research-trial", "research-report", "research-authorize",
    "research-adopt",
    "resident", "lifecycle", "migrate-germ", "migrate-resident", "migrate-spore",
    "rebind", "nest",
)

# every command answers to its hyphenated name and its underscore twin
_COMMAND_ALIASES = {name: name for name in _COMMANDS}
_COMMAND_ALIASES.update({name.replace("-", "_"): name
                         for name in _COMMANDS if "-" in name})


def known_commands(include_aliases: bool = False):
    """The canonical CLI command registry used by documentation/alignment audits."""
    if include_aliases:
        return sorted(_COMMAND_ALIASES)
    return sorted(set(_COMMAND_ALIASES.values()))


def _split(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a.split("=")[0]: (a.split("=", 1)[1] if "=" in a else True)
             for a in argv if a.startswith("--")}
    return args, flags


def cmd_anchor(argv):
    args, flags = _split(argv)
    if not args:
        print("usage: python -m mantle anchor <host-dir> [--credits=N] [--name=X]")
        return 2
    from .anchor import anchor, AnchorError
    print("=" * 74)
    print("MANTLE OS ANCHORING  ·  the merge ceremony  ·  host: %s" % args[0])
    print("=" * 74)
    try:
        result = anchor(args[0],
                        name=flags.get("--name") if isinstance(flags.get("--name"), str) else None,
                        starter_credits=float(flags.get("--credits", 5)))
    except AnchorError as e:
        print("\nANCHORING REFUSED: %s" % e)
        return 1
    r = result["report"]
    print("  resident      : %s" % r["resident"])
    print("  organ map     : %s" % r["organ_map"])
    print("  host files    : %d  -- unchanged: %s  (census-verified, byte for byte)"
          % (r["host_files"], r["host_unchanged"]))
    print("  certified     : %s  (the same Stage-1 gate every Body faces)" % r["certified"])
    print("  starter energy: %.1f credits" % r["starter_credits"])
    print("  nest          : %s" % r["nest"])
    print("\nANCHORED. The app has a resident now. Ask it things:")
    print("  python -m mantle ask %s \"how do I ...?\"" % args[0])
    return 0


def cmd_ask(argv):
    args, flags = _split(argv)
    if len(args) < 2:
        print("usage: python -m mantle ask <host-dir> [--mind] \"question\"")
        return 2
    from .anchor import ask, AnchorError
    try:
        result = ask(args[0], " ".join(args[1:]), use_mind=bool(flags.get("--mind")))
    except AnchorError as e:
        print(str(e)); return 1
    print(result["answer"])
    if result["thought"]:
        print("\n[the MIND adds]  %s" % result["thought"])
    print("\n(energy: %.1f credits · %s)" % (result["balance"], result["state"]))
    return 0


def cmd_feed(argv):
    args, flags = _split(argv)
    if not args or "--credits" not in flags:
        print("usage: python -m mantle feed <host-dir> --credits=N [--key=NAME]")
        return 2
    from .anchor import feed, AnchorError
    try:
        result = feed(args[0], float(flags["--credits"]),
                      key_name=flags.get("--key") if isinstance(flags.get("--key"), str) else None)
    except AnchorError as e:
        print(str(e)); return 1
    led = result["ledger"]
    print("fed. balance=%.1f credits (%s) · lifetime granted=%.1f · value delivered: %d record(s)"
          % (result["balance"], result["state"], led["granted"], len(led["value_records"])))
    return 0


def cmd_vitals(argv):
    args, _flags = _split(argv)
    if not args:
        print("usage: python -m mantle vitals <host-dir>")
        return 2
    from .anchor import vitals, AnchorError
    try:
        v = vitals(args[0])
    except AnchorError as e:
        print(str(e)); return 1
    led = v["ledger"]
    print("resident   : %s   (generation %d)" % (v["resident"], v["generation"]))
    print("vcw        : %d band(s)   verify=%s"
          % (v["band_count"], "ok" if v["verify_ok"] else "FAILED"))
    print("state      : %s   balance=%.1f / granted=%.1f credits   keys=%s"
          % (v["state"], led["balance"], led["granted"], led["keys"] or "none"))
    print("value      : %d record(s) of delivered work" % v["value_delivered"])
    print("immune log : %d event(s)" % v["immune_events"])
    if v["verify_errors"]:
        print("verify err : %s" % "; ".join(v["verify_errors"][:2]))
    print("portrait   : %s   (painted just now, by the resident)" % v["portrait"])
    return 0


def cmd_hatch(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a.split("=")[0]: (a.split("=", 1)[1] if "=" in a else True)
             for a in argv if a.startswith("--")}
    if not args:
        print("usage: python -m mantle hatch <spore.png|germ.json> --out=DIR --auth=FILE")
        return 2
    from .hatchery import hatch, HatchError
    print("=" * 74)
    print("MANTLE OS HATCHERY  ·  %s" % args[0])
    print("=" * 74)
    try:
        if not isinstance(flags.get("--out"), str) or not isinstance(flags.get("--auth"), str):
            print("\nTHE GERM DID NOT HATCH: --out and --auth are required for external activation")
            return 2
        from .lifecycle import load_authorization
        result = hatch(args[0], out_dir=flags.get("--out")
                       if isinstance(flags.get("--out"), str) else None,
                       authorization=load_authorization(str(flags["--auth"])))
    except (HatchError, RuntimeError, ValueError, OSError) as e:
        print("\nTHE GERM DID NOT HATCH: %s" % e)
        return 1
    rep = result["report"]
    for stage in rep["stages"]:
        for k, v in stage.items():
            print("  %-9s %s" % (k.upper(), v))
    print("\n  certified : %s  (the same Stage-1 gate every Body faces)" % rep["certified"])
    r = rep.get("spore_distillation")
    if r:
        print("  spore     : %s   (origin: %s, germ aboard: %s)"
              % (r["spore"], r["origin"], r["germ_carried"]))
        print("  memories  : %d conversation turn(s) ingested as INFERRED"
              % r["memories_ingested"])
        print("  sealed    : %s  (%s -> spore_vault, SELF tissue)"
              % (r["spore_sealed"], r["spore_sha256"][:23]))
        print("  key derived from spore : %s  (keys are MINTED, never derived)"
              % r["key_derived_from_spore"])
    if rep.get("saved_to"):
        print("  saved to  : %s" % rep["saved_to"])
        if rep.get("portrait"):
            print("  portrait  : %s   (the organism painted it itself)" % rep["portrait"])
    print("\nHATCHED. %s is alive, certified, and dormant -- ready for a MIND." % rep["germ"])
    return 0


def cmd_graft(argv):
    args, flags = _split(argv)
    if len(args) < 2:
        print("usage: python -m mantle graft <spore.png|germ.json> <host-dir> "
              "--workspace=DIR --auth=FILE [--allow-drift]")
        return 2
    from .graft import apply_artifact, GraftError, GraftDrift
    print("=" * 74)
    print("MANTLE OS GRAFT  ·  %s  ->  %s" % (args[0], args[1]))
    print("=" * 74)
    try:
        if not isinstance(flags.get("--workspace"), str) or not isinstance(flags.get("--auth"), str):
            print("\nGRAFT REFUSED: --workspace and --auth are required for external activation")
            return 2
        from .lifecycle import load_authorization
        result = apply_artifact(
            args[0], args[1], workspace=str(flags["--workspace"]),
            authorization=load_authorization(str(flags["--auth"])),
            allow_drift=bool(flags.get("--allow-drift")),
        )
    except GraftDrift as e:
        print("\nGRAFT DRIFT (the host moved): %s" % e)
        return 1
    except GraftError as e:
        print("\nGRAFT REFUSED: %s" % e)
        return 1
    r = result["report"]
    print("  resident           : %s" % r["graft"])
    print("  workspace          : %s" % r["workspace"])
    print("  original unchanged : %s  (census-verified, byte for byte)" % r["original_unchanged"])
    print("  extra bands        : %s" % (r["extra_bands"] or "none"))
    print("  hooks declared     : %d  (woven live with `weave()`)" % r["hooks"])
    print("  certified          : %s  (the same Stage-1 gate every Body faces)" % r["certified"])
    print("\nGRAFTED. The resident grew in the workspace; the original host was never touched.")
    return 0


def cmd_spore(argv):
    """The SPORE seed: the smallest reproductive form (mantle.spore)."""
    from . import spore
    if not argv:
        print("usage: python -m mantle spore <create|read|append|rename|verify|extract|demo> ...")
        print("       (the smallest SEED: one PNG that is a whole minimal agent)")
        return 2
    # spore.main dispatches on argv[1], so prepend a placeholder program name.
    return spore.main(["spore"] + list(argv))


def cmd_ghost(argv):
    """The cache-ghost substrate: a seed that metabolises in the LLM prompt cache (mantle.ghost)."""
    from . import ghost
    args, flags = _split(argv)
    sub = args[0] if args else "selftest"
    if sub == "selftest":
        return 0 if ghost.selftest() else 1
    if not args[1:]:
        print("usage: python -m mantle ghost <selftest | warm <png> | append <png> <role> "
              "\"<content>\" | hydrate <png> | status <png>>")
        return 2
    png = args[1]
    ttl = int(flags.get("--ttl", ghost.DEFAULT_TTL_S)) if isinstance(flags.get("--ttl"), str) else ghost.DEFAULT_TTL_S
    try:
        if sub == "warm":
            print(json.dumps(ghost.warm(png, ttl_s=ttl), indent=2))
        elif sub == "append":
            if len(args) < 4:
                print("usage: python -m mantle ghost append <png> <role> \"<content>\"")
                return 2
            print(json.dumps(ghost.append(png, args[2], args[3], ttl_s=ttl), indent=2))
        elif sub == "hydrate":
            h = ghost.hydrate(png)
            print("source=%s  rehydrated=%s  entries=%d"
                  % (h["source"], h["rehydrated"], len(h["body"].get("conversation", []))))
        elif sub == "status":
            print(json.dumps(ghost.status(png), indent=2))
        else:
            print("unknown ghost subcommand %r" % sub)
            return 2
    except ghost.GhostError as e:
        print("GHOST ERROR: %s" % e)
        return 1
    return 0


def cmd_reproduce(argv):
    """Print the two-method reproduction map (SEED vs GRAFT) -- the consolidation, one screen."""
    from . import reproduction as repro
    print("=" * 74)
    print("MANTLE OS REPRODUCTION  ·  two methods, ONE artifact: the spore")
    print("=" * 74)
    for method, spec in repro.describe().items():
        print("\n%-6s (%s)  --  %s" % (method.upper(), spec["kind"], spec["biology"]))
        for form, desc in spec["forms"].items():
            print("    %-10s %s" % (form, desc))
        print("    LAW: %s" % spec["law"])
    print("\nCall it:  from mantle import reproduction")
    print("          reproduction.seed('spore', ...)             # independent")
    print("          reproduction.graft('anchor'|'graft', ...)   # inside a host")
    return 0


def cmd_doctor(argv):
    args, _flags = _split(argv)
    if not args:
        print("usage: python -m mantle doctor <organism-dir>")
        return 2
    import json as _json
    import os as _os
    from .core.organism import Organism
    from . import doctor as _doc
    from . import paths
    target = args[0]
    if (not _os.path.isdir(target)
            or not _os.path.isfile(_os.path.join(target, "organism.json"))):
        print("DOCTOR REFUSED: no saved Mantle organism found at %s" % target)
        return 1
    try:
        org = Organism.load(target, verify_seals=True)
    except (_json.JSONDecodeError, KeyError, ValueError, PermissionError, OSError) as e:
        print("DOCTOR REFUSED: saved Mantle organism at %s could not be loaded: %s"
              % (target, e))
        return 1
    rep = _doc.checkup(org, repo_root=paths.REPO_ROOT)
    print("=" * 60)
    print("MANTLE OS DOCTOR  ·  %s" % target)
    print("=" * 60)
    for c in rep["checks"]:
        print("  [%s] %-16s %s" % ("OK" if c["ok"] else "XX", c["check"], c["detail"]))
    print("\n%s" % ("HEALTHY." if rep["ok"] else "PROBLEMS FOUND."))
    return 0 if rep["ok"] else 1


def cmd_face(argv):
    if not argv:
        print("usage: python -m mantle face <organism-dir> [out.png]")
        return 2
    from .core.organism import Organism
    from .face import render
    org = Organism.load(argv[0], verify_seals=True)
    out = argv[1] if len(argv) > 1 else "face.png"
    render(org, out)
    print("the organism painted its state: %s" % out)
    return 0


def cmd_face_list(argv):
    args, _flags = _split(argv)
    if not args:
        print("usage: python -m mantle face-list <organism-dir>")
        return 2
    from .core.organism import Organism
    from . import phenotype as ph
    org = Organism.load(args[0], verify_seals=True)
    faces = ph.list_faces(org)
    if not faces:
        print("(this organism carries no faces -- no phenotype band)")
        return 0
    print("worn  default  parts  name")
    for f in faces:
        print("  %s     %s       %3d   %s"
              % ("*" if f["worn"] else " ", "*" if f["default"] else " ",
                 f["parts"], f["name"]))
    return 0


def cmd_face_save(argv):
    args, flags = _split(argv)
    if len(args) < 3:
        print("usage: python -m mantle face-save <organism-dir> <name> <source-file> "
              "[--kind=html] [--entry=index.html] [--default]")
        return 2
    from .core.organism import Organism
    from . import phenotype as ph
    directory, name, source_file = args[0], args[1], args[2]
    with open(source_file, "r", encoding="utf-8") as f:
        source = f.read()
    org = Organism.load(directory, verify_seals=True)
    try:
        rec = ph.express(org, name, flags.get("--kind", "html"), source,
                         entry=flags.get("--entry", "") if isinstance(flags.get("--entry"), str) else "",
                         default=bool(flags.get("--default")))
    except ph.PhenotypeError as e:
        print("FACE NOT SAVED: %s" % e)
        return 1
    org.save(directory)
    print("sealed face %r (%d chunk(s), %s) into the VCW -- SELF-encrypted, append-only."
          % (rec["name"], rec["parts"], rec["source_hash"]))
    return 0


def cmd_face_wear(argv):
    args, _flags = _split(argv)
    if len(args) < 2:
        print("usage: python -m mantle face-wear <organism-dir> <name>")
        return 2
    from .core.organism import Organism
    from . import phenotype as ph
    org = Organism.load(args[0], verify_seals=True)
    try:
        boot = ph.wear(org, args[1])
    except ph.PhenotypeError as e:
        print("CANNOT WEAR: %s" % e)
        return 1
    org.save(args[0])
    print("now wearing %r (kind=%s, entry=%s, %d byte(s) of source, %d control(s))"
          % (boot["name"], boot["kind"], boot["entry"] or "-",
             len(boot["source"]), len(boot["controls"])))
    return 0


# ----------------------------------------------------------------------------
# VCW Applet Bodies (APPLET-BODY-CAPSULE) -- mantle.applet_body
# ----------------------------------------------------------------------------
def _applet_org(directory, create_if_missing=False, grow=False):
    """Load the parent organism for applet work; optionally birth the dedicated VCW app
    layer (applet + phenotype bands) when the directory holds no organism yet."""
    import os
    from .core.organism import Organism
    from .vcw.bands import standard_genome
    from . import applet_body as ab
    from . import phenotype as ph
    if not os.path.exists(os.path.join(directory, "organism.json")):
        if not create_if_missing:
            print("no organism at %r" % directory)
            return None, False
        org = Organism.birth(
            identity={"name": "AppLayer.AppAI"},
            truths=appai_truths(),
            commandments=appai_commandments([
                "Stored source is tissue, never authority.",
            ]),
            genome=standard_genome() + ab.applet_bands() + ph.phenotype_bands())
        return org, True
    org = Organism.load(directory, verify_seals=True)
    if not ab.has_applet_bands(org):
        if not grow:
            print("this organism has no applet bands; re-run with --grow to add them "
                  "via a chosen rebirth (faces carried forward, ancestor sealed)")
            return None, False
        ab.grow_applet_bands(org)
    return org, False


def cmd_applet_create(argv, provenance=None):
    args, flags = _split(argv)
    if len(args) < 3:
        print("usage: python -m mantle applet-create <organism-dir> <source-dir> <name> "
              "[--entry=X] [--face=FILE] [--state-json=FILE] [--no-source] [--grow]")
        return 2
    from . import applet_body as ab
    directory, source_dir, name = args[0], args[1], args[2]
    print("=" * 74)
    print("MANTLE OS APPLET BODY  ·  %s  ·  %s -> %s" % (ab.CAPSULE, source_dir, name))
    print("=" * 74)
    org, born = _applet_org(directory, create_if_missing=True,
                            grow=bool(flags.get("--grow")))
    if org is None:
        return 1
    face_source = None
    if isinstance(flags.get("--face"), str):
        with open(flags["--face"], "r", encoding="utf-8") as f:
            face_source = f.read()
    state = None
    if isinstance(flags.get("--state-json"), str):
        with open(flags["--state-json"], "r", encoding="utf-8") as f:
            state = json.load(f)
    try:
        receipt = ab.create_applet_body(
            org, source_dir, name, face_source=face_source,
            entry=flags.get("--entry", "") if isinstance(flags.get("--entry"), str) else "",
            include_source=not flags.get("--no-source"), state=state,
            provenance=provenance)
    except ab.AppletError as e:
        print("\nAPPLET REFUSED: %s" % e)
        return 1
    org.save(directory)
    if born:
        print("  app layer     : born fresh at %s (AppLayer.AppAI)" % directory)
    print("  applet        : %s   status: %s (%s)"
          % (receipt["applet"], receipt["status"], receipt["capsule"]))
    print("  source hash   : %s" % receipt["source_hash"])
    print("  files         : %d stored (%d chunk(s), %d skipped)"
          % (receipt["files"], receipt["chunks"], receipt["skipped"]))
    print("  organ roles   : %s" % (receipt["role_counts"] or "none"))
    print("  bands         : %s" % ", ".join(receipt["bands"]))
    print("  face          : %s   (from: %s)" % (receipt["face"], receipt["face_from"]))
    print("  export ready  : %s" % receipt["export_available"])
    if receipt["secret_suspects"]:
        print("  ! secret-suspect file(s) flagged to immune: %s"
              % receipt["secret_suspects"][:5])
    print("  stage1_ready  : %s  (a capsule is never labeled alive)"
          % receipt["stage1_ready"])
    print("\nRAISED. %s is stored as inert tissue -- not executable authority." % name)
    return 0


def cmd_applet_list(argv):
    args, _flags = _split(argv)
    if not args:
        print("usage: python -m mantle applet-list <organism-dir>")
        return 2
    org, _ = _applet_org(args[0])
    if org is None:
        return 1
    from . import applet_body as ab
    rows = ab.list_applet_bodies(org)
    if not rows:
        print("(no applet bodies in this VCW)")
        return 0
    print("status    files  export  name (face)")
    for r in rows:
        print("  %-8s %4d    %s     %s (%s)"
              % (r["status"], r["files"], "y" if r["export_available"] else "n",
                 r["applet"], r["face"]))
    return 0


def cmd_applet_show(argv):
    args, flags = _split(argv)
    if len(args) < 2:
        print("usage: python -m mantle applet-show <organism-dir> <name> [--json]")
        return 2
    org, _ = _applet_org(args[0])
    if org is None:
        return 1
    from . import applet_body as ab
    try:
        view = ab.show_applet_body(org, args[1])
    except ab.AppletError as e:
        print(str(e)); return 1
    if flags.get("--json"):
        print(json.dumps(view, indent=2, default=str))
        return 0
    m = view["manifest"]
    print("applet      : %s   status: %s (%s)" % (m["applet"], m["status"], m["capsule"]))
    print("source hash : %s" % m["source_hash"])
    print("files       : %d (%d byte(s)); skipped: %d"
          % (m["files"], m["bytes"], len(m["skipped"])))
    print("face        : %s (from: %s)" % (m["face"], m["face_from"]))
    print("provenance  : %s" % m["provenance"]["origin"])
    if view["organs"]:
        om = view["organs"]["organ_map"]
        print("organ roles : %s" % (om["role_counts"] or "none"))
        print("missing     : %s" % (om["missing_organs"] or "none"))
    print("state       : %s" % (view["state"] if view["state"] else "{}"))
    if view["last_audit"]:
        print("last audit  : %s" % ("PASS" if view["last_audit"]["ok"]
                                    else "FAIL %s" % view["last_audit"]["fails"]))
    print("source files (paths only -- export to download):")
    for f in view["source_files"][:40]:
        print("  %8s  %-10s %s" % (f["size"], f["lang"], f["path"]))
    if len(view["source_files"]) > 40:
        print("  ... and %d more" % (len(view["source_files"]) - 40))
    return 0


def cmd_applet_export(argv):
    args, flags = _split(argv)
    if len(args) < 3:
        print("usage: python -m mantle applet-export <organism-dir> <name> <dest-dir> "
              "[--overwrite]")
        return 2
    org, _ = _applet_org(args[0])
    if org is None:
        return 1
    from . import applet_body as ab
    try:
        receipt = ab.export_applet_source(org, args[1], args[2],
                                          overwrite=bool(flags.get("--overwrite")))
    except ab.AppletError as e:
        print(str(e)); return 1
    org.save(args[0])
    print("applet   : %s (%s)" % (receipt["applet"], receipt["capsule"]))
    print("dest     : %s" % receipt["destination"])
    print("written  : %d file(s)   hashes verified: %d/%d"
          % (len(receipt["files_written"]), receipt["hashes_verified"],
             receipt["files_total"]))
    if receipt["errors"]:
        print("errors   :")
        for e in receipt["errors"]:
            print("  ! %s" % e)
        return 1
    print("EXPORTED. Every byte hash-verified against the VCW record.")
    return 0


def cmd_applet_wear(argv):
    args, _flags = _split(argv)
    if len(args) < 2:
        print("usage: python -m mantle applet-wear <organism-dir> <name>")
        return 2
    org, _ = _applet_org(args[0])
    if org is None:
        return 1
    from . import applet_body as ab
    from . import phenotype as ph
    try:
        boot = ab.wear_applet_face(org, args[1])
    except (ab.AppletError, ph.PhenotypeError) as e:
        print("CANNOT WEAR: %s" % e)
        return 1
    org.save(args[0])
    print("now wearing %r (kind=%s, entry=%s, %d byte(s) of surface) -- a host renders "
          "this boot manifest; Mantle never executes it"
          % (boot["name"], boot["kind"], boot["entry"] or "-", len(boot["source"])))
    return 0


def cmd_applet_audit(argv):
    args, _flags = _split(argv)
    if len(args) < 2:
        print("usage: python -m mantle applet-audit <organism-dir> <name>")
        return 2
    org, _ = _applet_org(args[0])
    if org is None:
        return 1
    from . import applet_body as ab
    passed, rows = ab.audit_applet_body(org, args[1])
    org.save(args[0])
    print("=" * 74)
    print("MANTLE OS APPLET AUDIT  ·  %s  ·  %s" % (ab.CAPSULE, args[1]))
    print("=" * 74)
    width = max(len(r["check"]) for r in rows)
    for r in rows:
        print("  [%s] %-*s  %s" % ("PASS" if r["ok"] else "FAIL", width, r["check"],
                                   r["detail"]))
    print("\nRESULT: %s" % ("VALID APPLET-BODY-CAPSULE (capsule, not alive)" if passed
                            else "AUDIT FAILED"))
    return 0 if passed else 1


def cmd_applet_clone(argv):
    args, flags = _split(argv)
    if len(args) < 3:
        print("usage: python -m mantle applet-clone <organism-dir> "
              "<https-github-url>@<40-hex-commit> <name> --allow-network [--grow]")
        return 2
    import shutil
    import tempfile
    from . import applet_body as ab
    workdir = tempfile.mkdtemp(prefix="mantle-applet-")
    try:
        source = args[1]
        if "@" not in source:
            print("CLONE REFUSED: source must be <github-url>@<40-hex-commit>")
            return 1
        url, commit = source.rsplit("@", 1)
        try:
            acquisition = ab.clone_github(
                url, commit, workdir,
                allow_network=bool(flags.get("--allow-network")),
            )
        except ab.AppletError as e:
            print("CLONE REFUSED: %s" % e)
            return 1
        print("fetched %s@%s (detached; hooks/submodules disabled; no execution)"
              % (url, acquisition["commit"]))
        rc = cmd_applet_create(
            [args[0], acquisition["path"], args[2]]
            + [a for a in argv if a.startswith("--")],
            provenance={k: v for k, v in acquisition.items() if k != "path"},
        )
        return rc
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _cmd_teach(rest):
    from . import teach
    return teach.main(rest)


def _cmd_demo(rest):
    from . import demos
    return demos.demo(rest)


def _cmd_audit(rest):
    from .audits import stage1
    return stage1.main(rest)


def _cmd_prove(rest):
    from .audits import invariants
    return invariants.main(rest)


def _cmd_mind(rest):
    from . import demos
    return demos.mind_demo(rest)


def _cmd_audit_mind(rest):
    from .audits import stage2
    return stage2.main(rest)


def _cmd_assimilate(rest):
    from . import demos
    return demos.assimilate(rest)


def _cmd_check(rest):
    from . import check
    return check.main(rest)


def _cmd_certify(rest):
    args, flags = _split(rest)
    if len(args) != 1:
        print("usage: python -m mantle certify <nest> [--out=FILE]")
        return 2
    from .certify import CertificationError, certify_nest, write_certificate
    directory = args[0]
    out = flags.get("--out")
    if out is True or out is None:
        out = os.path.join(directory, "certification.json")
    try:
        receipt = certify_nest(directory)
        target = write_certificate(receipt, str(out))
    except CertificationError as exc:
        print("CERTIFICATION BLOCKED: %s" % exc)
        return 1
    print("APPLICATION CERTIFIED: %s" % receipt["subject"]["identity"])
    print("  target fingerprint : %s" % receipt["target"]["fingerprint"])
    print("  registry fingerprint: %s" % receipt["implementation"]["invariant_registry"])
    print("  receipt             : %s" % target)
    return 0


def cmd_resident(argv):
    """Run the canonical Body command/conversation loop for a saved resident."""
    args, _flags = _split(argv)
    if len(args) != 1:
        print("usage: python -m mantle resident <nest>")
        return 2
    from .core.organism import Organism
    from .resident.commands import BodyCommandDispatcher
    from .contracts import ResidentRuntime
    try:
        org = Organism.load(args[0], verify_seals=True)
    except Exception as exc:
        print("RESIDENT REFUSED: could not load nest: %s" % type(exc).__name__)
        return 1
    dispatcher = BodyCommandDispatcher(org)
    runtime = ResidentRuntime(dispatcher=dispatcher)
    print("Mantle resident protocol %s" % runtime.PROTOCOL_VERSION)
    print("Plain text enters conversation; slash commands are deterministic Body maintenance.")
    print("Use /help for commands; /quit closes the session.")
    while True:
        try:
            line = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() == "/exit":
            line = "/quit"
        if line.strip().lower() == "/key":
            import getpass
            secret = getpass.getpass("API key (hidden; blank cancels): ")
            result = dispatcher.dispatch("/key", secret_input=secret or None)
            print(result.message)
            continue
        try:
            result = runtime.turn(line)
            print(result.visible_output)
            if line.strip().lower() == "/quit":
                break
        except Exception as exc:
            print("Body fallback: conversation unavailable (%s)." % type(exc).__name__)
    return 0


def cmd_lifecycle(argv):
    """Operator-facing authorization and interrupted-stage inspection tools."""
    args, flags = _split(argv)
    if not args:
        print("usage: python -m mantle lifecycle <authorize|status|resume|quarantine> ...")
        return 2
    sub = args[0]
    if sub == "authorize":
        if len(args) != 4 or not isinstance(flags.get("--out"), str) or not flags.get("--approve"):
            print("usage: python -m mantle lifecycle authorize <hatch|graft> <artifact> "
                  "<exact-target> --approve --out=FILE")
            return 2
        from .lifecycle import (LifecycleAction, LifecycleAuthorization,
                                write_authorization)
        try:
            action = LifecycleAction(args[1])
            auth = LifecycleAuthorization.issue(action, args[2], args[3])
            target = write_authorization(auth, str(flags["--out"]))
        except (ValueError, OSError) as exc:
            print("AUTHORIZATION REFUSED: %s" % exc)
            return 1
        print("operator authorization written: %s" % target)
        print("artifact=%s target_hash=%s action=%s expires=%s" % (
            auth.artifact_sha256, auth.redacted()["target_id"], auth.action.value,
            auth.expires_at,
        ))
        return 0
    if sub == "status":
        if len(args) != 2:
            print("usage: python -m mantle lifecycle status <stage-or-target-dir>")
            return 2
        journal = os.path.join(os.path.abspath(args[1]), "lifecycle_journal.json")
        try:
            with open(journal, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
                print(json.dumps(payload, indent=2, sort_keys=True))
        except OSError as exc:
            print("LIFECYCLE STATUS UNAVAILABLE: %s" % exc)
            return 1
        result = str(payload.get("result", "fail")).lower()
        return 3 if result == "partial" else (0 if result == "pass" else 1)
    if sub == "resume":
        if len(args) != 2:
            print("usage: python -m mantle lifecycle resume <interrupted-stage-dir>")
            return 2
        from .lifecycle import LifecycleAuthorizationError, resume_transaction
        try:
            transaction = resume_transaction(args[1])
            target = transaction.promote()
        except (LifecycleAuthorizationError, FileExistsError, OSError) as exc:
            print("LIFECYCLE RESUME REFUSED: %s" % exc)
            return 1
        print(json.dumps({"result": "PASS", "target": target,
                          "source_stage_preserved": False}, sort_keys=True))
        return 0
    if sub == "quarantine":
        if len(args) != 2:
            print("usage: python -m mantle lifecycle quarantine <interrupted-stage-dir>")
            return 2
        import uuid
        stage = os.path.realpath(os.path.abspath(args[1]))
        if not os.path.basename(stage).startswith(".mantle-stage-"):
            print("QUARANTINE REFUSED: only a Mantle staging directory can be quarantined")
            return 1
        journal = os.path.join(stage, "lifecycle_journal.json")
        if not os.path.isfile(journal):
            print("QUARANTINE REFUSED: lifecycle journal missing")
            return 1
        target = os.path.join(os.path.dirname(stage),
                              ".mantle-quarantine-" + uuid.uuid4().hex)
        os.replace(stage, target)
        quarantined_journal = os.path.join(target, "lifecycle_journal.json")
        try:
            with open(quarantined_journal, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            payload["phase"] = "quarantined"
            payload["result"] = "REFUSED"
            from .core.persist import atomic_write_json
            atomic_write_json(quarantined_journal, payload)
        except (OSError, ValueError):
            # Quarantine already achieved its safety purpose.  The existing journal is
            # retained even when its terminal annotation cannot be updated.
            pass
        print(json.dumps({"result": "REFUSED", "quarantine": target}, sort_keys=True))
        return 0
    print("unknown lifecycle subcommand %r" % sub)
    return 2


def _cmd_migration(kind, argv):
    args, flags = _split(argv)
    if len(args) != 1 or not isinstance(flags.get("--out"), str):
        print("usage: python -m mantle migrate-%s <source> --out=<new-artifact>" % kind)
        return 2
    from .migration import migrate_germ, migrate_resident, migrate_spore
    operation = {"germ": migrate_germ, "resident": migrate_resident,
                 "spore": migrate_spore}[kind]
    try:
        result = operation(args[0], str(flags["--out"]))
    except (OSError, ValueError) as exc:
        print("MIGRATION REFUSED: %s" % exc)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_rebind(argv):
    args, flags = _split(argv)
    if len(args) != 1 or not flags.get("--preserve-old"):
        print("usage: python -m mantle rebind <host> --preserve-old [--certify] [--out=DIR]")
        return 2
    source = os.path.realpath(os.path.abspath(args[0]))
    out = flags.get("--out")
    if not isinstance(out, str):
        out = source.rstrip("/\\") + "-mantle2-rebound"
    from .certify import CertificationError
    from .migration import rebind
    try:
        result = rebind(source, out, certify=bool(flags.get("--certify")))
    except (OSError, ValueError, CertificationError) as exc:
        print("REBIND REFUSED: %s" % exc)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
# ---------------------------------------------------------------------------
# bounded research lifecycle (JSON-only operator/automation surface)
# ---------------------------------------------------------------------------
def _research_json(value):
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))


def _research_error(exc):
    _research_json({"status": "REFUSED", "error": str(exc), "automatic": False})
    return 1


def _research_root():
    return os.path.abspath(os.environ.get("MANTLE_RESEARCH_ROOT", os.getcwd()))


def _research_paths(protocol_path):
    protocol_path = os.path.abspath(protocol_path)
    return (protocol_path + ".ledger.vcw", protocol_path + ".proposals.jsonl")


def _load_research_protocol(path):
    from .research import load_protocol
    return load_protocol(path)


def _research_evaluator(protocol, root):
    if protocol.profile != "grimoire-dual-edition":
        raise ValueError("CLI profile %r is not implemented in the initial serial surface" %
                         protocol.profile)
    from .research.profiles.grimoire import GrimoireDualEditionEvaluator
    return GrimoireDualEditionEvaluator(root, protocol=protocol)


def _research_budget(protocol):
    from .research import ProcessBudget
    b = protocol.resource_budget
    return ProcessBudget(float(b.get("wall_seconds", 30)), int(b.get("cpu_seconds", 10)),
                         int(b.get("memory_bytes", 268435456)), int(b.get("output_bytes", 262144)),
                         int(b["file_count"]) if b.get("file_count") is not None else None)


def _research_ledger(protocol_path):
    from .core.body import Body
    from .research import ResearchLedger
    from .vcw.cube import Cube
    state_path, _ = _research_paths(protocol_path)
    body = Body()
    if os.path.exists(state_path):
        return body, ResearchLedger(body, Cube.load(state_path)), state_path
    return body, ResearchLedger.new(body), state_path


def _save_research_ledger(ledger, state_path):
    parent = os.path.dirname(state_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    ledger.cube.save(state_path)


def _cmd_research_init(rest):
    args, flags = _split(rest)
    if len(args) != 1:
        print("usage: python -m mantle research-init <profile> [--out=protocol.json]\n"
              "research does not self-adopt candidates")
        return 2
    from .research.profiles.grimoire import _default_protocol
    try:
        if args[0] != "grimoire-dual-edition":
            raise ValueError("unknown initial research profile %r" % args[0])
        protocol = _default_protocol()
        out = flags.get("--out")
        out = os.path.abspath("research-%s.json" % args[0]) if out in (None, True) else os.path.abspath(out)
        from .research import save_protocol
        save_protocol(protocol, out)
        _research_json(dict(protocol.to_dict(), path=out, digest=protocol.digest))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        return _research_error(exc)


def _cmd_research_baseline(rest):
    args, _flags = _split(rest)
    if len(args) != 1:
        print("usage: python -m mantle research-baseline <protocol.json>\n"
              "research does not self-adopt candidates")
        return 2
    try:
        path = os.path.abspath(args[0])
        protocol = _load_research_protocol(path)
        evaluation = _research_evaluator(protocol, _research_root()).baseline({"tree_hash": "baseline"})
        with open(path + ".baseline.json", "w", encoding="utf-8", newline="\n") as handle:
            json.dump(evaluation.to_dict(), handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        _research_json(evaluation.to_dict())
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        return _research_error(exc)


def _cmd_research_propose(rest):
    args, _flags = _split(rest)
    if len(args) != 2:
        print("usage: python -m mantle research-propose <protocol.json> <proposal.json>\n"
              "research does not self-adopt candidates")
        return 2
    try:
        protocol_path = os.path.abspath(args[0])
        protocol = _load_research_protocol(protocol_path)
        with open(args[1], encoding="utf-8") as handle:
            proposal = json.load(handle)
        if not isinstance(proposal, dict):
            raise ValueError("proposal must be a JSON object")
        if not proposal.get("experiment_id"):
            raise ValueError("proposal requires experiment_id")
        proposal_id = "proposal-" + __import__("hashlib").sha256(
            json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        record = {"proposal_id": proposal_id, "status": "PROPOSED", "author": "MIND",
                  "protocol_hash": protocol.digest, "proposal": proposal}
        _, proposals_path = _research_paths(protocol_path)
        with open(proposals_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        _research_json(record)
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return _research_error(exc)


def _find_research_proposal(protocol_path, proposal_id):
    _, proposals_path = _research_paths(protocol_path)
    if not os.path.exists(proposals_path):
        raise ValueError("proposal ledger does not exist")
    found = None
    with open(proposals_path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if row.get("proposal_id") == proposal_id:
                    found = row
    if found is None:
        raise ValueError("unknown proposal id %r" % proposal_id)
    return found["proposal"]


def _cmd_research_trial(rest):
    args, flags = _split(rest)
    if len(args) != 2:
        print("usage: python -m mantle research-trial <protocol.json> <proposal-id>\n"
              "research does not self-adopt candidates")
        return 2
    if "--network" in flags or "--allow-network" in flags:
        return _research_error(ValueError("research CLI has no network flag"))
    try:
        protocol_path = os.path.abspath(args[0])
        protocol = _load_research_protocol(protocol_path)
        proposal = _find_research_proposal(protocol_path, args[1])
        if proposal.get("network") or proposal.get("require_network_isolation"):
            raise ValueError("network is not available in the initial research CLI")
        from .research import (BoundedProcessRunner, CandidateChamber, ResearchGanglion,
                               SourceWorktreeAdapter)
        root = _research_root()
        paths = protocol.mutable_surface.get("paths", [])
        adapter = SourceWorktreeAdapter(root, allowlist=paths)
        body, ledger, state_path = _research_ledger(protocol_path)
        ganglion = ResearchGanglion(
            body=body, ledger=ledger, protocol=protocol,
            evaluator=_research_evaluator(protocol, root),
            chamber=CandidateChamber(adapter), runner=BoundedProcessRunner(
                allowed_env=set((proposal.get("env") or {}).keys())),
            budget=_research_budget(protocol), energy=lambda: float("inf"),
        )
        result = ganglion.pulse(proposal)
        _save_research_ledger(ledger, state_path)
        if result.get("artifact") is not None:
            artifact = result["artifact"]
            result["artifact"] = {"workspace": str(artifact.workspace),
                                   "tree_hash": artifact.tree_hash,
                                   "mutable_surface": artifact.mutable_surface}
        _research_json(result)
        return 0 if result.get("status") not in {"REFUSED", "CRASHED", "STOPPED", "INCONCLUSIVE"} else 1
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        return _research_error(exc)


def _cmd_research_report(rest):
    args, _flags = _split(rest)
    if len(args) != 1:
        print("usage: python -m mantle research-report <protocol.json> [--json]\n"
              "research does not self-adopt candidates")
        return 2
    try:
        protocol = _load_research_protocol(os.path.abspath(args[0]))
        _body, ledger, _state_path = _research_ledger(os.path.abspath(args[0]))
        _research_json({"protocol": protocol.to_dict(), "ledger": ledger.snapshot(),
                        "automatic_adoption": False})
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        return _research_error(exc)


def _operator_command(rest, *, adopt=False):
    args, flags = _split(rest)
    label = "research-adopt" if adopt else "research-authorize"
    if len(args) != 1 or not isinstance(flags.get("--operator-receipt"), str):
        print("usage: python -m mantle %s <experiment-id> --operator-receipt=receipt.json" % label)
        return 2
    try:
        with open(flags["--operator-receipt"], encoding="utf-8") as handle:
            receipt = json.load(handle)
        protocol_path = receipt.get("protocol")
        if not protocol_path:
            raise ValueError("operator receipt must name the protocol path")
        protocol_path = os.path.abspath(protocol_path)
        _load_research_protocol(protocol_path)
        _body, ledger, state_path = _research_ledger(protocol_path)
        event = ledger.adopt(args[0], receipt) if adopt else ledger.authorize(args[0], receipt)
        _save_research_ledger(ledger, state_path)
        _research_json({"status": event["status"], "experiment_id": args[0],
                        "automatic": False, "receipt_hash": event["receipt_hash"]})
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        return _research_error(exc)


def _cmd_nest(rest):
    """Route the additive ``nest <subcommand>`` family (remote GitHub NEST)."""
    from .nest.cli import main as nest_cli_main

    return nest_cli_main(rest)


_DISPATCH = {
    "anchor": cmd_anchor,
    "ask": cmd_ask,
    "feed": cmd_feed,
    "vitals": cmd_vitals,
    "hatch": cmd_hatch,
    "graft": cmd_graft,
    "spore": cmd_spore,
    "ghost": cmd_ghost,
    "reproduce": cmd_reproduce,
    "doctor": cmd_doctor,
    "teach": _cmd_teach,
    "face": cmd_face,
    "face-list": cmd_face_list,
    "face-save": cmd_face_save,
    "face-wear": cmd_face_wear,
    "applet-create": cmd_applet_create,
    "applet-list": cmd_applet_list,
    "applet-show": cmd_applet_show,
    "applet-export": cmd_applet_export,
    "applet-wear": cmd_applet_wear,
    "applet-audit": cmd_applet_audit,
    "applet-clone": cmd_applet_clone,
    # the narrated tours and the gates
    "demo": _cmd_demo,
    "audit": _cmd_audit,
    "prove": _cmd_prove,
    "mind": _cmd_mind,
    "audit-mind": _cmd_audit_mind,
    "assimilate": _cmd_assimilate,
    "check": _cmd_check,
    "certify": _cmd_certify,
    "resident": cmd_resident,
    "lifecycle": cmd_lifecycle,
    "migrate-germ": lambda rest: _cmd_migration("germ", rest),
    "migrate-resident": lambda rest: _cmd_migration("resident", rest),
    "migrate-spore": lambda rest: _cmd_migration("spore", rest),
    "rebind": cmd_rebind,
    "nest": _cmd_nest,
    "research-init": _cmd_research_init,
    "research-baseline": _cmd_research_baseline,
    "research-propose": _cmd_research_propose,
    "research-trial": _cmd_research_trial,
    "research-report": _cmd_research_report,
    "research-authorize": lambda rest: _operator_command(rest, adopt=False),
    "research-adopt": lambda rest: _operator_command(rest, adopt=True),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    raw_cmd = argv[0] if argv else "teach"
    if raw_cmd in ("-h", "--help", "help"):
        print(_USAGE)
        return 0
    cmd = _COMMAND_ALIASES.get(raw_cmd, raw_cmd)
    handler = _DISPATCH.get(cmd)
    if handler is not None:
        return handler(argv[1:])
    print(_USAGE)
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""Build a generic MantleOS Bio-Software Cartridge without using Raven."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import tempfile

from .cartridge import write_manifest, verify, pack
from .primer import create_lock
from .anchor_blueprint import validate_blueprint, render_runner_guide
from .birth import validate_birth, make_birth

ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,47}$")


def _json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _install_runtime_library(root: Path, *, minimal_metadata=False):
    """Embed the generic hosted transaction kernel in every generated Body.

    A Cartridge must not require the source checkout merely to run its PRIMER-first
    hosted bridge, so the small stdlib-only runtime subset travels with the Body.
    """
    source = Path(__file__).resolve().parent
    target = root / "runtime_lib" / "mantleos"
    target.mkdir(parents=True, exist_ok=True)
    for file in source.rglob('*.py'):
        rel = file.relative_to(source)
        if '__pycache__' in rel.parts: continue
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target / rel)
    # The optional parser still requires an explicitly pinned external Node and
    # compiler. Carry only MantleOS's trusted transport script in standalone Bodies.
    bridge = Path('scan/typescript_bridge.cjs')
    progressive = Path('progressive_runtime.js')
    shutil.copy2(source / progressive, target / progressive)
    shutil.copytree(source / 'app_assets', target / 'app_assets', dirs_exist_ok=True)
    # An Engram must carry the same construction tools it advertises in chat,
    # including the pinned first surface and progressive runtime, not only .py.
    for name in ('assets', 'resources'):
        shutil.copytree(source / 'kpp' / name, target / 'kpp' / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    (target / bridge).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / bridge, target / bridge)
    # Pinned Anchor reference source is data and template assets as well as Python.
    # A standalone Cartridge must carry them with its execution kernel.
    engine = source / 'anchor_engine'
    for sub in ('templates', 'profiles', 'reference_materials'):
        src = engine / sub
        if src.is_dir():
            shutil.copytree(src, target / 'anchor_engine' / sub, dirs_exist_ok=True)
    shutil.copy2(engine / 'SOURCE-PINS.json', target / 'anchor_engine' / 'SOURCE-PINS.json')
    if minimal_metadata:
        catalog = json.loads((target / 'anchor_engine/SOURCE-PINS.json').read_text('utf-8'))
        catalog.pop('source', None)
        _json(target / 'anchor_engine/SOURCE-PINS.json', catalog)
    profiles = source / 'agentic_profiles'
    if profiles.is_dir():
        shutil.copytree(profiles, target / 'agentic_profiles', dirs_exist_ok=True)
    notices = source / 'notices'
    if notices.is_dir():
        shutil.copytree(notices, target / 'notices', dirs_exist_ok=True)
    shutil.copy2(source / "body_entrypoint.py", root / "runtime.py")
    (root / "runtime.py").chmod(0o755)



def _systems():
    from .organs import registry
    groups = {name: {'id':'system.'+name,'kind':name,'version':1,'interfaces':[]}
              for name in ('neural','memory','immune','metabolism','expression')}
    for item in registry(Path('.'),constructing=True).catalog():
        name=item['name']
        system = ('neural' if name.startswith(('context.','anchor.')) else
                  'memory' if name.startswith(('memory.','engram.')) else
                  'metabolism' if name.startswith(('scan.','project.')) else
                  'expression' if name in {'body.save','cartridge.builder'} else 'immune')
        groups[system]['interfaces'].append({'name':name,'effect':item['effect'],
            'authority':item['authority'],'provider':item['provider_id'],'binding':'BOUND','replaceable':False})
    for name, system, effect, authority in (
        ('language.generate','neural','COMPUTE',None),('publication.release','immune','PUBLISH','release')):
        groups[system]['interfaces'].append({'name':name,'effect':effect,'authority':authority,
            'provider':'host-bound','binding':'HOST_BOUND','replaceable':True})
    for name in ('skin.status','skin.taste'):
        groups['immune']['interfaces'].append({'name':name,'effect':'READ','authority':None,
            'provider':'unbound','binding':'UNAVAILABLE','replaceable':False,'reason':'Integrity-only dependency-free core'})
    return {'schema':'cell.systems/2','binding_states':['BOUND','HOST_BOUND','UNAVAILABLE'],
            'systems':list(groups.values())}


def _systems_from_blueprint(blueprint):
    """Merge project-specific interfaces into the five stable Body systems."""
    registry = _systems()
    by_id = {system["id"]: system for system in registry["systems"]}
    existing = {interface["name"] for system in registry["systems"] for interface in system["interfaces"]}
    for contract in blueprint.get("systems", []):
        target = by_id[contract["id"]]
        for interface in contract["interfaces"]:
            if interface["name"] in existing:
                raise ValueError(f"Blueprint interface collides with built-in Body interface: {interface['name']}")
            target["interfaces"].append({
                "name": interface["name"],
                "effect": interface["effect"],
                "authority": interface["authority"],
                "provider": "host-bound", "binding": "HOST_BOUND", "declared_provider": interface["provider"],
                "replaceable": True,
                "description": interface["usage"],
                "blueprint_contract": {
                    "input": interface["input"],
                    "output": interface["output"],
                    "verification": interface["verification"],
                },
            })
            existing.add(interface["name"])
    return registry


def _new_anchor_register(bio_id):
    from .anchor_language import default_register
    return default_register(bio_id)


def _anchor_code():
    # Refined Anchor Coding is now the default across all Bio-Applications.
    from .anchor_language import communication_spec
    return communication_spec()



def _cognition_seed():
    return {
        "schema":"mantle.cognition-seed/1","language":"mantle-cognition/1",
        "purpose":"Substrate-neutral consequential cognitive state, not hidden chain-of-thought.",
        "record_kinds":["PERCEPT","BELIEF","UNKNOWN","NEUTRAL","ATTRACTOR","REPULSOR","GOAL","OPTION","PREDICTION","INTENT","OBSERVATION","DELTA","REVISION","MEMORY"],
        "statuses":["observed","held","tentative","unknown","active","candidate","selected","resolved","rejected","proposed"],
        "relations":["supports","contradicts","derives_from","targets","predicts","approaches","avoids","depends_on","revises","observes"],
        "modes":["FAST","TARGETED","DEEP"],
        "principles":[
            "Consequential semantic state is explicit and bounded.",
            "Unknown remains unknown; confidence is not evidence.",
            "MEMORY is a proposal until the Body admits it.",
            "ORIENT does not select final INTENT; RESPOND binds exact orientation and any checked observation before publication."
        ]
    }



def _validate_binding(birth: dict, anchor_blueprint: dict | None):
    b = validate_birth(birth)
    if anchor_blueprint is None:
        if b["blueprint"] is not None:
            raise ValueError("Birth contract is bound to an Anchor Blueprint but no Blueprint was supplied")
        return b, None
    bp = validate_blueprint(anchor_blueprint, require_ready=True)
    expected = {"schema": bp["schema"], "id": bp["id"], "sha256": bp["blueprint_sha256"]}
    if b["blueprint"] != expected:
        raise ValueError("Bio-Software birth contract does not match the supplied Anchor Blueprint binding")
    return b, bp


def _build_birth(birth: dict, output: str | Path, *, cartridge_id=None, anchor_blueprint=None):
    t, bp = _validate_binding(birth, anchor_blueprint)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Output already exists")
    cid = cartridge_id or t["id"] + "-cartridge"
    if not ID_RE.fullmatch(cid):
        raise ValueError("Invalid cartridge id")
    systems_registry = _systems_from_blueprint(bp) if bp else _systems()
    with tempfile.TemporaryDirectory(prefix="mantle-build-") as td:
        root = Path(td) / "body"; root.mkdir()
        (root / "PRIMER").mkdir()
        (root / "PRIMER/PERSONA.md").write_text(t["primer"]["persona"].strip() + "\n", encoding="utf-8")
        (root / "PRIMER/COMMANDMENTS.md").write_text(t["primer"]["commandments"].strip() + "\n", encoding="utf-8")
        create_lock(root)
        birth_value = {k: deepcopy(v) for k, v in t.items() if k != "birth_sha256"}
        cartridge = {
            "schema":"mantle.cartridge/1","format":"vcw/1","kind":"portable-bio-software-body",
            "cartridge_id":cid,
            "anatomy":{"file":"ANATOMY.json","schema":"mantle.anatomy/1","anatomy_id":cid+".anatomy"},
            "bio_software":{"file":"BIO-SOFTWARE.json","schema":"bio-software/3","id":t["id"]},
            "birth":{"file":"BIRTH.json","schema":"mantle.bio-software-birth/1","sha256":t["birth_sha256"]},
            "primer":{"lock":"PRIMER/PRIMER.lock.json","persona":"PRIMER/PERSONA.md","commandments":"PRIMER/COMMANDMENTS.md","birth_locked":True},
            "continuity":{"file":"ENGRAM.jsonl","role":"canonical-append-only-continuity" if t["kind"]=="engram" else "optional-continuity"},
            "manifest":"MANIFEST.json",
            "distribution":deepcopy(t["distribution"]),
            "lineage":{"generation":0,"parent":None,"birth":"explicit-bio-software-birth"},
            "construction":{"builder_interface":"cartridge.builder","explicit_invocation_required":True,"verification_required":True,"autonomous_replication":False},
            "nest":{"key_portable":False,"mind_key_access":False,"role":"external-non-portable-body-state"}
        }
        if bp:
            cartridge["anchor_blueprint"] = {"file":"ANCHOR-BLUEPRINT.json","schema":"anchor.blueprint/3","runner_guide":"RUNNER-GUIDE.md","sha256":bp["blueprint_sha256"]}
            cartridge["lineage"]["birth"] = "bio-software-birth+anchor-blueprint"
            cartridge["lineage"]["source"] = bp["source"]
        cell = {
            "schema":"mantle.anatomy/1","kind":"cartridge-anatomy","anatomy_id":cid+".anatomy",
            "bio_software":{"file":"BIO-SOFTWARE.json","schema":"bio-software/3","id":t["id"]},
            "birth":{"file":"BIRTH.json","schema":"mantle.bio-software-birth/1"},
            "anchor_code":{"file":"ANCHOR-CODE.json","schema":"mantle.anchor-communication/1","register":"ANCHOR-REGISTER.json"},
            "systems":{"file":"SYSTEMS.json","schema":"cell.systems/2"},
            "runtime":{"entrypoint":"python runtime.py","host_language":"python-stdlib"}
        }
        if bp:
            cell["anchor_blueprint"] = {"file":"ANCHOR-BLUEPRINT.json","schema":"anchor.blueprint/3","runner_guide":"RUNNER-GUIDE.md"}
        bio = {
            "schema":"bio-software/3","id":t["id"],"name":t["name"],
            "kind":t["kind"],"description":t["description"],
            "birth_contract":{"file":"BIRTH.json","schema":"mantle.bio-software-birth/1","sha256":t["birth_sha256"]},
            "persona":{"name":t["primer"]["persona_name"],"source":"PRIMER/PERSONA.md","birth_locked":True},
            "primer":{"commandments":"PRIMER/COMMANDMENTS.md","persona":"PRIMER/PERSONA.md","load_first":True},
            "continuity_source":"ENGRAM.jsonl",
            "default_language":"anchor.coding.conversation/1.1",
            "anchor_register":"ANCHOR-REGISTER.json",
            "required_systems":["system.neural","system.memory","system.immune","system.metabolism","system.expression"],
            "construction":{"may_request_cartridge_builder":True,"autonomous_spawn":False,"child_requires_verification":True}
        }
        if bp:
            bio["anchor_blueprint"] = {"file":"ANCHOR-BLUEPRINT.json","schema":"anchor.blueprint/3","id":bp["id"],"sha256":bp["blueprint_sha256"]}
            bio["source_lineage"] = bp["source"]
        state = {
            "schema":"mantle.body-state/1","body_form":"mantle.cartridge/1","cartridge_file":"CARTRIDGE.json",
            "cell_role":"internal-anatomy","continuity_file":"ENGRAM.jsonl","continuity_location":"CARTRIDGE",
            "birth_contract_file":"BIRTH.json","primer_lock":"PRIMER/PRIMER.lock.json","persona_file":"PRIMER/PERSONA.md","system_registry_file":"SYSTEMS.json",
            "distribution":deepcopy(t["distribution"]),"status":"BLANK_BIRTH_VERIFIED","communication_language":"anchor.coding.conversation/1.1"
        }
        if bp:
            state["anchor_blueprint_file"] = "ANCHOR-BLUEPRINT.json"
        if 'version' in t:
            for declaration in (cartridge, cell, bio):
                declaration['version'] = t['version']
        for name, value in [("CARTRIDGE.json",cartridge),("ANATOMY.json",cell),("BIO-SOFTWARE.json",bio),("BIRTH.json",birth_value),("BODY-STATE.json",state),("SYSTEMS.json",systems_registry),("ANCHOR-CODE.json",_anchor_code()),("ANCHOR-REGISTER.json",_new_anchor_register(t["id"])),("COGNITIVE-SEED.json",_cognition_seed())]:
            _json(root/name,value)
        if bp:
            _json(root/"ANCHOR-BLUEPRINT.json", anchor_blueprint)
            (root/"RUNNER-GUIDE.md").write_text(render_runner_guide(anchor_blueprint), encoding="utf-8")
        (root/"ENGRAM.jsonl").write_bytes(b"")
        _install_runtime_library(root, minimal_metadata='version' not in t)
        start = f"# {t['name']} Body\n\nThis is a MantleOS Cartridge Body for Bio-Software `{t['id']}` using Persona `{t['primer']['persona_name']}`. The PRIMER is birth-locked and loads before ordinary encounter context.\n\n`BIRTH.json` is the canonical Bio-Software birth contract. It is separate from project semantics.\n"
        if bp:
            start += "\n`ANCHOR-BLUEPRINT.json` describes the source/project semantics only; it does not define Persona, PRIMER, continuity, or Bio-Software identity. `RUNNER-GUIDE.md` is its cold-start rendering.\n"
        if t["distribution"]["role"] == "reference":
            start += "\n**Reference specimen:** this Body is immutable distribution material. Clone/construct an operational descendant before use.\n"
        start += "\n**Bio-Application language: Anchor Coding v1.1.** `ANCHOR-CODE.json` declares the current protocol, and `ANCHOR-REGISTER.json` carries the revisioned Neutral Rule Economy Anchor. `anchor.blueprint/3` applies the same immutable Anchors to project attributes. Only current schemas and pinned executable profiles are supported.\n"
        start += "\nThe Body carries the stdlib-only generic hosted transaction kernel. The external model must return the typed ORIENT/RESPOND JSON contracts; it does not need MantleOS installed.\n\n```bash\npython runtime.py status\npython runtime.py primer\npython runtime.py bridge-open --model-id <model> --request-id <id> --user \"hello\"\n```\n\nSee `HOSTED-BRIDGE.md` for the three-stage external-model protocol.\n"
        from .checkpoint import mount_contract
        (root/"HOSTED-BRIDGE.md").write_text(
            "# Hosted bridge\n\n"+
            mount_contract()+"\n\n"+
            "This Cartridge includes a provider-neutral `bridge-open -> bridge-advance -> bridge-commit` runtime. "
            "PRIMER content is first in every frame. ORIENT cannot select final intent. A requested action is executed only through the checked-effect authority gate. RESPOND receives the exact ORIENT and exact action observation. Publication requires an explicit release grant and only the committed reply may be released.\n\n"
            "The model returns `mantle.orientation/1` at ORIENT and `mantle.response-proposal/1` at RESPOND. "
            "Use `--allow-effect` only on the advance call when granting `effect.execute`; use `--allow-release` only on commit when granting publication. Preparations are hash-bound and stale Engram heads are rejected.\n\n"
            "App requests default to one self-contained .anchor app document: APP_LAUNCH_ONLY header, exact native program/primer/state, an Anchor-encoded standalone bridge and HTML/Python targets compiled at authoring time. The receiver uses the supplied bootstrap and materializes the prepared app, then opens an actual available Canvas or interactive HTML preview before tests or unrelated framework experiments. No receiver compiler design, model-driven translation, installation, lookup or separate guide is needed. Python is an optional loader; the Python target is a command engine, not a GUI. Notepad retains pinned NOTEPAD_LLM semantics; literal apps retain EMIT_TEXT. `anchor-code app notepad` returns the document. `anchor-code launch <file.anchor> --output <outside.html> --permit-effect` materializes its exact target. A host may bind the existing checked Canvas bridge. Host tools and permissions govern actual opening; local checks do not qualify cross-model compliance.\n",
            encoding="utf-8",
        )
        (root/"START-HERE.md").write_text(start,encoding="utf-8")
        write_manifest(root)
        verify(root)
        if output.suffix.lower() in {".vcw", ".zip"}:
            return pack(root, output)
        shutil.copytree(root, output)
        return {"output":str(output), **verify(output)}


def build(specification: dict, output: str | Path, *, cartridge_id=None, blueprint: dict | None = None):
    """Build Bio-Software from an explicit birth contract, optionally bound to project semantics.

    Anchor Blueprints never define Persona/PRIMER or Bio-Software identity. Supplying a
    Blueprint directly is therefore rejected; pair it with mantle.bio-software-birth/1.
    Only the current explicit birth contract is accepted.
    """
    if not isinstance(specification, dict):
        raise ValueError("Build specification must be an object")
    schema = specification.get("schema")
    if schema == "mantle.bio-software-birth/1":
        return _build_birth(specification, output, cartridge_id=cartridge_id, anchor_blueprint=blueprint)
    if schema == "anchor.blueprint/3":
        raise ValueError("Anchor Blueprint describes project semantics only; supply a mantle.bio-software-birth/1 contract and pass the Blueprint separately")
    raise ValueError(f"Unsupported build specification schema: {schema!r}")

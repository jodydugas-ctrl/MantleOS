"""Small, deterministic KPP contracts. No LLM or external service required."""
import hashlib
import json
import re
from pathlib import Path

SLUG = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
SUPPORTED_RECIPE = "kpp.recipe/3"
SUPPORTED_RECIPES = (SUPPORTED_RECIPE, "kpp.recipe/4")
SUPPORTED_INGREDIENT = "kpp.ingredient/1"
REPOSITORY_SOURCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")

class KPPError(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def validate_repository_source(source):
    """Validate an advisory, repo-relative source locator without opening files."""
    if not isinstance(source, dict) or set(source) != {"kind", "repository", "paths"}:
        raise KPPError("Invalid repository-files source declaration")
    if source.get("kind") != "repository-files":
        raise KPPError("Unsupported repository source kind")
    repository = source.get("repository")
    if not isinstance(repository, str) or not REPOSITORY_SOURCE_RE.fullmatch(repository):
        raise KPPError("Invalid repository source identity")
    paths = source.get("paths")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 16:
        raise KPPError("Repository source needs 1..16 paths")
    normalized = []
    windows_reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                        *(f"lpt{i}" for i in range(1, 10))}
    for path in paths:
        if (not isinstance(path, str) or not path or len(path) > 240 or
                "\\" in path or path.startswith("/") or
                any(ord(character) < 32 for character in path)):
            raise KPPError("Invalid repository source path")
        parts = path.split("/")
        if any(part in ("", ".", "..") or len(part) > 100 or
               not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part.endswith(".") or
               part.split(".", 1)[0].lower() in windows_reserved
               for part in parts):
            raise KPPError("Unsafe repository source path: " + path)
        normalized.append(path)
    if len(normalized) != len(set(normalized)):
        raise KPPError("Duplicate repository source path")
    return {"kind": "repository-files", "repository": repository, "paths": normalized}


def parse_json(content):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise KPPError("Duplicate JSON field: "+key)
            result[key]=value
        return result
    def invalid_number(value):raise KPPError("Non-finite JSON number: "+value)
    return json.loads(content,object_pairs_hook=unique,parse_constant=invalid_number)

def read_json(path):
    with open(path, "r", encoding="utf-8") as fp:return parse_json(fp.read())


def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True,allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(p)


def validate_recipe(recipe):
    if not isinstance(recipe, dict) or recipe.get("schema") not in SUPPORTED_RECIPES:
        raise KPPError("Unsupported recipe schema")
    if not isinstance(recipe.get("id"), str) or not SLUG.fullmatch(recipe["id"]):
        raise KPPError("Invalid recipe id")
    if not isinstance(recipe.get("goal"), str) or not recipe["goal"].strip():
        raise KPPError("Recipe needs goal")
    if recipe.get("tissue") not in ("anchor", "python", "javascript", "mixed", "unspecified"):
        raise KPPError("Unsupported tissue")
    from .language import validate_implementation
    validate_implementation(recipe)
    from .construction import construction_plan
    construction_plan(recipe)
    if not isinstance(recipe.get("fidelity"), int) or type(recipe["fidelity"]) is not int or not 1 <= recipe["fidelity"] <= 32:
        raise KPPError("Fidelity must be integer in 1..32")
    if recipe.get("mode") not in ("composition", "chase", "hybrid", "transformation"):
        raise KPPError("Invalid baking mode")
    if not isinstance(recipe.get("target"), dict) or not recipe["target"].get("description"):
        raise KPPError("Recipe needs described target")
    if not isinstance(recipe.get("ingredients"), list) or not all(isinstance(x,str) and SLUG.fullmatch(x) for x in recipe["ingredients"]):
        raise KPPError("Invalid ingredient identifiers")
    if len(recipe["ingredients"]) != len(set(recipe["ingredients"])):
        raise KPPError("Duplicate ingredients")
    # Product identity, construction method, and delivery are independent.
    kind = recipe.get("product_kind")
    if kind not in ("biosoftware", "bioagent", "appai", "conventional"):
        raise KPPError("Invalid product_kind")
    capabilities = recipe.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) - {"agent", "mind", "mantleos_splice"} or any(
            type(value) is not bool for value in capabilities.values()):
        raise KPPError("Invalid capabilities: use explicit booleans")
    if kind == "appai" and capabilities.get("mantleos_splice") is not True:
        raise KPPError("AppAI requires an explicit MantleOS splice")
    if kind == "bioagent" and capabilities.get("agent") is not True:
        raise KPPError("BioAgent requires explicit agent capability")
    delivery = recipe.get("delivery_mode")
    if delivery not in ("artifact", "progressive-web"):
        raise KPPError("Unsupported delivery_mode")
    preview = recipe.get("preview")
    if (delivery == "progressive-web") != (preview is not None):
        raise KPPError("Progressive-web delivery requires an explicit preview contract")
    if preview is not None:
        if recipe["tissue"] not in ("javascript", "mixed"):
            raise KPPError("Progressive-web requires javascript or mixed tissue")
        if not isinstance(preview, dict) or set(preview) != {"kind", "assets", "state_profile"} or preview["kind"] != "progressive-web":
            raise KPPError("Invalid progressive preview contract")
        if preview["state_profile"] != "json-body/1":
            raise KPPError("Unsupported preview state profile")
        assets = preview["assets"]
        if not isinstance(assets, dict) or set(assets) != {"index.html", "base.js", "style.css"}:
            raise KPPError("Preview assets must be index.html, base.js and style.css")
        for name, source in assets.items():
            if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
                raise KPPError("Preview asset needs source path and SHA-256 pin: " + name)
            path, checksum = source["path"], source["sha256"]
            if not isinstance(path, str) or not re.fullmatch(r"previews/[a-zA-Z0-9_./-]+", path) or \
                    ".." in Path(path).parts or Path(path).is_absolute():
                raise KPPError("Invalid preview source path")
            if not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum):
                raise KPPError("Invalid preview source SHA-256 pin")
    transform = recipe.get("transformation")
    if transform is not None:
        if not isinstance(transform, dict) or not isinstance(transform.get("preserve"), list) or not isinstance(transform.get("may_change"), list):
            raise KPPError("Transformation needs preserve and may_change lists")
        for key in ("preserve", "may_change"):
            if not all(isinstance(x, str) and x.strip() for x in transform[key]):
                raise KPPError("Invalid transformation property")
        if (len(set(transform["preserve"]))!=len(transform["preserve"]) or
                len(set(transform["may_change"]))!=len(transform["may_change"])):
            raise KPPError("Duplicate transformation properties")
        if set(transform["preserve"]) & set(transform["may_change"]):
            raise KPPError("A preserved property cannot also be marked changeable")
    anchors = recipe.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        raise KPPError("Recipe needs at least one acceptance anchor")
    ids = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise KPPError("Anchor must be an object")
        aid = anchor.get("id")
        if not isinstance(aid, str) or not SLUG.fullmatch(aid) or aid in ids:
            raise KPPError("Invalid or duplicate anchor id")
        ids.add(aid)
        if not isinstance(anchor.get("statement"), str) or not anchor["statement"].strip():
            raise KPPError("Anchor needs statement")
        if type(anchor.get("depth")) is not int or not 1 <= anchor["depth"] <= 32:
            raise KPPError("Anchor needs positive depth <= 32")
        if not isinstance(anchor.get("test"), str) or not anchor["test"].strip():
            raise KPPError("Anchor needs measurable acceptance test")
        if anchor.get("required") is not True and anchor.get("required") is not False:
            raise KPPError("Anchor required must be boolean")
        if not isinstance(anchor.get("depends", []), list):
            raise KPPError("Anchor dependencies must be list")
    for a in anchors:
        if any(dep not in ids or dep == a["id"] for dep in a.get("depends",[])):
            raise KPPError("Unknown/self anchor dependency")
    # Preservation obligations live ON their existing mandatory acceptance Anchors.
    # Avoid a duplicate transformation->coverage map that could diverge.
    preserved = transform.get("preserve", []) if transform else []
    for anchor in anchors:
        props = anchor.get("preserves", [])
        if not isinstance(props, list) or any(not isinstance(prop,str) for prop in props) or \
                len(props) != len(set(props)) or any(prop not in preserved for prop in props):
            raise KPPError("Anchor preserves must reference distinct declared transformation properties")
        if props and not anchor["required"]:
            raise KPPError("Only mandatory Anchors can guarantee preservation")
    for prop in preserved:
        if not any(a["required"] and prop in a.get("preserves", []) for a in anchors):
            raise KPPError("Preserved property missing mandatory Anchor coverage: " + prop)
    # Reflexes are recipe-declared edges in the SAME Functional Graph, not a
    # separate registry or execution engine. A declaration is not verification.
    reflexes = recipe.get("reflexes", [])
    if not isinstance(reflexes, list) or len(reflexes) > 32:
        raise KPPError("Invalid reflex declarations")
    reflex_ids = set()
    for ref in reflexes:
        if not isinstance(ref, dict) or set(ref) != {"id", "source", "ingredient", "timing", "anchors"}:
            raise KPPError("Reflex needs id, source, ingredient, timing and anchors")
        rid, source = ref["id"], ref["source"]
        if not isinstance(rid, str) or not SLUG.fullmatch(rid) or rid in reflex_ids:
            raise KPPError("Duplicate/invalid reflex id")
        reflex_ids.add(rid)
        if not isinstance(source, str) or not re.fullmatch(r"[a-zA-Z0-9_./-]+::[a-zA-Z_][a-zA-Z0-9_]*", source) or Path(source.split("::")[0]).is_absolute() or ".." in Path(source.split("::")[0]).parts:
            raise KPPError("Invalid reflex source hint")
        if ref["ingredient"] not in recipe["ingredients"] or ref["timing"] not in ("after-success", "before-call", "on-error"):
            raise KPPError("Invalid reflex ingredient/timing")
        links = ref["anchors"]
        mandatory = {a["id"] for a in anchors if a["required"]}
        if not isinstance(links, list) or not links or len(set(links)) != len(links) or not all(isinstance(x, str) and x in mandatory for x in links):
            raise KPPError("Reflex links must reference mandatory Anchors")
    edges={a["id"]:a.get("depends",[]) for a in anchors}
    visited=set()
    def visit(node, visiting):
        if node in visiting: raise KPPError("Cyclic anchor dependencies")
        if node in visited:return
        for x in edges[node]:visit(x,visiting | {node})
        visited.add(node)
    for aid in ids:visit(aid,set())
    from .gui import validate_contract
    validate_contract(recipe)
    from .language import binding_mode
    if binding_mode(recipe) == 'shared-neutral':
        # KPP requirements are contextual applications of the SAME source-defined
        # Neutral Anchor used by programs and project/register views.
        from .. import anchors as shared_anchors, kitchen
        neutral = shared_anchors.definition('Neutral')
        for obligation in anchors:
            for field, expected in (('type', neutral.type), ('definition', neutral.id),
                                    ('singularity', neutral.singularity)):
                if field in obligation and obligation[field] != expected:
                    raise KPPError('KPP obligations cannot redefine Anchor singularity or type')
        try:
            kitchen.bind(recipe)
        except (ValueError, TypeError, KeyError) as error:
            raise KPPError('Invalid shared Anchor application: ' + str(error)) from error
    elif any({'type', 'definition', 'singularity'} & obligation.keys() for obligation in anchors):
        raise KPPError('Anchor definition attributes require anchor_binding shared-neutral')
    return recipe


def find_repo_root():
    # Installed package can work without its original clone; CLI may override path.
    for p in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (p / "pantry").is_dir() and (p / "recipes").is_dir():
            return p
    bundled = Path(__file__).resolve().parent / 'resources'
    if (bundled / 'pantry').is_dir() and (bundled / 'recipes').is_dir():
        return bundled
    raise KPPError("Cannot find pantry/recipes. Use an extracted KPP project or pass --repo")


def ingredient_catalog(repo, check_sources=True):
    entries={}
    for path in sorted((Path(repo)/"pantry").glob("*.json")):
        obj=read_json(path)
        if obj.get("schema") != SUPPORTED_INGREDIENT or not SLUG.fullmatch(obj.get("id", "")):
            raise KPPError(f"Invalid ingredient manifest: {path}")
        source = obj.get("source")
        if isinstance(source, dict) and source.get("kind") == "repository-files":
            validate_repository_source(source)
        if obj["id"] in entries: raise KPPError("Duplicate ingredient: "+obj["id"])
        entries[obj["id"]]=obj
    # Portable Anchor specimens are packaged relative to the pantry repository,
    # and hashed so a changed example cannot silently masquerade as the same ingredient.
    for item in entries.values():
        specimen=item.get("specimen")
        if specimen is None:continue
        if not isinstance(specimen,dict) or specimen.get("profile")!="EMIT_TEXT/0.2" or specimen.get("emits") not in ("python","text"):
            raise KPPError("Invalid Anchor specimen manifest: "+item["id"])
        relative=specimen.get("path")
        if not isinstance(relative,str) or not relative.startswith("specimens/") or ".." in Path(relative).parts:
            raise KPPError("Invalid specimen path: "+item["id"])
        base=Path(repo).resolve()
        specimen_path=(base/relative).resolve()
        if not specimen_path.is_relative_to(base):
            raise KPPError("Unsafe specimen: "+item["id"])
        if check_sources:
            if not specimen_path.is_file():
                raise KPPError("Missing specimen: "+item["id"])
            if hashlib.sha256(specimen_path.read_bytes()).hexdigest()!=specimen.get("sha256"):
                raise KPPError("Specimen hash mismatch: "+item["id"])
            from .anchor import inspect_file
            inspect_file(specimen_path)
    return entries


def validate_pantry(recipe, catalog):
    missing=set(recipe["ingredients"])-set(catalog)
    if missing: raise KPPError("Unresolved ingredients: "+", ".join(sorted(missing)))
    return [catalog[i] for i in recipe["ingredients"]]

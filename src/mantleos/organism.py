"""Small public construction API over the inherited Body runtime."""
from pathlib import Path
import tempfile

from . import tissue as composition, lifecycle
from .birth import make_birth
from .transactions import write_json
from .anchor_engine.tools.anchor_runtime import render_hello_world


def notebook_tissue(greeting="Ready to remember."):
    from .anchor_engine.tools.notepad_blueprint import generate
    return composition.tissue("notebook", [
        composition.program("greeting", "EMIT_TEXT/0.2", render_hello_world("Greeting", greeting)),
        composition.program("notepad", "NOTEPAD_LLM/1.3", generate(), dependencies=["greeting"]),
    ])


def create(output, *, identity="notebook", tissue=None):
    """Explicitly construct a new synthetic Body, without model or network calls."""
    selected = composition.validate_tissue(tissue if tissue is not None else notebook_tissue())
    birth = make_birth(bio_id=identity, name="Notebook", description="Synthetic offline reference organism",
                       persona_name="Notebook", persona="A synthetic notebook. Preserve observations and uncertainty.")
    # Complete composition in a private staging directory before publishing.
    from .transactions import body_lock
    import os
    with body_lock(output), tempfile.TemporaryDirectory(prefix="mantle-compose-") as work:
        destination = lifecycle._destination(output)
        catalog = composition.write_programs(Path(work) / "programs", selected)
        import uuid
        stage = destination.parent / ("." + destination.name + ".stage-" + uuid.uuid4().hex)
        try:
            lifecycle.create(birth, stage, programs=catalog, portable=False)
            write_json(stage / "TISSUE.json", selected)
            receipt = lifecycle.finalize(stage)
            os.rename(stage, destination)
            return {**receipt, "result": "CREATED", "output": str(destination)}
        finally:
            if stage.exists():
                import shutil
                shutil.rmtree(stage)


def consult(body, mind=None):
    """Optional cognition has no authority handle; failure leaves Body usable."""
    from .compiled import inspect
    context = inspect(body)
    if mind is None:
        return {"status": "MIND_ABSENT", "body": context}
    try:
        candidate = mind(context)
        from .json_contract import canonical
        canonical(candidate)
        return {"status": "PROPOSED", "candidate": candidate, "authorized": False}
    except Exception:
        return {"status": "MIND_FAILED", "body": context}

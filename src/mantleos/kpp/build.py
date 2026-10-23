"""Preview-first, bounded Chase orchestration over the existing recipe/workspace.

The caller supplies authorized host operations. This module does not create a
model, approve evidence, mount a Canvas, run tests or install code on its own.
"""
from copy import deepcopy
from .core import KPPError
from .graph import coverage, chase
from .workshop import load

BUILD_RULE = (
    'For an app build, pin its recipe and identify the smallest independently useful interaction. '
    'Mount that first usable slice in the actual authorized Canvas/preview immediately while BUILDING, '
    'before generating later stages or packaging the full portable document. '
    'Check a real interaction; a blank frame or file link is not an interactive preview. '
    'Keep that mounted app and its current user state alive while admitting reviewed modules. '
    'After every build/test/refinement cycle, read mantleos.kpp.build.step(workspace) '
    '(CLI: kpp build-step --workspace DIR) and pursue the next ready unmet obligation. '
    'Continue the recipe-selected refinement loop within the authorized scope and declared budget; one visible app or one '
    'passing feature is not recipe completion. Failed or untested obligations stay open. '
    'Keep unavailable controls gated, retain recovery history, and check state preservation after updates. '
    'A test result or MIND proposal never supplies Baker/operator approval. '
    'Finish only with current evidence and required explicit acceptance for every mandatory obligation '
    'and preservation obligation. If blocked, awaiting review, out of budget or lacking a mount tool, '
    'report the exact remaining obligations and resume point; do not claim COMPLETE. '
    'Follow the pinned implementation choices; use an existing complete Anchor profile only when the recipe selects an .anchor artifact. '
    'Do not regenerate its bridge/Python target for every streamed source fragment. '
    'These are host workflow steps, not new Anchor opcodes or authority grants.'
)


def step(workspace):
    """Small current work packet, derived from the one recipe and acceptance graph."""
    recipe, state = load(workspace)
    report = coverage(recipe, state)
    obligations = {item['id']: item for item in recipe['anchors']}
    needed = set(report['unmet_anchors'])
    def dependencies(aid):
        for dep in obligations[aid].get('depends', []):
            if dep not in needed:
                needed.add(dep)
                dependencies(dep)
    for aid in tuple(needed):
        dependencies(aid)
    ordered = [item for item in chase(recipe, state) if item['id'] in needed]
    next_item = next((item for item in ordered if item['ready']), None)
    satisfied = not report['unmet_anchors'] and not report['unaccepted_properties']
    decision = ('COMPLETE' if state['phase'] == 'COMPLETE' and satisfied else
                'READY_FOR_COMPLETION' if satisfied else 'CONTINUE' if next_item else 'BLOCKED')
    from .language import implementation_plan
    from .construction import construction_plan
    return {'construction': construction_plan(recipe), 'implementation': implementation_plan(recipe), 'schema': 'mantle.kpp-build-step/1', 'recipe_id': recipe['id'],
        'recipe_sha256': state['recipe_hash'], 'revision': state['revision'],
        'phase': state['phase'], 'decision': decision,
        'unmet_anchors': report['unmet_anchors'],
        'unaccepted_preservation': report['unaccepted_properties'],
        'accepted': report['accepted_anchors'], 'required': report['required_anchors'],
        'next': deepcopy(obligations[next_item['id']]) if next_item else None,
        'waiting': ordered, 'preview': 'OPEN_FIRST_USABLE_SLICE; preserve the mounted Body during refinement',
        'authority': 'NONE; current scoped evidence and explicit Baker acceptance remain required'}


def run(workspace, *, open_preview, refine, max_cycles=16):
    """Call the host's preview operation BEFORE its first refinement operation.

    refine receives a fresh step, applies authorized work and checks, and returns
    CONTINUE, BLOCKED or AWAITING_REVIEW. It never gains authority from this driver.
    Completion is always derived from the current workspace, never that reply.
    Exceptions propagate: unknown effects must be reconciled, not silently retried.
    """
    if type(max_cycles) is not int or not 1 <= max_cycles <= 256:
        raise KPPError('Refinement needs a declared budget of 1..256 cycles')
    if not callable(open_preview) or not callable(refine):
        raise KPPError('Refinement requires explicit host preview and refinement operations')
    initial = step(workspace)
    def current_step():
        current = step(workspace)
        if current['recipe_sha256'] != initial['recipe_sha256']:
            raise KPPError('Recipe changed during ' + ('Chase' if initial['construction']['ordering'] == 'chase' else 'refinement') + '; review a new build explicitly')
        return current
    preview = open_preview(deepcopy(initial))
    if not isinstance(preview, dict):
        raise KPPError('Host preview operation must return its actual receipt object')
    if preview.get('status') not in ('OPENED', 'APPLIED'):
        return {'status': 'PREVIEW_UNAVAILABLE', 'preview_receipt': preview, 'cycles': [], 'step': initial}
    turns = []
    for cycle in range(max_cycles):
        current = current_step()
        if current['decision'] != 'CONTINUE':
            return {'status': current['decision'], 'preview_receipt': preview, 'cycles': turns, 'step': current}
        outcome = refine(deepcopy(current))
        if outcome not in ('CONTINUE', 'BLOCKED', 'AWAITING_REVIEW'):
            raise KPPError('Refinement must report CONTINUE, BLOCKED or AWAITING_REVIEW')
        turns.append({'cycle': cycle + 1, 'anchor': current['next']['id'],
                      'revision': current['revision'], 'outcome': outcome})
        if outcome != 'CONTINUE':
            return {'status': outcome, 'preview_receipt': preview, 'cycles': turns, 'step': current_step()}
    current = current_step()
    status = current['decision'] if current['decision'] != 'CONTINUE' else 'BUDGET_EXHAUSTED'
    return {'status': status, 'preview_receipt': preview, 'cycles': turns, 'step': current}

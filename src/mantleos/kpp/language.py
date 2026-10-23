"""Recipe implementation choices; declarations never establish execution or acceptance."""
import re

IDENTIFIER = re.compile(r'^[a-z][a-z0-9_-]{0,63}$')


def binding_mode(recipe):
    return 'shared-neutral' if recipe.get('schema') == 'kpp.recipe/3' else recipe.get('anchor_binding', 'none')


def validate_implementation(recipe):
    from .core import KPPError
    misplaced = {'implementation_language', 'language_selection', 'language', 'languages'} & recipe.keys()
    if misplaced:
        raise KPPError('Use recipe/4 implementation.components for language selection: ' + ', '.join(sorted(misplaced)))
    if recipe['schema'] == 'kpp.recipe/3':
        if {'implementation', 'anchor_binding'} & recipe.keys():
            raise KPPError('Explicit implementation choices and anchor_binding require kpp.recipe/4')
        return
    if binding_mode(recipe) not in ('none', 'shared-neutral'):
        raise KPPError('anchor_binding must be none or shared-neutral')
    value = recipe.get('implementation')
    if not isinstance(value, dict) or set(value) != {'components'}:
        raise KPPError('recipe/4 needs implementation.components')
    components = value['components']
    if not isinstance(components, list) or not 1 <= len(components) <= 128:
        raise KPPError('implementation.components needs 1..128 components')
    ids, selected_languages = set(), set()
    unresolved = False
    for component in components:
        if not isinstance(component, dict) or set(component) - {'id', 'policy', 'languages', 'selected', 'rationale', 'profile'}:
            raise KPPError('Unknown implementation component field; use id, policy, languages, selected, rationale, profile')
        identifier = component.get('id')
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier) or identifier in ids:
            raise KPPError('Invalid or duplicate implementation component id')
        ids.add(identifier)
        policy, languages = component.get('policy'), component.get('languages')
        if policy not in ('required', 'preferred', 'recommend'):
            raise KPPError('Component policy must be required, preferred or recommend')
        if (not isinstance(languages, list) or len(languages) > 64
                or any(not isinstance(x, str) or not IDENTIFIER.fullmatch(x) for x in languages)
                or len(languages) != len(set(languages))):
            raise KPPError('languages must contain distinct lowercase language identifiers')
        if policy == 'required' and len(languages) != 1 or policy == 'preferred' and not languages:
            raise KPPError('required needs exactly one language; preferred needs ordered preferences')
        selected = component.get('selected')
        if policy == 'required':
            if selected is not None and selected != languages[0]:
                raise KPPError('Selected language conflicts with required language')
            selected = languages[0]
        if selected is not None and (not isinstance(selected, str) or not IDENTIFIER.fullmatch(selected)):
            raise KPPError('Invalid selected language')
        rationale = component.get('rationale')
        if rationale is not None and (not isinstance(rationale, str) or not rationale.strip()):
            raise KPPError('Decision rationale must be nonempty text')
        if selected and policy != 'required' and rationale is None:
            raise KPPError('Completed preferred/recommend selection requires rationale')
        if 'profile' in component:
            if selected != 'anchor':
                raise KPPError('Execution profile requires selected Anchor language')
            from ..tissue import PROFILES
            if component['profile'] not in (*PROFILES, 'AGENTIC/0.2'):
                raise KPPError('Unsupported Anchor execution profile')
        if selected:
            selected_languages.add(selected)
        else:
            unresolved = True
    expected = ('mixed' if len(selected_languages) > 1 else
                next(iter(selected_languages)) if selected_languages <= {'python', 'javascript', 'anchor'} and selected_languages
                else 'unspecified')
    if not unresolved and recipe['tissue'] != expected:
        raise KPPError('tissue conflicts with resolved implementation choices; expected ' + expected)
    if unresolved and recipe['tissue'] != 'unspecified':
        raise KPPError('Unresolved language choices require unspecified tissue during preparation')


def implementation_plan(recipe):
    """Read-only preparation report; never chooses a language or runs tools."""
    from .core import validate_recipe, digest
    validate_recipe(recipe)
    components = []
    if recipe['schema'] == 'kpp.recipe/4':
        for item in recipe['implementation']['components']:
            selected = item['languages'][0] if item['policy'] == 'required' else item.get('selected')
            profiles = []
            support = {'python': 'REVIEWED_LOCAL_PYTHON_TEST_PATH',
                       'javascript': 'REVIEWED_BROWSER_MODULE_PATH'}.get(selected, 'NOT_PROVIDED')
            if selected == 'anchor':
                from ..tissue import PROFILES
                profiles = sorted(PROFILES) + ['AGENTIC/0.2 (explicit hosted inputs required)']
                support = 'QUALIFIED_PROFILES_ONLY'
            components.append({**item, 'selected': selected,
                'decision': 'RESOLVED' if selected else 'UNRESOLVED',
                'outside_preferences': bool(selected and item['policy'] == 'preferred' and selected not in item['languages']),
                'execution_support': support, 'available_execution_profiles': profiles,
                'verification': 'NOT_RUN'})
    return {'schema': 'kpp.implementation-plan/1', 'recipe_sha256': digest(recipe),
            'recipe_schema': recipe['schema'], 'anchor_binding': binding_mode(recipe),
            'legacy_tissue': recipe['tissue'], 'components': components,
            'ready': all(item['decision'] == 'RESOLVED' for item in components),
            'execution': 'NONE', 'acceptance': 'NOT_GRANTED',
            'limitations': 'Declared choices and existing tooling paths only; no compiler/backend installation, execution or behavioral qualification. Legacy recipe/3 tissue is unchanged.'}

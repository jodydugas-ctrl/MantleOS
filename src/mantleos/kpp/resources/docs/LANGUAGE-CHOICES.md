# Recipe implementation choices

KPP is the development protocol. A recipe selects the implementation approach.
MantleOS is the creator's experimental testbed for exploring AI embodiment through
code; its engineering experiments do not establish consciousness or a theory of
identity. Anchor Coding is a supported domain, with one authoritative model and
qualified execution profiles wherever that domain is selected.

Recipe/3 is retained without migration. Its tissue and shared Neutral binding
remain unchanged. Recipe/4 retains `anchors` as the historical JSON key for
measurable obligations; unbound obligations carry no Anchor type or singularity.
It defaults to `anchor_binding: "none"`. Explicit `"shared-neutral"` selects the
existing model. `bind` refuses unbound recipes; validation and graph construction
do not activate an adapter implicitly.

Recipe/4 adds this section:

```json
{
  "implementation": {
    "components": [
      {"id": "app", "policy": "required", "languages": ["python"]},
      {"id": "worker", "policy": "preferred", "languages": ["rust", "python"],
       "selected": "python", "rationale": "Use the already available local tooling"}
    ]
  }
}
```

Component IDs are unique lowercase slugs. `required` names exactly one language
and selects it directly; an explicit conflicting selection is rejected.
`preferred` has a nonempty ordered preference list. `recommend` may have an empty
list. The latter policies permit an unresolved selection during preparation;
completed decisions require a nonempty rationale. A justified preference override
is reported explicitly. No model, compiler or execution is invoked by planning.

Optional `profile` is separate from language and is valid only for selected
`anchor`, using an existing qualified profile. Unsupported profiles fail
explicitly. Declaring `rust` or another language does not add a compiler or
backend. All planning reports mark verification NOT_RUN and acceptance NOT_GRANTED.
Existing Python test and browser module paths also require their existing
explicit execution review and actual test evidence.

Tissue remains the delivery compatibility category. One selected Python,
JavaScript or Anchor language requires its corresponding tissue; multiple distinct
languages require mixed; one other language requires unspecified. During unresolved
preparation use unspecified tissue. Progressive-web still requires JavaScript or
mixed tissue and the pinned preview contract; a backend declaration does not
prove that backend executes.

```console
python -m kpp language-plan --recipe recipes/conventional-python-v4.json
python -m kpp language-plan --recipe recipes/anchor-literal-v4.json
python -m kpp language-plan --recipe recipes/mixed-declaration-v4.json
```

Python API: `mantleos.kpp.implementation_plan(recipe)` (also exposed through the
standalone kpp facade). The read-only `kpp.implementation-plan/1` report contains
recipe identity, binding choice, components, effective selections, unresolved
decisions, existing tooling paths, available profiles, and limitations.
Workspace creation refuses unresolved choices before publishing any files.
Preparation resolves them in the recipe using the ordinary recipe review process.
Existing workspaces are pinned: changing any decision requires a new recipe and
workspace and does not transfer acceptance. Handoff and build-step include the
same derived report; they do not create another writable decision registry.

Use implementation.components, rather than adding unrecognized language fields.
Misplaced `language`, `languages`, `implementation_language`, `language_selection`,
or version-3 implementation/binding fields are rejected with migration guidance.

The three version-4 recipes are illustrative declarations with measurable
obligations; their presence is not an executed application or Baker acceptance.

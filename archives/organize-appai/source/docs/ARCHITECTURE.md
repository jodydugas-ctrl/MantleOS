# Organize.AppAI architecture

Organize.AppAI is a compatibility layer around `organize`, not a rewrite. The original
parser, models, walker, filters, actions, templates, conflict resolver, outputs, and
simulation semantics remain authoritative.

The deterministic data path is:

```text
CLI -> Config parser -> rule/tag selection -> Walker -> target selection
    -> filter pipeline -> action plan -> simulation or execution -> Output
                              |
                              +-> optional structured TraceSink
```

`organize/mantle_appai/events.py` defines immutable evaluation events, monotonic sequencing,
privacy-bounded serialization, and no-op, memory, JSONL, composite, and optional buffered
Mantle sinks. Instrumentation is fail-open: a failed sink cannot change the host result.

`explain.py` inspects parsed objects without traversing files. `why.py` either performs a
read-only focused evaluation with the real filters or selects a correlated resource window
from a bounded prior JSONL trace; it never calls an action. For existing-behavior questions,
`assist.py` gathers a static map plus at most 200 facts from a 20-resource top-level sample.
Optional model answers must validate against `AnswerPayload` and every citation must name a
reference in that exact evidence packet. Proposal mode writes a separately validated rule
and performs simulation only. `bridge.py` is the only package that loads the resident Body.

Mutation remains owned by upstream action implementations. The assistant cannot bypass the
parser or call those mutations. Existing commands do not require MantleOS, a provider,
network access, or credentials.

## State transitions

```text
configured -> selected/skipped -> entered target -> matched/not_matched
           -> planned -> simulated(skipped) | executed | failed/refused/conflict
```

An event is evidence about a transition. It is not an instruction. Model interpretation is
never allowed to rewrite event outcomes or promote itself to verified fact.

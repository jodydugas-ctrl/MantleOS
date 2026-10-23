# Mantle OS Positioning

Non-normative on-ramp. The canonical doctrine lives in the project [`README`](../README.md)
(the primer) and the source-backed engineering map lives in
[`Mantle_for_Engineers.md`](Mantle_for_Engineers.md).

Mantle OS is a framework for installing an autonomic nervous system and brainstem into a
software or hardware container. That container becomes the Body of a virtual bio-robotic
agent: it can perceive inputs, react through deterministic reflexes, record experience,
protect its state, act through bounded outputs, and later accept a contained reasoning
layer.

The VCW cube is the booted durable nervous-memory substrate. It is not the Grimoire itself:
VCW is hardware/substrate, while the Grimoire is the Mantle software doctrine and one
possible layer profile. The standard body plan is visualized as an 800x800x800 cube made
from 800x800 RGBA layers with a soft cap of 800 layers, lazily generated as needed. The
cube bootloader declares the layout: bands, layer ranges, privacy, driver/profile, and
what each layer's four lanes encode.

A Grimoire-semantic layer may map lanes as atom, role, evidence, and force. Another layer
may map the same four lanes to tool state, app data, spatial memory, indexes, repair bytes,
or database content. The requirement is not a specific language or host. The requirement is
a container that can persist the VCW and expose clear input/output boundaries.

Mantle is built Body first, MIND second:

- **Body:** deterministic runtime. It runs without model calls, records state append-only,
  and must pass the audit gates before cognition is considered.
- **MIND:** optional LLM-backed cognition. It receives assembled context, writes only to its
  bounded cognition surface, and proposes actions. The Body still applies, verifies, and
  records effects.

This is why the organic language is intentional. It names engineering boundaries:

- **Senses** are the only inbound boundary.
- **Limbs** are the only outbound boundary.
- **Immune** is the failure and integrity boundary.
- **Heart** is the deterministic pulse.
- **Brain/MIND** is optional cognition, added only after the Body is proven.
- **VCW** is the append-only memory substrate.

For a plain-language introduction, read the [`README`](../README.md). For engineers and AI
agents, read [`Mantle_for_Engineers.md`](Mantle_for_Engineers.md).

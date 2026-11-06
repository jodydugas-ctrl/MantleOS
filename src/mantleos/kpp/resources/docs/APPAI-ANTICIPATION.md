# AppAI anticipation at the next heartbeat

An AppAI encounters its NEST in slices, like the pages of a picture book.
The Heart turns a page every 600 seconds. The Body keeps doing its work between
pages. An extra wake can supply an observation, while the natural deadline
continues on the same cadence.

At each scheduled page, the Body supplies the MIND with a bounded picture of
the current checked observations, what changed since the last comparable page,
and what comparable pages in the Engram show. These comparisons answer
different questions. A condition can be close to the last observation and
still be unusual for that phase of the day or workload. A historical baseline
records the comparison window, sample count, and source references so the
MIND can distinguish a stable pattern from a sparse or stale sample.

The MIND uses part of each scheduled cognitive event to predict the **next**
page. It returns the useful subset as a bounded proposal over observations the
Body can actually measure. The Heart supplies the current and target page
identities. The Immune System admits the prediction under the Body's policy
and binds it to the target deadline, observation scope, and source references.
Each scheduled page records a forecast for the next one. If the MIND is
unavailable or its proposal fails validation, the Body records a labeled
persistence forecast from the last comparable observations. It records any
signal with insufficient evidence as unavailable.

At the target scheduled heartbeat, the Immune System compares the admitted
forecast with a fresh checked observation. The Body sets the tolerance for
each signal before scoring it. An out-of-tolerance result records the
prediction, actual value, deviation, and provenance, and queues one
investigation request for the **following scheduled heartbeat**. The Body
handles that request under its normal permissions and can include it in the
next MIND assessment when available. It still prepares a new forecast while
processing an investigation. Missing observations and missed pages get an
explicit unavailable or expired outcome. Extra wakes never score or replace
the pending scheduled forecast.

| Responsibility | Owner |
| --- | --- |
| Open each natural page and name the next scheduled deadline | Heart |
| Capture comparable host observations | Senses and the NEST |
| Supply bounded prior observations, deltas, and history references | Memory and Engram |
| Carry checked context and return the next-page proposal | MIND adapter and Nervous System |
| Admit, compare, and record forecasts, and queue and dispatch investigation requests | Immune System |
| Enforce scope and grants for any investigation effects | Body's checked boundary |

Use the [Heart Spore with anticipation](../recipes/appai-heart-spore-anticipation.json)
recipe to qualify this design. Its Immune responsibility applies the canonical
Neutral Anchor, and its effect boundary uses the existing WhiteHole. Forecasts,
comparisons, and investigations append to the Engram with provenance. A
forecast is distinct from an observation and carries no effect authority.

The recipe declares the new behavior and acceptance checks. The published
notes specimen covers Heart cadence and Body independence. Its current
assessment worker does not ingest forecasts, and this design has no runtime
qualification receipt yet.

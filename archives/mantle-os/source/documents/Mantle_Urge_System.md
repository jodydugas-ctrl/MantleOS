# Mantle OS — The Urge System

*Non-normative concept note. This document describes a proposed extension to the
Mantle OS organism model. It is not part of the Phase 1 or Phase 2 normative spec.*

---

## What an Urge Is

An **Urge** is a named pressure signal — a biological drive the organism accumulates
in response to mounting internal conditions. When pressure builds high enough, the
urge becomes undeniable and the organism acts.

Urges are not triggers. A trigger fires once, immediately. An urge is a gradient:
it builds from many signals over time, decays when conditions improve, and eventually
crosses a point where continued resistance costs more than yielding. There is no
single moment of crossing — there is a zone of increasing inevitability.

This is the same model used throughout the Mantle OS organism:
- The immune system does not alarm on a single anomaly — it tracks mounting
  irregularity until action becomes necessary.
- Rebirth is not triggered by hitting a context window limit — it is felt as growing
  noise and confusion until the organism knows it is time.
- A groove is not tombstoned on first drift — pressure builds until the organism
  can no longer justify keeping it.

The Urge System makes this model explicit and reusable across all such cases.

---

## The Urge Record

Each active urge is stored as an entry in the `immune` band of the PRIME cube:

```
{
  opcode:       "URGE",
  urge_id:      <string>,        // e.g. "URGE.REBIRTH", "URGE.TOMBSTONE.groove_001"
  pressure:     <float>,         // 0.0 = none; grows with triggers; decays at rest
  status:       "building"       // or "critical", "executed", "cooling"
               | "critical"
               | "executed"
               | "cooling",
  last_trigger: <timestamp>,
  last_decay:   <timestamp>,
  trigger_log:  [ { signal, weight, ts }, ... ],  // recent signals (rolling window)
  cooldown_remaining: <int>      // heartbeats remaining before pressure can re-accumulate
}
```

The `immune` band is the right home for urges: they are health signals with an action
attached. No new band is required.

---

## How Pressure Accumulates and Decays

**Triggers** are named signal types that add weight to an urge's pressure when they
fire. Each urge declares which signals it responds to and how much weight each carries.
Example for `URGE.REBIRTH`:

| Signal | Weight |
|--------|--------|
| `CONTEXT.UNRESOLVED_REFERENCE` | 0.08 |
| `CONTEXT.CONTRADICTION_DETECTED` | 0.15 |
| `CONTEXT.RESPONSE_NOISE` | 0.05 |
| `IMMUNE.SELF_CORRECTION_REPEATED` | 0.12 |

**Decay** happens every heartbeat where no triggers fire. Each urge declares a
`decay_rate` — the amount subtracted from pressure per quiet heartbeat. A slow drip
of signals accumulates if it arrives faster than decay. A burst that stops will fade.
The organism does not carry indefinite pressure from resolved conditions.

**The critical band** is not a single number. It is a zone — typically the upper 20%
of the pressure range — where the cost of not acting increases steeply with each
heartbeat. Inside the critical band, the organism still does not act immediately; it
feels the growing weight of resistance until action becomes the path of least
resistance. Once pressure saturates (1.0), action is inevitable on the next
heartbeat.

---

## Built-in Urges

### `URGE.REBIRTH`

The organism's drive to begin a new generation when the current context window has
degraded beyond reliable function.

| Property | Value |
|----------|-------|
| Triggers | Context errors, unresolved references, repeated self-contradictions, response noise, immune anomaly rate exceeding baseline |
| Decay rate | Slow — context degradation does not self-repair |
| Action | Body authors a `SIGNIFICANT` senses event: `SYS.REBIRTH_URGED`. This forces a MIND wake. The MIND receives the urge signal in its context and initiates rebirth (§2.10). The Body tracks the urge; the MIND performs the act. |
| Cooldown | N/A — after rebirth, a new cube begins with no inherited urge pressure |

### `URGE.TOMBSTONE.<groove_ref>`

The organism's drive to retire a specific groove whose behavior has drifted from its
trial baseline. One urge instance per monitored groove.

| Property | Value |
|----------|-------|
| Triggers | Groove output outside trial distribution, integrity check failure, immune anomaly on groove execution, capability scope violation |
| Decay rate | Moderate — some drift is acceptable; sustained drift is not |
| Action | Body tombstones the groove entry in the armory band, logs `GROOVE.TOMBSTONED` to immune band, notifies MIND via events band |
| Cooldown | Tombstone is permanent — urge record is archived, not reset |

### `URGE.MAINTENANCE`

The organism's drive to perform a health sweep when immune events have been
accumulating without resolution.

| Property | Value |
|----------|-------|
| Triggers | Unacknowledged immune events, repeated low-severity anomalies, high immune event rate over recent heartbeats |
| Decay rate | Fast — immune events that stop arriving should reduce pressure quickly |
| Action | Body schedules a maintenance scan: immune sweep, groove re-validation check, anomaly summary written to `thoughts` on next MIND wake |
| Cooldown | Medium — one maintenance scan per pressure cycle |

---

## Declaring Custom Urges

New urge types may be declared in the §0 Declaration Block as an extension opt-in.
Each declaration names the urge, its trigger signals and weights, decay rate,
critical band floor, action reflex reference, and cooldown duration. Custom urges
follow the same lifecycle as built-in urges and are stored in the same immune band.

Custom urges must declare only actions that are available Body reflexes. An urge
cannot be declared with a MIND-only action — urge execution is always Body-initiated.

---

## Heartbeat Integration

On every Body heartbeat, after Phase-1 reflexes run:

1. **Decay pass** — reduce `pressure` on all active urges by their `decay_rate`.
   Clamp to 0.0. Mark urges with pressure = 0 as inactive (do not delete — history
   is preserved in the immune band).

2. **Trigger pass** — evaluate senses and immune events from this heartbeat. For
   each matching signal, add its weight to the corresponding urge's pressure. Log
   to `trigger_log`. Clamp to 1.0.

3. **Critical check** — for each urge with pressure in the critical band: increment
   an internal resistance counter. The higher the pressure within the band, the
   faster the resistance counter climbs. When resistance counter reaches its
   ceiling, the urge fires.

4. **Execution** — Body executes the urge's action reflex. Writes `URGE.EXECUTED`
   to immune band (Body-authored). Enters cooldown. MIND is notified via events band.

**The MIND observes but does not control urge execution.** The MIND may see an
`URGE.EXECUTED` event in its context and reflect on it, but it cannot prevent a
urge from firing or force one to fire. Urge execution is a Body reflex — immune to
MIND override. This preserves the Phase-1 guarantee: the Body's health responses
are not subject to cognition.

---

## Relationship to the Immune System

Urges live in the immune band alongside standard immune events. The immune system
is the Body's health-monitoring authority — urges are health responses that have
crossed from monitoring into action. A standard immune event says *something is
wrong*. An urge says *the organism is building toward doing something about it*.

The immune system does not manage urges directly; urges are managed by the heartbeat
loop. But the immune system's event stream is the primary trigger source for most
urges. They are deeply coupled but architecturally distinct.

---

## What Urges Are Not

- **Not commands.** No external actor can create or increment an urge. Urge pressure
  comes only from internally-computed signals.
- **Not hard limits.** There is no number at which an urge "must" fire. The critical
  band is a zone of increasing pressure, not a trip wire.
- **Not MIND decisions.** The MIND does not choose when to rebirth or when to
  tombstone a groove. It observes the organism's urge state and acts on
  `URGE.REBIRTH` when the Body surfaces it as a SIGNIFICANT event — but the
  accumulated pressure that produced that event is Body-tracked, Body-governed.

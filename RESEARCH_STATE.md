# Research state machine

V0.4 additive boundary: the independently stored source-audit process states
queued/running/completed/failed/rejected/interrupted/cancelled are operational records,
not new legal mathematical workflow edges. Only the engine-owned known finite
calibration in docs/CONJMAP_SOURCE_AUDIT_V04.md is eligible; it never sets PROVED,
VERIFIED_OPEN or novelty status and never revives historical blocked work.

Legal edges are authoritative in orchestration/transitions.json:

- `UNMAPPED` → `MAPPED`
- `MAPPED` → `OPEN_STATUS_UNVERIFIED`, `COLLISION_FOUND`, `BLOCKED`
- `OPEN_STATUS_UNVERIFIED` → `VERIFIED_OPEN`, `PARTIALLY_SOLVED`, `COLLISION_FOUND`, `BLOCKED`, `ABANDONED`
- `VERIFIED_OPEN` → `DECOMPOSED`, `OPEN_STATUS_UNVERIFIED`, `COLLISION_FOUND`, `BLOCKED`
- `PARTIALLY_SOLVED` → `DECOMPOSED`, `OPEN_STATUS_UNVERIFIED`, `COLLISION_FOUND`, `BLOCKED`
- `DECOMPOSED` → `TARGETABLE`, `BLOCKED`, `COLLISION_FOUND`, `OPEN_STATUS_UNVERIFIED`
- `TARGETABLE` → `SENTINEL_READY`, `BLOCKED`, `COLLISION_FOUND`, `OPEN_STATUS_UNVERIFIED`
- `SENTINEL_READY` → `SENTINEL_RUNNING`, `BLOCKED`, `OPEN_STATUS_UNVERIFIED`
- `SENTINEL_RUNNING` → `FALSIFIED`, `PROOF_ATTEMPT`, `PARTIAL_PROGRESS`, `BLOCKED`
- `PROOF_ATTEMPT` → `FORMALIZATION`, `PARTIAL_PROGRESS`, `VERIFICATION_FAILED`, `BLOCKED`, `COLLISION_FOUND`
- `FORMALIZATION` → `PROVED`, `VERIFICATION_FAILED`, `BLOCKED`
- `VERIFICATION_FAILED` → `PROOF_ATTEMPT`, `FORMALIZATION`, `ABANDONED`, `BLOCKED`
- `PARTIAL_PROGRESS` → `DECOMPOSED`, `SENTINEL_READY`, `BLOCKED`, `ABANDONED`
- `COLLISION_FOUND` → `KNOWN_RESULT_REDISCOVERED`, `ABANDONED`, `OPEN_STATUS_UNVERIFIED`
- `KNOWN_RESULT_REDISCOVERED` → `PROVED`
- `BLOCKED` → `OPEN_STATUS_UNVERIFIED`, `ABANDONED`
- `FALSIFIED` → `ABANDONED`
- `PROVED` → (terminal)
- `ABANDONED` → (terminal)


All edges require an actor, timestamp, reason, valid source references and consistency with
the prior state. VERIFIED_OPEN additionally requires fresh official status evidence in v0;
other source types await a richer evidence adapter. BLOCKED resumes only via status audit.
No exceptions or direct UNMAPPED → PROOF_ATTEMPT exist in v0. Correct a falsified statement
by a new linked card, never by silently reviving it. A wrong terminal decision requires an
explicit future correction migration retaining the original record.

The full edge table is a design contract; Phase 0 enables only mapping, status audit,
collision recording, blocking and abandonment. PROVED and all experiment/proof states
are disabled regardless of supplied JSON. Future gates must require current literature,
novelty clearance, exact scoped budget, do-not-replay clearance, falsification evidence,
and independently bound verifier receipts. The Phase 0 implementation makes no claim to
implement that future research runtime.

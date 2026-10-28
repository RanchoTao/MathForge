# ConjMap source-bound calibration gateway · V0.4

This is an additive, narrowly scoped execution protocol authorized by the owner's
2026-10-24 request. The existing Phase0 research/proof acceptance flags, synthetic
queue allowlist, frozen atlas and historical negative knowledge remain unchanged.
This document does not claim that a genuine run has already happened.

## Admission and scientific boundary

Only `cm-v04-union-closed-fin2-v1` for `cm-000118` is implemented. The engine-owned
`sources/conjmap-fin2/ADMISSION.json` binds the exact original statement, Lean signature,
versioned source hash, Fin2 variant, quantifiers, agent desk reviews and explicit owner
one-task/no-network authorization. It allows a **known finite calibration**, not a
novelty sentinel, open-problem attack, arbitrary program, proof acceptance or model call.

The worker enumerates all16 families of the four subsets of{0,1}, checks closure under
binary union for every ordered member pair, excludes exactly the singleton family{∅}
and retains the empty family. For each qualifying family it tests whether an element
occurs in at least half the members using exact integers. A bitmask representation is
cross-checked against actual Python sets. The source's Fin2 lemma is a solved special
case. This does not verify the complete Lean import closure or general conjecture.

Historical replay clearance is separately reviewed. The earlier minimal-generator/
join-irreducible question has a different target from the half-frequency calibration;
its collision/KILL and replay rules are preserved. REAL_RUN additionally reads the
original registry through an explicit local `--history-root`, hashes the same bounded
negative/replay inputs used by the historical controller, and compares the snapshot
to the admitted version on submission and immediately before launch. No historical
files, controller, atlas or secrets are modified or copied. Any drift blocks the task.
The public card records only desk-review rationale and hashes, not private history.

## Transport, quota and immutable provenance

Start explicitly using `python -m mathforge.gateway --root <core-checkout> --journal
reports/local/<new-run> --port9444 --mode REAL_RUN --history-root <read-only-history-root>
--serve-seconds180` (separate flags/values in an actual command). Configure
`MATHFORGE_GATEWAY_TOKEN` and `MATHFORGE_RECEIPT_SECRET` only in the process environment;
both require≥32 characters. No credential is included in examples, receipts or logs.
Default mode is CONTRACT_TEST. The process binds127.0.0.1 and stops after at most600s;
it is not a production service or persistent scheduler.

V2 routes: authenticated POST `/v2/research-tasks`, GET `/<engine-id>`, GET
`/by-key/<idempotency-key>`, POST `/<engine-id>/cancel`, GET
`/<engine-id>/artifacts/<signed-basename>`. The POST includes api_version/conjmap_task_id,
problem_id/objective/budget/context/admission_id. The original source-binding context
must match the card byte-for-byte. JSON is capped64KiB. Browser-origin requests,
redirect routes, unlisted tasks and arbitrary code/artifact paths are rejected.

Idempotency is durable; payload changes under one key conflict. A separate engine-root
REAL_RUN reservation prevents a new journal or key granting a second admitted run.
Request/mode/engine commit/code hashes are persisted at admission; restarting cannot
relabel CONTRACT_TEST as REAL_RUN. Old receipts retain their original code provenance.
Queued work is rejected after workspace, card, code or historical-registry drift.
Audit events use the existing hashed event mechanism and SQLite immediate transactions.
The chain authenticates event order; it is not a tamperproof database or author identity.

Every response includes `execution_mode` and a receipt envelope. HMAC-SHA256 signs the
exact canonical JSON payload, including both task identities, source/statement/admission
hashes, recorded engine commit/worker hash, state, attempts, indexed artifact bytes/hashes
and measured resources. Payload protocol is `mathforge-conjmap-receipt-v1`. Attempts
always say unverified. Public verification without the shared local secret is not claimed.

## Worker, failure and recovery

The trusted fixed worker waits for START until its controller assigns the existing
Windows Job Object (256MiB). It has no untrusted imports/code, inherits no provider
credentials and installs an audit hook denying sockets and child execution. This is
a reviewed-code boundary, not a sandbox for arbitrary hostile Python. One ordinary
Python computation thread, no GPU/network/paid API. Other OSes fail closed at the
resource adapter, rather than claiming a missing resource control succeeded.

An independent monotonic watchdog terminates the worker even while the controller is
blocked on SQLite. Logs, input, source, finite table, code/version accounting and errors
are retained with exclusive creation. Actual CPU/peak job memory are queried from the
Job Object; wall and controller elapsed times are distinct. Failure, interruption and
cancellation never become a mathematical counterexample or successful proof.

Cancel stops queued work or records a request for the running controller to terminate
its child. Only a terminal authenticated receipt establishes cancellation. GET does
not resubmit. Operator `--recover <engine-id>` requires no live recorded controller or
worker (PID checks fail closed on ambiguity), marks interrupted and never replays.
A dead controller's Job Object kills its child. Root one-task reservations stay spent;
new execution requires a separately reviewed protocol/admission version, not deletion.

Tests use isolated synthetic workspaces under reports/local and explicitly labeled
CONTRACT_TEST computations. They exercise REAL_RUN reservation boundaries without
launching a real research worker. Genuine integration evidence must be recorded by the
calling ConjMap acceptance report after an actual authenticated round trip.

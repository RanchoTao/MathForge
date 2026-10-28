# Scientific contract

1. PROVED requires either a successful Lean check, a deterministic formal-verifier
   certificate, or a reliable primary citation to an established theorem matching the
   exact hypotheses. A title claiming a proof is not an established theorem.
2. A computational observation is not a universal proof. Testing n <= N supports only
   that bounded scope, and even exhaustive finite conclusions require a verified complete
   encoding and checker. A solver exit code alone does not establish either.
3. LLM judgment, consensus and self-reported confidence are not verification.
4. VERIFIED_OPEN requires explicit, credible status evidence, a locator, source identity,
   retrieval date, scope match and freshness check. Uncertainty or conflicting proof claims
   gives OPEN_STATUS_UNVERIFIED. Retrieval of an old survey does not make it recent evidence.
5. Novelty UNKNOWN means research HOLD. GO_TO_LITERATURE_AUDIT authorizes an audit only.
6. Falsification precedes proof search. Preserve exact inputs, code, dependency versions,
   seeds, bounds, logs, output hashes, verifier versions and all failures.
7. Never silently overwrite history. Corrections must supersede immutable records and
   explain why. Hash chains detect accidental changes, not malicious rewriting; Git and
   independent backups are necessary. Consult do_not_replay before every work proposal.
8. Reject fabricated sources, circular support, omitted hypotheses, unsupported equivalent
   formulations and ambiguous mathematical reconstruction. Stop that card and record the
   blocker; continue independent infrastructure work. Missing sources must remain unknown.
9. Failed proof strategies, negative computations, barriers and collisions are permanent
   knowledge. A timeout is not a counterexample or an impossibility theorem. Minimality
   claims require an ordering, bound and completeness certificate.
10. MathForge must not manufacture negative findings to populate directories. Phase 0
    stores an operational replay prohibition and zero purported mathematical failures.

## Enforced boundary and trust

### V0.4 explicitly authorized, separately admitted calibration audit

The owner request dated2026-10-24 authorizes one source-bound offline task, at most60s,
without bypassing scientific admission. `source_audit.py` implements a separate fixed
allowlist for the known Fin2 half-frequency calibration linked to Formal Conjectures.
It is NOT an exception to Phase0 workflow transitions: the bootstrap policy and its
research/proof permissions stay false. No general conjecture proof or novelty claim is accepted.
Engine-owned admission binds exact original statement/variant, public-source hash,
hypotheses, a versioned replay-clearance snapshot, agent desk reviews and a one-task
engine-root reservation. Missing/drifting inputs reject execution. This limited audit
runtime is opt-in and distinct from the existing synthetic validate/export queue.

The actual finite table and two agreeing implementations remain computational evidence;
they do not replace an independently reviewed encoding, Lean kernel receipt or human
review. HMAC authenticates transport within a trusted local boundary, not public authorship
or mathematical truth. See docs/CONJMAP_SOURCE_AUDIT_V04.md for scope and recovery.

The Phase 0 CLI validates schema, links, source metadata, state transitions, dates and
replay restrictions. It refuses all proof acceptance and research execution. It does not
verify the truth of prose or authenticity of an arbitrary URL. Formal verifier adapters,
axiom auditing (including rejection of sorry/admit), proof-to-statement binding, provenance
signing and source semantic verification are Phase 1 work. No flag bypasses this boundary.

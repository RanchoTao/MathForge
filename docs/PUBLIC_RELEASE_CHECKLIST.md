# MathForge — Public Release Gate

**Release candidate:** MathForge Core, `v0.1.0-alpha` (planned)  
**Repository:** `RanchoTao/MathForge`  
**Snapshot:** 2026-10-20  
**Current state:** **PRIVATE · PUBLICATION HOLD**

This is a **live checklist** for the imported repository, complementing the [current readiness report](../OPEN_SOURCE_READINESS.md). The immutable [candidate baseline](../FILE_MANIFEST.json) and [initial import mapping](../IMPORT_PROVENANCE.json) retain historical provenance; the detailed private pre-import audit is preserved locally and is not distributed here.

## Scope and evidence

- [x] Private repository created and reviewed Core imported through PR #1.
- [x] Only the extracted synthetic Core, tests, documentation and branding assets are intended for release; the full internal research workspace, unpublished papers, results, credentials and old Git history are excluded from the imported code.
- [x] Pre-import baseline (58 files; 205,023 bytes) and mapping recorded in [FILE_MANIFEST.json](../FILE_MANIFEST.json) and [IMPORT_PROVENANCE.json](../IMPORT_PROVENANCE.json). Those records refer to the **pre-import candidate**, not a claim that the current repository has exactly 58 files.
- [x] Local audit previously reported a clean-environment wheel installation, 29 passing tests, real Lean kernel checks on **synthetic** cases, and successful minimal demo.
- [x] CI workflow present in [ci.yml](../.github/workflows/ci.yml); validation on the initial import PR was reported as passing.
- [ ] Reconfirm tests and CI on the **final proposed public commit**, including the docs and metadata changes.
- [ ] Re-audit the *entire repository and reachable Git history* (including previously uploaded branding assets) for secrets, personal paths, private datasets, private research output, unintended artifacts, and disallowed redistribution.

## Apache-2.0 adoption and rights

**Maintainer adoption (2026-10-20):** Apache License, Version 2.0 is adopted for original MathForge Core code and documentation within the maintainer's rights. The repository carries the [official license text](../LICENSE), and `pyproject.toml` now uses SPDX `Apache-2.0`. **This does not clear third-party, institution, collaborator or artwork rights.**

**This selection alone does not establish ownership or authorization for all included material.** Before public release, explicitly verify:

- [ ] The rights holder(s) have authority to publish and license **all extracted/reworked source code**, including derived historical components, under Apache-2.0.
- [ ] Any obligations arising from employment, institutional resources, funding, mentor/collaborator agreements, or other contributors have been reviewed; obtain any necessary written permissions.
- [ ] The owner has the necessary rights to publish and license **MathForgeBanner.png** and **MathForgeLOGO.png** (and their underlying third-party elements/fonts, if any).
- [ ] Third-party license and attribution requirements are satisfied, including any necessary `NOTICE`; see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
- [ ] Authorized holder confirms final copyright attribution and the license grant for this specific release.
- [x] Record the explicit maintainer decision, update `pyproject.toml` to SPDX `Apache-2.0`, supersede candidate-only notices, and align README and third-party licensing scope. This grants nothing the maintainer does not own or have permission to distribute.
- [ ] Finish the separate ownership, institutional/collaborator, and brand-assets authorization review before publication; see [BRANDING.md](../BRANDING.md).

**Licensing metadata is now updated, but rights clearance remains a separate stop condition.** Do not treat SPDX metadata, an image upload, or a successful CI run as independent proof of redistribution authority.

## Final publication gate

- [ ] Documentation and installation instructions tested against the published commit (Windows CPython 3.13 x64 currently supported).
- [ ] GitHub Actions jobs on the release commit show success; real Lean integration is optional and is not part of cloud CI by default.
- [x] Mermaid lifecycle labels distinguish implemented Phase 0 from internal-only, experimental, and planned steps; full visual rendering was tested locally. Signed-in browser visual inspection remains outstanding.
- [ ] Review README statements for accuracy; no public claim of fully autonomous discovery, original theorems, scientific novelty, or NeurIPS acceptance.
- [ ] Confirm the license transition and security review **before** making the repo public.
- [ ] Then, and only then, switch GitHub repository visibility to **Public**, confirm the repository is readable in a signed-out session, and optionally create a `v0.1.0-alpha` release tag after one more exact-commit review.

> A successful engineering smoke test does **not** establish the validity, originality, or publication-worthiness of generated mathematical results.

## How to switch visibility when gates pass

GitHub repository → **Settings → General → Danger Zone → Change repository visibility → Public**. Review the consequences of making all reachable history accessible. Do **not** perform this step before the unchecked items are resolved.

## Communications

Until visibility is Public, this repository URL is not accessible to ordinary external visitors. For early conversations, share a factual description of the **Core alpha** and the intended research pipeline, not unpublished research claims.

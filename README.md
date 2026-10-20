<p align="center">
  <img src="./MathForgeBanner.png" alt="MathForge — Automated Mathematical Research" width="100%" />
</p>

<div align="center">

  # MathForge

  **Forge mathematical ideas. Verify the evidence.**

  A research-oriented framework for structured mathematical exploration, verification gates, and reproducible evidence.

  [![Status: pre-release](https://img.shields.io/badge/status-pre--release-555555)](#development-status)
  [![License: Apache-2.0 selected](https://img.shields.io/badge/license-Apache--2.0%20selected-D57D43)](#license-and-provenance)
  [![Validation: local](https://img.shields.io/badge/validation-local%20candidate-91603B)](#local-validation)

  **[Overview](#what-is-mathforge) · [Research workflow](#research-workflow) · [Current status](#development-status) · [Release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md) · [中文简介](#中文简介)**
</div>

---

## What is MathForge?

Mathematical research is not just the production of plausible proofs. It is a cycle of **forming precise claims, exploring possible arguments or counterexamples, checking those claims independently, and preserving enough evidence for others to scrutinize the result**.

MathForge is being developed around that cycle. Its long-term goal is a modular, auditable environment in which human researchers, language models, computational tools, and formal proof assistants can participate in mathematical investigation **without confusing generated hypotheses with established results**.

The distinguishing design priority is **evidence before announcement**: a promising candidate should remain a candidate until the required verification and review have been completed.

> **Scope notice (October 20, 2026):** The reviewed synthetic Core and its CI workflow are committed to this repository following private import PR #1. The repository remains **private pending release authorization**. This Core is an inspectable research-workflow infrastructure candidate, **not** the full internal autonomous mathematical research system. See the [release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md).

## Research workflow

The following diagram is the **intended end-to-end research lifecycle**, not a claim that every step is implemented in the currently imported Phase 0 Core. An implementation-grounded, full-system diagram is being prepared separately and will identify internal-only and planned modules.

~~~mermaid
flowchart TD
    A["Research input<br/>Problem · conjecture · paper"] --> B["Candidate intake<br/>Normalize claims and constraints"]
    B --> C["Prior-work and identity checks<br/>Screen duplicates and known results"]
    C --> D["Research exploration<br/>Proof ideas · counterexamples · computation"]
    D --> E["Verification<br/>Independent checks · formal tools where applicable"]
    E --> F{"Scientific gate"}
    F -->|PASS| G["Evidence package<br/>Auditable records and independent review"]
    F -->|HOLD| H["Review queue<br/>Missing evidence or unresolved issues"]
    F -->|KILL| I["Record rejection<br/>Preserve the audit trail"]
    H -->|New evidence / revised approach| D
    G --> J["Human-reviewed research output<br/>Writing · replication · submission"]
~~~

A **PASS** is a gate decision supported by its defined checks, **not** an automatic assertion of novelty, a completed formalization, peer-review acceptance, or publication. A **HOLD** preserves uncertainty; a **KILL** records why a claim or route should stop. Scientific conclusions require domain-specific standards and review.

### Design principles

| Principle | Meaning |
| --- | --- |
| **Traceability** | Keep track of the candidate, inputs, checks, and supporting records behind each decision. |
| **Independent verification** | Separate proposing a claim from determining whether the claim has been substantiated. |
| **Explicit gates** | Make rejection, uncertainty, and evidence requirements visible rather than silently promoting drafts. |
| **Reproducibility** | Prefer inspectable procedures, recorded artifacts, and testable interfaces to opaque success narratives. |
| **Human accountability** | Reserve scientific interpretation, authorship, and publication decisions for responsible researchers. |

## Development status

MathForge has **two different scopes**: an internal research workspace, and a deliberately smaller Core intended for independent use and eventual open-source distribution. They are not equivalent.

| Area | Verified or current state | Boundary |
| --- | --- | --- |
| **Repository contents** | The reviewed Phase 0 Core, synthetic examples, tests, build files, CI workflow, brand assets, and documentation are committed. | The repository remains private; this is not the complete internal research system. |
| **Extracted Core candidate** | The original audited candidate comprised 58 files (about 205 KB), with its baseline hashes preserved in `FILE_MANIFEST.json` and import mapping recorded in `IMPORT_PROVENANCE.json`. | Imported files were integrated with existing repository content; current GitHub inventory is not identical to the pre-import baseline. |
| **Schemas, scientific contracts, state graph** | Included in the locally checked Core candidate. | Public APIs and compatibility guarantees are not finalized. |
| **Audit queue, replay, resource adapters, Inspector** | Core candidate exercised locally in validation. | These are framework mechanisms, not evidence of autonomous research success. |
| **Lean integration** | A synthetic positive check and invalid-type rejection passed using the real Lean kernel. | This does **not** establish formal proofs of the private research claims. |
| **Autonomous discovery and paper production** | Long-term research direction; additional internal components and experiments are outside this repository. | No claim of independently verified end-to-end discovery performance. |
| **Cloud CI and public installation** | A GitHub Actions workflow exists, and its initial import validation was reported as passing. | Recheck CI on the final release commit; no public release or independently confirmed installation is claimed. |

The repository will distinguish **implemented**, **experimental**, **internal-only**, and **planned** functionality as the source and documentation expand. A module appearing on a diagram is not, by itself, a verified product capability.

## Local validation

The extracted candidate was audited locally on October 20, 2026. The recorded checks included:

- installation into a fresh isolated Python environment and installation of a built wheel;
- **29 passing unit and adversarial tests**;
- synthetic Lean kernel acceptance and rejection checks;
- state and structure validation, persisted audit queue, export, replay, and package checks;
- ZIP integrity and file hash verification;
- confirmation that the original tracked research files were not rewritten.

Earlier validation attempts exposed a SQLite connection-lifetime issue, a Lean timeout, and a Python import-shadowing issue. Those were corrected and the final candidate was retested. **These results were established locally, not as a scientific discovery benchmark.** A separate GitHub Actions workflow now exists; final public-release validation must use the exact published commit.

## Getting started

The imported candidate supports Windows x64 / CPython 3.13.9. The demo creates synthetic data and executes validation and export only; it produces no research results.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements-build.lock
.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.venv\Scripts\python -m pip install --no-deps --no-build-isolation .
.venv\Scripts\python scripts/mathforge.py validate
.venv\Scripts\python -m mathforge demo --output reports/local/demo001
.venv\Scripts\python -m unittest discover -s tests -v
```

Use a new output directory. See [installation](docs/INSTALL.md), [candidate architecture](docs/ARCHITECTURE.md), and the [public release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md). The CI workflow tests the synthetic Core; the optional real Lean integration was exercised locally and is skipped by cloud CI unless an explicit reviewed toolchain is supplied. Confirm CI on the actual release commit before publication.

`FILE_MANIFEST.json` is the immutable 58-file pre-import candidate baseline (57 entries plus itself). `IMPORT_PROVENANCE.json` records the initial import mapping and hashes, including its README merge and relocated license review notice. Subsequent documentation updates do not rewrite that historical baseline. Original research history and private audit/validation files are excluded.

## Repository and research boundaries

The intended open-source release is a **clean, reusable Core**, not a mirror of the internal research environment. The original engineering inventory was roughly 94.7 MB and contained substantial third-party mathematical source material. The smaller public candidate deliberately excludes original research states, papers, private results, system-specific configuration, cached environments, and historical Git objects.

Publication of framework code should not be construed as:

- a release of unpublished mathematical results or private evidence;
- permission to redistribute unrelated third-party code or data;
- proof that an automatically generated claim is correct or novel;
- a guarantee that future experimental modules or hosted services will be released.

## Roadmap

| Stage | Goal |
| --- | --- |
| **01 · Foundation** | Audited Core imported; complete final-release CI, installation checks, ownership review, and public release. |
| **02 · Documentation** | Publish the implementation-grounded system map, full research lifecycle, API contracts, and a minimal synthetic example. |
| **03 · Research tooling** | Improve tool adapters, evidence handling, formal-verification workflows, and clearly defined scientific gates. |
| **04 · Evaluation** | Compare research workflows under controlled budgets, including failure analysis, independent validation, and ablations. |
| **05 · Research dissemination** | Release reviewed case studies and methodological papers only when their correctness, provenance, and scientific contributions are substantiated. |

The roadmap is an intention, not a delivery schedule or a claim of completed scientific work.

## Contributions and responsible use

MathForge is at a pre-release stage. After the public source is available, contributions should prioritize reproducible bug reports, tests, documentation, validation adapters, and clearly scoped improvements. Research submissions should identify assumptions, provenance, verification limits, and remaining uncertainty.

If you use any automated mathematical research workflow, **do not present model-generated reasoning as an established theorem without independent checking**. Formal proof assistants check statements under their encoded assumptions; they do not automatically settle whether those statements faithfully capture an original scientific question.

## 中文简介

**MathForge** 是一个面向数学研究的自动化框架项目，核心理念是：**生成数学候选结果只是开始，独立验证、科学门禁与可复现证据同样重要。**

长期目标是将数学问题输入、历史去重、证明与反例探索、计算验证、Lean 等形式化工具以及证据归档组织为可审计的研究流程，并明确区分 **PASS / HOLD / KILL** 等研究状态。

**当前状态（2026-10-20）：** GitHub 仓库仍处于私有预发布阶段。经过审查的精简 Core 已随 PR #1 合并，包含合成示例、测试与 CI 工作流；此前已在本地通过 29 项测试及合成 Lean 检查。完整自主数学研究系统与未发表科研资产不在此仓库内。正式公开前仍须确认源码与品牌资产权属，并在最终版本上完成 CI 和发布审核。

欢迎关注后续完整架构图、可复现演示和系统评测。本 README 将随实际实现与独立验证进度更新。

---

## License and provenance

The maintainer has **selected Apache License, Version 2.0** for the planned Core release. The [license text](./LICENSE) is already present, but the extracted package still carries a pending-approval marker until all applicable ownership, institutional/collaborator rights, third-party notices, and branding permissions are confirmed. The presence of the license text does **not** override the explicit pending-authorization notice in the source package. See the [release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md).

**MathForge · Research with evidence.**

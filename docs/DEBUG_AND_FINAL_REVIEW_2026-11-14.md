# Repository Debug & Final Review — 2026-11-14

**Repository:** `arshiataheri851-ops/arshiataheri851-ops`  
**Reviewed branch:** `main`  
**Main HEAD at review:** `af627bd1996686c104d38713535da5778580b03c`  
**Scope:** all 16 project directories, repository CI, Docker Compose integration, open AtlasRAG pull requests, and the static ERYNDEX website.

## Executive result

The main-branch checks inspected in this pass are green. The Docker Compose integration completed its full flow: all three APIs became healthy, FarsiPulse returned a real inference response, AtlasRAG ingested and retrieved a document with citations, and RelayForge accepted a subscription and queued/routed an event. The cleanup step also completed successfully.

A new CI workflow now exercises the previously uncovered projects and the website. All six jobs in the latest run passed. Together with the existing project workflows, automated checks have now been observed for all 16 project directories.

This is a repository and CI review, not a penetration test, formal security certification, legal review, or proof that every service is deployed safely in a live customer environment.

## Fixes committed

| Area | Finding | Change |
|---|---|---|
| Docker Compose CI | Required database and service credentials were missing from CI | Generate temporary, per-run credentials; pass tenant and service keys to authenticated smoke tests |
| RelayForge container | The mounted `/srv/app/data` volume had no pre-created writable directory for the non-root runtime user | Create the directory and assign ownership before switching to `appuser` |
| SignalDesk SQLite | The declared ticket-event foreign key was not enforced on connections | Enable `PRAGMA foreign_keys=ON` and add a regression test |
| ERYNDEX config | `config.js` contained literal backslash-n characters, so its assignment remained inside a line comment | Restore real line breaks and executable JavaScript |
| ERYNDEX case study | Internal links referenced paths and anchors that do not exist in this repository | Point navigation to the local homepage/work section and correct the source repository links |
| ERYNDEX quality checks | Broken local links/assets/anchors were not automatically checked | Add a standard-library HTML integrity check and JavaScript syntax checks |
| Project CI coverage | RoutePilot, SignalDesk, Grounded Document Retrieval, Market Intelligence, ML Model Serving and ERYNDEX did not have a suitable current CI path | Add `.github/workflows/portfolio-mvp-ci.yml` to run API tests and static-site checks |

### Main-branch commits from this repair pass

- `9354657bfb80d981fabd008e331ab01cb09a0d8d` — temporary CI credentials and authenticated integration smoke tests
- `80602fbdffa0f0d92ddcfdb8775e6eed5527fc3b` — expose the AtlasRAG CI tenant key to the smoke test
- `3dd089a10dc7e500eddf6d94f48535c03bbefc2f` — fix ERYNDEX JavaScript config line endings
- `5ae9c8af9fda2763e56da2f29871cff458b6cf0a` — enable SignalDesk SQLite foreign keys
- `e1c78c2bbbca7e728719d1d143c8b33f8c2b9ca1` — add SignalDesk foreign-key regression test
- `57370d2117b4db44edc6322ad7e2e599cb6db9d0` — add ERYNDEX local-link integrity check
- `e207cb0c8b59d97bdfe9b2da5d1b263eab1ce587` — add CI workflow for portfolio MVPs
- `2b0bbcd32cc39ebb072b05d51a1b11ad29b6a987` — run the ERYNDEX checker directly
- `e5bc4839ab468e2c71ce1fee7c780a162e939bf7` — fix ERYNDEX case-study links
- `40e6ef5159648cd243168303d9c61b9812fa76bd` — fix RelayForge Docker data-volume permissions
- `af627bd1996686c104d38713535da5778580b03c` — extend the portfolio CI matrix to the remaining Python projects

## Verification evidence

| Workflow | Result | Evidence |
|---|---|---|
| Docker Compose Integration | **Passed** | [Run 43598691849](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43598691849) |
| Engineering Projects CI | **Passed** | [Run 43598691769](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43598691769) |
| Advanced engineering project checks | **Passed** | [Run 43598691761](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43598691761) |
| Portfolio and MVP Project CI | **Passed — 6/6 jobs** | [Run 43598768363](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43598768363) |
| FarsiPulse real inference | **Passed** | [Run 43594528031](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43594528031) |
| FarsiPulse model evaluation | **Passed** | [Run 43594528071](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43594528071) |
| Production RAG Service CI | **Passed** | [Run 43594410627](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43594410627) |
| AtlasRAG large-corpus evaluation | **Passed** | [Run 43594410657](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43594410657) |
| Agent Workflow Orchestrator CI | **Passed** | [Run 42877450019](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/42877450019) |
| Event Stream Processing Platform CI | **Passed** | [Run 42877446721](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/42877446721) |
| Intelligent Recommendation Platform CI | **Passed** | [Run 42877146335](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/42877146335) |
| STRIDE Store CI | **Passed** | [Run 43020350890](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43020350890) |
| STRIDE Store Pages deployment workflow | **Passed** | [Run 43020351343](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43020351343) |

### Coverage across the 16 projects

| Project | Automated check evidence |
|---|---|
| Agent Workflow Orchestrator | Dedicated CI passed |
| Event Stream Processing Platform | Dedicated CI passed |
| Grounded Document Retrieval | New API regression CI passed |
| Intelligent Recommendation Platform | Dedicated CI passed |
| LLM Gateway Control Plane | Advanced engineering CI passed |
| Market Intelligence & Risk Engine | New regression CI passed |
| ML Feature Store | Advanced engineering CI passed |
| ML Model Serving Platform | New API regression CI passed |
| FarsiPulse | Engineering CI, real inference and evaluation passed |
| AtlasRAG | Python CI, large-corpus evaluation and main Compose integration passed |
| RoutePilot | New API regression CI passed |
| SignalDesk | New API regression CI and SQLite foreign-key regression passed |
| STRIDE Store | Static project CI and Pages workflow passed |
| RelayForge | Engineering CI, advanced checks and main Compose integration passed |
| Workflow Orchestration Engine | Advanced engineering CI passed |
| ERYNDEX Company Website | JavaScript syntax, local links, assets and anchors passed |

The older project-specific workflows for the first, second, fourth and STRIDE projects last ran on earlier commits than the current main HEAD. Their observed results are green, but the new matrix does not rerun every legacy workflow on every unrelated commit.

## Open AtlasRAG pull requests

Two open PRs still propose overlapping pgvector/hybrid-retrieval work. They should not both be merged independently.

### PR #4 — pgvector hybrid retrieval

- [Open PR #4](https://github.com/arshiataheri851-ops/arshiataheri851-ops/pull/4)
- Its Ruff import-order failure was corrected on branch `feat/atlasrag-pgvector-hybrid` in commit `89a742c596e740f38e4d88ae820bb623594c42d7`.
- A subsequent benchmark run exposed that the evaluation workflow still used plain `postgres:16` without the pgvector extension. The workflow now uses `pgvector/pgvector:pg16` in commit `9858039735420d79e50b531d8452c45afde8b140`.
- Python checks are green; the rerun's Compose smoke and benchmark jobs were still running at the time of this report update.

### PR #5 — tenant-scoped hybrid vector retrieval

- [Open PR #5](https://github.com/arshiataheri851-ops/arshiataheri851-ops/pull/5)
- Its earlier Compose run failed because FastEmbed rejected `intfloat/multilingual-e5-small` as a built-in model name.
- The branch was updated in commit `0757a5960a6910040d8c52bf7674ebd065a6d775` to register the published ONNX model as a custom 384-dimensional model before initialization.
- The follow-up branch checks are now green: Python 3.11/3.12, application tests, benchmark, and Docker Compose smoke all passed in [run 43598923048](https://github.com/arshiataheri851-ops/arshiataheri851-ops/actions/runs/43598923048).
- PR #5 is the more fully verified of the two overlapping alternatives at this point, but it has not been merged.

Neither PR has been merged into `main`. Select one implementation after the final branch checks and a review of the resulting schema, migrations, embedding backfill, and retrieval evaluation.

## Remaining risks — not fixed by this pass

1. Several portfolio demos intentionally lack authentication, role-based authorization, or tenant isolation. Keep them local/demo-only until those boundaries exist.
2. RoutePilot and SignalDesk still use SQLite and are not multi-tenant customer-ready services.
3. STRIDE is a frontend/storefront demonstration, not a real transactional ecommerce platform.
4. ERYNDEX's contact Worker remains source-only until deployed, configured with real secrets, rate-limited, and tested on its live host.
5. AtlasRAG's vector-search branch must pass its final Compose and retrieval-quality checks before merge. A green synthetic smoke test does not establish semantic relevance on a real authorized corpus.
6. RelayForge still needs production-host egress controls, secret management, backup/restore drills, monitoring and an independent security review.
7. No full penetration test, live-host load test, disaster-recovery exercise, or legal/privacy compliance review was performed in this pass.

## Final assessment

The repository's main integrated demo stack is now verified by a passing Docker Compose integration run, and the new CI path adds automated checks for all project directories. The concrete defects found during this pass were corrected and the relevant main-branch checks passed.

**Portfolio/demo readiness is improved; universal production readiness is not claimed.** Use FarsiPulse, AtlasRAG and RelayForge as technical case studies with their documented boundaries. Keep the remaining projects accurately labeled as MVPs, prototypes or static demonstrations until their listed access-control and operational requirements are implemented.

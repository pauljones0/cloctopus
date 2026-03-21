# EPIC: Cloctopus Dark Factory

> Autonomous software engineering via the Attractor Loop methodology.
> Specs in, verified code out. No human reads or reviews the generated code.

---

## Glossary

| Term | Definition |
|------|------------|
| **Attractor Loop** | Generate code -> build in Docker -> validate against holdout scenarios -> LLM-as-Judge score -> feedback -> iterate until convergence |
| **Holdout Scenario** | End-to-end behavioral test hidden from the coder agent via `.claudeignore`. The coder never sees these. |
| **Satisfaction Score** | 0-100 probabilistic score from the LLM Judge. Not boolean -- holistic behavioral evaluation. |
| **Convergence** | Satisfaction score >= 95 across all holdout scenarios. The loop terminates. |
| **Stall** | N consecutive iterations with no score improvement (< 5 points). Triggers escalation. |
| **Wonder/Reflect** | Two-phase stall recovery: high-temperature diagnostic brainstorm (Wonder) followed by low-temperature surgical fix (Reflect). |
| **Model Escalation** | Start with cheap model (Haiku), escalate to expensive model (Opus) on stalls, downgrade on recovery. |
| **Gene Transfusion** | Extract architectural patterns from exemplar codebases and inject as generation context. |
| **Digital Twin Universe (DTU)** | Local mock servers simulating external APIs for safe, fast, unlimited testing. |
| **Oscillation** | Score cycling pattern (e.g., 70->80->70->80) indicating the coder is flip-flopping between approaches. |
| **Regression** | A scenario that previously passed now fails after a code change. |
| **Information Barrier** | Strict separation ensuring the coder never sees holdout scenarios and the judge never sees source code. |

---

## Team Roster

| Agent | Role | Scope | Spawns In |
|-------|------|-------|-----------|
| **Archie** | System Architect | Interfaces, schemas, type contracts, technical decisions | Phase 0+ |
| **Morty** | Core Loop Developer | Attractor loop state machine, iteration logic, convergence detection | Phase 1+ |
| **Judd** | Judge System Developer | LLM-as-Judge prompts, scoring pipeline, satisfaction rubric, multi-judge consensus | Phase 2+ |
| **Scenario** | Scenario System Developer | Holdout YAML schema, scenario runner, result collection, DTU mock framework | Phase 2+ |
| **DockerDan** | Infrastructure / DevOps | Dockerfiles, container orchestration, build pipeline, sandbox isolation | Phase 0+ |
| **Huxley** | Hooks & Integration Developer | Claude Code hooks, `.claude/` config, CLI interface, team orchestration | Phase 4+ |
| **Brains** | Intelligence Developer | Wonder/Reflect, model escalation, gene transfusion, oscillation detection | Phase 3+ |
| **QALead** | Test Engineer | All test authoring, gate script implementation, integration test fixtures | Phase 0+ |
| **SecOps** | Security Officer | Information barrier enforcement, sandbox audit, secret management | Phase 0+ |
| **TechWriter** | Documentation | README, user guides, configuration reference, example specs | Phase 6 |

### Dispatch Rules

1. **Check the phase.** Only assign work from the current phase or earlier incomplete work.
2. **Check the gate.** Before starting a subphase, verify all prerequisite gates passed.
3. **Match agent to subphase.** Every subphase lists which agents are assigned.
4. **Parallelize within a phase.** Subphases with no dependencies can run concurrently.
5. **Gate before proceeding.** A subphase is not done until its binary gate returns exit 0.
6. **One agent per file.** Two agents must not edit the same file concurrently.
7. **QALead writes all tests.** Dev agents write production code; QALead writes test code.
8. **SecOps gates are blocking.** Security subphases must pass before any phase exit gate.

---

## Phase 0: Bootstrap & Project Skeleton

**Goal:** Git repo, directory structure, Docker base images, gate harness, and information barrier.
**Agents:** DockerDan, SecOps, QALead

### 0.1 Repository Scaffold

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 0.1.1 | Create directory tree: `src/loop/`, `src/judge/`, `src/scenarios/`, `src/runner/`, `src/intelligence/`, `src/hooks/`, `tests/`, `tests/fixtures/`, `tests/holdout/`, `docker/`, `docs/`, `gates/`, `specs/` | DockerDan | `[ -d src/loop ] && [ -d src/judge ] && [ -d src/scenarios ] && [ -d src/runner ] && [ -d src/intelligence ] && [ -d tests/holdout ] && [ -d gates ] && [ -d docker ]` |
| 0.1.2 | Write `gates/run_gate.sh` -- universal gate runner that takes a gate script path, runs it, prints PASS/FAIL, returns exit code | DockerDan, QALead | `bash gates/run_gate.sh gates/gate_self_test.sh` exits 0 (self-test gate that always passes) |
| 0.1.3 | Write `.claudeignore` excluding `tests/holdout/` from agent context | SecOps | `grep -q "tests/holdout" .claudeignore` |
| 0.1.4 | Write `docker/Dockerfile.sandbox` -- Python 3.12 + bash + common build tools, no network after build | DockerDan | `docker build -f docker/Dockerfile.sandbox -t cloctopus-sandbox . 2>&1 && echo PASS` exits 0 |
| 0.1.5 | Write `docker-compose.yml` with sandbox service definition | DockerDan | `docker compose config --quiet` exits 0 |
| 0.1.6 | Write `pyproject.toml` with dependencies: click, pyyaml, pydantic, anthropic, docker, httpx | DockerDan | `pip install -e . 2>&1 && python -c "import click, yaml, pydantic"` exits 0 |
| 0.1.7 | Write `__init__.py` files in all `src/` subdirectories | DockerDan | `python -c "import src.loop; import src.judge; import src.scenarios; import src.runner; import src.intelligence; import src.hooks"` exits 0 |

### 0.2 Information Barrier Verification

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 0.2.1 | Write `gates/gate_info_barrier.sh` -- verifies no file in `src/loop/`, `src/runner/` imports or reads from `tests/holdout/` | SecOps, QALead | `bash gates/gate_info_barrier.sh` exits 0 |
| 0.2.2 | Write `tests/test_info_barrier.py` -- static analysis test that greps all source for holdout path references | QALead | `python -m pytest tests/test_info_barrier.py -v` exits 0 |

### Phase 0 EXIT Gate
```bash
bash gates/gate_phase_0.sh
# Runs: 0.1.1 through 0.2.2 gates sequentially. All must pass.
```

---

## Phase 1: Core Attractor Loop

**Goal:** The generate-build-validate-score-feedback state machine.
**Depends on:** Phase 0
**Agents:** Archie, Morty, DockerDan, QALead

### 1.1 Loop State Machine

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 1.1.1 | Write `src/loop/state.py` -- Pydantic models: `LoopState` (enum: GENERATING, BUILDING, VALIDATING, SCORING, FEEDING_BACK, CONVERGED, FAILED), `IterationRecord` (iteration number, score, duration, model used, feedback), `LoopConfig` (threshold, max_iterations, stall_limit, timeout) | Archie | `python -c "from src.loop.state import LoopState, IterationRecord, LoopConfig; assert LoopState.CONVERGED.value"` exits 0 |
| 1.1.2 | Write `src/loop/engine.py` -- `AttractorLoop` class with `run()` (main entry, loops until convergence or max iterations), `step()` (single iteration: generate->build->validate->score->feedback), state transition enforcement, max iteration guard, stall counter | Morty | `python -c "from src.loop.engine import AttractorLoop"` exits 0 |
| 1.1.3 | Write `tests/test_loop_state.py` -- unit tests for state transitions: happy path (GENERATING->BUILDING->VALIDATING->SCORING->CONVERGED at score 95+), all valid transitions, invalid transition rejection | QALead | `python -m pytest tests/test_loop_state.py -v` exits 0 |
| 1.1.4 | Write `tests/test_loop_failures.py` -- unit tests for: build failure -> FEEDING_BACK, max iterations -> FAILED, stall detection (N iterations no improvement) | QALead | `python -m pytest tests/test_loop_failures.py -v` exits 0 |

### 1.2 Code Generation Interface

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 1.2.1 | Write `src/runner/coder.py` -- `CoderAgent` class: takes spec string + optional feedback string, calls Claude API, parses file blocks from response (`=== FILE: path === ... === END FILE ===`), returns dict of filepath->content | Morty | `python -c "from src.runner.coder import CoderAgent"` exits 0 |
| 1.2.2 | Write `src/runner/workspace.py` -- `WorkspaceManager`: creates temp dirs per iteration, writes files from CoderAgent output, supports snapshot (copy current best) and rollback (restore snapshot) for regression blocking | Morty, Archie | `python -c "from src.runner.workspace import WorkspaceManager"` exits 0 |
| 1.2.3 | Write `tests/test_coder.py` -- integration test: CoderAgent generates a Python file given a trivial spec (using mocked LLM client) | QALead | `python -m pytest tests/test_coder.py -v` exits 0 |

### 1.3 Docker Build Pipeline

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 1.3.1 | Write `src/runner/builder.py` -- `BuildRunner`: copies workspace into Docker container, runs build command, captures stdout/stderr, returns `BuildResult(success: bool, output: str, duration_s: float)` | DockerDan | `python -c "from src.runner.builder import BuildRunner, BuildResult"` exits 0 |
| 1.3.2 | Write `tests/test_builder.py` -- integration tests: build a known-good Python project in sandbox (passes), build a syntax-error project (fails with error captured) | QALead, DockerDan | `python -m pytest tests/test_builder.py -v` exits 0 |
| 1.3.3 | Security review: verify container has no network post-build, no host mounts beyond workspace | SecOps | `bash gates/gate_sandbox_isolation.sh` exits 0 |

### 1.4 Feedback Composer

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 1.4.1 | Write `src/loop/feedback.py` -- `FeedbackComposer`: takes `BuildResult`, list of `ScenarioResult`, `ScoredResult` from judge; produces structured feedback string for the coder (includes: build errors if any, failing scenario names + judge commentary, score delta from previous iteration, iteration count) | Morty, Archie | `python -c "from src.loop.feedback import FeedbackComposer"` exits 0 |
| 1.4.2 | Write `tests/test_feedback.py` -- tests: feedback from build failure includes error output; feedback from low judge score includes judge commentary and failing scenarios | QALead | `python -m pytest tests/test_feedback.py -v` exits 0 |

### 1.5 Loop Integration

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 1.5.1 | Write `tests/test_loop_e2e.py::test_happy_path` -- end-to-end with mocked LLM: spec -> generate -> build (pass) -> validate (mock pass) -> score (mock 100) -> CONVERGED | QALead, Morty | `python -m pytest tests/test_loop_e2e.py::test_happy_path -v` exits 0 |
| 1.5.2 | Write `tests/test_loop_e2e.py::test_two_iterations` -- first iteration scores 50, second iteration scores 96 -> CONVERGED in 2 iterations | QALead | `python -m pytest tests/test_loop_e2e.py::test_two_iterations -v` exits 0 |

### Phase 1 EXIT Gate
```bash
python -m pytest tests/ -k "loop or coder or builder or feedback" --tb=short
# ALL tests must pass.
```

---

## Phase 2: Scenario System & Judge

**Goal:** Holdout scenario YAML format, scenario runner, LLM-as-Judge scoring, stratified tiers.
**Depends on:** Phase 0 (Phase 1 can run in parallel for early subphases)
**Agents:** Archie, Scenario, Judd, DockerDan, QALead, SecOps

### 2.1 Scenario Schema & Loader

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 2.1.1 | Write `src/scenarios/schema.py` -- Pydantic models: `ScenarioStep` (type: http/exec/script, request, expected_behavior, captures), `Scenario` (id, name, tier: 1-3, description, setup_commands, steps), `ScenarioSuite` (scenarios list, metadata) | Archie, Scenario | `python -c "from src.scenarios.schema import Scenario, ScenarioSuite, ScenarioStep"` exits 0 |
| 2.1.2 | Write 3 example holdout scenarios in `tests/holdout/` as YAML: `smoke_health.yaml` (tier 1, GET /health), `basic_crud.yaml` (tier 2, POST+GET+DELETE), `edge_cases.yaml` (tier 3, invalid input, auth, timeouts) | Scenario, QALead | `python -c "import yaml; [yaml.safe_load(open(f)) for f in ['tests/holdout/smoke_health.yaml','tests/holdout/basic_crud.yaml','tests/holdout/edge_cases.yaml']]"` exits 0 |
| 2.1.3 | Write `src/scenarios/loader.py` -- `ScenarioLoader`: loads YAML files from a directory, validates against schema, returns `ScenarioSuite` | Scenario | `python -c "from src.scenarios.loader import ScenarioLoader"` exits 0 |
| 2.1.4 | Write `tests/test_scenario_schema.py` -- tests: valid YAML loads, invalid YAML rejected, tier ordering | QALead | `python -m pytest tests/test_scenario_schema.py -v` exits 0 |

### 2.2 Scenario Runner

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 2.2.1 | Write `src/scenarios/runner.py` -- `ScenarioRunner`: given a running Docker container URL and a `Scenario`, executes each step (HTTP requests via httpx, exec via docker SDK, script via subprocess), captures actual output per step, returns `ScenarioResult` (scenario_id, step_results, raw_output) | Scenario, DockerDan | `python -c "from src.scenarios.runner import ScenarioRunner, ScenarioResult"` exits 0 |
| 2.2.2 | Write `tests/test_scenario_runner.py` -- integration test: run smoke_health scenario against a fixture HTTP server in Docker | QALead | `python -m pytest tests/test_scenario_runner.py -v` exits 0 |
| 2.2.3 | Write `src/scenarios/dtu.py` -- `DigitalTwinUniverse`: lightweight mock HTTP server (using Python's http.server or FastAPI) that scenarios can reference for external API simulation; configurable responses per endpoint | Scenario, Archie | `python -m pytest tests/test_dtu.py -v` exits 0 |

### 2.3 LLM-as-Judge

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 2.3.1 | Write `src/judge/judge.py` -- `JudgeAgent`: takes scenario description + expected behavior + actual output, calls Claude API with judge prompt, parses response into `ScoredResult(score: int, commentary: str, failing_steps: list[str], passed: bool)` | Judd, Archie | `python -c "from src.judge.judge import JudgeAgent, ScoredResult"` exits 0 |
| 2.3.2 | Write `src/judge/rubric.py` -- `ScoringRubric`: configurable scoring criteria templates (strict for API contracts, lenient for UI, custom per-scenario); injected into judge prompt | Judd | `python -c "from src.judge.rubric import ScoringRubric"` exits 0 |
| 2.3.3 | Write `src/judge/consensus.py` -- `ConsensusJudge`: runs N independent judge calls, takes median score, flags high-variance results (sigma > 15) for human review | Judd, Archie | `python -c "from src.judge.consensus import ConsensusJudge"` exits 0 |
| 2.3.4 | Write `tests/test_judge.py` -- tests: judge scores a clearly-passing scenario near 100, clearly-failing near 0, partial near 50-70 (mocked LLM) | QALead | `python -m pytest tests/test_judge.py -v` exits 0 |
| 2.3.5 | Security review: verify judge prompt never includes generated source code, only behavioral output | SecOps | `bash gates/gate_judge_isolation.sh` exits 0 |

### 2.4 Stratified Validation Tiers

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 2.4.1 | Write `src/scenarios/tiers.py` -- `TierManager`: groups scenarios by tier (1=smoke, 2=standard, 3=comprehensive), enforces progression (must converge tier N before tier N+1 scenarios are evaluated), returns current active tier and eligible scenarios | Scenario, Archie | `python -c "from src.scenarios.tiers import TierManager"` exits 0 |
| 2.4.2 | Write `tests/test_tiers.py` -- tests: tier progression logic, tier 1 must pass before tier 2 activates, all-tier convergence | QALead | `python -m pytest tests/test_tiers.py -v` exits 0 |

### Phase 2 EXIT Gate
```bash
python -m pytest tests/ -k "scenario or judge or dtu or tier" --tb=short
# ALL tests must pass.
```

---

## Phase 3: Intelligence Layer

**Goal:** Model escalation, wonder/reflect, oscillation detection, regression blocking, gene transfusion.
**Depends on:** Phase 1 + Phase 2
**Agents:** Brains, Archie, Morty, QALead

### 3.1 Model Escalation

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 3.1.1 | Write `src/intelligence/escalation.py` -- `ModelEscalationManager`: tracks model tier (haiku -> sonnet -> opus), escalates after `stall_limit` iterations with < 5 point improvement, downgrades after 5 consecutive improving iterations, exposes `current_model() -> str` | Brains, Archie | `python -c "from src.intelligence.escalation import ModelEscalationManager"` exits 0 |
| 3.1.2 | Write `tests/test_escalation.py` -- tests: escalation on stall, downgrade on recovery, stays at max tier, initial tier is cheapest | QALead | `python -m pytest tests/test_escalation.py -v` exits 0 |

### 3.2 Wonder/Reflect

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 3.2.1 | Write `src/intelligence/wonder.py` -- `WonderPhase`: takes score history + failing scenarios + previous code attempts, calls LLM at high temperature (0.8), outputs `Diagnosis(hypotheses: list[str], root_causes: list[str], suggested_approach: str)` | Brains | `python -c "from src.intelligence.wonder import WonderPhase, Diagnosis"` exits 0 |
| 3.2.2 | Write `src/intelligence/reflect.py` -- `ReflectPhase`: takes `Diagnosis` from Wonder, calls LLM at low temperature (0.2), produces targeted code fix instructions injected into coder's next prompt | Brains | `python -c "from src.intelligence.reflect import ReflectPhase"` exits 0 |
| 3.2.3 | Write `tests/test_wonder_reflect.py` -- tests: wonder produces diagnosis from failure data, reflect produces actionable fix from diagnosis (mocked LLM) | QALead | `python -m pytest tests/test_wonder_reflect.py -v` exits 0 |

### 3.3 Oscillation Detection & Regression Blocking

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 3.3.1 | Write `src/intelligence/oscillation.py` -- `OscillationDetector`: maintains hash of last 4 code outputs, detects A->B->A->B cycling, returns steering text ("code alternates between two implementations -- pick one approach and commit") | Brains | `python -c "from src.intelligence.oscillation import OscillationDetector"` exits 0 |
| 3.3.2 | Write `src/intelligence/regression.py` -- `RegressionBlocker`: maintains per-scenario best scores, detects when a scenario drops below its previous best by > threshold, blocks convergence declaration until regressions are fixed, supports workspace rollback to best snapshot | Brains, Morty | `python -c "from src.intelligence.regression import RegressionBlocker"` exits 0 |
| 3.3.3 | Write `tests/test_oscillation.py` -- tests: detects ABAB pattern, no false positive on ABCD, steering text injected | QALead | `python -m pytest tests/test_oscillation.py -v` exits 0 |
| 3.3.4 | Write `tests/test_regression.py` -- tests: regression detected on score drop, no regression on improvement, rollback triggered | QALead | `python -m pytest tests/test_regression.py -v` exits 0 |

### 3.4 Gene Transfusion

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 3.4.1 | Write `src/intelligence/transfusion.py` -- `GeneTransfusion`: scans an exemplar directory, extracts patterns (file structure, naming conventions, architectural idioms) via LLM, produces `GeneContext` string that gets prepended to coder's system prompt | Brains, Archie | `python -c "from src.intelligence.transfusion import GeneTransfusion, GeneContext"` exits 0 |
| 3.4.2 | Write `tests/test_transfusion.py` -- tests: extracts patterns from a fixture exemplar project, gene context contains expected structure references | QALead | `python -m pytest tests/test_transfusion.py -v` exits 0 |

### Phase 3 EXIT Gate
```bash
python -m pytest tests/ -k "escalation or wonder or reflect or oscillation or regression or transfusion" --tb=short
# ALL tests must pass.
```

---

## Phase 4: Claude Code Integration & CLI

**Goal:** Wire everything into Claude Code hooks, CLI commands, and team orchestration.
**Depends on:** Phase 1 + 2 + 3
**Agents:** Huxley, Archie, Morty, SecOps, QALead

### 4.1 Hooks System

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 4.1.1 | Write `.claude/settings.local.json` with permission allowlist: all gate scripts, Docker commands, pip, pytest, python invocations | Huxley | `python -c "import json; d=json.load(open('.claude/settings.local.json')); assert 'permissions' in d"` exits 0 |
| 4.1.2 | Write `src/hooks/stop_hook.py` -- the "Pickle Rick" stop hook: intercepts agent exit, checks if convergence achieved, if not generates session summary and forces re-entry into attractor loop | Huxley, Morty | `python -c "from src.hooks.stop_hook import StopHook"` exits 0 |
| 4.1.3 | Write `src/hooks/context_manager.py` -- manages context window hygiene: summarizes current loop state before context clear, injects summary on resume, tracks iteration count across context resets | Huxley | `python -c "from src.hooks.context_manager import ContextManager"` exits 0 |

### 4.2 CLI Interface

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 4.2.1 | Write `src/cli.py` -- Click CLI: `cloctopus run --spec <path> --scenarios <dir> [--threshold 95] [--max-iterations 20] [--model claude-sonnet-4-20250514]`, `cloctopus status` (show current loop state), `cloctopus history` (show score curve), `cloctopus reset` (clear workspace) | Huxley, Morty | `python -m src.cli --help` exits 0 |
| 4.2.2 | Write `src/cli_orchestrator.py` -- `Orchestrator` class: wires `AttractorLoop` + `ScenarioLoader` + `ScenarioRunner` + `JudgeAgent` + `ModelEscalationManager` + `OscillationDetector` + `RegressionBlocker` + `TierManager` + `BuildRunner` + `CoderAgent` into a single runnable pipeline | Huxley, Archie | `python -c "from src.cli_orchestrator import Orchestrator"` exits 0 |

### 4.3 Agent Team Orchestration

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 4.3.1 | Write `src/hooks/team_bootstrap.py` -- creates Claude Code team, spawns Coder agent (with .claudeignore enforcing holdout blindness) and Judge agent (with source code isolation), manages inter-agent messaging | Huxley, SecOps | `python -c "from src.hooks.team_bootstrap import bootstrap_team"` exits 0 |
| 4.3.2 | Write `tests/test_integration_e2e.py::test_trivial_spec` -- full loop with real Claude API (sonnet), trivial spec ("write a Python function that returns the sum of two numbers"), 3 holdout scenarios, convergence within 5 iterations | QALead | `python -m pytest tests/test_integration_e2e.py -k trivial_spec --timeout=300` exits 0 |

### Phase 4 EXIT Gate
```bash
python -m pytest tests/ -k "hook or cli or orchestrator or integration_e2e" --tb=short
# ALL tests must pass.
```

---

## Phase 5: Hardening & Security

**Goal:** Production hardening, comprehensive security audit, resilience.
**Depends on:** Phase 4
**Agents:** SecOps, DockerDan, Morty, Archie, Brains, QALead

### 5.1 Security Hardening

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 5.1.1 | Deep information barrier audit: static analysis that coder agent context never contains holdout scenario content across all code paths | SecOps, QALead | `python -m pytest tests/test_security.py::test_info_barrier_deep -v` exits 0 |
| 5.1.2 | Docker sandbox escape review: verify no volume mounts leak host filesystem, no network after build, no privileged mode, no capability escalation | SecOps, DockerDan | `bash gates/gate_sandbox_hardened.sh` exits 0 |
| 5.1.3 | Secret management: API keys via env vars only, never logged, never in generated code, never in feedback prompts | SecOps | `bash gates/gate_no_secrets_leak.sh` exits 0 |

### 5.2 Resilience

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 5.2.1 | Timeout handling: each loop phase (generate, build, validate, score) has configurable timeout with graceful degradation (not crash) | Morty, Archie | `python -m pytest tests/test_resilience.py::test_timeouts -v` exits 0 |
| 5.2.2 | API failure retry: exponential backoff for Claude API calls (429, 529, 500), model fallback on persistent overload (sonnet -> haiku for non-critical calls) | Brains | `python -m pytest tests/test_resilience.py::test_api_retry -v` exits 0 |
| 5.2.3 | State persistence: loop state serialized to JSON on disk after each iteration, resumable after crash/interrupt via `cloctopus resume` | Morty | `python -m pytest tests/test_resilience.py::test_state_persistence -v` exits 0 |

### Phase 5 EXIT Gate
```bash
python -m pytest tests/ --tb=short && bash gates/gate_all_security.sh
# Full test regression AND all security gates must pass.
```

---

## Phase 6: Documentation & Release

**Goal:** User-facing documentation, working demo, release readiness.
**Depends on:** Phase 5
**Agents:** TechWriter, Scenario, QALead

### 6.1 Documentation

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 6.1.1 | Write `README.md`: quickstart (install, write spec, run loop), architecture overview, configuration reference, scoring rubric explanation | TechWriter | `[ -f README.md ] && [ $(wc -l < README.md) -ge 100 ]` |
| 6.1.2 | Write example spec + holdout scenarios: `specs/examples/calculator/SPEC.md` (calculator API: add, subtract, multiply, divide with error handling) + `specs/examples/calculator/holdout/` (3 tiers of scenarios) | TechWriter, Scenario | `[ -f specs/examples/calculator/SPEC.md ] && [ -d specs/examples/calculator/holdout ] && [ $(ls specs/examples/calculator/holdout/*.yaml 2>/dev/null | wc -l) -ge 3 ]` |
| 6.1.3 | Write `docs/CONFIGURATION.md`: all CLI flags, env vars, YAML config options, Docker settings, model selection | TechWriter | `[ -f docs/CONFIGURATION.md ] && [ $(wc -l < docs/CONFIGURATION.md) -ge 50 ]` |
| 6.1.4 | Write `docs/SCENARIO_FORMAT.md`: YAML schema reference with examples for HTTP, exec, and script step types | TechWriter | `[ -f docs/SCENARIO_FORMAT.md ]` |

### 6.2 Release Validation

| Sub | Action | Agents | Binary Gate |
|-----|--------|--------|-------------|
| 6.2.1 | Full E2E demo: run calculator example end-to-end, attractor loop converges to score >= 95 | QALead | `python -m pytest tests/test_e2e_demo.py --timeout=600 -v` exits 0 |
| 6.2.2 | Code quality: zero TODO/FIXME/HACK in `src/` | QALead | `[ $(grep -rn "TODO\|FIXME\|HACK" src/ 2>/dev/null | wc -l) -eq 0 ]` |
| 6.2.3 | Full test suite green | QALead | `python -m pytest tests/ --tb=short` exits 0 |

### Phase 6 EXIT Gate
```bash
python -m pytest tests/ --tb=short && [ -f README.md ] && [ -f docs/CONFIGURATION.md ] && echo "RELEASE READY"
# Full test suite + all docs exist.
```

---

## Phase Dependency Graph

```
Phase 0 (Bootstrap)
    |
    +---> Phase 1 (Core Loop) ---+
    |                            |
    +---> Phase 2 (Scenarios) ---+--> Phase 3 (Intelligence) --> Phase 4 (Integration) --> Phase 5 (Hardening) --> Phase 6 (Docs)
```

Phase 1 and Phase 2 can run in parallel after Phase 0 completes. All others are sequential.

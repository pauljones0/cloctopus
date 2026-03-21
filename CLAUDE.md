# Cloctopus -- Dark Factory Autonomous Software Engineering

## What This Is

Cloctopus is a Claude Code-native implementation of the OctopusGarden "Dark Factory" methodology. It implements an autonomous attractor loop: generate code via LLM -> build in Docker sandbox -> validate against hidden holdout scenarios -> score via LLM-as-Judge (0-100) -> feed failures back to coder -> iterate until convergence (score >= 95). No human reads or reviews the generated code. The generated codebase is treated as opaque computational weights -- correctness is inferred solely from externally observable behavior.

Full build specification: `docs/EPIC.md`

## Current Phase

**Phase 0 -- Bootstrap** NOT STARTED

Update this line as work progresses. Format: `Phase X.Y -- Description [STATUS]`

---

## Architecture

```
cloctopus/
├── CLAUDE.md              # This file -- project rules
├── .claudeignore          # Information barrier (hides tests/holdout/)
├── .claude/
│   └── settings.local.json  # Permission allowlist
├── docs/
│   ├── EPIC.md            # Phased build plan with gates
│   ├── CONFIGURATION.md   # Config reference (Phase 6)
│   └── SCENARIO_FORMAT.md # Scenario YAML reference (Phase 6)
├── src/
│   ├── loop/              # Attractor loop state machine + engine
│   │   ├── state.py       # LoopState, IterationRecord, LoopConfig
│   │   ├── engine.py      # AttractorLoop.run(), .step()
│   │   └── feedback.py    # FeedbackComposer
│   ├── judge/             # LLM-as-Judge scoring pipeline
│   │   ├── judge.py       # JudgeAgent, ScoredResult
│   │   ├── rubric.py      # ScoringRubric templates
│   │   └── consensus.py   # Multi-judge consensus
│   ├── scenarios/         # Holdout scenario system
│   │   ├── schema.py      # Scenario, ScenarioStep, ScenarioSuite
│   │   ├── loader.py      # ScenarioLoader (YAML -> models)
│   │   ├── runner.py      # ScenarioRunner (execute against Docker)
│   │   ├── dtu.py         # DigitalTwinUniverse (mock servers)
│   │   └── tiers.py       # TierManager (stratified validation)
│   ├── runner/            # Code generation + Docker build
│   │   ├── coder.py       # CoderAgent (spec -> code via LLM)
│   │   ├── builder.py     # BuildRunner (Docker build + run)
│   │   └── workspace.py   # WorkspaceManager (temp dirs, snapshots)
│   ├── intelligence/      # Adaptive convergence mechanisms
│   │   ├── escalation.py  # ModelEscalationManager (haiku->sonnet->opus)
│   │   ├── wonder.py      # WonderPhase (high-temp diagnosis)
│   │   ├── reflect.py     # ReflectPhase (low-temp surgical fix)
│   │   ├── oscillation.py # OscillationDetector (ABAB pattern)
│   │   ├── regression.py  # RegressionBlocker (per-scenario tracking)
│   │   └── transfusion.py # GeneTransfusion (exemplar extraction)
│   ├── hooks/             # Claude Code integration
│   │   ├── stop_hook.py   # Pickle Rick stop hook
│   │   ├── context_manager.py  # Context window hygiene
│   │   └── team_bootstrap.py   # Team creation + agent spawning
│   ├── cli.py             # Click CLI entry point
│   └── cli_orchestrator.py  # Top-level pipeline wiring
├── tests/
│   ├── holdout/           # HIDDEN from coder agent (.claudeignore)
│   ├── fixtures/          # Test fixture projects
│   └── test_*.py          # All test modules
├── gates/                 # Binary gate scripts
│   ├── run_gate.sh        # Universal gate runner
│   └── gate_*.sh          # Per-subphase and per-phase gates
├── scripts/               # Self-improvement loop scripts
│   ├── orchestrate.sh     # Full converge + evolve cycle
│   ├── run_scenarios.py   # Run scenarios, output JSON scores
│   └── generate_scenario.py  # Generate new harder scenarios
├── docker/
│   └── Dockerfile.sandbox # Python 3.12 sandbox image
├── docker-compose.yml
├── pyproject.toml
└── specs/
    └── examples/          # Demo specs + holdout scenarios
```

---

## Team Roster

| Agent | Role | Scope |
|-------|------|-------|
| **Archie** | System Architect | Interfaces, schemas, type contracts, technical decisions |
| **Morty** | Core Loop Developer | Attractor loop state machine, iteration logic, convergence |
| **Judd** | Judge System Developer | LLM-as-Judge, scoring rubric, multi-judge consensus |
| **Scenario** | Scenario System Developer | YAML schema, runner, DTU mocks, stratified tiers |
| **DockerDan** | Infrastructure / DevOps | Dockerfiles, containers, build pipeline, sandbox isolation |
| **Huxley** | Hooks & Integration | Claude Code hooks, CLI, settings, team orchestration |
| **Brains** | Intelligence Developer | Wonder/Reflect, escalation, oscillation, regression, genes |
| **QALead** | Test Engineer | All tests, gate scripts, integration fixtures |
| **SecOps** | Security Officer | Information barriers, sandbox audit, secret management |
| **TechWriter** | Documentation | README, guides, examples, config reference |

### Dispatch Rules

1. **Check the phase.** Only assign work from the current phase or earlier incomplete work.
2. **Check the gate.** Before starting a subphase, verify all prerequisite gates have passed.
3. **Match agent to subphase.** Every subphase in `docs/EPIC.md` lists which agents are needed.
4. **Parallelize within a phase.** Subphases with no dependency can run concurrently.
5. **Gate before proceeding.** A subphase is not done until its binary gate returns exit 0.
6. **One agent per file.** Two agents must not edit the same file concurrently.
7. **QALead writes all tests.** Dev agents write production code; QALead writes test code.
8. **SecOps gates are blocking.** Security subphases must pass before any phase exit gate.

---

## Dark Factory Philosophy

### The Attractor Loop

The system converges on correct code through iterative refinement, not one-shot generation. Each iteration produces a satisfaction score (0-100). The loop terminates when score >= 95 (configurable via `--threshold`).

This is NOT test-driven development. The judge evaluates behavioral correctness holistically using probabilistic scoring, not boolean pass/fail assertions. A score of 72 means "mostly working with gaps," not "failed."

### Information Barriers (CRITICAL)

These barriers are the foundation of the entire methodology. Violating them invalidates all results.

- **The Coder agent NEVER sees holdout scenarios.** They live in `tests/holdout/` which is listed in `.claudeignore`. The coder generates code based solely on the spec (`SPEC.md`).
- **The Judge agent NEVER sees generated source code.** It only sees behavioral output (HTTP responses, stdout, exit codes). It scores behavior, not implementation.
- **The Orchestrator manages both** but never leaks information between them. It passes the spec to the coder and the behavioral output to the judge. Never the reverse.

### Why No Human Code Review

Generated code is treated as opaque computational weights -- structurally identical to neural network parameters. Attempting to manually parse agent-generated code is as futile as tracing activation layers in an LLM. Correctness is inferred strictly from externally observable behavior against exhaustive holdout scenarios.

If the software's phenotype (behavior) is correct, the genotype (code syntax) is irrelevant.

### Convergence Over Elegance

The goal is achieving a 95+ satisfaction score. Do not optimize for:
- Human readability
- Code style or linting
- Naming conventions
- Comment coverage

These are irrelevant when the machine maintains and regenerates the code autonomously.

### Self-Improvement Loop (Continuous Evolution)

After initial convergence, the system enters a self-improvement cycle:

```
Converge (score >= 95)
    |
    v
Generate NEW harder scenario (tier 3)
    |
    v
New scenario added to holdout/
    |
    v
Next cycle must converge on ALL scenarios (including the new one)
    |
    v
Repeat -- the bar rises every cycle
```

This means the codebase is never "done." Each cycle produces a harder test that
the code must pass. Over time, the holdout suite grows from 3 scenarios to 10, 20,
or more -- each one targeting a gap the previous scenarios missed.

**How to run:**
- One-shot: `/improve` in Claude Code
- Continuous: `/loop 1h /improve` (runs every hour, 3-day session limit)
- Manual: `bash scripts/orchestrate.sh --spec SPEC.md --scenarios holdout/`

**What gets generated:**
The scenario generator reads the spec and existing scenarios, identifies coverage gaps,
and produces new adversarial scenarios targeting: edge cases, security boundaries,
malformed inputs, race conditions, and failure modes.

---

## Conventions

### Spec Format

Specs live in `specs/` as `SPEC.md` files. They describe WHAT the code should do, not HOW. Implementation is the coder's problem.

A spec must include:
- Clear description of the software's purpose
- Input/output interface contracts (API routes, CLI args, file formats)
- Expected behavioral characteristics (response codes, error messages, data formats)
- External dependencies that require DTU mocking

### Holdout Scenario Format

YAML files in `tests/holdout/`. Each scenario has:

```yaml
id: scenario-name
name: Human-readable scenario name
tier: 1  # 1=smoke, 2=standard, 3=comprehensive
description: What this scenario tests
steps:
  - type: http
    method: GET
    path: /health
    expected_status: 200
    expected_body_contains: "ok"
  - type: exec
    command: "python -c 'print(1+1)'"
    expected_stdout_contains: "2"
  - type: script
    script: |
      import requests
      r = requests.get("http://localhost:8080/api/items")
      assert r.status_code == 200
```

### Scoring Rubric

| Range | Meaning |
|-------|---------|
| 0-30 | Fundamentally broken (does not build or crashes immediately) |
| 31-60 | Partially working (some scenarios pass, major gaps) |
| 61-80 | Mostly working (edge cases failing) |
| 81-94 | Nearly correct (minor behavioral deviations) |
| 95-100 | Converged (meets spec as judged by LLM) |

### Gate Scripts

Every subphase has a binary gate. Gates live in `gates/` as shell scripts. They MUST return exit 0 (pass) or exit 1 (fail). No partial credit.

Run any gate: `bash gates/run_gate.sh gates/gate_X_Y_Z.sh`

### Git

- Commit after each subphase gate passes
- Commit message format: `X.Y.Z: description` (e.g., `1.1.1: loop state machine schema`)
- Do not commit code that fails its binary gate

### Docker

- All generated code executes inside `cloctopus-sandbox` container
- No network access after build step
- No host filesystem mounts beyond the workspace directory
- Build timeout: 120 seconds
- Scenario execution timeout: 60 seconds per scenario

### Python

- Python 3.12+
- Pydantic for all data models
- Type hints on all function signatures
- No global mutable state
- Errors wrapped with context: `raise ValueError(f"operation failed: {detail}")`

---

## Phase Progression Checklist

When advancing to a new phase:

- [ ] All subphase binary gates for the current phase pass
- [ ] Phase EXIT gate command passes
- [ ] SecOps gates within the phase are signed off
- [ ] All code is committed with passing gates
- [ ] No skipped subphases
- [ ] Update "Current Phase" at the top of this file

---

## Quick Reference: Gate Commands

```bash
# Phase 0 -- Bootstrap
bash gates/gate_phase_0.sh

# Phase 1 -- Core Loop
python -m pytest tests/ -k "loop or coder or builder or feedback" --tb=short

# Phase 2 -- Scenarios & Judge
python -m pytest tests/ -k "scenario or judge or dtu or tier" --tb=short

# Phase 3 -- Intelligence
python -m pytest tests/ -k "escalation or wonder or reflect or oscillation or regression or transfusion" --tb=short

# Phase 4 -- Integration
python -m pytest tests/ -k "hook or cli or orchestrator or integration_e2e" --tb=short

# Phase 5 -- Hardening
python -m pytest tests/ --tb=short && bash gates/gate_all_security.sh

# Phase 6 -- Release
python -m pytest tests/ --tb=short && [ -f README.md ] && [ -f docs/CONFIGURATION.md ]
```

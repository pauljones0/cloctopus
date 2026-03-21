# Cloctopus

A Claude Code-native implementation of [OctopusGarden](https://github.com/foundatron/octopusgarden) -- the "Dark Factory" autonomous software engineering methodology. Write a spec, walk away, come back to working code that keeps getting better.

**The twist:** after your code converges, cloctopus automatically generates new, harder test scenarios and re-converges against them. The quality bar rises every cycle without human intervention.

## How It Works

```
SPEC.md ──> Coder generates code ──> Docker builds it
                                          │
Score >= 95? ←── Judge scores behavior ←── Scenarios test it
  │    │                                       │
  │    └── No? Feedback ───────────────────────┘
  │
  └── Yes? Generate NEW harder scenario, repeat
```

Three agents with strict information barriers:
- **Coder** -- reads your spec, writes code. Cannot see test scenarios.
- **Judge** -- scores behavioral output. Cannot see source code.
- **Orchestrator** -- manages the loop, enforces barriers between agents.

## Before You Start

You need:
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- [Docker](https://docs.docker.com/get-docker/) running
- Python 3.12+

## Setup

Clone this repo into your project directory, then add **one file**:

### `SPEC.md` (required)

Describe what you want built. Be precise about interfaces -- the coder has no other context.

```markdown
# Todo API

REST API for todo items.

## Endpoints
- POST /todos -- Body: {"title": "string", "done": false}. Returns 201.
- GET /todos -- Returns 200 + JSON array.
- DELETE /todos/:id -- Returns 204 or 404.

## Requirements
- Python with FastAPI
- In-memory storage
```

### `holdout/` scenarios (optional)

You can write YAML test scenarios manually in a `holdout/` directory, or **skip this entirely** -- cloctopus auto-generates starter scenarios from your spec.

### `.claudeignore` (auto-created)

Contains `holdout/` to hide scenarios from the coder agent. Created automatically if missing.

## Commands

| Command | What it does |
|---------|-------------|
| `/factory` | Launch the full 3-agent team (Coder + Judge + Orchestrator). Bootstraps scenarios if none exist, iterates until convergence, then generates a new harder scenario. |
| `/improve` | Single-agent mode: score current code, fix failures, generate a new harder scenario. Simpler but no agent isolation. |
| `/loop 1h /improve` | Run `/improve` every hour. The codebase continuously evolves. Sessions auto-expire after 3 days. |

You can also run the loop directly:

```bash
bash scripts/orchestrate.sh --spec SPEC.md --scenarios holdout/ --threshold 95
```

## What's Configured Behind the Scenes

### Agent Definitions (`.claude/agents/`)

| Agent | Model | Access |
|-------|-------|--------|
| `coder.md` | Sonnet | Reads SPEC.md only. Scenario-blind. |
| `judge.md` | Opus | Reads holdout scenarios. Source-blind. |
| `orchestrator.md` | Default | Manages both. Enforces the barrier. |

### Information Barrier (4 layers)

1. `.claudeignore` -- hides `holdout/` from agent context
2. `.claude/settings.local.json` -- deny rules block explicit reads of holdout files
3. Agent definitions -- role constraints baked into each agent's prompt
4. Orchestrator -- never forwards scenario content to Coder or source code to Judge

### Permissions (`.claude/settings.local.json`)

Pre-approved: gate scripts, Docker commands, pytest, pip, git, scenario scripts. This prevents permission prompts from stalling autonomous execution.

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `orchestrate.sh` | Full converge-then-evolve cycle |
| `run_scenarios.py` | Run all holdout scenarios, output scores (supports `--json`) |
| `generate_scenario.py` | Generate a new harder scenario targeting coverage gaps |
| `bootstrap_scenarios.py` | Generate initial tier 1-3 scenarios from spec alone |

## Self-Improvement Cycle

Each cycle: converge (score >= 95) then evolve (generate harder scenario). Over time your holdout suite grows from 3 scenarios to 10, 20+ -- each targeting gaps the previous ones missed (adversarial inputs, security boundaries, race conditions, failure modes).

## Building Cloctopus Itself

See `docs/EPIC.md` for the phased build plan (6 phases, 10 named agents, gated subphases) and `KICKOFF.md` for the multi-agent team prompt.

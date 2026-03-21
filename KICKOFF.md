# Kickoff Prompt

Copy and paste the following prompt into Claude Code to start the multi-agent build:

---

```
Read CLAUDE.md and docs/EPIC.md completely. These define the cloctopus project -- a Claude Code-native autonomous software engineering loop (Dark Factory). You are the team lead orchestrator.

Execute the following:

1. CREATE THE TEAM
   Use TeamCreate to create team "cloctopus-factory" with description "Building the cloctopus Dark Factory autonomous engineering system".

2. PHASE 0 TASKS
   Create tasks from docs/EPIC.md Phase 0. Each subphase (0.1.1, 0.1.2, ... 0.2.2) becomes a task.

3. SPAWN PHASE 0 AGENTS (in parallel)
   Spawn these agents using the Agent tool with team_name="cloctopus-factory":

   a) Agent name="DockerDan" -- Infrastructure/DevOps agent.
      Prompt: "You are DockerDan, the infrastructure and DevOps agent for cloctopus. Read CLAUDE.md for project rules. Your Phase 0 tasks: create directory tree (0.1.1), write gates/run_gate.sh (0.1.2), write docker/Dockerfile.sandbox (0.1.4), write docker-compose.yml (0.1.5), write pyproject.toml (0.1.6), write __init__.py files (0.1.7). After completing each subphase, run its binary gate from docs/EPIC.md. Report results via SendMessage."

   b) Agent name="SecOps" -- Security officer agent.
      Prompt: "You are SecOps, the security officer for cloctopus. Read CLAUDE.md for project rules. Your Phase 0 tasks: write .claudeignore excluding tests/holdout/ (0.1.3), write gates/gate_info_barrier.sh (0.2.1). After completing each subphase, run its binary gate. Report results via SendMessage."

   c) Agent name="QALead" -- Test engineer agent.
      Prompt: "You are QALead, the test engineer for cloctopus. Read CLAUDE.md for project rules. Your Phase 0 tasks: help with gates/run_gate.sh (0.1.2), write tests/test_info_barrier.py (0.2.2). After completing each subphase, run its binary gate. Report results via SendMessage."

4. PHASE MANAGEMENT PROTOCOL
   - Wait for all Phase 0 agents to report gate results
   - Run the Phase 0 EXIT gate: bash gates/gate_phase_0.sh
   - If it passes, update CLAUDE.md "Current Phase" to "Phase 1 -- Core Loop"
   - Spawn new agents as needed (Archie, Morty) for Phase 1
   - Shutdown agents no longer needed via SendMessage shutdown_request
   - Continue phase-by-phase through docs/EPIC.md

5. RULES
   - Never skip a gate. Every subphase gate must pass before marking the task complete.
   - Never start a phase until the previous phase EXIT gate passes.
   - Phase 1 and Phase 2 can run in parallel after Phase 0 (see dependency graph in EPIC.md).
   - Commit after each passing subphase gate with message format "X.Y.Z: description".
   - If a gate fails, diagnose and fix before proceeding. Do not skip.

Begin now.
```

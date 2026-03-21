Launch the Dark Factory as a multi-agent team.

This spawns 3 agents with strict information barriers:
- **Coder (Morty)**: Generates code from SPEC.md. Cannot see holdout scenarios.
- **Judge (Meeseeks)**: Scores behavioral output. Cannot see source code.
- **Orchestrator (Rick)**: Manages the loop, enforces barriers, triggers evolution.

## Execution

You are the Orchestrator. Follow the workflow defined in `.claude/agents/orchestrator.md`:

1. **Bootstrap**: If `holdout/` has no YAML files, run:
   `python scripts/bootstrap_scenarios.py --spec SPEC.md --output holdout/`

2. **Create team**: Use TeamCreate with name "dark-factory"

3. **Spawn Coder**: Use Agent tool with subagent_type="general-purpose", name="Coder".
   Prompt: "You are the Coder agent (Morty). Read `.claude/agents/coder.md` for your rules. Then read SPEC.md and generate the full implementation. Report completion via SendMessage when done."
   IMPORTANT: Do NOT include any scenario content in the prompt.

4. **Run the loop**:
   - Wait for Coder to complete
   - Build: `docker build -t dark-factory-app . && docker run -d -p 8080:8080 --name dark-factory-app dark-factory-app`
   - Score: `python scripts/run_scenarios.py --scenarios holdout/ --json`
   - If score >= 95: converged
   - If score < 95: extract failure commentary (NOT scenario content), send to Coder, repeat

5. **Spawn Judge** (for complex scoring): Use Agent tool with name="Judge".
   Prompt: "You are the Judge agent (Meeseeks). Read `.claude/agents/judge.md` for your rules. Score the following execution results against the holdout scenarios..."
   Only spawn Judge when deterministic scoring from run_scenarios.py is insufficient.

6. **Evolve**: After convergence, run:
   `python scripts/generate_scenario.py --spec SPEC.md --existing-scenarios holdout/ --output holdout/evolved_N.yaml --tier 3`

7. **Report**: Print final score, iteration count, scenario count, and what the new scenario tests.

8. **Cleanup**: Stop Docker, shutdown agents, delete team.

## Information Barrier Enforcement

- NEVER include holdout YAML content in messages to Coder
- NEVER include source code in messages to Judge
- Only pass: failure commentary, score numbers, step descriptions (not step expectations)

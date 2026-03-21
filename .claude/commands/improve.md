Run the Dark Factory self-improvement cycle on this project.

## What this does

1. **Score**: Run all holdout scenarios against the current codebase via `python scripts/run_scenarios.py --scenarios holdout/ --json`
2. **Converge**: If score < 95, read SPEC.md and fix the failing code. Do NOT read or access the `holdout/` directory. Iterate until all scenarios pass.
3. **Evolve**: Once converged, generate a NEW harder holdout scenario via `python scripts/generate_scenario.py --spec SPEC.md --existing-scenarios holdout/ --output holdout/evolved_$(ls holdout/*.yaml | wc -l).yaml --tier 3`
4. **Report**: Print the final score, number of scenarios, and what the new scenario tests.

## Rules

- You CANNOT read, list, or access anything in the `holdout/` directory. It is hidden from you via .claudeignore.
- Only use SPEC.md as your source of truth for what the code should do.
- Do NOT write your own tests. The external judge evaluates your code.
- Do NOT ask for human input. Just iterate until converged, then evolve.
- After evolving, report what you did and the new scenario count.

## Execution

First, check if the codebase builds and the app starts. If not, fix build issues first.
Then run `python scripts/run_scenarios.py --scenarios holdout/ --json` to get current scores.
Parse the JSON output. If `aggregate_score >= 95`, skip to evolution.
Otherwise, read the failing scenario commentaries and fix the code. Re-run scenarios. Repeat.
Once converged, generate the new scenario and report completion.

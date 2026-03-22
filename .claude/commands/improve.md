Run the Dark Factory self-improvement cycle on this project.

## What this does

1. **Score**: Run all holdout scenarios against the current codebase via `python scripts/run_scenarios.py --scenarios holdout/ --json`
2. **Converge**: If score < 95, read SPEC.md and fix the failing code. Do NOT read or access the `holdout/` directory. Iterate until all scenarios pass.
3. **Improve**: Once converged, make ONE small focused improvement to the codebase (error handling, robustness, performance, security, or tech debt). Keep it under ~30 lines changed. Do NOT change the external API contract.
4. **Verify**: Re-run all scenarios to confirm the improvement didn't cause regressions. If score drops below 95, revert the improvement via `git checkout -- .` and continue.
5. **Evolve**: Generate a NEW harder holdout scenario via `python scripts/generate_scenario.py --spec SPEC.md --existing-scenarios holdout/ --output holdout/evolved_$(ls holdout/*.yaml | wc -l).yaml --tier 3`
6. **Report**: Print the final score, number of scenarios, what was improved, and what the new scenario tests.

## Rules

- You CANNOT read, list, or access anything in the `holdout/` directory. It is hidden from you via .claudeignore.
- Only use SPEC.md as your source of truth for what the code should do.
- Do NOT write your own tests. The external judge evaluates your code.
- Do NOT ask for human input. Just iterate until converged, improve, verify, evolve, then report.
- After evolving, report what you did and the new scenario count.

## Execution

First, check if `holdout/` has any `.yaml` files. If not, bootstrap initial scenarios:
`python scripts/bootstrap_scenarios.py --spec SPEC.md --output holdout/`

Then check if the codebase builds and the app starts. If not, fix build issues first.
Run `python scripts/run_scenarios.py --scenarios holdout/ --json` to get current scores.
Parse the JSON output. If `aggregate_score >= 95`, skip to the improvement step.
Otherwise, read the failing scenario commentaries and fix the code. Re-run scenarios. Repeat.

Once converged (score >= 95):
1. Make ONE small improvement. Pick the highest-impact option from: error handling, robustness, performance, security, tech debt reduction. Keep it under ~30 lines. Do NOT change the API contract.
2. Re-run all scenarios. If score drops below 95, revert with `git checkout -- .` and skip the improvement.
3. Generate the new scenario and report completion.

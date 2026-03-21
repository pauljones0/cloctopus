Run the self-improvement loop continuously. This is the "set it and forget it" version.

Execute the full orchestration script:

```bash
bash scripts/orchestrate.sh --spec SPEC.md --scenarios holdout/ --threshold 95 --max-iterations 20
```

Monitor the output. Each cycle:
1. Runs all scenarios
2. Fixes code until converged (score >= 95)
3. Generates a new harder scenario
4. Reports completion

To run this on a recurring schedule, use:
```
/loop 1h /improve
```

This will run the improvement cycle every hour, continuously generating new scenarios
and raising the quality bar. The session must stay open (3-day auto-expiry applies).

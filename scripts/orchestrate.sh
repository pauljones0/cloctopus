#!/usr/bin/env bash
# orchestrate.sh -- Dark Factory Self-Improvement Loop
#
# This script runs the full converge-then-evolve cycle:
#   1. Run all holdout scenarios against the current codebase
#   2. If score < threshold, feed failures back to coder and re-run
#   3. Once converged (score >= threshold), generate a NEW harder scenario
#   4. The new scenario automatically raises the bar for the next cycle
#
# Usage:
#   bash scripts/orchestrate.sh [--spec SPEC.md] [--scenarios holdout/] [--threshold 95] [--max-iterations 20]
#
# Environment:
#   ANTHROPIC_API_KEY  -- Required for LLM judge and scenario generation
#   CLOCTOPUS_MODEL    -- Model for coder (default: claude-sonnet-4-20250514)
#   CLOCTOPUS_JUDGE    -- Model for judge (default: claude-haiku-4-5-20251001)

set -euo pipefail

# --- Defaults ---
SPEC="${1:---spec}"
SPEC_PATH="SPEC.md"
SCENARIO_DIR="holdout"
THRESHOLD=95
MAX_ITERATIONS=20
ITERATION=0
BEST_SCORE=0

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --spec) SPEC_PATH="$2"; shift 2 ;;
    --scenarios) SCENARIO_DIR="$2"; shift 2 ;;
    --threshold) THRESHOLD="$2"; shift 2 ;;
    --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "============================================"
echo "  CLOCTOPUS DARK FACTORY -- SELF-IMPROVEMENT"
echo "============================================"
echo "Spec:           $SPEC_PATH"
echo "Scenarios:      $SCENARIO_DIR"
echo "Threshold:      $THRESHOLD"
echo "Max iterations: $MAX_ITERATIONS"
echo "============================================"
echo ""

# --- Phase 0: Bootstrap scenarios if none exist ---
SCENARIO_COUNT=$(ls "$SCENARIO_DIR"/*.yaml 2>/dev/null | wc -l)
if [ "$SCENARIO_COUNT" -eq 0 ]; then
  echo "[BOOTSTRAP] No scenarios found in $SCENARIO_DIR"
  echo "Generating initial holdout scenarios from spec..."
  echo ""
  python scripts/bootstrap_scenarios.py --spec "$SPEC_PATH" --output "$SCENARIO_DIR"
  echo ""
  SCENARIO_COUNT=$(ls "$SCENARIO_DIR"/*.yaml 2>/dev/null | wc -l)
  if [ "$SCENARIO_COUNT" -eq 0 ]; then
    echo "[FATAL] Could not generate any scenarios. Write them manually."
    exit 1
  fi
  echo "[OK] $SCENARIO_COUNT scenarios bootstrapped. Starting convergence loop."
  echo ""
fi

# --- Phase 1: Convergence Loop ---
echo "[PHASE 1] Convergence Loop -- iterating until score >= $THRESHOLD"
echo ""

while [ "$ITERATION" -lt "$MAX_ITERATIONS" ]; do
  ITERATION=$((ITERATION + 1))
  echo "--- Iteration $ITERATION / $MAX_ITERATIONS ---"

  # Run scenarios and capture JSON output
  RESULT=$(python scripts/run_scenarios.py --scenarios "$SCENARIO_DIR" --json 2>/dev/null || echo '{"aggregate_score": 0, "results": [], "error": "runner failed"}')

  SCORE=$(echo "$RESULT" | python -c "import sys,json; print(json.load(sys.stdin).get('aggregate_score', 0))" 2>/dev/null || echo "0")
  echo "Score: $SCORE / 100"

  # Track best
  if [ "$(echo "$SCORE > $BEST_SCORE" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    BEST_SCORE="$SCORE"
    echo "New best score: $BEST_SCORE"
  fi

  # Check convergence
  if [ "$(echo "$SCORE >= $THRESHOLD" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    echo ""
    echo "[CONVERGED] Score $SCORE >= threshold $THRESHOLD after $ITERATION iterations"
    break
  fi

  # Extract failures for feedback
  FAILURES=$(echo "$RESULT" | python -c "
import sys, json
data = json.load(sys.stdin)
for r in data.get('results', []):
    if r.get('score', 0) < 95:
        print(f\"- {r['scenario_id']}: {r.get('score', 0)}/100 -- {r.get('commentary', 'no details')}\")
" 2>/dev/null || echo "- Could not parse failures")

  echo "Failing scenarios:"
  echo "$FAILURES"
  echo ""

  # Feed back to coder via Claude Code headless mode
  echo "[FEEDBACK] Sending failures to coder agent..."
  claude -p "You are fixing code based on test feedback. Read $SPEC_PATH for the spec.

The following scenarios are failing (score < $THRESHOLD):
$FAILURES

Current score: $SCORE / $THRESHOLD required.
Iteration: $ITERATION / $MAX_ITERATIONS

Fix the code to pass these scenarios. Do NOT read or access the $SCENARIO_DIR directory.
Do NOT ask for clarification. Just fix the code." \
    --allowedTools "Read,Edit,Write,Bash(pip*),Bash(python*),Bash(docker*)" \
    2>/dev/null || echo "[WARN] Coder agent failed, retrying next iteration"

  echo ""
done

if [ "$(echo "$SCORE < $THRESHOLD" | bc -l 2>/dev/null || echo 1)" = "1" ] && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
  echo ""
  echo "[FAILED] Did not converge after $MAX_ITERATIONS iterations. Best score: $BEST_SCORE"
  echo "Consider: refining the spec, simplifying scenarios, or increasing max iterations."
  exit 1
fi

# --- Phase 2: Small Improvement ---
echo ""
echo "[PHASE 2] Small Improvement -- making one focused improvement to the codebase"
echo ""

claude -p "You are improving a converged codebase. Read $SPEC_PATH for the spec.

The code currently passes all holdout scenarios with a score of $SCORE / 100.
Your job is to make ONE small, focused improvement. Pick exactly one from this list:

- Harden error handling: find a place where an unexpected input could cause a crash or
  unclear error message, and add a guard with a clear error response.
- Improve robustness: find a place where a missing field, null value, or type mismatch
  could slip through, and add validation.
- Reduce technical debt: find duplicated logic, an overly complex function, or a magic
  number, and clean it up.
- Improve performance: find an obvious inefficiency (N+1 query, redundant computation,
  unnecessary allocation) and fix it.
- Strengthen security: find an input that isn't sanitized, a header that's missing, or
  a permission check that could be tighter.

RULES:
- Make exactly ONE improvement. Do not refactor the entire codebase.
- The improvement must be small: no more than ~30 lines changed.
- Do NOT change the external API contract (endpoints, request/response shapes, exit codes).
- Do NOT read or access the $SCENARIO_DIR directory.
- Do NOT ask for clarification. Just pick the highest-impact small fix and make it.
- Briefly describe what you changed and why in a single paragraph at the end." \
  --allowedTools "Read,Edit,Write,Bash(pip*),Bash(python*),Bash(docker*)" \
  2>/dev/null || echo "[WARN] Improvement agent failed, continuing to verification"

echo ""

# --- Phase 2b: Re-run scenarios to verify improvement didn't break anything ---
echo "[PHASE 2b] Verifying improvement didn't cause regressions..."
echo ""

VERIFY_RESULT=$(python scripts/run_scenarios.py --scenarios "$SCENARIO_DIR" --json 2>/dev/null || echo '{"aggregate_score": 0, "results": [], "error": "runner failed"}')
VERIFY_SCORE=$(echo "$VERIFY_RESULT" | python -c "import sys,json; print(json.load(sys.stdin).get('aggregate_score', 0))" 2>/dev/null || echo "0")
echo "Post-improvement score: $VERIFY_SCORE / 100"

if [ "$(echo "$VERIFY_SCORE < $THRESHOLD" | bc -l 2>/dev/null || echo 1)" = "1" ]; then
  echo "[REGRESSION] Improvement broke something (score dropped to $VERIFY_SCORE). Reverting..."
  git checkout -- . 2>/dev/null || echo "[WARN] Could not revert, manual cleanup needed"
  echo "Reverted. Continuing to evolution with original code."
else
  echo "[OK] Improvement verified -- all scenarios still pass."
fi

echo ""

# --- Phase 3: Evolution -- Generate a new harder scenario ---
echo ""
echo "[PHASE 3] Evolution -- generating a new holdout scenario"
echo ""

SCENARIO_COUNT=$(ls "$SCENARIO_DIR"/*.yaml 2>/dev/null | wc -l)
NEXT_NUM=$((SCENARIO_COUNT + 1))

python scripts/generate_scenario.py \
  --spec "$SPEC_PATH" \
  --existing-scenarios "$SCENARIO_DIR" \
  --output "$SCENARIO_DIR/evolved_${NEXT_NUM}.yaml" \
  --tier 3

if [ $? -eq 0 ]; then
  echo "[EVOLVED] New scenario written to $SCENARIO_DIR/evolved_${NEXT_NUM}.yaml"
  echo "Next run of the loop will include this scenario, raising the bar."
else
  echo "[WARN] Scenario generation failed. Manual scenario authoring recommended."
fi

echo ""
echo "============================================"
echo "  CYCLE COMPLETE"
echo "  Final score: $SCORE"
echo "  Total scenarios: $((SCENARIO_COUNT + 1))"
echo "  Run again to converge on the new scenario"
echo "============================================"

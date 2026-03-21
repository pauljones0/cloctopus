#!/usr/bin/env python3
"""Run all holdout scenarios against the current codebase and output scores.

Executes each YAML scenario, scores the results, and outputs either
a human-readable table or JSON (with --json flag) for machine consumption.

Usage:
    python scripts/run_scenarios.py --scenarios holdout/
    python scripts/run_scenarios.py --scenarios holdout/ --json
    python scripts/run_scenarios.py --scenarios holdout/ --target http://localhost:8080
"""

import argparse
import json
import subprocess
import sys
import time
import yaml
from pathlib import Path


def load_scenarios(scenario_dir: str) -> list[dict]:
    """Load and sort all scenario YAML files by tier."""
    scenarios = []
    for f in sorted(Path(scenario_dir).glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh)
                if data and "id" in data:
                    data["_file"] = str(f)
                    scenarios.append(data)
        except Exception as e:
            print(f"[WARN] Skipping {f}: {e}", file=sys.stderr)
    return sorted(scenarios, key=lambda s: (s.get("tier", 99), s.get("id", "")))


def execute_http_step(step: dict, target: str, captures: dict) -> dict:
    """Execute a single HTTP step and return the result."""
    import urllib.request
    import urllib.error

    method = step.get("method", "GET")
    path = step.get("path", "/")

    # Substitute captured values
    for key, val in captures.items():
        path = path.replace(f"{{{key}}}", str(val))

    url = f"{target.rstrip('/')}{path}"
    body = step.get("body")
    if body:
        for key, val in captures.items():
            body = body.replace(f"{{{key}}}", str(val))

    headers = step.get("headers", {})
    headers.setdefault("Content-Type", "application/json")

    try:
        data = body.encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_body = resp.read().decode()
            return {
                "status": resp.status,
                "body": response_body,
                "headers": dict(resp.headers),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "body": e.read().decode() if e.fp else "",
            "headers": dict(e.headers) if e.headers else {},
            "error": None,  # HTTP errors are expected results, not failures
        }
    except Exception as e:
        return {
            "status": 0,
            "body": "",
            "headers": {},
            "error": str(e),
        }


def execute_exec_step(step: dict, captures: dict) -> dict:
    """Execute a command step."""
    command = step.get("command", "echo test")
    for key, val in captures.items():
        command = command.replace(f"{{{key}}}", str(val))

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": None,
        }
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": "", "error": str(e)}


def score_step(step: dict, result: dict) -> tuple[int, str]:
    """Score a single step result against expectations. Returns (score, commentary)."""
    issues = []
    total_checks = 0
    passed_checks = 0

    if step.get("type") == "http":
        # Check status code
        if "expected_status" in step:
            total_checks += 1
            expected = step["expected_status"]
            actual = result.get("status", 0)
            if actual == expected:
                passed_checks += 1
            else:
                issues.append(f"Expected status {expected}, got {actual}")

        # Check body contains
        if "expected_body_contains" in step:
            total_checks += 1
            expected_text = step["expected_body_contains"]
            actual_body = result.get("body", "")
            if expected_text in actual_body:
                passed_checks += 1
            else:
                issues.append(f"Body missing expected text: '{expected_text}'")

        # Check headers
        for header, expected_val in step.get("expected_headers", {}).items():
            total_checks += 1
            actual_val = result.get("headers", {}).get(header, "")
            if expected_val.lower() in actual_val.lower():
                passed_checks += 1
            else:
                issues.append(f"Header {header}: expected '{expected_val}', got '{actual_val}'")

    elif step.get("type") == "exec":
        if "expected_exit_code" in step:
            total_checks += 1
            if result.get("exit_code") == step["expected_exit_code"]:
                passed_checks += 1
            else:
                issues.append(f"Expected exit {step['expected_exit_code']}, got {result.get('exit_code')}")

        if "expected_stdout_contains" in step:
            total_checks += 1
            if step["expected_stdout_contains"] in result.get("stdout", ""):
                passed_checks += 1
            else:
                issues.append(f"Stdout missing: '{step['expected_stdout_contains']}'")

    # Connection errors are automatic 0
    if result.get("error"):
        return 0, f"Connection error: {result['error']}"

    if total_checks == 0:
        return 100, "No assertions to check"

    score = int((passed_checks / total_checks) * 100)
    commentary = "; ".join(issues) if issues else "All checks passed"
    return score, commentary


def run_scenario(scenario: dict, target: str) -> dict:
    """Run a single scenario and return scored results."""
    captures = {}
    step_results = []
    total_score = 0
    step_count = len(scenario.get("steps", []))

    for i, step in enumerate(scenario.get("steps", [])):
        step_type = step.get("type", "http")

        if step_type == "http":
            result = execute_http_step(step, target, captures)
        elif step_type == "exec":
            result = execute_exec_step(step, captures)
        elif step_type == "script":
            result = execute_exec_step(
                {"command": f"python -c '{step.get('script', '')}'"},
                captures,
            )
        else:
            result = {"error": f"Unknown step type: {step_type}"}

        # Process captures (simple JSONPath-like extraction)
        for capture_name, capture_expr in step.get("capture", {}).items():
            try:
                if capture_expr.startswith("$."):
                    field = capture_expr[2:]
                    body = json.loads(result.get("body", "{}"))
                    captures[capture_name] = body.get(field, "")
            except (json.JSONDecodeError, KeyError):
                pass

        step_score, commentary = score_step(step, result)
        total_score += step_score
        step_results.append({
            "step": i + 1,
            "type": step_type,
            "score": step_score,
            "commentary": commentary,
        })

    aggregate = int(total_score / step_count) if step_count > 0 else 0

    return {
        "scenario_id": scenario.get("id", "unknown"),
        "scenario_name": scenario.get("name", "Unknown"),
        "tier": scenario.get("tier", 0),
        "score": aggregate,
        "step_results": step_results,
        "commentary": "; ".join(
            sr["commentary"]
            for sr in step_results
            if sr["score"] < 100
        ) or "All steps passed",
    }


def print_table(results: list[dict], aggregate: float):
    """Print human-readable results table."""
    print()
    print(f"{'#':<4} {'Scenario':<30} {'Tier':<6} {'Score':<10} {'Verdict'}")
    print("-" * 70)
    for i, r in enumerate(results, 1):
        verdict = "PASS" if r["score"] >= 95 else "FAIL"
        print(f"{i:<4} {r['scenario_name']:<30} {r['tier']:<6} {r['score']}/100    {verdict}")
    print("-" * 70)
    print(f"{'':4} {'AGGREGATE':<30} {'':6} {aggregate:.1f}/100")
    print()


def main():
    parser = argparse.ArgumentParser(description="Run holdout scenarios")
    parser.add_argument("--scenarios", required=True, help="Scenario YAML directory")
    parser.add_argument("--target", default="http://localhost:8080", help="Target URL")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    parser.add_argument("--all", action="store_true", help="Run all scenarios (alias)")
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenarios)
    if not scenarios:
        output = {"aggregate_score": 0, "results": [], "error": "No scenarios found"}
        if args.json:
            print(json.dumps(output))
        else:
            print("[ERROR] No scenario YAML files found in", args.scenarios)
        sys.exit(1)

    results = []
    for scenario in scenarios:
        result = run_scenario(scenario, args.target)
        results.append(result)

    total = sum(r["score"] for r in results)
    aggregate = total / len(results) if results else 0

    output = {
        "aggregate_score": round(aggregate, 1),
        "threshold": 95,
        "converged": aggregate >= 95,
        "scenario_count": len(results),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": results,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print_table(results, aggregate)

    sys.exit(0 if aggregate >= 95 else 1)


if __name__ == "__main__":
    main()

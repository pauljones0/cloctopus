#!/usr/bin/env python3
"""Bootstrap initial holdout scenarios from a spec when none exist.

When a user starts with only SPEC.md and no scenarios, this script
generates a starter set covering all 3 tiers:
  - Tier 1: Smoke tests (does it start? does the health endpoint work?)
  - Tier 2: Core business logic (CRUD, main features from the spec)
  - Tier 3: Edge cases (bad input, missing fields, auth, error handling)

Usage:
    python scripts/bootstrap_scenarios.py --spec SPEC.md --output holdout/
"""

import argparse
import json
import os
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path


def load_spec(spec_path: str) -> str:
    with open(spec_path) as f:
        return f.read()


def generate_tier_via_claude(spec: str, tier: int, tier_desc: str, output_path: str) -> bool:
    """Use Claude CLI to generate a scenario for a specific tier."""
    prompt = f"""You are a QA engineer designing holdout scenarios for autonomous code generation.
This is a BRAND NEW project with ZERO existing tests. You are creating the very first scenarios.

SPEC (what the software should do):
{spec}

Generate ONE holdout scenario for TIER {tier}: {tier_desc}

Tier guidelines:
- Tier 1 (Smoke): Can the app start? Does the most basic endpoint/function work?
  Think: health checks, "hello world" level, does it respond at all?
- Tier 2 (Core): Does the main business logic work?
  Think: CRUD operations, the primary feature described in the spec, happy path workflows.
- Tier 3 (Edge): What breaks it?
  Think: malformed input, missing required fields, invalid types, empty bodies,
  special characters, boundary values, unauthorized access.
  IMPORTANT: Include at least one step where the expected behavior is an error response
  or empty result (a "negative test"). Not every step should expect success -- the app
  should gracefully reject bad input. Also include variety: not every scenario should be
  a high-stakes incident. Include ordinary daily-use workflows too.

CRITICAL: Every step MUST have at least one assertion field (expected_status, expected_exit_code,
expected_body_contains, expected_stdout_contains, or expected_headers). Steps without assertions
are scored as 0 (untestable) and waste the scenario.

Read the spec carefully. Identify the ACTUAL endpoints/functions/interfaces described,
and write scenarios that test THOSE specific interfaces.

Output ONLY valid YAML with this structure:
```yaml
id: descriptive-kebab-case-id
name: Human-Readable Scenario Name
tier: {tier}
description: >
  What this scenario tests and why.
steps:
  - type: http
    method: GET
    path: /actual-endpoint-from-spec
    expected_status: 200
    expected_body_contains: "expected content"
```

For exec-based apps (CLI tools, scripts), use:
```yaml
steps:
  - type: exec
    command: "python app.py --arg value"
    expected_exit_code: 0
    expected_stdout_contains: "expected output"
```

Output ONLY the YAML. No markdown fences, no explanation."""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=None,  # No timeout -- let it finish naturally
        )
        if result.returncode != 0:
            print(f"  [ERROR] Claude CLI failed for tier {tier}: {result.stderr}", file=sys.stderr)
            return False

        raw = result.stdout.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        parsed = yaml.safe_load(raw)
        if not parsed or "id" not in parsed or "steps" not in parsed:
            print(f"  [ERROR] Generated YAML for tier {tier} missing required fields", file=sys.stderr)
            return False

        # Ensure tier is set correctly
        parsed["tier"] = tier

        with open(output_path, "w") as f:
            f.write(f"# Auto-generated starter scenario -- {datetime.now().isoformat()}\n")
            f.write(f"# Tier {tier}: {tier_desc}\n")
            yaml.dump(parsed, f, default_flow_style=False, sort_keys=False)

        print(f"  [OK] Tier {tier}: {parsed.get('name', parsed['id'])} ({len(parsed.get('steps', []))} steps)")
        return True

    except subprocess.TimeoutExpired:
        # Safety net -- shouldn't trigger with timeout=None, but fall through gracefully
        print(f"  [WARN] Claude CLI timed out for tier {tier}, falling back to template", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("  [ERROR] 'claude' CLI not found", file=sys.stderr)
        return False


def generate_template_fallback(spec: str, tier: int, tier_desc: str, output_path: str) -> bool:
    """Generate a template when Claude CLI is unavailable."""
    # Try to extract endpoints from spec using simple heuristics
    endpoints = []
    for line in spec.split("\n"):
        line_stripped = line.strip()
        # Look for patterns like "GET /path", "POST /path", "- GET /path"
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            if method in line_stripped and "/" in line_stripped:
                idx = line_stripped.index("/")
                path = line_stripped[idx:].split()[0].split(")")[0].split('"')[0]
                if len(path) > 1:
                    endpoints.append((method, path))
                break

    if tier == 1:
        steps = [{"type": "http", "method": "GET", "path": endpoints[0][1] if endpoints else "/", "expected_status": 200}]
    elif tier == 2:
        if endpoints:
            steps = [{"type": "http", "method": e[0], "path": e[1], "expected_status": 200} for e in endpoints[:3]]
        else:
            steps = [{"type": "exec", "command": "echo 'TODO: add core logic test'", "expected_exit_code": 0}]
    else:  # tier 3
        steps = [
            {"type": "http", "method": "POST", "path": endpoints[0][1] if endpoints else "/", "body": "not-json", "expected_status": 400},
            {"type": "http", "method": "GET", "path": "/nonexistent-path-12345", "expected_status": 404},
        ]

    scenario = {
        "id": f"bootstrap-tier-{tier}",
        "name": f"Bootstrap {tier_desc}",
        "tier": tier,
        "description": f"Auto-generated template for tier {tier}. Edit to add meaningful assertions.",
        "steps": steps,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(f"# Template scenario -- edit to add real assertions\n")
        f.write(f"# Tier {tier}: {tier_desc}\n")
        yaml.dump(scenario, f, default_flow_style=False, sort_keys=False)

    print(f"  [OK] Tier {tier}: Template written (needs manual refinement)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Bootstrap initial holdout scenarios from spec")
    parser.add_argument("--spec", required=True, help="Path to SPEC.md")
    parser.add_argument("--output", required=True, help="Output directory for scenarios")
    args = parser.parse_args()

    # Check if scenarios already exist
    output_dir = Path(args.output)
    if output_dir.exists():
        existing = list(output_dir.glob("*.yaml"))
        if existing:
            print(f"[SKIP] {len(existing)} scenarios already exist in {args.output}:")
            for f in existing:
                print(f"  - {f.name}")
            print("Use scripts/generate_scenario.py to add more, or delete existing to re-bootstrap.")
            sys.exit(0)

    output_dir.mkdir(parents=True, exist_ok=True)
    spec = load_spec(args.spec)

    print(f"[BOOTSTRAP] Generating initial scenarios from {args.spec}")
    print(f"Output directory: {args.output}")
    print()

    tiers = [
        (1, "Smoke Tests", "smoke.yaml"),
        (2, "Core Business Logic", "core.yaml"),
        (3, "Edge Cases & Error Handling", "edge_cases.yaml"),
    ]

    success_count = 0
    for tier_num, tier_desc, filename in tiers:
        output_path = str(output_dir / filename)
        ok = generate_tier_via_claude(spec, tier_num, tier_desc, output_path)
        if not ok:
            print(f"  [FALLBACK] Using template for tier {tier_num}")
            ok = generate_template_fallback(spec, tier_num, tier_desc, output_path)
        if ok:
            success_count += 1

    print()
    if success_count == 3:
        print(f"[DONE] {success_count}/3 scenarios generated in {args.output}")
        print("The attractor loop can now run against these scenarios.")
    elif success_count > 0:
        print(f"[PARTIAL] {success_count}/3 scenarios generated. Some may need manual editing.")
    else:
        print("[FAILED] Could not generate any scenarios. Check Claude CLI or write them manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()

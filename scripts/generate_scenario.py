#!/usr/bin/env python3
"""Generate a new, harder holdout scenario based on the spec and existing scenarios.

After convergence, this script creates a NEW scenario that targets gaps in coverage:
- Edge cases not yet tested
- Adversarial inputs
- Performance boundaries
- Security attack vectors
- Integration failure modes

The new scenario is written to the holdout directory, automatically raising
the bar for the next convergence cycle.

Usage:
    python scripts/generate_scenario.py \
        --spec SPEC.md \
        --existing-scenarios holdout/ \
        --output holdout/evolved_4.yaml \
        --tier 3
"""

import argparse
import json
import os
import subprocess
import sys
import yaml
from pathlib import Path
from datetime import datetime


def load_spec(spec_path: str) -> str:
    """Load the product spec."""
    with open(spec_path) as f:
        return f.read()


def load_existing_scenarios(scenario_dir: str) -> list[dict]:
    """Load all existing scenario YAML files."""
    scenarios = []
    scenario_path = Path(scenario_dir)
    if not scenario_path.exists():
        return scenarios
    for f in sorted(scenario_path.glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh)
                if data:
                    data["_source_file"] = f.name
                    scenarios.append(data)
        except Exception as e:
            print(f"[WARN] Could not parse {f}: {e}", file=sys.stderr)
    return scenarios


def summarize_existing_coverage(scenarios: list[dict]) -> str:
    """Summarize what existing scenarios already test."""
    if not scenarios:
        return "No existing scenarios."

    lines = []
    for s in scenarios:
        name = s.get("name", s.get("id", "unknown"))
        tier = s.get("tier", "?")
        step_count = len(s.get("steps", []))
        step_types = set()
        endpoints = set()
        for step in s.get("steps", []):
            step_types.add(step.get("type", "unknown"))
            if step.get("path"):
                endpoints.add(f"{step.get('method', 'GET')} {step['path']}")
        lines.append(
            f"- {name} (tier {tier}, {step_count} steps, "
            f"types: {', '.join(step_types)}, "
            f"endpoints: {', '.join(endpoints) if endpoints else 'n/a'})"
        )
    return "\n".join(lines)


def generate_via_claude(spec: str, coverage_summary: str, tier: int, output_path: str) -> bool:
    """Use Claude CLI to generate a new scenario."""
    prompt = f"""You are a QA adversary designing holdout scenarios for autonomous code generation.

SPEC (what the software should do):
{spec}

EXISTING COVERAGE (what is already tested -- DO NOT duplicate):
{coverage_summary}

YOUR TASK:
Generate ONE new holdout scenario in YAML format that tests something NOT already covered.
Focus on tier {tier} difficulty:
- Tier 1: Basic smoke tests (connectivity, simple happy paths)
- Tier 2: Core business logic (CRUD, state transitions, data validation)
- Tier 3: Edge cases, security, adversarial inputs, failure modes, race conditions

The scenario should be HARDER than existing ones. Think about:
- What could go wrong that existing scenarios don't catch?
- What adversarial inputs might break the implementation?
- What happens under unusual sequences of operations?
- What security boundaries could be violated?
- What happens with malformed data, missing fields, or unexpected types?

Output ONLY valid YAML with this structure:
```yaml
id: descriptive-kebab-case-id
name: Human-Readable Scenario Name
tier: {tier}
description: >
  One paragraph explaining what this scenario tests and why it matters.
steps:
  - type: http  # or exec or script
    method: POST
    path: /endpoint
    body: '{{"key": "value"}}'
    expected_status: 201
    expected_body_contains: "expected substring"
```

Output ONLY the YAML. No markdown fences, no explanation, no commentary."""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"[ERROR] Claude CLI failed: {result.stderr}", file=sys.stderr)
            return False

        raw = result.stdout.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        # Validate it's valid YAML
        parsed = yaml.safe_load(raw)
        if not parsed or "id" not in parsed or "steps" not in parsed:
            print("[ERROR] Generated YAML missing required fields (id, steps)", file=sys.stderr)
            return False

        # Write to output
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(f"# Auto-generated scenario -- {datetime.now().isoformat()}\n")
            f.write(f"# Generated by cloctopus self-improvement loop\n")
            yaml.dump(parsed, f, default_flow_style=False, sort_keys=False)

        print(f"[OK] Generated scenario: {parsed.get('name', parsed['id'])}")
        print(f"     Tier: {parsed.get('tier', tier)}")
        print(f"     Steps: {len(parsed.get('steps', []))}")
        return True

    except subprocess.TimeoutExpired:
        print("[ERROR] Claude CLI timed out after 120s", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[ERROR] 'claude' CLI not found. Falling back to template.", file=sys.stderr)
        return False


def generate_template_fallback(spec: str, coverage_summary: str, tier: int, output_path: str) -> bool:
    """Generate a template scenario when Claude CLI is unavailable."""
    scenario_id = f"evolved-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    template = {
        "id": scenario_id,
        "name": f"Evolved Scenario (Tier {tier})",
        "tier": tier,
        "description": (
            "Auto-generated template scenario. "
            "Replace the steps below with specific behavioral tests "
            "targeting gaps in the existing coverage."
        ),
        "steps": [
            {
                "type": "http",
                "method": "GET",
                "path": "/health",
                "expected_status": 200,
            },
            {
                "type": "http",
                "method": "POST",
                "path": "/",
                "body": "{}",
                "expected_status": 400,
                "description": "Empty body should be rejected",
            },
        ],
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(f"# Template scenario -- needs manual refinement\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Existing coverage:\n")
        for line in coverage_summary.split("\n"):
            f.write(f"#   {line}\n")
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)

    print(f"[OK] Template scenario written to {output_path}")
    print(f"     NOTE: This is a template. Edit it to add meaningful test steps.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate a new holdout scenario")
    parser.add_argument("--spec", required=True, help="Path to SPEC.md")
    parser.add_argument("--existing-scenarios", required=True, help="Directory of existing scenarios")
    parser.add_argument("--output", required=True, help="Output YAML file path")
    parser.add_argument("--tier", type=int, default=3, help="Scenario difficulty tier (1-3)")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    existing = load_existing_scenarios(args.existing_scenarios)
    coverage = summarize_existing_coverage(existing)

    print(f"Spec: {args.spec} ({len(spec)} chars)")
    print(f"Existing scenarios: {len(existing)}")
    print(f"Target tier: {args.tier}")
    print(f"Output: {args.output}")
    print()

    # Try Claude CLI first, fall back to template
    success = generate_via_claude(spec, coverage, args.tier, args.output)
    if not success:
        print("[FALLBACK] Using template generator")
        success = generate_template_fallback(spec, coverage, args.tier, args.output)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

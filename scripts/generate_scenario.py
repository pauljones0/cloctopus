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
import re
import subprocess
import sys
import yaml
from collections import Counter
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


SCENARIO_TYPES = [
    "edge_case",
    "security",
    "daily_use",
    "negative_result",
    "onboarding",
    "audit",
    "performance",
    "error_handling",
]

# Keywords used to classify scenario themes from descriptions and step content
THEME_KEYWORDS = {
    "security": ["security", "auth", "token", "injection", "xss", "csrf", "secret",
                 "password", "permission", "unauthorized", "forbidden", "attack"],
    "edge_case": ["edge", "boundary", "overflow", "empty", "null", "unicode",
                  "special character", "malformed", "invalid", "unexpected"],
    "daily_use": ["daily", "typical", "normal", "common", "routine", "standard",
                  "basic workflow", "ordinary", "simple"],
    "negative_result": ["not found", "missing", "absent", "empty result", "zero results",
                        "no match", "does not exist", "404", "no content"],
    "error_handling": ["error", "failure", "crash", "timeout", "retry", "fallback",
                       "exception", "500", "503", "unavailable"],
    "performance": ["performance", "latency", "throughput", "load", "concurrent",
                    "stress", "benchmark", "slow", "fast"],
    "audit": ["audit", "compliance", "trace", "log", "monitor", "blast radius",
              "dependency", "impact", "coverage"],
    "onboarding": ["onboarding", "getting started", "first time", "new user",
                   "setup", "introduction", "tutorial"],
}

SATURATION_THRESHOLD = 3


def classify_scenario_theme(scenario: dict) -> str:
    """Classify a scenario into a theme based on its description and step content."""
    text_parts = [
        scenario.get("description", "").lower(),
        scenario.get("name", "").lower(),
    ]
    for step in scenario.get("steps", []):
        text_parts.append(step.get("description", "").lower())
        text_parts.append(step.get("path", "").lower())
        text_parts.append(step.get("command", "").lower())
        text_parts.append(step.get("script", "").lower())
    full_text = " ".join(text_parts)

    scores = {}
    for theme, keywords in THEME_KEYWORDS.items():
        scores[theme] = sum(1 for kw in keywords if kw in full_text)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "edge_case"


def summarize_existing_coverage(scenarios: list[dict]) -> str:
    """Produce a rich coverage analysis with theme saturation and gap detection."""
    if not scenarios:
        return "No existing scenarios."

    lines = []

    # --- Per-scenario summary ---
    lines.append("== SCENARIO LIST ==")
    theme_counter: Counter = Counter()
    step_type_counter: Counter = Counter()
    method_counter: Counter = Counter()
    endpoint_counter: Counter = Counter()
    assertion_types_used: set = set()

    for s in scenarios:
        name = s.get("name", s.get("id", "unknown"))
        tier = s.get("tier", "?")
        theme = classify_scenario_theme(s)
        theme_counter[theme] += 1

        step_types = set()
        endpoints = set()
        assertions = set()
        for step in s.get("steps", []):
            stype = step.get("type", "unknown")
            step_types.add(stype)
            step_type_counter[stype] += 1
            if step.get("path"):
                method = step.get("method", "GET")
                ep = f"{method} {step['path']}"
                endpoints.add(ep)
                endpoint_counter[ep] += 1
                method_counter[method] += 1
            if step.get("expected_status"):
                assertions.add("expected_status")
            if step.get("expected_body_contains"):
                assertions.add("expected_body_contains")
            if step.get("expected_headers"):
                assertions.add("expected_headers")
            if step.get("expected_exit_code") is not None:
                assertions.add("expected_exit_code")
            if step.get("expected_stdout_contains"):
                assertions.add("expected_stdout_contains")
            if step.get("capture"):
                assertions.add("capture")
            assertion_types_used.update(assertions)

        lines.append(
            f"- {name} (tier {tier}, theme={theme}, {len(s.get('steps', []))} steps, "
            f"types: {', '.join(step_types)}, "
            f"endpoints: {', '.join(endpoints) if endpoints else 'n/a'})"
        )

    # --- Theme saturation ---
    lines.append("")
    lines.append("== THEME SATURATION ==")
    for theme in SCENARIO_TYPES:
        count = theme_counter.get(theme, 0)
        if count >= SATURATION_THRESHOLD:
            lines.append(f"  {theme}: {count}x -- SATURATED (do NOT generate more)")
        elif count == 0:
            lines.append(f"  {theme}: 0 -- << NOT YET COVERED (priority target)")
        else:
            lines.append(f"  {theme}: {count}x")

    # --- Step type distribution ---
    lines.append("")
    lines.append("== STEP TYPE DISTRIBUTION ==")
    for stype in ["http", "exec", "script"]:
        lines.append(f"  {stype}: {step_type_counter.get(stype, 0)} steps")

    # --- HTTP method coverage ---
    lines.append("")
    lines.append("== HTTP METHOD COVERAGE ==")
    all_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    for m in all_methods:
        count = method_counter.get(m, 0)
        status = "covered" if count > 0 else "<< MISSING"
        lines.append(f"  {m}: {count} ({status})")

    # --- Most-tested endpoints ---
    if endpoint_counter:
        lines.append("")
        lines.append("== MOST-TESTED ENDPOINTS (potential over-coverage) ==")
        for ep, count in endpoint_counter.most_common(5):
            lines.append(f"  {ep}: {count}x")

    # --- Assertion type coverage ---
    lines.append("")
    lines.append("== ASSERTION TYPE COVERAGE ==")
    all_assertion_types = [
        "expected_status", "expected_body_contains", "expected_headers",
        "expected_exit_code", "expected_stdout_contains", "capture",
    ]
    for at in all_assertion_types:
        status = "used" if at in assertion_types_used else "<< NEVER USED"
        lines.append(f"  {at}: {status}")

    return "\n".join(lines)


def generate_via_claude(spec: str, coverage_summary: str, tier: int, output_path: str) -> bool:
    """Use Claude CLI to generate a new scenario."""
    prompt = f"""You are a QA engineer designing holdout scenarios for autonomous code generation.

SPEC (what the software should do):
{spec}

EXISTING COVERAGE ANALYSIS:
{coverage_summary}

== STEP 1: CHOOSE A SCENARIO TYPE ==

Pick ONE type from this list. You MUST choose a type marked "<< NOT YET COVERED" if any exist.
If all types are covered, choose the one with the LOWEST count that is NOT marked SATURATED.

HARD RULE: If a theme is marked "SATURATED", you MUST NOT generate another scenario of that type.
Violating this rule makes the scenario useless -- it will be rejected.

Scenario types:
- edge_case: Boundary values, malformed input, unexpected types
- security: Auth bypass, injection, token leaks, permission escalation
- daily_use: Ordinary workflows a developer does every day (adding a function, checking imports, quick PR review)
- negative_result: Scenarios where the CORRECT answer is "nothing found" or "this doesn't exist" (verifying clean abstractions, confirming no callers before deletion)
- onboarding: First-time user exploring the system, "show me the seam between X and Y"
- audit: Compliance checks, blast radius analysis, coverage audits
- performance: Latency, throughput, concurrent access, resource exhaustion
- error_handling: Graceful degradation, timeouts, retry behavior, error messages

== STEP 2: WRITE THE SCENARIO ==

Focus on tier {tier} difficulty:
- Tier 1: Basic smoke tests (connectivity, simple happy paths)
- Tier 2: Core business logic (CRUD, state transitions, data validation)
- Tier 3: Edge cases, security, adversarial inputs, failure modes, race conditions

Not every scenario is a production incident. Include ordinary, realistic workflows too.

VALID STEP FIELDS REFERENCE (use ONLY these fields):

HTTP steps:
  - type: http
    method: GET|POST|PUT|DELETE|PATCH
    path: /endpoint
    body: '{{"key": "value"}}'           # optional, JSON string
    headers: {{Authorization: "Bearer X"}}  # optional
    expected_status: 200                  # REQUIRED -- every step needs assertions
    expected_body_contains: "substring"   # optional but recommended
    expected_headers: {{Content-Type: "application/json"}}  # optional
    capture: {{var_name: "$.json_field"}}   # optional, for chaining steps
    description: "What this step tests"   # optional

Exec steps:
  - type: exec
    command: "shell command here"
    expected_exit_code: 0                 # REQUIRED
    expected_stdout_contains: "output"    # optional but recommended
    description: "What this step tests"

Script steps:
  - type: script
    script: |
      import requests
      r = requests.get("http://localhost:8080/api/items")
      assert r.status_code == 200
    expected_exit_code: 0                 # REQUIRED
    description: "What this step tests"

CRITICAL: Every step MUST have at least one assertion field (expected_status, expected_exit_code,
expected_body_contains, expected_stdout_contains, or expected_headers). Steps without assertions
score 0 and are flagged as untestable.

== STEP 3: SELF-CHECK (do this mentally before outputting) ==

Before writing your YAML, verify:
1. The theme is NOT marked SATURATED in the coverage analysis
2. Every step has at least one assertion field
3. The scenario tests something genuinely different from existing ones
4. If this is a negative_result type, at least one step expects an error code or empty/missing response
5. The description explains WHY this scenario matters, not just WHAT it tests

Output ONLY valid YAML. No markdown fences, no explanation, no commentary.

```yaml
id: descriptive-kebab-case-id
name: Human-Readable Scenario Name
tier: {tier}
description: >
  One paragraph explaining what this tests and WHY it matters.
steps:
  - type: http
    method: POST
    path: /endpoint
    body: '{{"key": "value"}}'
    expected_status: 201
    expected_body_contains: "expected substring"
```

Output ONLY the YAML."""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=None,  # No timeout -- let it finish naturally
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
        # Safety net -- shouldn't trigger with timeout=None, but fall through gracefully
        print("[WARN] Claude CLI timed out, falling back to template", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[ERROR] 'claude' CLI not found. Falling back to template.", file=sys.stderr)
        return False


def _extract_endpoints_from_spec(spec: str) -> list[tuple[str, str]]:
    """Extract (METHOD, /path) pairs from a spec using heuristics."""
    endpoints = []
    for line in spec.split("\n"):
        stripped = line.strip()
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            if method in stripped and "/" in stripped:
                idx = stripped.index("/")
                path = stripped[idx:].split()[0].split(")")[0].split('"')[0].rstrip(",;")
                if len(path) > 1 and not path.startswith("//"):
                    endpoints.append((method, path))
                break
    return endpoints


# Template variants covering different scenario types
_TEMPLATE_VARIANTS = [
    {
        "type": "negative_result",
        "name": "Negative Result -- Missing Resource",
        "description": "Verifies the app returns proper error responses for nonexistent resources.",
        "make_steps": lambda eps: [
            {
                "type": "http",
                "method": "GET",
                "path": "/nonexistent-resource-abc123",
                "expected_status": 404,
                "expected_body_contains": "not found",
                "description": "Nonexistent path returns 404",
            },
            {
                "type": "http",
                "method": "GET",
                "path": (eps[0][1] if eps else "/api") + "/99999999",
                "expected_status": 404,
                "description": "Nonexistent ID returns 404",
            },
        ],
    },
    {
        "type": "error_handling",
        "name": "Error Handling -- Malformed Input",
        "description": "Tests graceful handling of malformed requests and invalid data.",
        "make_steps": lambda eps: [
            {
                "type": "http",
                "method": "POST",
                "path": eps[0][1] if eps else "/",
                "body": "this is not json",
                "expected_status": 400,
                "description": "Non-JSON body rejected with 400",
            },
            {
                "type": "http",
                "method": "POST",
                "path": eps[0][1] if eps else "/",
                "body": "{}",
                "expected_status": 400,
                "expected_body_contains": "required",
                "description": "Empty JSON body rejected for missing required fields",
            },
        ],
    },
    {
        "type": "daily_use",
        "name": "Daily Use -- Health and Basic CRUD",
        "description": "Smoke test covering health endpoint and basic read operations.",
        "make_steps": lambda eps: [
            {
                "type": "http",
                "method": "GET",
                "path": "/health",
                "expected_status": 200,
                "description": "Health endpoint responds",
            },
        ]
        + [
            {
                "type": "http",
                "method": e[0],
                "path": e[1],
                "expected_status": 200,
                "description": f"Basic {e[0]} {e[1]} works",
            }
            for e in eps[:2]
        ],
    },
    {
        "type": "security",
        "name": "Security -- Unauthorized Access",
        "description": "Tests that protected endpoints reject unauthenticated requests.",
        "make_steps": lambda eps: [
            {
                "type": "http",
                "method": "DELETE",
                "path": eps[0][1] if eps else "/api/resource/1",
                "expected_status": 401,
                "description": "DELETE without auth token rejected",
            },
            {
                "type": "http",
                "method": "PUT",
                "path": eps[0][1] if eps else "/api/resource/1",
                "body": '{"admin": true}',
                "expected_status": 401,
                "description": "PUT without auth token rejected",
            },
        ],
    },
]


def generate_template_fallback(
    spec: str, coverage_summary: str, tier: int, output_path: str
) -> bool:
    """Generate a template scenario that adapts to the spec and avoids saturated themes."""
    endpoints = _extract_endpoints_from_spec(spec)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Pick the template variant whose type is least represented in coverage
    saturated = set()
    type_counts: dict[str, int] = {}
    for line in coverage_summary.split("\n"):
        for stype in SCENARIO_TYPES:
            if stype in line:
                if "SATURATED" in line:
                    saturated.add(stype)
                # Extract count if present
                match = re.search(rf"{stype}:\s*(\d+)", line)
                if match:
                    type_counts[stype] = int(match.group(1))

    best_variant = _TEMPLATE_VARIANTS[0]
    best_count = float("inf")
    for variant in _TEMPLATE_VARIANTS:
        vtype = variant["type"]
        if vtype in saturated:
            continue
        count = type_counts.get(vtype, 0)
        if count < best_count:
            best_count = count
            best_variant = variant

    scenario = {
        "id": f"template-{best_variant['type']}-{ts}",
        "name": best_variant["name"],
        "tier": tier,
        "description": best_variant["description"],
        "steps": best_variant["make_steps"](endpoints),
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(f"# Template scenario ({best_variant['type']}) -- refine assertions for your spec\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        yaml.dump(scenario, f, default_flow_style=False, sort_keys=False)

    print(f"[OK] Template scenario written to {output_path}")
    print(f"     Type: {best_variant['type']} (least covered)")
    print(f"     Steps: {len(scenario['steps'])}")
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

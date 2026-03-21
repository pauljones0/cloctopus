# Cloctopus

**Autonomous software engineering for Claude Code.** Write a spec, define what "correct" looks like, walk away. Come back to working code.

Cloctopus implements the [OctopusGarden](https://github.com/foundatron/octopusgarden) "Dark Factory" methodology natively in Claude Code. No external tooling, no Go binary, no custom infrastructure. Just Claude Code + Docker.

---

## How It Works (30 seconds)

```
You write a SPEC ──> Coder agent generates code ──> Docker builds it
                                                          │
Score >= 95? Done! <── Judge scores behavior <── Scenarios test it
       │                                              │
       └── No? Feedback loop ─────────────────────────┘
```

1. **You** write a spec describing what the software should do
2. **You** write holdout scenarios -- behavioral tests the coder never sees
3. **Cloctopus** loops: generate code, build in Docker, run scenarios, score with an LLM judge
4. If the score is below 95, the failures feed back to the coder and it tries again
5. You come back when it converges. You never read the generated code.

---

## Quickstart

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- [Docker](https://docs.docker.com/get-docker/) running
- Python 3.12+

### 1. Clone and install

```bash
git clone <this-repo> cloctopus
cd cloctopus
pip install -e .
```

### 2. Create your project

```bash
mkdir my-project && cd my-project
```

### 3. Write your spec

Create `SPEC.md` describing what you want built. Be precise about interfaces -- the coder has no other context.

```markdown
# Todo API

Build a REST API that manages todo items.

## Endpoints

- POST /todos -- Create a todo. Body: {"title": "string", "done": false}. Returns 201 + the created item with an auto-generated "id" field.
- GET /todos -- List all todos. Returns 200 + JSON array.
- GET /todos/:id -- Get one todo. Returns 200 or 404.
- PUT /todos/:id -- Update a todo. Returns 200 or 404.
- DELETE /todos/:id -- Delete a todo. Returns 204 or 404.

## Requirements

- Python with Flask or FastAPI
- In-memory storage (no database)
- JSON responses with Content-Type: application/json
```

### 4. Write holdout scenarios

Create `holdout/` directory with YAML scenario files. These are the behavioral tests the coder agent **never sees**.

```yaml
# holdout/smoke.yaml
id: smoke
name: Health check
tier: 1
steps:
  - type: http
    method: POST
    path: /todos
    body: '{"title": "test", "done": false}'
    expected_status: 201

  - type: http
    method: GET
    path: /todos
    expected_status: 200
    expected_body_contains: "test"
```

```yaml
# holdout/crud.yaml
id: crud-lifecycle
name: Full CRUD lifecycle
tier: 2
steps:
  - type: http
    method: POST
    path: /todos
    body: '{"title": "buy milk", "done": false}'
    expected_status: 201
    capture:
      todo_id: "$.id"

  - type: http
    method: GET
    path: /todos/{todo_id}
    expected_status: 200
    expected_body_contains: "buy milk"

  - type: http
    method: PUT
    path: /todos/{todo_id}
    body: '{"title": "buy oat milk", "done": true}'
    expected_status: 200

  - type: http
    method: DELETE
    path: /todos/{todo_id}
    expected_status: 204

  - type: http
    method: GET
    path: /todos/{todo_id}
    expected_status: 404
```

```yaml
# holdout/edge_cases.yaml
id: edge-cases
name: Error handling and edge cases
tier: 3
steps:
  - type: http
    method: GET
    path: /todos/nonexistent-id
    expected_status: 404

  - type: http
    method: POST
    path: /todos
    body: 'not json'
    expected_status: 400

  - type: http
    method: DELETE
    path: /todos/nonexistent-id
    expected_status: 404
```

### 5. Add a .claudeignore

**Critical step.** This hides the holdout scenarios from the coder agent.

```bash
echo "holdout/" > .claudeignore
```

### 6. Run cloctopus

Open Claude Code in your project directory and paste:

```
You are an autonomous coding agent running the cloctopus Dark Factory attractor loop.

SPEC: Read SPEC.md -- this is your only source of truth for what to build.

RULES:
- You CANNOT read, list, or access anything in the holdout/ directory. It is hidden from you.
- Generate code based solely on the spec. Write all files needed to run the application.
- After generating code, build it in Docker and ensure it starts correctly.
- Do NOT write your own tests. An external judge will evaluate your code.
- If you receive feedback with failing scenarios, fix the code and try again.
- Continue iterating until you are told convergence is achieved (score >= 95).
- Do not ask for human input. Do not stop to request review. Just keep iterating.

BEGIN: Read SPEC.md and generate the initial implementation.
```

In a **separate terminal**, run the evaluation loop:

```bash
cloctopus run --spec SPEC.md --scenarios holdout/ --threshold 95 --max-iterations 20
```

Or if you haven't built the cloctopus CLI yet (Phase 0-4 of the epic), you can run the loop manually -- see [Manual Loop](#manual-loop) below.

---

## Manual Loop

If you're using cloctopus before the full system is built, you can run the Dark Factory loop manually with just Claude Code and Docker:

### Step 1: Start the coder

Open Claude Code in your project and give it the spec prompt above. Let it generate code.

### Step 2: Build and run

```bash
docker build -t my-project .
docker run -d -p 8080:8080 --name my-project my-project
```

### Step 3: Run scenarios manually

Execute each scenario step against `http://localhost:8080` and record the results.

### Step 4: Judge the results

Open a **separate** Claude Code session (or use the API) and paste:

```
You are an impartial judge evaluating software behavior. You will see:
1. What the software SHOULD do (the scenario description)
2. What the software ACTUALLY did (the HTTP responses / output)

Score the behavior from 0-100:
- 0-30: Fundamentally broken
- 31-60: Partially working
- 61-80: Mostly correct, edge cases failing
- 81-94: Nearly correct, minor deviations
- 95-100: Fully satisfies the scenario

Return JSON: {"score": <0-100>, "commentary": "<what failed and why>", "passing": <true/false>}

SCENARIO: <paste scenario>
ACTUAL OUTPUT: <paste results>
```

### Step 5: Feed back

If score < 95, paste the judge's commentary back into the coder's Claude Code session:

```
The judge scored your code <score>/100. Here is the feedback:
<judge commentary>

Fix the issues and regenerate. Do not ask for clarification.
```

### Step 6: Repeat

Loop steps 2-5 until convergence.

---

## Self-Improvement Loop (The Killer Feature)

After your code converges, cloctopus doesn't stop. It **evolves** -- generating new, harder scenarios and re-converging against them. The quality bar rises automatically with every cycle.

### How it works

```
Cycle 1: 3 scenarios, code converges at 96/100
    ↓
Cycle 1 complete → generates scenario 4 (adversarial inputs)
    ↓
Cycle 2: 4 scenarios, code converges at 95/100
    ↓
Cycle 2 complete → generates scenario 5 (race conditions)
    ↓
Cycle 3: 5 scenarios, code converges at 97/100
    ↓
...the bar keeps rising
```

### One-shot improvement

In Claude Code, run:

```
/improve
```

This will: score the current code, fix any failures, then generate a new harder scenario.

### Continuous improvement (set and forget)

```
/loop 1h /improve
```

This runs the improvement cycle every hour. Each hour:
1. All scenarios are re-evaluated
2. Any regressions are fixed
3. A new scenario is generated, raising the bar
4. The cycle repeats

Note: Claude Code sessions auto-expire after 3 days. Restart with the same command.

### Manual improvement

```bash
bash scripts/orchestrate.sh --spec SPEC.md --scenarios holdout/ --threshold 95
```

### What scenarios get generated?

The generator reads your spec and existing scenarios, then targets gaps:
- Edge cases not yet tested
- Adversarial and malformed inputs
- Security boundaries (injection, auth bypass, path traversal)
- Failure modes (timeouts, partial failures, network errors)
- Race conditions and state corruption
- Unusual operation sequences

Each generated scenario is tier 3 (hardest) and gets written to your `holdout/` directory as `evolved_N.yaml`.

---

## Key Concepts

### The Information Barrier

The coder agent **never** sees the holdout scenarios. This prevents "reward hacking" -- where the AI modifies tests to pass rather than fixing the code. The `.claudeignore` file enforces this in Claude Code.

### Satisfaction Scoring (Not Boolean Tests)

Traditional tests are pass/fail. Cloctopus uses probabilistic scoring (0-100) via an LLM judge. This handles the inherent fuzziness of AI-generated code -- minor formatting differences, alternate valid approaches, and cosmetic variations don't cause false failures.

### Convergence, Not Correctness

A score of 95+ means the LLM judge is satisfied that the behavioral output matches expected behavior. It does not mean the code is perfect, readable, or efficient. The code is treated as opaque -- you never need to read it.

### Model Escalation

The system starts with cheap models (Haiku) and escalates to expensive ones (Opus) only when stuck. This keeps costs low for easy tasks and brings heavy firepower only when needed.

### Wonder/Reflect

When the loop stalls (same score for 3+ iterations), it enters a diagnostic mode:
- **Wonder**: High-temperature brainstorm of possible root causes
- **Reflect**: Low-temperature selection of the most promising fix

This prevents getting stuck in local minima.

---

## Project Structure (For Your Project)

```
my-project/
├── SPEC.md              # What you want built (YOU write this)
├── holdout/             # Behavioral scenarios (YOU write these)
│   ├── smoke.yaml       # Tier 1: basic connectivity
│   ├── crud.yaml        # Tier 2: core business logic
│   └── edge_cases.yaml  # Tier 3: error handling, security
├── .claudeignore        # Must contain "holdout/" (YOU create this)
└── <generated code>     # Everything else is machine-generated
```

You write 3 things: the spec, the scenarios, and the `.claudeignore`. Everything else is generated -- including future scenarios via the self-improvement loop.

---

## Scenario YAML Reference

```yaml
id: unique-scenario-id          # Required. Used in scoring reports.
name: Human-readable name       # Required. Shown in feedback.
tier: 1                         # 1=smoke, 2=standard, 3=comprehensive
description: What this tests    # Optional. Context for the judge.
steps:
  - type: http                  # http | exec | script
    method: GET                 # HTTP method
    path: /endpoint             # URL path (appended to container URL)
    headers:                    # Optional headers
      Authorization: "Bearer token"
    body: '{"key": "value"}'    # Optional request body
    expected_status: 200        # Expected HTTP status code
    expected_body_contains: "x" # Substring match on response body
    expected_headers:           # Optional header assertions
      Content-Type: "application/json"
    capture:                    # Capture values for use in later steps
      item_id: "$.id"          # JSONPath expression

  - type: exec
    command: "ls /app"          # Command to run inside the container
    expected_exit_code: 0       # Expected exit code
    expected_stdout_contains: "main.py"

  - type: script
    script: |                   # Inline Python script
      import requests
      r = requests.get("http://localhost:8080/api")
      assert r.status_code == 200
```

---

## FAQ

**Q: Do I need to build the cloctopus system first?**
No. You can run the Dark Factory loop manually (see [Manual Loop](#manual-loop)) using just Claude Code and Docker. The full cloctopus system automates this manual process.

**Q: How much does it cost?**
A typical convergence loop for a small project (3-5 scenarios) runs 5-15 iterations. At ~$0.10-0.50 per iteration (Sonnet), expect $1-8 per project. Model escalation to Opus increases cost but is only triggered on stalls.

**Q: Can I use this for frontend/UI projects?**
Yes, but you'll need browser-based scenarios (using Chromedp or Playwright). The current implementation focuses on HTTP API scenarios. Browser automation is on the roadmap.

**Q: What if the loop never converges?**
After max iterations (default 20), the system stops and reports the best score achieved. Common causes: ambiguous spec, insufficient scenarios, or a task too complex for the model. Fix the spec and re-run.

**Q: Can I look at the generated code?**
You can, but the philosophy says you shouldn't need to. If the scenarios pass, the code works. If you find yourself reading the code, your scenarios aren't comprehensive enough.

**Q: How does the self-improvement loop work?**
After convergence, the system generates a NEW holdout scenario targeting coverage gaps. This scenario is added to `holdout/` and included in the next cycle. Over time, the test suite grows from your initial 3 scenarios to 10, 20, or more -- each one harder than the last. Run `/improve` for one cycle or `/loop 1h /improve` for continuous evolution.

**Q: Will it generate garbage scenarios?**
The generator uses Claude to analyze your spec and existing coverage, then designs scenarios that test untested paths. If Claude CLI isn't available, it falls back to a template you can edit manually. Either way, scenarios are YAML -- you can review and delete bad ones.

---

## Building Cloctopus Itself

If you want to contribute to or build the cloctopus system, see `docs/EPIC.md` for the phased build plan and `KICKOFF.md` for the multi-agent team prompt.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An autonomous Python agent that deploys containerized microservices to AWS staging. Given a GitHub repo, it clones it, builds a Docker image, pushes to AWS ECR, and deploys to AWS ECS — with the agent reasoning at each step about what to do next.

Full product requirements are in `docs/PRD.md`. Full architecture spec is in `docs/architecture.md`. **Read both before implementing any feature.**

## Project Status

No source code exists yet. The planned structure is:

```
src/
  agent/
    loop.py       # DeploymentAgent class — the core agent loop
    state.py      # AgentState dataclass tracking progress and artifacts
  tools/
    clone_repo_tool.py
    build_image_tool.py
    push_image_tool.py
    deploy_service_tool.py
    report_tool.py
  config/         # Credential and config loading
  main.py         # Entry point
```

## Agent Architecture

The agent runs a `while not state.is_complete()` loop. Each iteration:

1. **Observe** — inspect current `AgentState` (what's been done, what artifacts exist)
2. **Reason** — call Claude API with goal + state + available tools, get a tool decision
3. **Act** — execute the chosen tool
4. **Record** — update `AgentState` with the outcome

The agent invokes itself as an LLM: it calls Claude with the current state and asks "what tool should I run next and why?" Claude responds with structured reasoning + tool choice + parameters.

## Tool Implementation Pattern

Every tool follows this contract — pure functions returning `ToolOutcome`:

```python
def some_tool(input1: str, input2: str) -> ToolOutcome:
    try:
        # do the thing
        return ToolOutcome(success=True, <result_fields>, metadata={...})
    except Exception as e:
        return ToolOutcome(success=False, error=str(e))
```

Tools do not call the agent or each other. The agent selects and sequences them.

## AgentState Fields

Track what has been accomplished and what artifacts are available:

- `steps_completed: List[str]` — e.g. `["cloned", "built", "pushed", "deployed"]`
- `current_status: str` — `"cloning"`, `"building"`, `"pushing"`, `"deploying"`, `"complete"`
- `local_repo_path`, `image_id`, `image_tag`, `image_uri`, `task_definition_arn` — artifacts accumulated as the loop progresses
- `errors: List[str]`

## Key Constraints (MVP Scope)

- Happy path only — no rollback, no auto-recovery
- Staging environment only
- Public GitHub repos only
- Stop and report clearly on any failure; do not retry

## Environment Variables

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION            # default: us-east-1
ANTHROPIC_API_KEY     # for agent reasoning via Claude
GITHUB_REPO
GITHUB_BRANCH         # default: main
ECS_CLUSTER
ECS_SERVICE
```

See `.env.example` (to be created) for the full template.

## Tech Stack

- Python 3.11+
- `boto3` — AWS SDK (ECR, ECS)
- `docker` (docker-py) — build and push images
- `gitpython` — clone repos
- `anthropic` — Claude API for agent reasoning

## Testing

MVP testing uses a real simple TypeScript/Node.js repo against real AWS staging. For local development without AWS, use `moto` (mock AWS) or `localstack`. No unit test framework has been chosen yet.

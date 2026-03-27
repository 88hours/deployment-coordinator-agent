# Deployment Coordinator Agent - System Architecture

## Overview

The Deployment Coordinator Agent is a Python application with three main layers:

1. **Agent Loop** -- the core reasoning engine that decides what to do next
2. **Tools** -- concrete functions that perform actions (clone, build, push, deploy)
3. **Observables** -- structured data representing the current state and tool outcomes

The agent loop repeatedly observes the current state, reasons about the next action, executes a tool, and loops until the goal is achieved.

---

## High-Level Architecture

```
+----------------------+
|   User / Invoker     |
|  deploy(repo, ...)   |
+----------+-----------+
           |
           v
+----------------------+
| Agent Loop           |
| - Observe state      |
| - Reason next step   |
| - Select tool        |
| - Execute tool       |
| - Record outcome     |
+----------+-----------+
           |
    +------+------+------+------+
    |      |      |      |      |
    v      v      v      v      v
  Clone  Build  Push  Deploy  Report
  Tool   Tool   Tool   Tool    Tool
    |      |      |      |      |
    +------+------+------+------+
           |
           v
   +------------------+
   | External Services|
   | - GitHub         |
   | - AWS (ECR, ECS) |
   | - Docker Daemon  |
   +------------------+
```

---

## Components

### Agent Loop (`src/agent/loop.py`)

The core of the agent. It maintains a state object and repeatedly:

1. **Observe**: Inspect the current state (what repo? what's been done? what's next?)
2. **Reason**: Call Claude API with the goal and current state, get a decision
3. **Act**: Execute the chosen tool
4. **Record**: Update state with the outcome
5. **Report**: Return the final outcome or loop if more work remains

```python
class DeploymentAgent:
    def deploy(self, github_repo, branch, aws_region, ecs_cluster, ecs_service):
        state = AgentState(
            goal="Deploy this repo",
            github_repo=github_repo,
            branch=branch,
            aws_region=aws_region,
            ecs_cluster=ecs_cluster,
            ecs_service=ecs_service,
            steps_completed=[],
            current_status="starting"
        )

        while not state.is_complete():
            # Observe
            observation = self.observe(state)

            # Reason (call Claude)
            decision = self.reason(state, observation)

            # Act
            outcome = self.act(state, decision)

            # Record
            state = self.record(state, outcome)

        return state.report()
```

### Tools (`src/tools/`)

Simple, focused functions that perform one action each.

**clone_repo_tool.py**
- Input: GitHub URL, branch
- Output: local path to cloned repo
- Errors: Git clone failed, branch not found

**build_image_tool.py**
- Input: local repo path, image tag
- Output: image ID, image size
- Errors: Dockerfile not found, build failed

**push_image_tool.py**
- Input: image ID, AWS region, ECR repo name
- Output: image URI in ECR, push time
- Errors: Not authenticated to ECR, rate limited

**deploy_service_tool.py**
- Input: image URI, AWS region, ECS cluster, ECS service name
- Output: deployment status, new task definition ARN
- Errors: Service not found, insufficient permissions

**report_tool.py**
- Input: final state
- Output: human-readable report
- Example: "Successfully deployed my-api:abc123 to my-api-staging ECS service. New tasks starting up."

### State and Observables (`src/agent/state.py`)

```python
class AgentState:
    goal: str
    github_repo: str
    branch: str
    aws_region: str
    ecs_cluster: str
    ecs_service: str

    # Progress tracking
    steps_completed: List[str]  # ["cloned", "built", "pushed", "deployed"]
    current_status: str         # "cloning", "building", "pushing", "deploying", "complete"

    # Artifacts
    local_repo_path: Optional[str]
    image_id: Optional[str]
    image_tag: Optional[str]
    image_uri: Optional[str]
    task_definition_arn: Optional[str]

    # Errors
    errors: List[str]

    def is_complete(self) -> bool:
        return self.current_status == "complete"

    def report(self) -> str:
        # Return a human-readable summary
```

---

## Agent Reasoning Flow

When the agent calls Claude, it provides:

1. **Goal**: "Deploy the code from [repo] to [ECS service]"
2. **Current state**: What's been done so far, what artifacts exist, what's the next logical step
3. **Available tools**: List of tools the agent can invoke (clone, build, push, deploy)
4. **Instructions**: "Reason about what to do next. Choose one tool. Explain your decision."

Claude responds with:

```
Reasoning:
The repo has been cloned and I can see a Dockerfile. The next step is to build a Docker image.

Decision:
Tool: build_image_tool
Parameters:
  repo_path: "/tmp/my-api-abc123"
  image_tag: "my-api:latest"
```

The agent then executes the tool and loops.

---

## Data Flow

```
User invokes:
deploy(repo="https://github.com/user/api", branch="main", ...)
    |
    v
Agent.deploy() - initialize state
    |
    v
Loop iteration 1: Clone
  - Observe: "Need to clone repo"
  - Reason: "Call git clone"
  - Act: clone_repo_tool()
  - Record: local_repo_path = "/tmp/api-abc"
    |
    v
Loop iteration 2: Build
  - Observe: "Repo cloned, found Dockerfile"
  - Reason: "Build Docker image"
  - Act: build_image_tool(repo_path, "api:latest")
  - Record: image_id = "sha256:abc123"
    |
    v
Loop iteration 3: Push
  - Observe: "Image built, ready to push"
  - Reason: "Push to AWS ECR"
  - Act: push_image_tool(image_id, region, "api")
  - Record: image_uri = "123456789.dkr.ecr.us-east-1.amazonaws.com/api:latest"
    |
    v
Loop iteration 4: Deploy
  - Observe: "Image in ECR, ready to deploy"
  - Reason: "Update ECS service"
  - Act: deploy_service_tool(image_uri, cluster, service)
  - Record: task_definition_arn = "arn:aws:ecs:..."
    |
    v
Loop exits: state.is_complete() == True
    |
    v
Return: report()
  Output: "Successfully deployed api:latest to my-api-staging"
```

---

## Tool Implementation Pattern

Each tool follows the same pattern:

```python
def clone_repo_tool(github_url: str, branch: str) -> ToolOutcome:
    """
    Clone a GitHub repository.

    Args:
        github_url: Full GitHub URL (https://github.com/user/repo)
        branch: Branch to check out (e.g., "main")

    Returns:
        ToolOutcome with:
            - success: bool
            - local_path: str (if successful)
            - error: str (if failed)
            - metadata: dict (timing, repo info, etc.)
    """
    try:
        temp_dir = tempfile.mkdtemp()
        Repo.clone_from(github_url, temp_dir, branch=branch)
        return ToolOutcome(
            success=True,
            local_path=temp_dir,
            metadata={"cloned_at": datetime.now(), "repo": github_url}
        )
    except Exception as e:
        return ToolOutcome(success=False, error=str(e))
```

---

## Configuration and Credentials

AWS credentials are read from environment variables or IAM role:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION (default: us-east-1)
```

Configuration for the deployment:

```
GITHUB_REPO
GITHUB_BRANCH (default: main)
ECS_CLUSTER
ECS_SERVICE
```

---

## Error Handling (MVP)

MVP is happy path only. Errors cause the agent to stop and report:

```
Error: Docker build failed
Step that failed: Build
Error message: "No such file or directory: Dockerfile"
Action: Stopping deployment. Check that Dockerfile exists in repo root.
```

Rollback and recovery come in Phase 2.

---

## Testing Strategy (MVP)

For MVP, test with a real, simple TypeScript/Node.js service in a GitHub repo:

1. Create a test repo with a basic Dockerfile and source
2. Invoke the agent with test AWS staging environment
3. Verify: repo cloned, image built, image pushed to ECR, ECS service updated
4. Agent reports success

Mock AWS services if you cannot test against real AWS. Use localstack or moto for local testing.

---

## What to Revisit as the Product Grows

- **Rollback logic**: Phase 2 adds logic to detect if deployed service is unhealthy and roll back
- **Multi-environment**: Currently staging only, add production and custom environments
- **Parallel execution**: Currently tools run sequentially. Some (push + deploy) could be parallel
- **Caching**: Docker layer caching, build artifact caching
- **Observability**: Structured logging, metrics collection
- **Private repos**: Support for private GitHub repos with SSH keys
- **Advanced reasoning**: More sophisticated Claude prompts to handle edge cases

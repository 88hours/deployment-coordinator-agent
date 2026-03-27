from typing import Any

import anthropic
from anthropic.types import ToolParam

from src.agent.state import AgentState
from src.tools.clone_repo_tool import clone_repo_tool
from src.tools.build_image_tool import build_image_tool
from src.tools.push_image_tool import push_image_tool
from src.tools.deploy_service_tool import deploy_service_tool
from src.tools.report_tool import report_tool

TOOLS: list[ToolParam] = [
    {
        "name": "clone_repo",
        "description": "Clone a public GitHub repository to a local temporary directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "Full GitHub URL (https://github.com/user/repo)"},
                "branch": {"type": "string", "description": "Branch to check out (e.g. 'main')"},
            },
            "required": ["github_url", "branch"],
        },
    },
    {
        "name": "build_image",
        "description": "Build a Docker image from the cloned repository. Requires a Dockerfile in the repo root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute local path to the cloned repo"},
                "image_tag": {"type": "string", "description": "Tag for the image, e.g. 'myapp:abc123'"},
            },
            "required": ["repo_path", "image_tag"],
        },
    },
    {
        "name": "push_image",
        "description": "Authenticate to AWS ECR and push the built Docker image.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_tag": {"type": "string", "description": "Local image tag to push"},
                "aws_region": {"type": "string", "description": "AWS region (e.g. 'us-east-1')"},
                "ecr_repo_name": {"type": "string", "description": "ECR repository name (created if missing)"},
            },
            "required": ["image_tag", "aws_region", "ecr_repo_name"],
        },
    },
    {
        "name": "deploy_service",
        "description": "Register a new ECS task definition with the pushed image and update the ECS service.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_uri": {"type": "string", "description": "Full ECR image URI"},
                "aws_region": {"type": "string"},
                "ecs_cluster": {"type": "string"},
                "ecs_service": {"type": "string"},
            },
            "required": ["image_uri", "aws_region", "ecs_cluster", "ecs_service"],
        },
    },
]

SYSTEM_PROMPT = """\
You are an autonomous deployment agent. Your job is to deploy a containerized service to AWS ECS staging.

You execute exactly one tool per turn. After each tool runs, you will receive the updated state and decide the next step.
The deployment pipeline is: clone → build → push → deploy.

Always derive a short, lowercase ECR repository name from the GitHub repo name (e.g. "my-api" from "https://github.com/user/my-api").
Use the git repo name plus ":latest" as the image tag (e.g. "my-api:latest").
"""


class DeploymentAgent:
    def __init__(self, anthropic_api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = model

    def deploy(
        self,
        github_repo: str,
        branch: str,
        aws_region: str,
        ecs_cluster: str,
        ecs_service: str,
    ) -> str:
        state = AgentState(
            github_repo=github_repo,
            branch=branch,
            aws_region=aws_region,
            ecs_cluster=ecs_cluster,
            ecs_service=ecs_service,
        )

        while not state.is_complete():
            tool_name, tool_input = self._reason(state)
            print(f"[agent] → {tool_name}({tool_input})")

            outcome = self._act(tool_name, tool_input)
            state = self._record(state, tool_name, outcome)

            if outcome.success:
                print(f"[agent] ✓ {tool_name} succeeded")
            else:
                print(f"[agent] ✗ {tool_name} failed: {outcome.error}")

        return report_tool(state)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _reason(self, state: AgentState) -> tuple[str, dict[str, Any]]:
        """Call Claude with the current state; return the chosen tool name and inputs."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": self._state_to_prompt(state)}],
        )

        tool_use = next(b for b in message.content if b.type == "tool_use")
        return tool_use.name, tool_use.input

    def _act(self, tool_name: str, tool_input: dict[str, Any]):
        """Dispatch to the appropriate tool function."""
        if tool_name == "clone_repo":
            return clone_repo_tool(
                github_url=tool_input["github_url"],
                branch=tool_input["branch"],
            )
        if tool_name == "build_image":
            return build_image_tool(
                repo_path=tool_input["repo_path"],
                image_tag=tool_input["image_tag"],
            )
        if tool_name == "push_image":
            return push_image_tool(
                image_tag=tool_input["image_tag"],
                aws_region=tool_input["aws_region"],
                ecr_repo_name=tool_input["ecr_repo_name"],
            )
        if tool_name == "deploy_service":
            return deploy_service_tool(
                image_uri=tool_input["image_uri"],
                aws_region=tool_input["aws_region"],
                ecs_cluster=tool_input["ecs_cluster"],
                ecs_service=tool_input["ecs_service"],
            )
        raise ValueError(f"Unknown tool: {tool_name}")

    def _record(self, state: AgentState, tool_name: str, outcome) -> AgentState:
        """Update state in-place based on the tool outcome and return it."""
        if not outcome.success:
            state.errors.append(outcome.error or "unknown error")
            state.current_status = "failed"
            return state

        if tool_name == "clone_repo":
            state.local_repo_path = outcome.local_path
            state.steps_completed.append("cloned")
            state.current_status = "building"

        elif tool_name == "build_image":
            state.image_id = outcome.image_id
            state.image_tag = outcome.image_tag
            state.steps_completed.append("built")
            state.current_status = "pushing"

        elif tool_name == "push_image":
            state.image_uri = outcome.image_uri
            state.steps_completed.append("pushed")
            state.current_status = "deploying"

        elif tool_name == "deploy_service":
            state.task_definition_arn = outcome.task_definition_arn
            state.steps_completed.append("deployed")
            state.current_status = "complete"

        return state

    @staticmethod
    def _state_to_prompt(state: AgentState) -> str:
        return f"""\
Deployment goal: deploy {state.github_repo} (branch: {state.branch}) to ECS service \
'{state.ecs_service}' on cluster '{state.ecs_cluster}' in {state.aws_region}.

Current status: {state.current_status}
Steps completed: {', '.join(state.steps_completed) or 'none'}

Artifacts available:
  local_repo_path : {state.local_repo_path or 'not yet cloned'}
  image_id        : {state.image_id or 'not yet built'}
  image_tag       : {state.image_tag or 'not yet built'}
  image_uri       : {state.image_uri or 'not yet pushed'}
  task_def_arn    : {state.task_definition_arn or 'not yet deployed'}

Errors so far: {', '.join(state.errors) or 'none'}

Choose the next tool to execute."""

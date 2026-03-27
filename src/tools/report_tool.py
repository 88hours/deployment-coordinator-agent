from __future__ import annotations

from typing import TYPE_CHECKING

from src.agent.state import AgentState


def report_tool(state: AgentState) -> str:
    """
    Generate a human-readable deployment report from the final agent state.

    Args:
        state: The completed (or failed) AgentState

    Returns:
        A plain-language summary string suitable for printing to the user.
    """
    if state.errors:
        failed_step = state.current_status.capitalize()
        error_detail = state.errors[-1]
        return (
            f"Deployment failed at step: {failed_step}\n"
            f"Error: {error_detail}\n"
            f"Steps completed before failure: {', '.join(state.steps_completed) or 'none'}\n"
            f"Action: Stopping deployment. Resolve the error above and retry."
        )

    image_ref = state.image_uri or state.image_tag or "unknown image"
    return (
        f"Deployment succeeded.\n"
        f"Image: {image_ref}\n"
        f"ECS service '{state.ecs_service}' updated on cluster '{state.ecs_cluster}'.\n"
        f"Task definition: {state.task_definition_arn}\n"
        f"Steps completed: {', '.join(state.steps_completed)}\n"
        f"New tasks are starting up."
    )

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentState:
    # Deployment target
    github_repo: str
    branch: str
    aws_region: str
    ecs_cluster: str
    ecs_service: str

    # Progress
    steps_completed: List[str] = field(default_factory=list)
    current_status: str = "starting"

    # Artifacts accumulated during the loop
    local_repo_path: Optional[str] = None
    image_id: Optional[str] = None
    image_tag: Optional[str] = None
    image_uri: Optional[str] = None
    task_definition_arn: Optional[str] = None

    # Errors
    errors: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        return self.current_status in ("complete", "failed")

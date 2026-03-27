from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolOutcome:
    success: bool
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # clone_repo_tool
    local_path: Optional[str] = None

    # build_image_tool
    image_id: Optional[str] = None
    image_tag: Optional[str] = None

    # push_image_tool
    image_uri: Optional[str] = None

    # deploy_service_tool
    task_definition_arn: Optional[str] = None
    deployment_id: Optional[str] = None

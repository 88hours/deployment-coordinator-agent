from datetime import datetime, timezone

import docker
from docker.errors import BuildError, DockerException

from src.tools.types import ToolOutcome


def build_image_tool(repo_path: str, image_tag: str) -> ToolOutcome:
    """
    Build a Docker image from a local repository.

    Args:
        repo_path: Absolute path to the cloned repository (must contain a Dockerfile)
        image_tag: Tag for the built image (e.g., "myapp:latest" or "myapp:abc123")

    Returns:
        ToolOutcome with image_id and image_tag set on success, error set on failure.
    """
    try:
        client = docker.from_env()
        image, _ = client.images.build(path=repo_path, tag=image_tag, rm=True)
        return ToolOutcome(
            success=True,
            image_id=image.id,
            image_tag=image_tag,
            metadata={
                "repo_path": repo_path,
                "built_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except BuildError as e:
        return ToolOutcome(success=False, error=str(e))
    except DockerException as e:
        return ToolOutcome(success=False, error=str(e))

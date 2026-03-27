import tempfile
from datetime import datetime, timezone

from git import Repo, GitCommandError

from src.tools.types import ToolOutcome


def clone_repo_tool(github_url: str, branch: str = "main") -> ToolOutcome:
    """
    Clone a public GitHub repository to a temporary local directory.

    Args:
        github_url: Full GitHub URL (https://github.com/user/repo)
        branch: Branch to check out (default: "main")

    Returns:
        ToolOutcome with local_path set on success, error set on failure.
    """
    temp_dir = tempfile.mkdtemp(prefix="deployment-agent-")
    try:
        Repo.clone_from(github_url, temp_dir, branch=branch)
        return ToolOutcome(
            success=True,
            local_path=temp_dir,
            metadata={
                "github_url": github_url,
                "branch": branch,
                "cloned_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except GitCommandError as e:
        return ToolOutcome(success=False, error=str(e))

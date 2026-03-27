import os

from dotenv import load_dotenv

load_dotenv()


def load_config() -> dict:
    missing = []
    for key in ("ANTHROPIC_API_KEY", "GITHUB_REPO", "ECS_CLUSTER", "ECS_SERVICE"):
        if not os.environ.get(key):
            missing.append(key)
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    return {
        "anthropic_api_key": os.environ["ANTHROPIC_API_KEY"],
        "github_repo": os.environ["GITHUB_REPO"],
        "github_branch": os.environ.get("GITHUB_BRANCH", "main"),
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
        "ecs_cluster": os.environ["ECS_CLUSTER"],
        "ecs_service": os.environ["ECS_SERVICE"],
    }

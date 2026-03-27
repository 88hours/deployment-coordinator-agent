import base64
from datetime import datetime, timezone

import boto3
import docker
from botocore.exceptions import BotoCoreError, ClientError
from docker.errors import DockerException

from src.tools.types import ToolOutcome


def push_image_tool(image_tag: str, aws_region: str, ecr_repo_name: str) -> ToolOutcome:
    """
    Push a locally built Docker image to AWS ECR.
    Creates the ECR repository if it does not exist.

    Args:
        image_tag: Local image tag to push (e.g., "myapp:latest")
        aws_region: AWS region where the ECR registry lives (e.g., "us-east-1")
        ecr_repo_name: ECR repository name (e.g., "myapp")

    Returns:
        ToolOutcome with image_uri set on success, error set on failure.
    """
    try:
        ecr = boto3.client("ecr", region_name=aws_region)

        # Get AWS account ID and registry URI
        account_id = boto3.client("sts", region_name=aws_region).get_caller_identity()["Account"]
        registry = f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com"

        # Create ECR repo if it doesn't exist
        try:
            ecr.create_repository(repositoryName=ecr_repo_name)
        except ClientError as e:
            if e.response["Error"]["Code"] != "RepositoryAlreadyExistsException":
                raise

        # Get ECR auth token and configure Docker
        token = ecr.get_authorization_token()
        auth_data = token["authorizationData"][0]
        username, password = (
            base64.b64decode(auth_data["authorizationToken"]).decode().split(":", 1)
        )

        # Tag image with ECR URI
        local_tag = image_tag.split(":")[1] if ":" in image_tag else "latest"
        image_uri = f"{registry}/{ecr_repo_name}:{local_tag}"

        client = docker.from_env()
        image = client.images.get(image_tag)
        image.tag(image_uri)

        # Push
        client.images.push(image_uri, auth_config={"username": username, "password": password})

        return ToolOutcome(
            success=True,
            image_uri=image_uri,
            metadata={
                "ecr_repo_name": ecr_repo_name,
                "aws_region": aws_region,
                "pushed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except (BotoCoreError, ClientError) as e:
        return ToolOutcome(success=False, error=str(e))
    except DockerException as e:
        return ToolOutcome(success=False, error=str(e))

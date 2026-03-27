from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.tools.types import ToolOutcome


def deploy_service_tool(
    image_uri: str,
    aws_region: str,
    ecs_cluster: str,
    ecs_service: str,
) -> ToolOutcome:
    """
    Deploy a new image to an existing ECS service by registering a new task
    definition revision and updating the service to use it.

    Args:
        image_uri: Full ECR image URI (e.g., "123456789.dkr.ecr.us-east-1.amazonaws.com/myapp:latest")
        aws_region: AWS region of the ECS cluster (e.g., "us-east-1")
        ecs_cluster: ECS cluster name (e.g., "staging")
        ecs_service: ECS service name (e.g., "my-api-staging")

    Returns:
        ToolOutcome with task_definition_arn and deployment_id set on success, error on failure.
    """
    try:
        ecs = boto3.client("ecs", region_name=aws_region)

        # Get the current task definition used by the service
        service_resp = ecs.describe_services(cluster=ecs_cluster, services=[ecs_service])
        services = service_resp.get("services", [])
        if not services:
            return ToolOutcome(
                success=False,
                error=f"ECS service '{ecs_service}' not found in cluster '{ecs_cluster}'",
            )

        current_task_def_arn = services[0]["taskDefinition"]

        # Describe the current task definition
        task_def_resp = ecs.describe_task_definition(taskDefinition=current_task_def_arn)
        task_def = task_def_resp["taskDefinition"]

        # Update container definitions with the new image URI
        container_defs = task_def["containerDefinitions"]
        for container in container_defs:
            container["image"] = image_uri

        # Register a new task definition revision
        register_kwargs = {
            "family": task_def["family"],
            "containerDefinitions": container_defs,
        }
        # Carry over optional fields if present
        for field in (
            "taskRoleArn",
            "executionRoleArn",
            "networkMode",
            "volumes",
            "placementConstraints",
            "requiresCompatibilities",
            "cpu",
            "memory",
            "tags",
            "pidMode",
            "ipcMode",
            "proxyConfiguration",
            "inferenceAccelerators",
            "ephemeralStorage",
            "runtimePlatform",
        ):
            if field in task_def:
                register_kwargs[field] = task_def[field]

        new_task_def_resp = ecs.register_task_definition(**register_kwargs)
        new_task_def_arn = new_task_def_resp["taskDefinition"]["taskDefinitionArn"]

        # Update the service to use the new task definition
        update_resp = ecs.update_service(
            cluster=ecs_cluster,
            service=ecs_service,
            taskDefinition=new_task_def_arn,
            forceNewDeployment=True,
        )
        deployment_id = update_resp["service"]["deployments"][0]["id"]

        return ToolOutcome(
            success=True,
            task_definition_arn=new_task_def_arn,
            deployment_id=deployment_id,
            metadata={
                "ecs_cluster": ecs_cluster,
                "ecs_service": ecs_service,
                "image_uri": image_uri,
                "deployed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except (BotoCoreError, ClientError) as e:
        return ToolOutcome(success=False, error=str(e))

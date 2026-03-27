from config import load_config
from src.agent.loop import DeploymentAgent


def main() -> None:
    config = load_config()

    agent = DeploymentAgent(anthropic_api_key=config["anthropic_api_key"])
    result = agent.deploy(
        github_repo=config["github_repo"],
        branch=config["github_branch"],
        aws_region=config["aws_region"],
        ecs_cluster=config["ecs_cluster"],
        ecs_service=config["ecs_service"],
    )
    print(result)


if __name__ == "__main__":
    main()

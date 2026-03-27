# Deployment Coordinator Agent - Product Requirements Document

## Overview

The Deployment Coordinator Agent is an autonomous Python agent that manages the end-to-end deployment of containerized microservices to AWS staging environments. Given a GitHub repository containing a Dockerfile and source code, the agent clones the repo, builds a Docker image, pushes it to AWS ECR (Elastic Container Registry), and deploys it to AWS ECS (Elastic Container Service). The agent makes decisions along the way and reports the outcome.

## Problem Statement

Deploying code to production is repetitive and error-prone when done manually. Developers run a sequence of commands: clone the repo, build a Docker image, push to a registry, update a service definition, and verify the deployment. Each step requires watching for errors and deciding what to do next. An agent can automate this workflow, make intelligent decisions, and free developers from manual orchestration.

## Target User

Developers and DevOps engineers who deploy containerized services to AWS and want to offload the deployment orchestration to an autonomous agent.

## Core Value Proposition

Tell the agent "deploy this repo to staging" and it handles cloning, building, pushing, and deploying. No manual steps. The agent reasons about what went wrong if something fails and reports clearly.

---

## User Flow

### Invoke the Agent

The developer provides the agent with a GitHub repository URL and AWS credentials. Example:

```
agent.deploy(
  github_repo="https://github.com/user/my-api",
  branch="main",
  aws_region="us-east-1",
  ecs_cluster="staging",
  ecs_service="my-api-staging"
)
```

### Agent Execution Loop (Happy Path)

The agent executes the following steps autonomously:

**Step 1: Clone the Repository**
- Agent observes: "I need to clone the repo"
- Agent acts: Clones the GitHub repository to a local directory
- Agent observes: "Repo cloned. What's in it?"
- Reason to next step: Repository is ready to build

**Step 2: Validate the Docker Setup**
- Agent observes: "Is there a Dockerfile?"
- Agent acts: Checks for Dockerfile in the repo root
- Agent observes: "Dockerfile found. Build args?"
- Reason to next step: Dockerfile exists and is ready to build

**Step 3: Build the Docker Image**
- Agent observes: "I need to build a Docker image"
- Agent acts: Runs `docker build` with a versioned tag (image:latest, image:git-sha, etc.)
- Agent observes: "Build completed successfully"
- Reason to next step: Image is ready to push

**Step 4: Push to AWS ECR**
- Agent observes: "I need to push this image to ECR"
- Agent acts: Authenticates to AWS ECR and pushes the image
- Agent observes: "Image pushed to ECR. Ready to deploy."
- Reason to next step: Image is in the registry

**Step 5: Deploy to AWS ECS**
- Agent observes: "I need to update the ECS service"
- Agent acts: Calls AWS ECS to update the service task definition with the new image
- Agent observes: "Service update initiated"
- Reason to next step: Deployment command sent

**Step 6: Report Success**
- Agent observes: "Deployment workflow completed"
- Agent reports: "Successfully deployed image:tag to my-api-staging. ECS service updated."

---

## Feature Set

### MVP Features (Happy Path Only)

These are the features required for the first working version.

**Repository Cloning**
- Clone a GitHub repository to a temporary local directory
- Check out a specific branch (default: main)
- Validate the clone was successful

**Docker Build**
- Detect Dockerfile in the repo root
- Build a Docker image with a versioned tag (e.g., `myapp:latest`, `myapp:abc123def`)
- Handle build logs and report build status

**Push to AWS ECR**
- Authenticate to AWS ECR using provided credentials or IAM role
- Create an ECR repository if it does not exist
- Push the built image to ECR
- Return the image URI (for use in ECS deployment)

**Deploy to AWS ECS**
- Update an ECS service to use the new image
- Trigger a rolling deployment
- Report the deployment status

**Agent Reasoning and Observation**
- At each step, the agent observes the current state
- The agent reasons about the next action based on the goal (deploy this repo)
- The agent reports its findings and decisions in plain language

**Error Reporting**
- If any step fails, the agent stops and reports what went wrong
- Report includes: which step failed, what error was encountered, what action was taken

### Phase 2 Features (Out of Scope for MVP)

- Health checks and monitoring after deployment
- Rollback if the deployed service becomes unhealthy
- Support for multiple environments (staging, production, custom)
- Slack/email notifications of deployment status
- Deployment history and logs
- Auto-remediation for common failures (rate limits, auth issues)
- Support for non-ECS deployment targets (Lambda, AppRunner, Kubernetes)

---

## Out of Scope

The following are explicitly not part of the MVP to keep the product focused.

- Rollback functionality (Phase 2)
- Health monitoring and automatic remediation (Phase 2)
- Multi-environment support (MVP focuses on staging only)
- External notifications (Phase 2)
- Support for private GitHub repositories (MVP uses public repos)
- Build caching optimization
- Secrets management beyond AWS credentials
- Database migrations as part of deployment
- Canary deployments or blue-green deployments

---

## Key Product Decisions

**Why an agent, not a CI/CD pipeline?**
A traditional CI/CD system (GitHub Actions, Jenkins) is great for automated testing and building. An agent adds reasoning -- it can decide what to do based on what it observes, adapt to failures, and explain its decisions. For learning agentic AI, building the agent teaches you autonomy and decision-making, not just automation.

**Why Python?**
Python is the standard for DevOps automation. Libraries like boto3 (AWS SDK), docker-py, and subprocess are mature and widely used. Python is also simpler for focusing on agent logic without language boilerplate. The deployed service can be any language -- the agent language is separate.

**Why happy path only in MVP?**
Focusing on the success case first lets you build the core agent loop (observe, reason, act) without getting lost in error handling. Phase 2 adds rollback and recovery.

**Why staging only in MVP?**
Deploying to staging is lower risk than production. This is the right scope for learning agent behavior and validating the workflow before adding production safety measures.

---

## Success Metrics (MVP)

- Agent successfully clones, builds, pushes, and deploys a simple TypeScript/Node.js service from GitHub to AWS ECS staging
- Agent makes at least three observable decisions (e.g., "Dockerfile found" -> proceed, "Build succeeded" -> push to ECR, "Image pushed" -> deploy to ECS)
- Agent reports its actions and decisions in plain language a human can understand
- No manual intervention required once the agent is invoked
- End-to-end deployment takes under five minutes for a small microservice

---

## Development Approach

This agent is built agentic-first. The core focus is on the agent loop and reasoning, not infrastructure glue. Each tool the agent has (clone, build, push, deploy) is simple and focused. The agent's job is to orchestrate them, observe outcomes, and reason about next steps.

See `CLAUDE.md` for development context and instructions for Claude Code sessions.

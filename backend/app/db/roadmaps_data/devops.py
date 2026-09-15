"""Cloud / DevOps Engineer roadmap definition with progressive practice problems and market demand integration."""
from typing import Any, Dict
from app.db.roadmaps_data.common import CANONICAL_ROLE_IDS, ROADMAP_IDS, make_problem, make_skill

DEVOPS_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["cloud-devops-engineer"],
    "slug": "cloud-devops-engineer",
    "role_id": CANONICAL_ROLE_IDS["cloud-devops-engineer"],
    "title": "Cloud / DevOps Engineer",
    "domain": "Cloud & Infrastructure",
    "category": "Engineering",
    "description": "Master cloud platforms, container orchestration, Infrastructure as Code, CI/CD automation, cloud networking, and enterprise observability across AWS, Docker, Kubernetes, and Terraform.",
    "version": "v2.0",
    "has_market_data": True,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Operating Systems & Systems Fundamentals",
            "description": "Master Linux system administration, networking protocols, process lifecycle, and distributed version control.",
            "skills": [
                make_skill(
                    slug="linux-devops",
                    name="Linux Systems",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="POSIX operating systems: Kernel architecture, systemd services, networking utilities, Bash scripting, process limits, and server hardening.",
                    key_topics=["Linux Kernel & Process Management (ps, top, systemctl)", "Networking Utilities (netstat, ss, curl, dig, iptables)", "Shell Scripting (Bash, set -euo pipefail)", "Permissions, Ownership & sudoers (chmod, chown)", "SSH Key Management & Server Hardening"],
                    role_relevance="The foundation of cloud infrastructure; production microservices run almost exclusively on Linux container hosts.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Linux Foundation Docs", "url": "https://docs.linuxfoundation.org/", "description": "Comprehensive resources on Linux systems administration, kernel, and networking."},
                        {"type": "YOUTUBE", "title": "Linux for DevOps Full Course", "url": "https://www.youtube.com/watch?v=ROjZy1WbCIA", "description": "Hands-on guide to Linux server administration, bash scripting, and networking."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="linux-dev-prob-1",
                            title="Automated Server Setup & User Hardening Script",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Automate user provisioning and disable insecure SSH root login.",
                            problem_statement="Write a bash provisioning script that creates a sudo user, configures SSH keys, and disables root login.",
                            requirements=[
                                "Write a bash script with 'set -euo pipefail' for error safety.",
                                "Create a non-root deploy user with sudo privileges.",
                                "Disable PermitRootLogin and PasswordAuthentication in /etc/ssh/sshd_config and restart sshd."
                            ],
                            concepts_tested=["Bash Scripting", "User & Sudo Management", "SSH Configuration", "Security Hardening"],
                            expected_outcome="A secure Linux server configuration accessible only via authorized SSH keys.",
                            optional_hints=["Always verify SSH access in a secondary terminal before logging out of root."]
                        ),
                        make_problem(
                            problem_id="linux-dev-prob-2",
                            title="Network Troubleshooting & Port Inspection",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Diagnose network connectivity and packet flow issues using standard Linux CLI tools.",
                            problem_statement="Troubleshoot a service that cannot reach an external database using dig, curl, ss, and traceroute.",
                            requirements=[
                                "Use 'ss -tulpn' to inspect open listening TCP ports.",
                                "Use 'dig +short' to verify DNS resolution for database hostnames.",
                                "Use 'curl -v telnet://host:port' to test socket reachability through firewall rules."
                            ],
                            concepts_tested=["ss / netstat", "DNS Resolution (dig)", "TCP Handshakes (curl/telnet)", "Network Troubleshooting"],
                            expected_outcome="Accurate isolation of network failure root causes (DNS vs firewall vs service crash).",
                            optional_hints=["'ss -tulpn' shows process names and listening ports without netstat deprecation."]
                        ),
                        make_problem(
                            problem_id="linux-dev-prob-3",
                            title="Systemd Service Daemon with Resource Limits (cgroups)",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Create a self-healing systemd service unit enforcing memory and CPU limits.",
                            problem_statement="Create a systemd unit file running a background worker process, enforcing a 512MB RAM ceiling and automatic restart on crash.",
                            requirements=[
                                "Create /etc/systemd/system/worker.service with ExecStart and User=deploy.",
                                "Enforce MemoryMax=512M and CPUQuota=50% to prevent resource exhaustion.",
                                "Configure Restart=always and RestartSec=5s.",
                                "Simulate an OOM kill and verify systemd recovers and logs to journalctl."
                            ],
                            concepts_tested=["systemd Unit Files", "cgroups Resource Limits (MemoryMax, CPUQuota)", "Restart Policies", "journalctl Log Inspection"],
                            expected_outcome="A robust daemonized service that restarts automatically and never starves neighboring server processes.",
                            optional_hints=["Check 'systemctl status worker.service' after an OOM event to see systemd kill status."]
                        ),
                    ],
                ),
                make_skill(
                    slug="git-devops",
                    name="Git & Version Control",
                    canonical_slug="git",
                    difficulty="BEGINNER",
                    description="Version control workflows for infrastructure: Branching models, semantic tagging, Pull Request automation, and GitOps foundations.",
                    key_topics=["Trunk-Based Development & Feature Branches", "Semantic Versioning & Git Tags", "Handling Merge Conflicts & Interactive Rebase", "Pull Request Approvals & Branch Protection Rules"],
                    role_relevance="The single source of truth for Infrastructure as Code, CI/CD pipeline triggers, and GitOps deployments.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Git Documentation", "url": "https://git-scm.com/doc", "description": "Official Git documentation and Pro Git reference guide."},
                        {"type": "YOUTUBE", "title": "Git for DevOps & Cloud Engineers", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "description": "Git workflows for infrastructure repositories, tagging, and automated releases."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="git-dev-prob-1",
                            title="Semantic Tagging & Release Notes",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Manage semantic version tags for infrastructure releases.",
                            problem_statement="Create annotated Git release tags following SemVer standards and generate release logs.",
                            requirements=[
                                "Create annotated tags: git tag -a v1.0.0 -m 'Release v1.0.0'.",
                                "Generate a changelog comparing two tags using git log v1.0.0..v1.1.0 --oneline.",
                                "Push tags to remote using git push --tags."
                            ],
                            concepts_tested=["Git Tags", "Semantic Versioning (SemVer)", "git log range comparison", "Release Tracking"],
                            expected_outcome="A clean, verifiable release history linking infrastructure states to specific git tags.",
                            optional_hints=["Use annotated tags (-a) because they store tagger date, name, and message."]
                        ),
                        make_problem(
                            problem_id="git-dev-prob-2",
                            title="Branch Protection & Git Conflict Resolution",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Resolve conflicting Terraform code across divergent branches.",
                            problem_statement="Resolve a merge conflict between two branches modifying the same Terraform resource configuration.",
                            requirements=[
                                "Introduce divergent updates to main.tf across feature and main branches.",
                                "Execute git merge, locate conflict markers, and preserve both required configuration blocks.",
                                "Commit the resolved state and verify git status is clean."
                            ],
                            concepts_tested=["Git Merging", "Conflict Markers", "Terraform Code Merging", "Clean Commits"],
                            expected_outcome="A clean, non-destructive merge resolution preserving all required infrastructure settings.",
                            optional_hints=["Use 'git diff' to review resolved changes before committing."]
                        ),
                        make_problem(
                            problem_id="git-dev-prob-3",
                            title="Automated Pre-Commit Security Hooks",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Install and enforce pre-commit git hooks that block committing secrets or invalid Terraform code.",
                            problem_statement="Configure the pre-commit framework to automatically run terraform_fmt, terraform_validate, and detect-secrets before allowing any commit.",
                            requirements=[
                                "Create a .pre-commit-config.yaml declaring terraform and secret detection hooks.",
                                "Install hooks using 'pre-commit install'.",
                                "Verify that attempting to commit a file with a hardcoded AWS key is automatically blocked by the hook."
                            ],
                            concepts_tested=["Git Hooks", "pre-commit Framework", "Secret Leak Prevention", "Automated Validation"],
                            expected_outcome="A local developer security gate that intercepts secrets before they ever touch git history.",
                            optional_hints=["Never use 'git commit --no-verify' to bypass security hooks."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Containers & CI/CD Pipelines",
            "description": "Package workloads into reproducible container images and automate verification pipelines.",
            "skills": [
                make_skill(
                    slug="docker-devops",
                    name="Docker",
                    canonical_slug="docker",
                    difficulty="INTERMEDIATE",
                    description="Container virtualization: Multi-stage Dockerfiles, image optimization, layer caching, Docker networking, non-root users, and vulnerability scanning.",
                    key_topics=["Container Runtimes vs Virtual Machines", "Multi-stage Dockerfile Optimization", "Docker Compose Multi-Container Networking", "Container Security (Non-root, read-only rootfs)", "Container Registries & Image Scanning (Trivy)"],
                    role_relevance="The universal runtime packaging unit for microservices and cloud deployments.",
                    prerequisites=["linux-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Docker Documentation", "url": "https://docs.docker.com/", "description": "Official guides for Docker engine, multi-stage builds, and CLI reference."},
                        {"type": "YOUTUBE", "title": "Docker Tutorial for Beginners — TechWorld with Nana", "url": "https://www.youtube.com/watch?v=3c-iBn73dDE", "description": "Comprehensive tutorial on containers, images, networking, and volumes."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="docker-dev-prob-1",
                            title="Containerize a Microservice with Layer Caching",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write a Dockerfile structured for optimal build caching.",
                            problem_statement="Build a Dockerfile for a backend service that caches dependency installation across rebuilds.",
                            requirements=[
                                "Copy dependency manifests first and run package installation.",
                                "Copy application source code in a subsequent step.",
                                "Verify that editing application code does not re-download dependencies during 'docker build'."
                            ],
                            concepts_tested=["Dockerfile Layer Caching", "COPY vs RUN", "Image Rebuilding Speed"],
                            expected_outcome="Near-instant local container rebuilds when modifying application source code.",
                            optional_hints=["Layers are invalidated as soon as any copied file changes."]
                        ),
                        make_problem(
                            problem_id="docker-dev-prob-2",
                            title="Multi-Service Stack with Docker Compose & Health Checks",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Orchestrate a web service, database, and cache with dependent health checks.",
                            problem_statement="Build a docker-compose.yml file managing app, postgres, and redis containers on an isolated network.",
                            requirements=[
                                "Define custom bridge network 'backend_net'.",
                                "Add health checks to postgres (pg_isready) and redis (redis-cli ping).",
                                "Configure web service to wait for both health checks before starting."
                            ],
                            concepts_tested=["Docker Compose", "Health Checks", "depends_on with conditions", "Isolated Bridge Networks"],
                            expected_outcome="A reliable local stack that starts without race condition database connection failures.",
                            optional_hints=["Use 'condition: service_healthy' in depends_on."]
                        ),
                        make_problem(
                            problem_id="docker-dev-prob-3",
                            title="Hardened Multi-Stage Production Container with Trivy Scan",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Produce a minimal, secure production container image and verify zero high/critical vulnerabilities.",
                            problem_statement="Build a hardened multi-stage image running as an unprivileged user and scan it with Trivy.",
                            requirements=[
                                "Use multi-stage build to separate build tools from the final runtime.",
                                "Create and switch to non-root user 'appuser' with explicit UID.",
                                "Run 'trivy image --severity HIGH,CRITICAL <image>' and achieve zero unpatched vulnerabilities."
                            ],
                            concepts_tested=["Multi-stage Builds", "Non-root Execution", "Trivy Vulnerability Scanning", "Minimal Base Images (distroless / alpine)"],
                            expected_outcome="An enterprise-hardened container image ready for production Kubernetes deployment.",
                            optional_hints=["Google's distroless base images contain only your app and runtime dependencies without package managers."]
                        ),
                    ],
                ),
                make_skill(
                    slug="github-actions-devops",
                    name="GitHub Actions",
                    canonical_slug="github-actions",
                    difficulty="INTERMEDIATE",
                    description="Continuous Integration and Continuous Deployment: Workflow syntax, matrix builds, automated testing, container publishing, and environment protection rules.",
                    key_topics=["Workflow Syntax & Triggers (push, pull_request, workflow_dispatch)", "Job Matrices & Parallelism", "Service Containers for Integration Tests", "Encrypted Secrets & Environment Protection", "Publishing Images to GitHub Container Registry (GHCR)"],
                    role_relevance="Automates code quality gates, security scans, and continuous release pipelines.",
                    prerequisites=["git-devops", "docker-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "GitHub Actions Docs", "url": "https://docs.github.com/en/actions", "description": "Official guides, reference, and examples for building automated workflows."},
                        {"type": "YOUTUBE", "title": "GitHub Actions CI/CD — TechWorld with Nana", "url": "https://www.youtube.com/watch?v=R8_veQiYBjI", "description": "Full course on building automated CI/CD pipelines from scratch."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="actions-dev-prob-1",
                            title="Automated Test & Lint Pipeline",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a CI pipeline that runs linters and test suites on pull requests.",
                            problem_statement="Build a GitHub Actions workflow that triggers on pull requests and executes linting and automated tests.",
                            requirements=[
                                "Trigger on pull_request to main.",
                                "Set up language runtime and cache dependencies.",
                                "Run lint checks and automated test runner, failing the job if any test fails."
                            ],
                            concepts_tested=["GitHub Actions Syntax", "PR Triggers", "Dependency Caching", "Job Exit Codes"],
                            expected_outcome="An automated gate preventing broken code from being merged into production branches.",
                            optional_hints=["Use actions/cache or built-in setup-action cache flags."]
                        ),
                        make_problem(
                            problem_id="actions-dev-prob-2",
                            title="Parallel Matrix Build with Service Container",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Execute integration tests across multiple runtime versions against an active database service container.",
                            problem_statement="Configure a matrix CI workflow that tests multiple runtime versions with an active PostgreSQL service container.",
                            requirements=[
                                "Define strategy: matrix for runtime versions.",
                                "Launch a services: postgres container with health checks.",
                                "Execute database integration tests against localhost:5432 in parallel across matrix jobs."
                            ],
                            concepts_tested=["Build Matrices", "Service Containers", "Parallel Execution", "Database Integration in CI"],
                            expected_outcome="Faster feedback across runtime versions with real database validation.",
                            optional_hints=["Use 'ports: - 5432:5432' in the service container configuration."]
                        ),
                        make_problem(
                            problem_id="actions-dev-prob-3",
                            title="Secure OIDC Cloud Deployment Pipeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Deploy to AWS or Kubernetes using OpenID Connect (OIDC) without storing static long-lived cloud credentials in GitHub Secrets.",
                            problem_statement="Configure a GitHub Actions deployment workflow using AWS OIDC federation to assume an IAM role securely.",
                            requirements=[
                                "Configure permissions: id-token: write and contents: read.",
                                "Use aws-actions/configure-aws-credentials with role-to-assume.",
                                "Build and push a container image to AWS ECR and deploy to ECS/EKS."
                            ],
                            concepts_tested=["OpenID Connect (OIDC)", "IAM Role Assumption", "Zero Static Secrets in CI", "Cloud Deployment Automation"],
                            expected_outcome="A modern, secure cloud deployment pipeline free of vulnerable static access keys.",
                            optional_hints=["OIDC eliminates the risk of leaked AWS_ACCESS_KEY_ID in GitHub repository secrets."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Cloud Platforms & Infrastructure as Code",
            "description": "Provision cloud infrastructure programmatically using Terraform and architect secure cloud networking on AWS.",
            "skills": [
                make_skill(
                    slug="aws-devops",
                    name="AWS",
                    canonical_slug="aws",
                    difficulty="INTERMEDIATE",
                    description="Amazon Web Services: Core infrastructure services including EC2 compute, S3 storage, RDS databases, IAM security governance, and VPC networking.",
                    key_topics=["IAM Roles, Policies & Principle of Least Privilege", "S3 Storage Classes & Bucket Policies", "RDS High Availability & Read Replicas", "EC2 Auto Scaling & Application Load Balancers (ALB)", "CloudWatch Metrics, Alarms & Logs"],
                    role_relevance="The market-leading cloud provider hosting enterprise backend and microservice workloads globally.",
                    prerequisites=["docker-devops", "linux-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "AWS Documentation", "url": "https://docs.aws.amazon.com/", "description": "Official guides, architecture best practices, and CLI reference for all AWS services."},
                        {"type": "YOUTUBE", "title": "AWS Certified Cloud Practitioner — freeCodeCamp", "url": "https://www.youtube.com/watch?v=SOTamWNgDKc", "description": "Comprehensive guide to core AWS services, security, architecture, and deployment."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="aws-dev-prob-1",
                            title="S3 Bucket Setup with Encryption & Lifecycle Policies",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Provision and configure an Amazon S3 bucket with encryption and automated tiering.",
                            problem_statement="Configure an S3 bucket with default KMS encryption, public access blocking, and a lifecycle rule moving objects to Glacier after 90 days.",
                            requirements=[
                                "Enable Block Public Access on the bucket.",
                                "Enable default server-side encryption with AWS-KMS.",
                                "Configure a lifecycle transition rule moving files to S3 Glacier Flexible Retrieval after 90 days."
                            ],
                            concepts_tested=["Amazon S3", "Bucket Policies", "KMS Encryption", "Lifecycle Tiering"],
                            expected_outcome="A cost-optimized, secure storage bucket that transitions aging files automatically.",
                            optional_hints=["Use 'aws s3api put-bucket-encryption' to test via AWS CLI."]
                        ),
                        make_problem(
                            problem_id="aws-dev-prob-2",
                            title="Application Load Balancer (ALB) & Auto Scaling Group",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Configure high availability compute with an Application Load Balancer and Auto Scaling Group.",
                            problem_statement="Set up an ALB distributing traffic across an Auto Scaling Group of EC2 instances spanning two Availability Zones.",
                            requirements=[
                                "Configure a Target Group with HTTP health check path '/health'.",
                                "Create an Auto Scaling Group with min=2, max=6 instances across two subnets.",
                                "Configure target tracking scaling policy maintaining average CPU utilization under 60%."
                            ],
                            concepts_tested=["Application Load Balancer (ALB)", "Auto Scaling Group (ASG)", "Health Checks", "Target Tracking Policies", "Multi-AZ Resilience"],
                            expected_outcome="A self-healing compute tier that automatically scales up under load and replaces failing instances.",
                            optional_hints=["Ensure Security Groups allow traffic from the ALB into the EC2 instances."]
                        ),
                        make_problem(
                            problem_id="aws-dev-prob-3",
                            title="RDS Multi-AZ Failover & Read Replica Architecture",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Configure an enterprise database tier with Multi-AZ automated failover and read scaling.",
                            problem_statement="Deploy a PostgreSQL RDS instance in a Multi-AZ configuration with a dedicated Read Replica for reporting traffic.",
                            requirements=[
                                "Configure RDS PostgreSQL in Multi-AZ mode for synchronous standby replication.",
                                "Create a cross-AZ Read Replica to handle read-heavy analytical queries.",
                                "Simulate primary database failover and measure failover latency and application reconnection."
                            ],
                            concepts_tested=["RDS Multi-AZ", "Read Replicas", "Automated Failover", "Database High Availability", "Connection Strings"],
                            expected_outcome="Enterprise database resilience guaranteeing sub-60-second recovery during primary hardware failures.",
                            optional_hints=["Use the 'Reboot with failover' option in the AWS console or CLI to test failover."]
                        ),
                    ],
                ),
                make_skill(
                    slug="terraform-iac",
                    name="Infrastructure as Code with Terraform",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Declarative infrastructure provisioning with HashiCorp Terraform: HCL syntax, state management, remote backends, modules, variables, and plan/apply workflows.",
                    key_topics=["Terraform HCL Syntax & Resources", "State Management & S3/DynamoDB Remote Backends", "Terraform Variables & Outputs", "Reusable Infrastructure Modules", "Terraform Plan, Apply & Drift Detection"],
                    role_relevance="The industry standard tool for version-controlled, repeatable, and automated cloud infrastructure deployment.",
                    prerequisites=["aws-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Terraform Documentation — HashiCorp", "url": "https://developer.hashicorp.com/terraform/docs", "description": "Official guides, tutorials, and provider documentation for Terraform."},
                        {"type": "YOUTUBE", "title": "Terraform Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=SLB_c_ayRMo", "description": "Complete beginner to advanced tutorial covering HCL, state management, modules, and AWS provisioning."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="tf-prob-1",
                            title="Declare VPC & S3 Bucket with Remote State",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write HCL code to provision an S3 bucket with remote state locking.",
                            problem_statement="Configure Terraform with an S3 remote backend and DynamoDB state locking, and provision a storage bucket.",
                            requirements=[
                                "Configure terraform { backend \"s3\" { ... } } with dynamodb_table for state locking.",
                                "Define an aws_s3_bucket resource with tags and lifecycle rules.",
                                "Execute 'terraform plan' and 'terraform apply', inspecting the generated state file."
                            ],
                            concepts_tested=["HCL Syntax", "Remote State (S3)", "State Locking (DynamoDB)", "terraform plan & apply"],
                            expected_outcome="A safely locked remote state architecture preventing concurrent deployment corruption.",
                            optional_hints=["Never commit local .tfstate files to Git."]
                        ),
                        make_problem(
                            problem_id="tf-prob-2",
                            title="Reusable Microservice Infrastructure Module",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Extract repeatable cloud components into a parameterized Terraform module.",
                            problem_statement="Build a reusable Terraform module for a microservice that provisions an ECS task definition, service, and security group.",
                            requirements=[
                                "Create a module with variables.tf (service_name, cpu, memory, image), main.tf, and outputs.tf.",
                                "Instantiate the module twice in root configuration for 'auth-service' and 'billing-service'.",
                                "Verify parameterized outputs expose service ARNs cleanly."
                            ],
                            concepts_tested=["Terraform Modules", "Module Inputs (variables.tf)", "Module Outputs (outputs.tf)", "DRY Infrastructure"],
                            expected_outcome="A modular infrastructure codebase where adding a new microservice requires only 10 lines of HCL.",
                            optional_hints=["Document module inputs with description and type constraints."]
                        ),
                        make_problem(
                            problem_id="tf-prob-3",
                            title="Automated Terraform CI/CD with Atlantis / GitHub Actions",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Automate Terraform pull request plans and drift detection in CI.",
                            problem_statement="Build a GitHub Actions workflow that runs 'terraform plan' on pull requests and comments the plan diff directly on the PR.",
                            requirements=[
                                "Configure setup-terraform action with cloud credentials.",
                                "Run 'terraform validate' and 'terraform plan -no-color'.",
                                "Post the plan output as a pull request comment for team review.",
                                "Apply changes automatically when the pull request is merged to main."
                            ],
                            concepts_tested=["GitOps for Infrastructure", "Automated Terraform CI", "PR Plan Comments", "Infrastructure Drift Detection"],
                            expected_outcome="Full visibility of infrastructure changes prior to merging with automated production application.",
                            optional_hints=["Use 'actions/github-script' to post or update PR comments with the plan output."]
                        ),
                    ],
                ),
                make_skill(
                    slug="cloud-networking-security",
                    name="Cloud Networking & Security Architecture",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Enterprise cloud networking: VPC design, public/private subnets, NAT Gateways, Route Tables, Security Groups, Network ACLs, Bastion hosts, and AWS WAF.",
                    key_topics=["VPC CIDR Block Allocation & Subnetting", "Public vs Private Subnet Architecture & Route Tables", "NAT Gateways & Internet Gateways", "Stateful Security Groups vs Stateless NACLs", "AWS WAF (Web Application Firewall) & DDoS Defense"],
                    role_relevance="Guarantees isolation of internal databases and microservices from direct internet exposure, protecting cloud workloads.",
                    prerequisites=["aws-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "AWS VPC User Guide", "url": "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html", "description": "Official guide for designing Virtual Private Clouds, subnets, route tables, and gateways."},
                        {"type": "YOUTUBE", "title": "AWS Networking Masterclass", "url": "https://www.youtube.com/watch?v=2bEeeiJ23Yw", "description": "Deep dive into VPC design, CIDR math, subnets, NAT gateways, and security groups."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="net-prob-1",
                            title="Two-Tier VPC Network Design",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Architect a custom VPC with public and private subnets across two Availability Zones.",
                            problem_statement="Create a VPC (10.0.0.0/16) with 2 public subnets for load balancers and 2 private subnets for application servers.",
                            requirements=[
                                "Attach an Internet Gateway to the VPC.",
                                "Configure a public route table with default route (0.0.0.0/0) pointing to the Internet Gateway.",
                                "Verify public subnets are associated with the public route table and private subnets have no direct internet route."
                            ],
                            concepts_tested=["VPC CIDR Math", "Public vs Private Subnets", "Internet Gateway (IGW)", "Route Tables"],
                            expected_outcome="A standard two-tier network where databases in private subnets have zero public IP exposure.",
                            optional_hints=["Allocate /24 subnets: 10.0.1.0/24 (public-1), 10.0.2.0/24 (public-2), 10.0.10.0/24 (private-1), 10.0.11.0/24 (private-2)."]
                        ),
                        make_problem(
                            problem_id="net-prob-2",
                            title="NAT Gateway & Egress-Only Internet Routing",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Enable outbound internet access for private instances without permitting inbound connections.",
                            problem_statement="Provision a NAT Gateway in a public subnet and route private subnet outbound traffic through it for software updates.",
                            requirements=[
                                "Allocate an Elastic IP and create an aws_nat_gateway in public subnet 1.",
                                "Create a private route table with route 0.0.0.0/0 -> NAT Gateway.",
                                "Associate private subnets with the private route table and verify private instances can curl external APIs."
                            ],
                            concepts_tested=["NAT Gateway", "Elastic IP", "Private Route Tables", "Outbound-Only Internet Routing"],
                            expected_outcome="Private instances can download package updates from the internet while rejecting all incoming connections.",
                            optional_hints=["NAT Gateways must always reside in a public subnet with an Internet Gateway route."]
                        ),
                        make_problem(
                            problem_id="net-prob-3",
                            title="Defense-in-Depth with Security Groups, NACLs & WAF",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement layered perimeter security using Security Groups, Network ACLs, and AWS WAF rules.",
                            problem_statement="Harden a web application: allow only ALB traffic into app servers via security group chaining, block malicious IPs via NACLs, and deploy AWS WAF with rate-based rules.",
                            requirements=[
                                "Chain Security Groups: App SG ingress allows port 8000 only from ALB SG source (no CIDR blocks).",
                                "Configure Network ACLs blocking a known abusive CIDR block at the subnet boundary.",
                                "Deploy an AWS WAF WebACL associated with the ALB containing an AWS-managed CommonRuleSet and a rate-limiting rule (2,000 req/5 min)."
                            ],
                            concepts_tested=["Security Group Chaining", "Network ACLs (Stateless Filtering)", "AWS WAF (Web Application Firewall)", "Rate-Based Rules", "DDoS Mitigation"],
                            expected_outcome="A fortified cloud perimeter that filters malicious traffic at DNS, CDN, network, and application layers.",
                            optional_hints=["Security group rules that reference another security group ID adapt dynamically when instance IPs change."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Container Orchestration & GitOps",
            "description": "Deploy, scale, and manage containerized microservices with Kubernetes, Helm, ArgoCD, and Prometheus.",
            "skills": [
                make_skill(
                    slug="kubernetes-devops",
                    name="Kubernetes",
                    canonical_slug="kubernetes",
                    difficulty="ADVANCED",
                    description="Container orchestration: Pods, Deployments, Services (ClusterIP, NodePort, LoadBalancer), Ingress controllers, ConfigMaps, Secrets, Horizontal Pod Autoscaling (HPA), and persistent storage.",
                    key_topics=["Kubernetes Architecture (Control Plane vs Worker Nodes)", "Pods, ReplicaSets & Deployments", "Services (ClusterIP, NodePort, LoadBalancer) & Ingress", "ConfigMaps & Secrets Management", "Horizontal Pod Autoscaler (HPA) & Resource Requests/Limits"],
                    role_relevance="The global operating system of the cloud, orchestrating containerized microservices at planetary scale.",
                    prerequisites=["docker-devops", "linux-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Kubernetes Official Documentation", "url": "https://kubernetes.io/docs/home/", "description": "Official documentation covering concepts, tasks, tutorials, and reference for Kubernetes."},
                        {"type": "YOUTUBE", "title": "Kubernetes Course for Beginners — TechWorld with Nana", "url": "https://www.youtube.com/watch?v=X48VuDVv0do", "description": "Complete guide to Kubernetes architecture, deployments, services, and ingress."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="k8s-prob-1",
                            title="Zero-Downtime Deployment & Service Manifests",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write Kubernetes manifests for a resilient Deployment and internal ClusterIP Service.",
                            problem_statement="Deploy a containerized web service with 3 replicas, readiness/liveness probes, and a ClusterIP Service.",
                            requirements=[
                                "Define a Deployment with replicas: 3 and rollingUpdate strategy (maxSurge: 1, maxUnavailable: 0).",
                                "Configure livenessProbe and readinessProbe targeting '/health'.",
                                "Define a ClusterIP Service exposing port 80 and routing to container port 8000 using label selectors."
                            ],
                            concepts_tested=["Deployment Manifests", "Rolling Updates", "Liveness & Readiness Probes", "ClusterIP Services", "Label Selectors"],
                            expected_outcome="A zero-downtime deployment where traffic is routed only to pods whose readiness checks pass.",
                            optional_hints=["Use 'kubectl rollout status deployment/my-app' to monitor rolling updates."]
                        ),
                        make_problem(
                            problem_id="k8s-prob-2",
                            title="Ingress Routing & TLS Termination with Cert-Manager",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Expose HTTP services externally using an Ingress controller with automated Let's Encrypt TLS certificates.",
                            problem_statement="Configure an Nginx Ingress resource that routes traffic based on host and path, securing it with automated TLS certificates.",
                            requirements=[
                                "Define an Ingress resource routing 'api.example.com/v1' to backend-service.",
                                "Configure cert-manager ClusterIssuer using Let's Encrypt ACME HTTP-01 challenge.",
                                "Verify that navigating to the URL serves a valid HTTPS certificate with automatic HTTP-to-HTTPS redirect."
                            ],
                            concepts_tested=["Ingress Controller (Nginx)", "Host & Path-Based Routing", "TLS Secret Management", "Cert-Manager Automation"],
                            expected_outcome="An external-facing gateway delivering automated HTTPS encryption and intelligent path routing.",
                            optional_hints=["Add the annotation 'cert-manager.io/cluster-issuer: letsencrypt-prod' to your Ingress."]
                        ),
                        make_problem(
                            problem_id="k8s-prob-3",
                            title="Horizontal Pod Autoscaler (HPA) under Simulated Load",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Configure automated pod scaling based on CPU utilization thresholds.",
                            problem_statement="Configure an HPA that scales a deployment from 2 to 10 pods when average CPU exceeds 60%, verifying scaling with Apache Bench.",
                            requirements=[
                                "Set explicit resources.requests and resources.limits for CPU and Memory in the Pod spec.",
                                "Define HorizontalPodAutoscaler targeting 60% average CPU utilization.",
                                "Generate load using 'ab -n 100000 -c 100' or k6 and observe 'kubectl get hpa' scale pods up, followed by cooldown scale-down."
                            ],
                            concepts_tested=["Horizontal Pod Autoscaler (HPA)", "Resource Requests & Limits", "Metrics Server", "Autoscaling Policies (Cooldowns)"],
                            expected_outcome="Dynamic cluster scaling that absorbs traffic spikes and scales down to conserve cloud costs.",
                            optional_hints=["HPA requires the Kubernetes Metrics Server to be running in the cluster."]
                        ),
                    ],
                ),
                make_skill(
                    slug="gitops-helm",
                    name="GitOps & Continuous Delivery with Helm & ArgoCD",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Declarative continuous delivery for Kubernetes: Packaging applications with Helm charts, values.yaml configuration, and automating GitOps deployments with ArgoCD.",
                    key_topics=["Helm Chart Architecture (Chart.yaml, templates, values.yaml)", "Helm Templating & Built-in Objects", "Helm Dependencies & Subcharts", "GitOps Principles (Declarative, Versioned, Automated)", "ArgoCD Application CRDs & Automated Sync / Self-Healing"],
                    role_relevance="The modern paradigm for deploying microservices to Kubernetes, eliminating manual kubectl executions in favor of audited git commits.",
                    prerequisites=["kubernetes-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "ArgoCD Documentation", "url": "https://argo-cd.readthedocs.io/en/stable/", "description": "Official guides for GitOps continuous delivery and declarative Kubernetes management."},
                        {"type": "YOUTUBE", "title": "GitOps with ArgoCD and Helm Tutorial", "url": "https://www.youtube.com/watch?v=MeU5_r9XZ44", "description": "Hands-on walkthrough connecting GitHub repositories to Kubernetes clusters with ArgoCD."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="gitops-prob-1",
                            title="Parameterized Helm Chart Packaging",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Package a Kubernetes application into a reusable Helm chart with values.yaml parameterization.",
                            problem_statement="Create a Helm chart for a web application parameterizing replica count, image repository, tag, and service ports.",
                            requirements=[
                                "Create chart structure: Chart.yaml, values.yaml, and templates/.",
                                "Template deployment.yaml using {{ .Values.replicaCount }} and {{ .Values.image.repository }}.",
                                "Lint the chart with 'helm lint' and test rendering with 'helm template'."
                            ],
                            concepts_tested=["Helm Charts", "values.yaml Parameterization", "Helm Templating Syntax", "helm lint & template"],
                            expected_outcome="A portable Helm chart deployable across dev, staging, and prod with distinct values files.",
                            optional_hints=["Use the 'default' function in templates for optional values."]
                        ),
                        make_problem(
                            problem_id="gitops-prob-2",
                            title="Multi-Environment Values Hierarchy",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Deploy dev and prod environments using the same Helm chart with overlay values files.",
                            problem_statement="Manage staging and production releases using values-staging.yaml (1 replica, low resources) and values-prod.yaml (5 replicas, high resources).",
                            requirements=[
                                "Create values-staging.yaml and values-prod.yaml overrides.",
                                "Deploy to staging namespace with 'helm upgrade --install -f values-staging.yaml'.",
                                "Verify that staging and production pods receive correct environment variables and replica counts."
                            ],
                            concepts_tested=["Helm Values Hierarchy", "helm upgrade --install", "Multi-Environment Management", "Namespace Isolation"],
                            expected_outcome="Consistent, repeatable multi-environment deployments from a single parameterized chart.",
                            optional_hints=["Use 'helm diff upgrade' plugin to preview manifest changes before applying."]
                        ),
                        make_problem(
                            problem_id="gitops-prob-3",
                            title="ArgoCD GitOps Sync & Self-Healing Pipeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Deploy applications automatically from a Git repository using ArgoCD with automated self-healing.",
                            problem_statement="Deploy an ArgoCD Application custom resource that monitors a GitHub repository, applies changes automatically, and heals manual configuration drift.",
                            requirements=[
                                "Define an ArgoCD Application manifest targeting a git repo and Helm path.",
                                "Configure syncPolicy with automated prune=true and selfHeal=true.",
                                "Commit an image tag update to the git repo and observe ArgoCD detect and apply the change within seconds.",
                                "Manually delete a pod or service with kubectl and observe ArgoCD instantly recreate it (self-healing)."
                            ],
                            concepts_tested=["ArgoCD Application CRD", "GitOps Synchronization", "Self-Healing (Drift Remediation)", "Automated Pruning"],
                            expected_outcome="A completely hands-off deployment loop where git commits are the sole mechanism for cluster changes.",
                            optional_hints=["Self-healing prevents manual 'hotfixes' from lingering in production without git audit trails."]
                        ),
                    ],
                ),
                make_skill(
                    slug="observability-monitoring-devops",
                    name="Observability & Monitoring with Prometheus & Grafana",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Cloud infrastructure telemetry: Prometheus scraping, PromQL queries, Alertmanager notification routing, Grafana visualization dashboards, and node-exporter / kube-state-metrics.",
                    key_topics=["Prometheus Server Architecture & Scraping Targets", "PromQL Syntax (rate, histogram_quantile, sum by)", "Node Exporter & Kube-State-Metrics", "Alertmanager Routing & PagerDuty/Slack Integrations", "Grafana Dashboards & Alert Rules"],
                    role_relevance="Ensures 24/7 visibility into cluster health, prevents cascading failures, and alerts on-call engineers to anomalies.",
                    prerequisites=["kubernetes-devops"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Prometheus Documentation", "url": "https://prometheus.io/docs/introduction/overview/", "description": "Official guides to metrics collection, PromQL, and Alertmanager."},
                        {"type": "YOUTUBE", "title": "Prometheus & Grafana Monitoring Tutorial", "url": "https://www.youtube.com/watch?v=h4Sl21AK9g8", "description": "Complete setup of Prometheus, Node Exporter, and Grafana dashboards for Kubernetes."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="obs-dev-prob-1",
                            title="Node Exporter & Cluster Metric Scraping",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Collect host-level metrics using Prometheus and Node Exporter.",
                            problem_statement="Deploy Prometheus and Node Exporter on a Linux server and author PromQL queries measuring CPU and memory usage.",
                            requirements=[
                                "Configure prometheus.yml scrape_configs targeting node-exporter on port 9100.",
                                "Write a PromQL query calculating CPU usage percentage: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100).",
                                "Write a PromQL query calculating available memory percentage."
                            ],
                            concepts_tested=["Prometheus Scraping", "Node Exporter", "PromQL Syntax", "rate() and avg by()"],
                            expected_outcome="Accurate real-time visibility into server CPU and memory consumption.",
                            optional_hints=["Always calculate rate over a time range at least 4 times the scrape interval."]
                        ),
                        make_problem(
                            problem_id="obs-dev-prob-2",
                            title="SLO-Based Prometheus Alerting Rules",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Configure Alertmanager rules triggering alerts when error budget burn rates exceed thresholds.",
                            problem_statement="Write Prometheus alerting rules that trigger an alert when HTTP 5xx error rates exceed 1% over a 5-minute window.",
                            requirements=[
                                "Create an alert rule 'HighHttpErrorRate' using expr: sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) > 0.01.",
                                "Set 'for: 2m' to prevent alerting on temporary transient spikes.",
                                "Route alerts via Alertmanager to Slack or email with severity annotations."
                            ],
                            concepts_tested=["Alerting Rules", "PromQL Error Ratios", "Alertmanager Routing", "SLO Monitoring"],
                            expected_outcome="Actionable alerts notifying on-call engineers before system outages affect users.",
                            optional_hints=["Use 'for: 2m' to ensure the alert condition persists before firing."]
                        ),
                        make_problem(
                            problem_id="obs-dev-prob-3",
                            title="Enterprise Grafana Kubernetes Cluster Dashboard",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a comprehensive Grafana dashboard visualizing cluster health, pod restarts, and resource saturation.",
                            problem_statement="Construct a production Grafana dashboard displaying cluster CPU/memory usage, pod restart count, and network I/O with template variables.",
                            requirements=[
                                "Configure Prometheus datasource in Grafana.",
                                "Add template variables for $namespace and $pod allowing interactive filtering.",
                                "Create visual panels for pod memory usage vs limits and container restart counts (changes(kube_pod_container_status_restarts_total[1h])).",
                                "Export dashboard as version-controlled JSON for automated provisioning."
                            ],
                            concepts_tested=["Grafana Dashboards", "Template Variables", "Dashboard as Code (JSON)", "Resource Saturation Visualization"],
                            expected_outcome="A single-pane-of-glass dashboard used by SREs to triage cluster incidents within minutes.",
                            optional_hints=["Store Grafana dashboard JSON in git and provision using ConfigMaps."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

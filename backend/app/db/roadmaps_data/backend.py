"""Backend Engineer roadmap definition with progressive practice problems and market demand integration."""
from typing import Any, Dict
from app.db.roadmaps_data.common import CANONICAL_ROLE_IDS, ROADMAP_IDS, make_problem, make_skill

BACKEND_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["backend-engineer"],
    "slug": "backend-engineer",
    "role_id": CANONICAL_ROLE_IDS["backend-engineer"],
    "title": "Backend Engineer",
    "domain": "Backend Engineering",
    "category": "Engineering",
    "description": "Master server-side architectures, REST & asynchronous APIs, relational data modeling, task queues, enterprise security, and high-throughput distributed systems.",
    "version": "v2.0",
    "has_market_data": True,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Foundations",
            "description": "Core computer science fundamentals, shell navigation, version control, and primary programming language proficiency.",
            "skills": [
                make_skill(
                    slug="python",
                    name="Python",
                    canonical_slug="python",
                    difficulty="BEGINNER",
                    description="High-level object-oriented and functional language widely utilized in backend microservices, data manipulation, and automation.",
                    key_topics=["Control Flow & Loops", "Data Structures & Collections", "Object-Oriented Programming & Classes", "Exception Handling & Context Managers", "Virtual Environments & Packaging"],
                    role_relevance="Primary backend scripting and API implementation language across scalable cloud microservices.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Official Python Documentation", "url": "https://docs.python.org/3/", "description": "Comprehensive language reference, tutorials, and standard library guides."},
                        {"type": "YOUTUBE", "title": "Python for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=rfscVS0vtbw", "description": "Full course covering Python core concepts, syntax, and hands-on coding."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="python-prob-1",
                            title="CLI Expense Calculator",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master Python variables, types, loops, conditionals, and functions.",
                            problem_statement="Build a command-line expense calculator that takes user inputs, categorizes expenses, and computes running totals and averages.",
                            requirements=[
                                "Implement functions add_expense(amount: float, category: str), get_total(), and get_average().",
                                "Validate user input using conditionals to reject negative or zero values.",
                                "Loop through inputs and output a formatted summary table."
                            ],
                            concepts_tested=["Variables & Types", "Conditionals", "Loops", "Functions", "Input Validation"],
                            expected_outcome="A functional CLI script calculating exact category totals and averages with graceful error handling.",
                            optional_hints=["Use try-except float(input) to validate numeric entries."]
                        ),
                        make_problem(
                            problem_id="python-prob-2",
                            title="File-Based Log Aggregator with OOP",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Combine object-oriented programming, collections, file handling, and custom exceptions.",
                            problem_statement="Create a log analyzer class that reads structured log files, aggregates error counts by service, and generates a JSON summary report.",
                            requirements=[
                                "Define LogEntry and LogReport classes with encapsulation and type annotations.",
                                "Use open() with context managers to safely stream large log files line by line.",
                                "Use collections.defaultdict and Counter to count occurrences of HTTP status codes and error messages.",
                                "Raise a custom CorruptedLogException when encountering malformed lines."
                            ],
                            concepts_tested=["Classes & OOP", "File I/O & Context Managers", "Collections (Counter, defaultdict)", "Custom Exceptions", "JSON Serialization"],
                            expected_outcome="A reusable LogAnalyzer class producing formatted JSON reports from multi-megabyte log files.",
                            optional_hints=["Use context manager 'with open(...) as f:' to prevent file descriptor leaks."]
                        ),
                        make_problem(
                            problem_id="python-prob-3",
                            title="Thread-Safe In-Memory Cache with TTL",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a production-grade in-memory cache with expiration, thread locking, and eviction policies.",
                            problem_statement="Implement a thread-safe in-memory cache supporting Key-Value storage, Time-To-Live (TTL) expiration, and LRU eviction.",
                            requirements=[
                                "Implement an InMemoryCache class with get, set(key, value, ttl_seconds), and delete methods.",
                                "Use threading.Lock or RLock to ensure thread-safety across concurrent reader and writer threads.",
                                "Implement active or passive expiration cleanup for keys whose TTL has elapsed.",
                                "Implement Least Recently Used (LRU) eviction when the cache hits a maximum capacity threshold."
                            ],
                            concepts_tested=["Concurrency & Threading (Lock)", "TTL Expiration", "LRU Eviction", "Data Structure Design", "Magic Methods (__getitem__, __len__)"],
                            expected_outcome="A high-performance in-memory cache component verified with concurrent multithreaded test cases.",
                            optional_hints=["collections.OrderedDict is well-suited for implementing LRU eviction in Python."]
                        ),
                    ],
                ),
                make_skill(
                    slug="git",
                    name="Git",
                    canonical_slug="git",
                    difficulty="BEGINNER",
                    description="Distributed version control system essential for tracking source history, collaborating on repositories, and managing feature branches.",
                    key_topics=["Branching & Merging", "Rebasing & Cherry-picking", "Resolving Merge Conflicts", "Git Flow & Trunk-Based Development", "Stashing & Worktrees"],
                    role_relevance="Fundamental tool for team collaboration, code reviews, and enterprise software release cycles.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Git SCM Documentation", "url": "https://git-scm.com/doc", "description": "Official Git documentation, reference manuals, and Pro Git book."},
                        {"type": "YOUTUBE", "title": "Git & GitHub Crash Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "description": "Step-by-step walkthrough of Git version control fundamentals and GitHub workflows."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="git-prob-1",
                            title="Repository Initialization & History Tracking",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master staging, committing, and viewing commit history.",
                            problem_statement="Initialize a local Git repository, configure author credentials, stage multiple files, and create clean atomic commits.",
                            requirements=[
                                "Initialize a git repo with 'git init' and configure user.name and user.email.",
                                "Create a .gitignore file ignoring .env and __pycache__/ directories.",
                                "Create two atomic commits and inspect history with 'git log --oneline'."
                            ],
                            concepts_tested=["git init", "git status", "git add & staging", "git commit", ".gitignore"],
                            expected_outcome="A clean local repository with structured commit messages and unversioned secret files ignored.",
                            optional_hints=["Use git status frequently to verify staged changes."]
                        ),
                        make_problem(
                            problem_id="git-prob-2",
                            title="Branching, Merging & Conflict Resolution",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Create feature branches, introduce an intentional conflict, and resolve it cleanly.",
                            problem_statement="Simulate parallel team development across two branches modifying the same line in a configuration file and resolve the conflict.",
                            requirements=[
                                "Create a feature/api-auth branch from main and modify settings.py.",
                                "Switch back to main and commit an alternative modification to the same line in settings.py.",
                                "Merge feature/api-auth into main, inspect the conflict markers, and manually resolve the conflict.",
                                "Complete the merge commit and verify the file content is valid."
                            ],
                            concepts_tested=["git branch", "git checkout/switch", "git merge", "Conflict Markers", "Merge Commits"],
                            expected_outcome="A resolved merge commit integrating both changes cleanly without leftover conflict markers.",
                            optional_hints=["Search for '<<<<<<<', '=======', '>>>>>>>' markers in your editor during resolution."]
                        ),
                        make_problem(
                            problem_id="git-prob-3",
                            title="Interactive Rebase & Cherry-Pick Workflow",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Clean up development history using interactive rebase and cherry-pick hotfixes across branches.",
                            problem_statement="Perform an interactive rebase to squash multiple WIP commits, reword commit messages, and cherry-pick a critical hotfix commit onto a release branch.",
                            requirements=[
                                "Use 'git rebase -i HEAD~4' to squash 3 experimental commits into one cohesive feature commit.",
                                "Reword the squashed commit message to follow Conventional Commits (feat: ...).",
                                "Create a release/v1.0 branch from an older commit and cherry-pick a specific bugfix commit onto it using 'git cherry-pick'."
                            ],
                            concepts_tested=["Interactive Rebase (git rebase -i)", "Squash & Fixup", "Rewording Commits", "git cherry-pick", "Trunk-Based Clean History"],
                            expected_outcome="A linear, clean commit history ready for pull request merge and an isolated cherry-picked release branch.",
                            optional_hints=["If a rebase goes wrong, you can abort safely using 'git rebase --abort'."]
                        ),
                    ],
                ),
                make_skill(
                    slug="linux-fundamentals",
                    name="Linux Fundamentals",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Essential POSIX operating system operations, file permissions, process monitoring, and shell scripting for server management.",
                    key_topics=["File System Hierarchy & Navigation", "Permissions & Ownership (chmod, chown)", "Process Inspection & Control (ps, top, kill, systemctl)", "Pipes, Redirection & Grep / Sed / Awk", "Bash Shell Scripting & Environment Variables"],
                    role_relevance="Backend services deploy onto Linux containers; operational fluency is mandatory for debugging production environments.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Ubuntu Server Documentation", "url": "https://ubuntu.com/server/docs", "description": "Official guides for Linux server administration, packages, and services."},
                        {"type": "YOUTUBE", "title": "Linux for Beginners — NetworkChuck", "url": "https://www.youtube.com/watch?v=ROjZy1WbCIA", "description": "Engaging, practical introduction to Linux terminal navigation and core utilities."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="linux-prob-1",
                            title="Permissions & Process Inspection",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master POSIX file permissions and background process management.",
                            problem_statement="Manage file permissions with chmod/chown and inspect running server processes from the shell.",
                            requirements=[
                                "Create a script with read/write/execute permissions for owner only (chmod 700).",
                                "Launch a background command (sleep 300 &) and retrieve its Process ID (PID) using ps and pgrep.",
                                "Send a SIGTERM and SIGKILL signal to terminate the background process using kill."
                            ],
                            concepts_tested=["File Permissions (chmod/chown)", "Numeric Notation (700/644)", "Process Management (ps, pgrep)", "Kill Signals (SIGTERM, SIGKILL)"],
                            expected_outcome="Fluent control over file security attributes and process lifecycles via the terminal.",
                            optional_hints=["Use 'kill -15 <pid>' for graceful shutdown and 'kill -9 <pid>' for forced kill."]
                        ),
                        make_problem(
                            problem_id="linux-prob-2",
                            title="Log Parsing with Pipes, Grep, and Awk",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Analyze web server access logs using standard Linux stream processing utilities.",
                            problem_statement="Write a shell pipeline that parses an Nginx access log, extracts all 500 error occurrences, and outputs the top 5 requested URLs.",
                            requirements=[
                                "Use grep or egrep to filter lines containing HTTP 500 status codes.",
                                "Use awk to extract the URL path and client IP columns.",
                                "Pipe output through sort and uniq -c, sorting descending to reveal the top 5 failing endpoints."
                            ],
                            concepts_tested=["Pipes (|) and Redirection", "grep / egrep", "awk Column Extraction", "sort and uniq -c", "Stream Processing"],
                            expected_outcome="A one-line shell command that produces a sorted frequency breakdown of failing endpoints.",
                            optional_hints=["awk '{print $7}' typically extracts the request URI in standard combined log format."]
                        ),
                        make_problem(
                            problem_id="linux-prob-3",
                            title="Systemd Service Unit & Automated Health Check Script",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Create an automated bash monitoring script and package it as a Linux systemd background service.",
                            problem_statement="Develop a robust bash script that monitors server disk usage and memory thresholds, and install it as a self-restarting systemd daemon.",
                            requirements=[
                                "Write a bash script with strict mode (set -euo pipefail) that checks df -h and free -m, logging alerts to /var/log/health.log.",
                                "Create a systemd unit file (/etc/systemd/system/app-monitor.service) with Restart=always.",
                                "Reload systemd daemon, enable the service, and verify status via systemctl and journalctl."
                            ],
                            concepts_tested=["Bash Scripting (set -euo pipefail)", "systemd Service Units", "systemctl & journalctl", "Automated Health Monitoring", "Environment Configuration"],
                            expected_outcome="A daemonized systemd service that launches on boot, logs health metrics periodically, and restarts automatically on crash.",
                            optional_hints=["Use 'journalctl -u app-monitor.service -f' to stream daemon logs in real time."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Backend & API Engineering",
            "description": "Building performant, well-structured web APIs, handling authentication, and enforcing data validation schemas.",
            "skills": [
                make_skill(
                    slug="rest-apis",
                    name="REST APIs",
                    canonical_slug="rest-apis",
                    difficulty="BEGINNER",
                    description="Representational State Transfer architectural principles for designing clean, idempotent, and discoverable HTTP endpoints.",
                    key_topics=["HTTP Verbs & Status Codes", "Statelessness & Idempotency", "Pagination & Filtering (Cursor vs Offset)", "API Versioning & Error Schemas", "OpenAPI (Swagger) Specifications"],
                    role_relevance="The universal contract layer connecting client applications to backend server services.",
                    prerequisites=["python"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MDN HTTP & REST Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP", "description": "Comprehensive Mozilla documentation on HTTP methods, headers, and status codes."},
                        {"type": "YOUTUBE", "title": "RESTful APIs in 100 Seconds — Fireship", "url": "https://www.youtube.com/watch?v=-mN3VyJuCjM", "description": "Rapid conceptual overview of REST architecture and endpoint conventions."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="rest-apis-prob-1",
                            title="Resource URI & HTTP Method Modeling",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Design RESTful resource URIs, verbs, and correct HTTP status codes.",
                            problem_statement="Design the endpoint schema for an e-commerce order management system adhering to REST principles.",
                            requirements=[
                                "Map CRUD actions for /orders and /orders/{id}/items to appropriate verbs (GET, POST, PUT, PATCH, DELETE).",
                                "Assign appropriate status codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 404 Not Found, 409 Conflict.",
                                "Specify standard RFC 7807 problem details JSON format for error responses."
                            ],
                            concepts_tested=["REST URIs", "HTTP Methods", "HTTP Status Codes", "Idempotency", "Error Schemas"],
                            expected_outcome="A clean, consistent REST API design document conforming to enterprise REST standards.",
                            optional_hints=["PUT replaces the entire resource; PATCH applies partial modifications."]
                        ),
                        make_problem(
                            problem_id="rest-apis-prob-2",
                            title="Pagination, Filtering & Sorting Spec",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement robust query parameter handling for pagination, search, and sorting.",
                            problem_statement="Build a mock endpoint handler supporting cursor-based and offset-based pagination with sorting and multi-field filtering.",
                            requirements=[
                                "Accept query params: page, limit, sort_by, order (asc/desc), and status filter.",
                                "Return metadata envelope containing total_count, current_page, has_next, and next_cursor.",
                                "Enforce maximum page size limits (e.g. limit <= 100) to prevent denial of service."
                            ],
                            concepts_tested=["Pagination (Cursor vs Offset)", "Query Parameters", "Envelope Responses", "Defensive Limits", "Filtering & Sorting"],
                            expected_outcome="A paginated API response structure that prevents database strain and provides smooth client pagination.",
                            optional_hints=["Cursor-based pagination is immune to the 'page drift' issue that plagues offset pagination."]
                        ),
                        make_problem(
                            problem_id="rest-apis-prob-3",
                            title="Complete OpenAPI 3.0 Specification & Mocking",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Author a production-grade OpenAPI 3.0 specification with reusable components and security schemes.",
                            problem_statement="Write an OpenAPI 3.0 YAML specification for a multi-tenant SaaS billing API with reusable schemas and mock server validation.",
                            requirements=[
                                "Define reusable components in components/schemas with strict validation constraints (min/max, regex pattern).",
                                "Define securitySchemes with Bearer JWT authentication.",
                                "Define response codes for success and error states across all operations.",
                                "Validate the specification with an OpenAPI linter (e.g. Spectral) with zero warnings."
                            ],
                            concepts_tested=["OpenAPI 3.0 (Swagger)", "Reusable Components", "Security Schemes", "Schema Validation Constraints", "API Linting"],
                            expected_outcome="A validated OpenAPI specification that can generate client SDKs and mock servers automatically.",
                            optional_hints=["Use $ref pointers to avoid repeating schema definitions across endpoints."]
                        ),
                    ],
                ),
                make_skill(
                    slug="fastapi",
                    name="FastAPI",
                    canonical_slug="fastapi",
                    difficulty="INTERMEDIATE",
                    description="Modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints and ASGI.",
                    key_topics=["Dependency Injection System (Depends)", "Pydantic Request & Response Models", "Asynchronous Handlers (async/await)", "Automatic OpenAPI & Swagger UI Docs", "Middleware & Exception Handlers"],
                    role_relevance="High-throughput, asynchronous Python API framework widely chosen for cloud microservices and AI inference backends.",
                    prerequisites=["python", "rest-apis"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Official FastAPI Documentation", "url": "https://fastapi.tiangolo.com/", "description": "Interactive documentation with deep tutorials on dependency injection, security, and testing."},
                        {"type": "YOUTUBE", "title": "FastAPI Course for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=tLKKmouU5OI", "description": "Comprehensive hands-on course covering CRUD, routers, schemas, and deployment."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="fastapi-prob-1",
                            title="CRUD Microservice with Pydantic Validation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a FastAPI CRUD application with Pydantic request and response models.",
                            problem_statement="Build an in-memory product management API in FastAPI with full CRUD endpoints and automatic Swagger documentation.",
                            requirements=[
                                "Define ProductCreate and ProductResponse Pydantic models with field validations.",
                                "Implement GET /products, GET /products/{id}, POST /products, and DELETE /products/{id}.",
                                "Return 404 HTTPException when requesting nonexistent product IDs."
                            ],
                            concepts_tested=["FastAPI Endpoints", "Pydantic Models", "HTTPException", "Path Parameters", "Swagger UI"],
                            expected_outcome="A running FastAPI application with interactive documentation at /docs and strict JSON validation.",
                            optional_hints=["Use response_model=ProductResponse to filter out internal attributes."]
                        ),
                        make_problem(
                            problem_id="fastapi-prob-2",
                            title="Dependency Injection & Custom Middleware",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Leverage FastAPI's dependency injection system for database sessions and add performance logging middleware.",
                            problem_statement="Build a FastAPI application that injects database sessions via Depends() and records request execution latency via custom ASGI middleware.",
                            requirements=[
                                "Implement a get_db() generator dependency yielding a session and closing it in a finally block.",
                                "Create a custom middleware calculating process_time and injecting 'X-Process-Time' headers on all responses.",
                                "Inject common pagination parameters into endpoints using a shared Depends(PaginationParams) class."
                            ],
                            concepts_tested=["FastAPI Dependency Injection (Depends)", "Generator Dependencies", "Custom ASGI Middleware", "Header Injection"],
                            expected_outcome="An application demonstrating clean inversion of control for resources and transparent request profiling.",
                            optional_hints=["Use time.perf_counter() in middleware for microsecond timing precision."]
                        ),
                        make_problem(
                            problem_id="fastapi-prob-3",
                            title="Async Background Tasks & Streaming Response Engine",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement asynchronous background task processing and server-sent event (SSE) streaming with FastAPI.",
                            problem_statement="Build an asynchronous document processing service that offloads long-running tasks to BackgroundTasks and streams progress via StreamingResponse.",
                            requirements=[
                                "Use BackgroundTasks to trigger asynchronous email notifications after returning an HTTP 202 Accepted response.",
                                "Implement a Server-Sent Events (SSE) endpoint utilizing StreamingResponse and an async generator yielding progress events.",
                                "Handle client disconnections gracefully in the async generator without leaking resources."
                            ],
                            concepts_tested=["BackgroundTasks", "StreamingResponse", "Async Generators", "Server-Sent Events (SSE)", "Non-blocking Async I/O"],
                            expected_outcome="A high-concurrency API capable of handling long operations asynchronously while keeping HTTP clients updated in real time.",
                            optional_hints=["Set media_type=\"text/event-stream\" for SSE responses."]
                        ),
                    ],
                ),
                make_skill(
                    slug="authentication-authorization",
                    name="Authentication & Authorization (JWT, OAuth2, RBAC)",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Secure backend identity management: Password hashing (Argon2/bcrypt), OAuth2 Password Bearer flow, JWT access & refresh tokens, and Role-Based Access Control (RBAC).",
                    key_topics=["Password Hashing with Passlib / Argon2", "OAuth2 Password Flow & Token Endpoints", "JWT Structure, Signing & Expiration Verification", "Refresh Token Rotation & Invalidation", "Role-Based Access Control (RBAC) & Scopes"],
                    role_relevance="Critical for safeguarding user accounts, enforcing data tenancy, and protecting private backend resources.",
                    prerequisites=["rest-apis", "fastapi"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "FastAPI Security & OAuth2 Documentation", "url": "https://fastapi.tiangolo.com/tutorial/security/", "description": "Step-by-step tutorial on implementing OAuth2 with password hashing and JWT tokens."},
                        {"type": "YOUTUBE", "title": "JWT Authentication in FastAPI — Amigoscode", "url": "https://www.youtube.com/watch?v=6hTRw_HK3Ts", "description": "Hands-on guide to implementing JWT tokens, password hashing, and protecting routes."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="auth-prob-1",
                            title="Password Hashing & User Registration",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement secure password storage using modern cryptographic hashing algorithms.",
                            problem_statement="Build a user registration endpoint that validates password complexity and stores salted, hashed passwords.",
                            requirements=[
                                "Use passlib or bcrypt/argon2 to hash user passwords with random salt.",
                                "Enforce complexity rules: minimum 8 characters, at least one digit and one special character.",
                                "Implement a verify_password(plain, hashed) function returning boolean."
                            ],
                            concepts_tested=["Password Hashing (Argon2 / bcrypt)", "Salt Generation", "Password Complexity", "Secure Storage"],
                            expected_outcome="A user registration service that never stores plain-text passwords in databases or logs.",
                            optional_hints=["Never use MD5 or SHA-256 for password hashing; use bcrypt or Argon2."]
                        ),
                        make_problem(
                            problem_id="auth-prob-2",
                            title="JWT Access & Refresh Token Service",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement JWT generation, decoding, and expiration validation with refresh token exchange.",
                            problem_statement="Build a token service that signs JWTs with HS256/RS256, validates expiry, and exchanges refresh tokens for new access tokens.",
                            requirements=[
                                "Generate short-lived access tokens (15 mins) and long-lived refresh tokens (7 days) using PyJWT.",
                                "Decode and verify JWT signature and 'exp' claim in an auth dependency.",
                                "Implement POST /auth/refresh validating the refresh token and issuing a fresh access token."
                            ],
                            concepts_tested=["JWT (Header, Payload, Signature)", "Token Expiration ('exp')", "OAuth2PasswordBearer", "Refresh Token Rotation"],
                            expected_outcome="A token authentication pipeline with seamless session continuity and instant token expiration enforcement.",
                            optional_hints=["Store the token subject in the 'sub' claim as a string."]
                        ),
                        make_problem(
                            problem_id="auth-prob-3",
                            title="Role-Based Access Control (RBAC) Guard",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement fine-grained Role-Based Access Control (RBAC) with hierarchical permissions and route decorators.",
                            problem_statement="Build a permission enforcement system where users have roles (User, Manager, Admin) with granular permission checks on sensitive endpoints.",
                            requirements=[
                                "Define roles and permissions mapping (e.g. Permission.USER_DELETE, Permission.BILLING_VIEW).",
                                "Implement a reusable dependency factory require_permissions(*perms) that inspects current_user and raises 403 Forbidden.",
                                "Write test cases verifying that regular users receive 403 Forbidden on admin-protected endpoints."
                            ],
                            concepts_tested=["Role-Based Access Control (RBAC)", "Permission Dependencies", "HTTP 403 Forbidden", "Dependency Factories", "Security Auditing"],
                            expected_outcome="A declarative authorization system protecting endpoints with concise annotations.",
                            optional_hints=["Use Python closure or callable class as a dependency factory for require_permissions."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Databases & Persistence",
            "description": "Relational schema design, ACID transactions, query optimization, database migrations, and memory caching layers.",
            "skills": [
                make_skill(
                    slug="sql",
                    name="SQL",
                    canonical_slug="sql",
                    difficulty="BEGINNER",
                    description="Standard declarative query language for relational database management systems and analytical query authoring.",
                    key_topics=["Complex Joins (INNER, LEFT, FULL, CROSS)", "Subqueries & Common Table Expressions (CTEs)", "Aggregate Functions & Group By / Having", "Indexes & EXPLAIN Query Plans", "Transactions & Isolation Levels (ACID)"],
                    role_relevance="Fundamental skill for persisting, retrieving, and aggregating persistent enterprise data.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PostgreSQL SQL Language Tutorial", "url": "https://www.postgresql.org/docs/current/tutorial-sql.html", "description": "Official PostgreSQL documentation covering SQL syntax, joins, and functions."},
                        {"type": "YOUTUBE", "title": "SQL Tutorial — Full Database Course", "url": "https://www.youtube.com/watch?v=HXV3zeQKqGY", "description": "Comprehensive beginner to intermediate course on relational SQL fundamentals."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sql-prob-1",
                            title="Multi-Table Joins & Aggregations",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write multi-table relational joins with grouping and filtering.",
                            problem_statement="Author SQL queries calculating customer order statistics across customers, orders, and order_items tables.",
                            requirements=[
                                "Join customers to orders with LEFT JOIN to include customers with zero orders.",
                                "Calculate total spend per customer with SUM() and COUNT().",
                                "Filter results using HAVING to display only customers who spent over $500."
                            ],
                            concepts_tested=["INNER vs LEFT JOIN", "GROUP BY", "HAVING", "SUM & COUNT", "Aliases"],
                            expected_outcome="Accurate analytical results with proper handling of nulls for zero-order customers.",
                            optional_hints=["Aggregate filters belong in HAVING, not WHERE."]
                        ),
                        make_problem(
                            problem_id="sql-prob-2",
                            title="Common Table Expressions (CTEs) & Window Functions",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Write complex analytical queries using WITH clauses and window functions.",
                            problem_statement="Calculate rolling 30-day average revenue and rank products by sales volume within each category.",
                            requirements=[
                                "Use a Common Table Expression (WITH monthly_sales AS ...) to organize data preparation.",
                                "Use ROW_NUMBER() or DENSE_RANK() OVER (PARTITION BY category_id ORDER BY total_sales DESC) to rank products.",
                                "Compute running totals using SUM(revenue) OVER (ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)."
                            ],
                            concepts_tested=["Common Table Expressions (CTEs)", "Window Functions", "PARTITION BY", "Running Totals", "Ranking Functions"],
                            expected_outcome="Advanced analytical reports generated entirely in database engine with optimal execution speed.",
                            optional_hints=["Window functions calculate values across partitions without collapsing rows like GROUP BY does."]
                        ),
                        make_problem(
                            problem_id="sql-prob-3",
                            title="Query Performance Optimization & Index Tuning",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Diagnose slow queries with EXPLAIN ANALYZE and design composite/partial indexes.",
                            problem_statement="Optimize a slow analytical query performing sequential scans on a table with 500,000 rows to execute in under 10ms.",
                            requirements=[
                                "Analyze query plans using EXPLAIN (ANALYZE, BUFFERS) to detect Sequential Scans and high cost nodes.",
                                "Create a composite index (tenant_id, created_at DESC) to eliminate sort operations.",
                                "Create a partial index for active records (WHERE is_deleted = false) and verify Index Scan adoption."
                            ],
                            concepts_tested=["EXPLAIN ANALYZE", "Sequential Scan vs Index Scan", "Composite Indexes", "Partial Indexes", "Query Cost Metrics"],
                            expected_outcome="A 95%+ reduction in execution time and I/O buffer reads verified through query plan analysis.",
                            optional_hints=["Index column order matters: equality conditions first, followed by range conditions."]
                        ),
                    ],
                ),
                make_skill(
                    slug="postgresql",
                    name="PostgreSQL",
                    canonical_slug="postgresql",
                    difficulty="INTERMEDIATE",
                    description="Enterprise-grade open-source relational database known for reliability, robust feature set, JSONB support, and ACID compliance.",
                    key_topics=["Schema Constraints & Foreign Keys", "JSONB Columns & GIN Indexes", "Full-Text Search (tsvector / tsquery)", "Connection Pooling (PgBouncer)", "Database Transactions & Savepoints"],
                    role_relevance="The gold standard relational database engine for modern cloud microservice architectures.",
                    prerequisites=["sql"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PostgreSQL Official Documentation", "url": "https://www.postgresql.org/docs/current/", "description": "Reference manual for administration, indexing, replication, and performance tuning."},
                        {"type": "YOUTUBE", "title": "PostgreSQL Tutorial for Beginners", "url": "https://www.youtube.com/watch?v=qw--VYLpxG4", "description": "Covers schema creation, indexing, transactions, and real-world backend queries."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="postgres-prob-1",
                            title="Schema Constraints & Referential Integrity",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Define robust database tables with constraints and foreign keys.",
                            problem_statement="Create a normalized database schema enforcing business rules via database-level constraints.",
                            requirements=[
                                "Create users and accounts tables with UUID primary keys (gen_random_uuid()).",
                                "Add CHECK constraints verifying positive balance (balance >= 0) and valid email format.",
                                "Configure Foreign Key with ON DELETE CASCADE and add explicit index on foreign key column."
                            ],
                            concepts_tested=["UUID Primary Keys", "CHECK Constraints", "FOREIGN KEY (ON DELETE CASCADE)", "Index on Foreign Keys"],
                            expected_outcome="A robust database schema that rejects invalid data at the storage layer regardless of application bugs.",
                            optional_hints=["Postgres does not automatically index foreign key columns; create indexes explicitly."]
                        ),
                        make_problem(
                            problem_id="postgres-prob-2",
                            title="JSONB Storage & GIN Indexing",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Store flexible semi-structured document data using Postgres JSONB with GIN indexing.",
                            problem_statement="Model a dynamic user preferences and telemetry payload using JSONB and query nested keys efficiently.",
                            requirements=[
                                "Create an audit_events table with a metadata JSONB column.",
                                "Query records matching nested JSON attributes using the @> containment operator and ->> text extraction operator.",
                                "Create a GIN index on the JSONB column and verify with EXPLAIN that containment queries utilize the index."
                            ],
                            concepts_tested=["JSONB Data Type", "JSON Operators (@>, ->, ->>)", "GIN (Generalized Inverted Index)", "Semi-Structured Querying"],
                            expected_outcome="High-speed querying of nested document structures with relational join capabilities.",
                            optional_hints=["CREATE INDEX ... USING GIN (metadata) enables fast containment queries."]
                        ),
                        make_problem(
                            problem_id="postgres-prob-3",
                            title="Transactional Concurrency & Pessimistic Locking",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Prevent race conditions during concurrent financial balance transfers using SELECT ... FOR UPDATE.",
                            problem_statement="Implement a balance transfer transaction between two accounts that guarantees zero double-spend or overdraft under high concurrency.",
                            requirements=[
                                "Begin a transaction with BEGIN.",
                                "Acquire a pessimistic lock on account rows using SELECT ... FOR UPDATE in deterministic ID order to prevent deadlocks.",
                                "Verify balance, execute debit and credit UPDATEs, and COMMIT or ROLLBACK on insufficient funds.",
                                "Simulate concurrent transfer attempts and verify total money is conserved."
                            ],
                            concepts_tested=["Pessimistic Locking (SELECT FOR UPDATE)", "Deadlock Prevention", "Transaction Isolation Levels", "ACID Guarantees", "Savepoints"],
                            expected_outcome="Zero race conditions or data anomalies even under concurrent simulated load tests.",
                            optional_hints=["Lock accounts in ascending ID order (e.g. min(from_id, to_id) first) to prevent circular deadlocks."]
                        ),
                    ],
                ),
                make_skill(
                    slug="sqlalchemy-migrations",
                    name="Database Migrations & ORM with SQLAlchemy & Alembic",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Enterprise ORM mapping with SQLAlchemy 2.0 (DeclarativeBase, Mapped, mapped_column), async sessions, relationship loading strategies, and Alembic version-controlled migrations.",
                    key_topics=["SQLAlchemy 2.0 Typed Mappings", "Session Lifecycle & AsyncSession", "Relationship Loading (joinedload, selectinload) & N+1 Prevention", "Alembic Migration Autogeneration & Custom DDL", "Database Rollbacks & Zero-Downtime Migrations"],
                    role_relevance="The standard Python bridge between application code and relational databases, ensuring maintainable data access and versioned schema evolutions.",
                    prerequisites=["postgresql", "python"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "SQLAlchemy 2.0 Documentation", "url": "https://docs.sqlalchemy.org/en/20/", "description": "Official documentation for modern 2.0 style ORM, core expressions, and async engines."},
                        {"type": "YOUTUBE", "title": "SQLAlchemy 2.0 & Alembic Crash Course", "url": "https://www.youtube.com/watch?v=woS_A6Oq8i0", "description": "Modern tutorial on SQLAlchemy 2.0 declarative models and Alembic schema migrations."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="orm-prob-1",
                            title="SQLAlchemy 2.0 Typed Model Definitions",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Define relational entities using modern SQLAlchemy 2.0 typed syntax.",
                            problem_statement="Define User and Post models with 1-to-many relationship using DeclarativeBase, Mapped, and mapped_column.",
                            requirements=[
                                "Define User with id (UUID), email (String, unique), and posts (Mapped[List[Post]]).",
                                "Define Post with ForeignKey('users.id') and back_populates='posts'.",
                                "Perform a basic session insert and query using Session.execute(select(User))."
                            ],
                            concepts_tested=["SQLAlchemy 2.0 DeclarativeBase", "Mapped & mapped_column", "relationship(back_populates)", "select() statements"],
                            expected_outcome="Type-safe Python models verified by Pyright / Mypy with clean relational mapping.",
                            optional_hints=["Use 2.0 syntax 'session.scalars(select(User))' rather than legacy 1.x 'session.query()'."]
                        ),
                        make_problem(
                            problem_id="orm-prob-2",
                            title="Alembic Versioned Migration Pipeline",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Manage database schema evolution using Alembic revisions.",
                            problem_statement="Initialize Alembic, generate an auto-migration from SQLAlchemy models, apply it to Postgres, and execute a downgrade rollback.",
                            requirements=[
                                "Configure alembic.ini and env.py targeting the SQLAlchemy Base.metadata.",
                                "Generate a revision with 'alembic revision --autogenerate -m \"create users and posts\"'.",
                                "Apply the migration with 'alembic upgrade head' and verify rollback with 'alembic downgrade -1'."
                            ],
                            concepts_tested=["Alembic init & env.py", "Autogenerate Revisions", "alembic upgrade", "alembic downgrade", "Schema Versioning"],
                            expected_outcome="Repeatable, version-controlled migrations tracking database schema state across team environments.",
                            optional_hints=["Always inspect generated migration files before executing upgrade head."]
                        ),
                        make_problem(
                            problem_id="orm-prob-3",
                            title="N+1 Query Elimination with Eager Loading",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Detect and eliminate N+1 query bottlenecks using joinedload and selectinload.",
                            problem_statement="Profile an endpoint loading 100 users and their posts, detect the 101-query N+1 issue, and optimize it to execute in 2 queries.",
                            requirements=[
                                "Simulate the N+1 problem by accessing user.posts in a loop with lazy loading.",
                                "Refactor the query using 'select(User).options(selectinload(User.posts))'.",
                                "Enable SQLAlchemy echo=True to verify only 2 SQL queries execute instead of 101."
                            ],
                            concepts_tested=["N+1 Query Problem", "selectinload vs joinedload", "Lazy Loading Pitfalls", "Query Profiling", "SQLAlchemy Options"],
                            expected_outcome="Dramatic reduction in database roundtrips and latency when serializing relational hierarchies.",
                            optional_hints=["Use selectinload for 1-to-many collections and joinedload for many-to-1 foreign keys."]
                        ),
                    ],
                ),
                make_skill(
                    slug="redis",
                    name="Redis",
                    canonical_slug="redis",
                    difficulty="INTERMEDIATE",
                    description="In-memory key-value data structure store used as a distributed cache, message broker, and rate limiter.",
                    key_topics=["Caching Strategies (Cache-Aside, Write-Through)", "Data Structures (Strings, Hashes, Lists, Sets, Sorted Sets)", "Key Expiration & Eviction Policies (LRU/LFU)", "Pub/Sub Messaging & Streams", "Distributed Locking (Redlock)"],
                    role_relevance="Crucial for reducing database load, session management, and microsecond data lookups.",
                    prerequisites=["sql"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Redis Official Documentation", "url": "https://redis.io/docs/", "description": "Official documentation covering commands, clustering, persistence, and caching architectures."},
                        {"type": "YOUTUBE", "title": "Redis Crash Course — Traversy Media", "url": "https://www.youtube.com/watch?v=jgpVdJB2sKQ", "description": "Hands-on guide to Redis commands, Node/Python integration, and caching."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="redis-prob-1",
                            title="Cache-Aside Repository Wrapper",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement the standard Cache-Aside pattern with key expiration.",
                            problem_statement="Build a caching decorator or wrapper that checks Redis before querying the database, populating Redis on cache misses.",
                            requirements=[
                                "Check Redis for key 'item:{id}' using redis.get().",
                                "On cache miss, fetch item from database, serialize to JSON, and store in Redis with 60-second TTL (setex).",
                                "On cache hit, deserialize JSON and return without querying the database."
                            ],
                            concepts_tested=["Cache-Aside Pattern", "redis.get / redis.setex", "Key Expiration (TTL)", "JSON Serialization for Cache"],
                            expected_outcome="Microsecond response times on cached reads with automatic invalidation after TTL expires.",
                            optional_hints=["Use a consistent key naming convention like 'service:entity:id'."]
                        ),
                        make_problem(
                            problem_id="redis-prob-2",
                            title="Sliding Window Rate Limiter with Sorted Sets",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an accurate sliding-window rate limiter using Redis Sorted Sets (ZSET).",
                            problem_statement="Build an API rate limiter that allows a maximum of 10 requests per minute per IP using Redis Sorted Sets.",
                            requirements=[
                                "Use a Redis Sorted Set with current Unix timestamp as both score and member.",
                                "Remove timestamps older than (now - 60 seconds) with zremrangebyscore.",
                                "Count remaining requests with zcard; reject request with 429 if count >= 10, otherwise add current timestamp with zadd."
                            ],
                            concepts_tested=["Sorted Sets (ZSET)", "zremrangebyscore & zcard", "Sliding Window Rate Limiting", "HTTP 429 Too Many Requests"],
                            expected_outcome="A precision rate limiter that prevents burst exploits at boundary edges of fixed windows.",
                            optional_hints=["Wrap the Redis commands in a pipeline or transaction for atomicity."]
                        ),
                        make_problem(
                            problem_id="redis-prob-3",
                            title="Distributed Lock with Auto-Release",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement a safe distributed lock in Redis to coordinate tasks across multiple microservice replicas.",
                            problem_statement="Build a DistributedLock context manager in Python that prevents race conditions across competing worker processes.",
                            requirements=[
                                "Acquire lock using 'SET lock:resource random_token NX PX 5000' (atomic set with expiration).",
                                "Release lock using a Lua script that verifies the token matches before deleting to prevent unlocking someone else's expired lock.",
                                "Handle lock acquisition failures with retries and exponential jitter."
                            ],
                            concepts_tested=["Atomic SET NX PX", "Lua Scripting in Redis", "Distributed Locking (Redlock)", "Race Condition Elimination", "Context Managers"],
                            expected_outcome="Safe coordination of critical sections across multiple container replicas without deadlocks.",
                            optional_hints=["Never delete a distributed lock with a simple DEL; always check token ownership in a Lua script."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Asynchronous Queues & Microservices",
            "description": "Decouple long-running operations, manage message brokers, and protect distributed services against vulnerabilities.",
            "skills": [
                make_skill(
                    slug="celery-task-queues",
                    name="Asynchronous Task Queues with Celery & Redis",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Offloading background workloads: Celery workers, Redis/RabbitMQ brokers, periodic tasks with Celery Beat, task retries with backoff, and task result backends.",
                    key_topics=["Celery Worker Architecture & Broker Configuration", "Defining & Invoking Tasks (.delay, .apply_async)", "Retries with Exponential Backoff", "Periodic Cron Scheduling with Celery Beat", "Task Canvas (Signatures, Chains, Chords)"],
                    role_relevance="Essential for offloading slow operations (emails, PDF generation, AI inference) from HTTP request loops, maintaining low API response times.",
                    prerequisites=["python", "redis"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Celery Project Documentation", "url": "https://docs.celeryq.dev/", "description": "Official documentation for distributed task queues in Python."},
                        {"type": "YOUTUBE", "title": "Celery & Redis Crash Course — Very Academy", "url": "https://www.youtube.com/watch?v=THxCyGUSMCU", "description": "Hands-on tutorial connecting Python backends to Celery workers via Redis."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="celery-prob-1",
                            title="Background Email Worker",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Offload an asynchronous task from an API endpoint to a Celery worker.",
                            problem_statement="Create a Celery task that simulates sending a welcome email, invoking it asynchronously from an endpoint.",
                            requirements=[
                                "Configure Celery app with Redis broker URL.",
                                "Define @celery.task send_welcome_email(user_email: str).",
                                "Call send_welcome_email.delay(email) in an API handler and return an immediate 200 OK."
                            ],
                            concepts_tested=["Celery Setup", "@celery.task", ".delay() async invocation", "Redis Broker"],
                            expected_outcome="Immediate sub-50ms API response while the email job executes in the background worker.",
                            optional_hints=["Run 'celery -A tasks worker --loglevel=info' in a separate shell."]
                        ),
                        make_problem(
                            problem_id="celery-prob-2",
                            title="Resilient Task with Exponential Backoff Retry",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Configure automated task retries with exponential backoff on third-party service failures.",
                            problem_statement="Build a payment webhook task that automatically retries up to 5 times when the remote payment gateway returns an error.",
                            requirements=[
                                "Configure autoretry_for=(NetworkException,), retry_kwargs={'max_retries': 5}, and retry_backoff=True.",
                                "Incorporate exponential jitter to prevent thundering herd problems on the downstream service.",
                                "Log failure alerts when max retries are exhausted."
                            ],
                            concepts_tested=["Celery Retries", "retry_backoff", "Exponential Jitter", "Max Retries Handling", "Dead Letter Queues"],
                            expected_outcome="A resilient worker task that recovers gracefully from transient network glitches.",
                            optional_hints=["Set retry_backoff_max to cap the maximum wait time between retries."]
                        ),
                        make_problem(
                            problem_id="celery-prob-3",
                            title="Complex Workflow with Celery Chains & Chords",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Coordinate parallel and sequential task workflows using Celery Canvas primitives.",
                            problem_statement="Build an image processing pipeline: download image -> execute parallel filters (resize, grayscale, thumbnail) -> aggregate and notify user.",
                            requirements=[
                                "Use celery.chain to run download followed by processing.",
                                "Use celery.chord to execute 3 image transformations in parallel and invoke a final callback task with all results.",
                                "Verify that if any parallel task fails, the callback handles partial results cleanly."
                            ],
                            concepts_tested=["Celery Canvas", "chain", "chord (group + callback)", "Parallel Processing", "Result Backends"],
                            expected_outcome="A multi-step distributed pipeline executing parallel workloads efficiently across available workers.",
                            optional_hints=["Chord requires a result backend (e.g. Redis or PostgreSQL) to synchronize task completion."]
                        ),
                    ],
                ),
                make_skill(
                    slug="api-security-owasp",
                    name="API Security & OWASP Top 10",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Defending backend APIs against common exploits: Injection, Broken Object Level Authorization (BOLA), Rate Limiting, CORS, CSRF, and Secure Header configuration.",
                    key_topics=["OWASP API Security Top 10", "Broken Object Level Authorization (BOLA/IDOR) Mitigation", "SQL & Command Injection Prevention", "CORS Configuration & CSRF Protection", "Security Headers (HSTS, CSP, X-Content-Type-Options)"],
                    role_relevance="Mandatory for preventing data breaches, unauthorized cross-tenant data access, and server compromise.",
                    prerequisites=["rest-apis", "authentication-authorization"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "OWASP API Security Project", "url": "https://owasp.org/www-project-api-security/", "description": "Official OWASP API security top 10 vulnerabilities and mitigation guidance."},
                        {"type": "YOUTUBE", "title": "OWASP Top 10 API Security Risks Explained", "url": "https://www.youtube.com/watch?v=7U5eXG9j_f8", "description": "Clear breakdown of BOLA, broken authentication, and excessive data exposure in APIs."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="owasp-prob-1",
                            title="BOLA / IDOR Vulnerability Remediation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Detect and patch Broken Object Level Authorization (IDOR) vulnerabilities.",
                            problem_statement="Audit an endpoint GET /invoices/{id} that allows any authenticated user to view other customers' invoices, and enforce strict ownership verification.",
                            requirements=[
                                "Inspect invoice query to verify invoice.customer_id == current_user.id.",
                                "Return 404 Not Found (or 403 Forbidden) when user attempts to access another user's invoice.",
                                "Write automated tests simulating User A attempting to fetch User B's resource."
                            ],
                            concepts_tested=["Broken Object Level Authorization (BOLA)", "Insecure Direct Object References (IDOR)", "Tenant Isolation", "Security Testing"],
                            expected_outcome="A secure endpoint that strictly prevents unauthorized data access across tenants.",
                            optional_hints=["Returning 404 instead of 403 prevents attackers from enumerating valid IDs."]
                        ),
                        make_problem(
                            problem_id="owasp-prob-2",
                            title="CORS & Security Headers Middleware",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Configure Cross-Origin Resource Sharing (CORS) securely and inject standard security headers.",
                            problem_statement="Configure CORS middleware to allow only trusted origin domains and inject standard hardening HTTP headers.",
                            requirements=[
                                "Configure CORSMiddleware with explicit allow_origins (never allow_origins=[\"*\"] with allow_credentials=True).",
                                "Add security headers: Content-Security-Policy, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Strict-Transport-Security.",
                                "Verify preflight OPTIONS requests return correct Access-Control-Allow-* headers."
                            ],
                            concepts_tested=["CORS (Cross-Origin Resource Sharing)", "Preflight OPTIONS", "Security Headers", "Clickjacking Prevention (X-Frame-Options)"],
                            expected_outcome="A hardened API that rejects requests from unauthorized browser origins and prevents framing/MIME-sniffing.",
                            optional_hints=["Wildcard origins with credentials allowed is rejected by modern browsers."]
                        ),
                        make_problem(
                            problem_id="owasp-prob-3",
                            title="Automated SAST & Secret Scanning Pipeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Integrate automated Static Application Security Testing (SAST) and secret detection into a backend codebase.",
                            problem_statement="Configure Bandit security linter and TruffleHog/Gitleaks secret scanner to detect vulnerabilities and hardcoded credentials in pull requests.",
                            requirements=[
                                "Run Bandit across Python code to identify insecure eval(), raw SQL formatting, or weak cryptography.",
                                "Configure a pre-commit or CI check running Gitleaks to block commits containing API keys or private certificates.",
                                "Remediate detected warnings to achieve a completely green security audit report."
                            ],
                            concepts_tested=["Static Application Security Testing (SAST)", "Bandit Linter", "Secret Scanning (Gitleaks)", "Secure Coding Standards"],
                            expected_outcome="An automated security gate preventing dangerous code patterns and leaked secrets from reaching production.",
                            optional_hints=["Use 'bandit -r app/ -ll' to scan for medium and high severity security risks."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 5,
            "name": "Stage 5 — Testing & Quality Assurance",
            "description": "Unit testing, integration testing, fixture architecture, and test coverage enforcement.",
            "skills": [
                make_skill(
                    slug="pytest",
                    name="Pytest",
                    canonical_slug="pytest",
                    difficulty="INTERMEDIATE",
                    description="Mature Python testing framework supporting unit, integration, fixture-driven, and parameterized test execution.",
                    key_topics=["Fixtures & Scope (function, module, session)", "Parameterized Testing (@pytest.mark.parametrize)", "Mocking External APIs (unittest.mock, pytest-mock)", "Test Database Isolation (Rollbacks / In-Memory)", "Code Coverage Analysis (pytest-cov)"],
                    role_relevance="Ensures backend regressions are caught before deployment and enforces deterministic API contracts.",
                    prerequisites=["python", "fastapi"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Official Pytest Documentation", "url": "https://docs.pytest.org/", "description": "Complete guides on test discovery, fixture patterns, and configuration."},
                        {"type": "YOUTUBE", "title": "Python Testing with Pytest — Corey Schafer", "url": "https://www.youtube.com/watch?v=byaxg00Gf9I", "description": "In-depth guide to writing unit tests, mocking, and fixtures in Python."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="pytest-prob-1",
                            title="Parameterized Business Logic Tests",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write compact, multi-scenario tests using Pytest parameterization.",
                            problem_statement="Test a discount calculation engine across 10 distinct coupon codes, expiration dates, and cart value scenarios using a single test function.",
                            requirements=[
                                "Use @pytest.mark.parametrize to supply input tuples and expected outputs.",
                                "Test boundary conditions: 0% discount, 100% discount, expired coupons, and negative totals.",
                                "Assert exact floating-point equality using pytest.approx()."
                            ],
                            concepts_tested=["@pytest.mark.parametrize", "Boundary Testing", "pytest.approx", "Assertions"],
                            expected_outcome="Clean test execution verifying all 10 scenarios in parallel with clear failure messages.",
                            optional_hints=["Use pytest.approx(val, abs=1e-2) for monetary calculations."]
                        ),
                        make_problem(
                            problem_id="pytest-prob-2",
                            title="Database Fixtures with Transaction Rollbacks",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement isolated database test fixtures that roll back changes after each test without slow re-creation.",
                            problem_statement="Build a Pytest fixture db_session that begins a nested transaction before each test and rolls back in a teardown generator block.",
                            requirements=[
                                "Create a @pytest.fixture(scope=\"function\") db_session yielding a SQLAlchemy session.",
                                "Wrap test execution inside a transaction and call transaction.rollback() in fixture teardown.",
                                "Verify that records inserted in Test A do not exist when Test B runs."
                            ],
                            concepts_tested=["Pytest Fixture Yield & Teardown", "Database Isolation", "Transaction Rollback", "Test Cleanliness"],
                            expected_outcome="100% isolated test runs with rapid execution speed without leaving orphan rows in the test database.",
                            optional_hints=["Use connection.begin_nested() for savepoint-based transaction rollbacks."]
                        ),
                        make_problem(
                            problem_id="pytest-prob-3",
                            title="End-to-End API Integration Suite with Mocked Payment Gateway",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Test complete HTTP flows with FastAPI TestClient and mock third-party HTTP responses using respx or monkeypatch.",
                            problem_statement="Build an integration test verifying the entire checkout flow (POST /cart/checkout), mocking external Stripe API calls and verifying database records.",
                            requirements=[
                                "Use fastapi.testclient.TestClient to issue real HTTP requests against the FastAPI app.",
                                "Mock external payment API using unittest.mock.patch or respx.",
                                "Assert status code 200, verify database order record was created, and check that email background task was enqueued.",
                                "Measure and assert 90%+ code coverage using pytest-cov."
                            ],
                            concepts_tested=["FastAPI TestClient", "Mocking External APIs", "Integration Testing", "Code Coverage (pytest-cov)", "State Verification"],
                            expected_outcome="A comprehensive integration test suite validating end-to-end user workflows with high coverage.",
                            optional_hints=["Use 'pytest --cov=app --cov-report=term-missing' to inspect uncovered lines."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 6,
            "name": "Stage 6 — Containerization, Architecture & Cloud",
            "description": "Containerize microservices, orchestrate CI/CD pipelines, monitor observability metrics, and scale distributed architectures.",
            "skills": [
                make_skill(
                    slug="docker",
                    name="Docker",
                    canonical_slug="docker",
                    difficulty="INTERMEDIATE",
                    description="Container virtualization platform enabling reproducible packaging and execution of applications across environments.",
                    key_topics=["Multi-stage Dockerfiles", "Image Optimization & Layer Caching", "Container Networking & Volumes", "Docker Compose Orchestration", "Non-root Users & Container Security"],
                    role_relevance="Standard runtime unit for deploying microservices, CI testing, and cloud server workloads.",
                    prerequisites=["linux-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Official Docker Documentation", "url": "https://docs.docker.com/", "description": "Comprehensive guide for Docker engine, multi-stage builds, and CLI commands."},
                        {"type": "YOUTUBE", "title": "Docker Tutorial for Beginners — TechWorld with Nana", "url": "https://www.youtube.com/watch?v=3c-iBn73dDE", "description": "Complete beginner walkthrough of container concepts, images, and networking."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="docker-prob-1",
                            title="Containerize a Simple Python Web App",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write a Dockerfile and run a containerized web application.",
                            problem_statement="Write a Dockerfile for a FastAPI application, build the image, and run it with port mapping to access it locally.",
                            requirements=[
                                "Use an official python:3.11-slim base image.",
                                "Copy requirements.txt, install dependencies, and copy source code.",
                                "Expose port 8000 and configure CMD with uvicorn.",
                                "Run the container with docker run -p 8000:8000."
                            ],
                            concepts_tested=["Dockerfile Instructions (FROM, COPY, RUN, CMD)", "docker build", "docker run -p", "Port Mapping"],
                            expected_outcome="A running container serving HTTP requests on localhost:8000.",
                            optional_hints=["Order Dockerfile instructions from least frequently changed to most frequently changed to maximize layer caching."]
                        ),
                        make_problem(
                            problem_id="docker-prob-2",
                            title="Multi-Container App with Docker Compose",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Orchestrate multiple dependent containers using Docker Compose.",
                            problem_statement="Create a docker-compose.yml file managing FastAPI, PostgreSQL, and Redis containers on a shared network.",
                            requirements=[
                                "Define web, db, and redis services on a custom bridge network.",
                                "Configure persistent named volumes for postgres data.",
                                "Use depends_on with condition: service_healthy so the web app waits for PostgreSQL to be ready before starting."
                            ],
                            concepts_tested=["Docker Compose", "Named Volumes", "Container Networking", "Health Checks (service_healthy)", "Environment Files (.env)"],
                            expected_outcome="A single 'docker compose up' command launches the full application stack with persistent database storage.",
                            optional_hints=["Use pg_isready in the postgres health check definition."]
                        ),
                        make_problem(
                            problem_id="docker-prob-3",
                            title="Production-Hardened Multi-Stage Dockerfile",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a minimal, secure production Docker image with multi-stage builds and a non-root user.",
                            problem_statement="Refactor an application Dockerfile to use multi-stage builds, compile wheels in a builder stage, and run as a non-root user in the final stage.",
                            requirements=[
                                "Stage 1 (builder): Install build-essential, compile dependencies into wheels in /install.",
                                "Stage 2 (runner): Copy only wheels and install without compilers, reducing image size by 70%+.",
                                "Create and switch to a non-privileged system user (appuser) with USER appuser.",
                                "Add a HEALTHCHECK instruction and verify container vulnerability scan with docker scout or trivy."
                            ],
                            concepts_tested=["Multi-stage Builds", "Image Size Optimization", "Non-root Container Security", "HEALTHCHECK Directive", "Vulnerability Scanning"],
                            expected_outcome="A lightweight, hardened production container image free of unnecessary build tools and root privileges.",
                            optional_hints=["Never run production containers as root."]
                        ),
                    ],
                ),
                make_skill(
                    slug="system-design-fundamentals",
                    name="System Design Fundamentals",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Core principles for building high-availability, fault-tolerant distributed web systems.",
                    key_topics=["CAP Theorem & PACELC Trade-offs", "Horizontal Scaling & Load Balancing Algorithms", "Database Sharding, Partitioning & Replication", "Consistent Hashing & Distributed Caching", "Message Brokers & Asynchronous Decoupling"],
                    role_relevance="Differentiates senior backend engineers by enabling them to design systems capable of handling millions of concurrent requests.",
                    prerequisites=["rest-apis", "postgresql", "redis"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "System Design Primer by Donne Martin", "url": "https://github.com/donnemartin/system-design-primer", "description": "Industry-standard open-source guide to distributed systems and architectural patterns."},
                        {"type": "YOUTUBE", "title": "System Design for Beginners Course", "url": "https://www.youtube.com/watch?v=m8Icp_Cid5o", "description": "Clear breakdown of load balancers, CDN, caching, replication, and database sharding."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sysdesign-prob-1",
                            title="Capacity Estimation & Back-of-the-Envelope Math",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Perform back-of-the-envelope calculations for traffic, storage, and bandwidth.",
                            problem_statement="Estimate throughput (QPS), memory cache sizing, and 5-year storage requirements for a URL shortening service.",
                            requirements=[
                                "Calculate Read QPS and Write QPS assuming 100M daily active users creating 10M new links daily (10:1 read-to-write ratio).",
                                "Estimate 5-year storage capacity needed for short link mappings.",
                                "Calculate memory needed to cache 20% of the daily read traffic following the 80/20 Pareto principle."
                            ],
                            concepts_tested=["QPS Calculations", "Bandwidth Estimation", "Storage Sizing", "Pareto 80/20 Caching Math"],
                            expected_outcome="A quantitative capacity blueprint providing defensible hardware and memory specifications.",
                            optional_hints=["10 million requests per day = ~115 requests per second."]
                        ),
                        make_problem(
                            problem_id="sysdesign-prob-2",
                            title="High-Concurrency URL Shortener Architecture",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Design an end-to-end distributed system with caching and unique key generation.",
                            problem_statement="Draft an architecture design document for a distributed URL shortener generating unique 7-character base62 hashes under 10k writes/sec.",
                            requirements=[
                                "Design a unique ID generation strategy (Base62 encoding of counter vs pre-generated key range service / Snowflake).",
                                "Architect multi-tier caching with Redis and CDN edge caching.",
                                "Specify database schema and horizontal sharding key strategy."
                            ],
                            concepts_tested=["Base62 Encoding", "ID Generation Services", "CDN & Redis Caching", "Database Sharding", "Fault Tolerance"],
                            expected_outcome="An architectural diagram and RFC detailing component interactions, failure modes, and latency targets.",
                            optional_hints=["A standalone Key Generation Service (KGS) avoids hash collisions under high write concurrency."]
                        ),
                        make_problem(
                            problem_id="sysdesign-prob-3",
                            title="Fault-Tolerant Distributed Notification Service",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Design a multi-channel notification engine (Push, SMS, Email) handling 100M daily messages with rate limiting and deduplication.",
                            problem_statement="Design a notification platform that ingests events from multiple internal services, prevents duplicate messages, and handles downstream provider rate limits.",
                            requirements=[
                                "Use message queues (Kafka / RabbitMQ) for decoupled ingestion and prioritization (Transactional vs Marketing).",
                                "Implement idempotency keys in Redis to guarantee at-most-once delivery across duplicate client retries.",
                                "Incorporate circuit breakers and fallback providers when third-party gateways (Twilio/SendGrid) experience outages."
                            ],
                            concepts_tested=["Message Queues", "Idempotency Keys", "Circuit Breakers (Resilience4j / Tenacity)", "Priority Queues", "Graceful Degradation"],
                            expected_outcome="A resilient architectural design capable of absorbing traffic spikes and guaranteeing delivery SLAs.",
                            optional_hints=["Partition Kafka topics by user_id to maintain in-order delivery per user."]
                        ),
                    ],
                ),
                make_skill(
                    slug="aws",
                    name="AWS",
                    canonical_slug="aws",
                    difficulty="INTERMEDIATE",
                    description="Cloud infrastructure services: EC2 instances, S3 object storage, RDS managed databases, IAM security policies, and serverless compute with AWS Lambda.",
                    key_topics=["IAM Users, Roles & Least Privilege Policies", "S3 Bucket Storage & Pre-signed URLs", "RDS PostgreSQL Configuration & Backups", "EC2 & Security Group Networking", "CloudWatch Metrics & Alarms"],
                    role_relevance="The dominant public cloud platform hosting enterprise backend microservices globally.",
                    prerequisites=["docker", "linux-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "AWS Official Documentation", "url": "https://docs.aws.amazon.com/", "description": "Official guides, architecture centers, and CLI reference for all AWS cloud services."},
                        {"type": "YOUTUBE", "title": "AWS Certified Cloud Practitioner Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=SOTamWNgDKc", "description": "Complete breakdown of AWS core services, security, architecture, and billing."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="aws-prob-1",
                            title="Secure S3 Uploads with Pre-Signed URLs",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Enable secure direct client uploads to Amazon S3 without exposing AWS credentials.",
                            problem_statement="Build a backend endpoint that generates time-limited S3 pre-signed URLs allowing frontend clients to upload files directly to S3.",
                            requirements=[
                                "Initialize boto3 S3 client reading credentials from environment variables.",
                                "Implement generate_presigned_url('put_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=300).",
                                "Verify client can successfully upload files directly to S3 within the 5-minute expiry window."
                            ],
                            concepts_tested=["Amazon S3", "Boto3 SDK", "Pre-signed URLs", "IAM Least Privilege", "Direct-to-Cloud Uploads"],
                            expected_outcome="Safe file uploads bypassing backend server memory and CPU bottlenecks.",
                            optional_hints=["Configure S3 bucket CORS rules to permit PUT requests from your frontend origin."]
                        ),
                        make_problem(
                            problem_id="aws-prob-2",
                            title="IAM Role & Policy Least Privilege Auditing",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Author fine-grained IAM policies restricting permissions to specific ARNs and resources.",
                            problem_statement="Create an IAM policy for an application EC2 instance that grants read-only access to a specific S3 bucket and write access to a CloudWatch log group.",
                            requirements=[
                                "Author a JSON IAM policy document using Action, Effect, and Resource statements.",
                                "Restrict S3 actions to 's3:GetObject' on 'arn:aws:s3:::my-app-bucket/*'.",
                                "Ensure wildcard ('*') actions are eliminated to enforce strict least privilege."
                            ],
                            concepts_tested=["IAM Policies & Roles", "Least Privilege Principle", "ARN Formatting", "CloudWatch Logs Policy"],
                            expected_outcome="A tight security posture ensuring compromised servers cannot access unrelated cloud resources.",
                            optional_hints=["Use AWS Policy Simulator to validate permissions without manual deployment."]
                        ),
                        make_problem(
                            problem_id="aws-prob-3",
                            title="Serverless Document Processor with Lambda & S3 Triggers",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build an event-driven serverless workflow using S3 bucket events and AWS Lambda.",
                            problem_statement="Deploy a Lambda function triggered automatically when an image is uploaded to an S3 bucket, generating a thumbnail and saving to a destination bucket.",
                            requirements=[
                                "Configure an S3 ObjectCreated event notification targeting a Python Lambda function.",
                                "Process the image in Lambda using Pillow, creating a 200x200 thumbnail.",
                                "Upload the thumbnail to a destination bucket and write completion metrics to CloudWatch."
                            ],
                            concepts_tested=["AWS Lambda", "S3 Event Triggers", "Serverless Architecture", "CloudWatch Metrics", "Event-Driven Processing"],
                            expected_outcome="An auto-scaling, serverless image processing pipeline executing without persistent EC2 compute costs.",
                            optional_hints=["Ensure the destination bucket is different from the source bucket to avoid infinite trigger loops."]
                        ),
                    ],
                ),
                make_skill(
                    slug="backend-observability",
                    name="Backend Observability & Monitoring (Prometheus, Grafana, OpenTelemetry)",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Three pillars of observability: Structured JSON logging, Prometheus application metrics (RED method), Grafana visualization dashboards, and OpenTelemetry distributed tracing.",
                    key_topics=["Three Pillars: Metrics, Logs, Traces", "Structured Logging with Context (correlation IDs)", "Prometheus Metrics (Counter, Gauge, Histogram)", "RED Method (Rate, Errors, Duration)", "OpenTelemetry Distributed Tracing across Microservices"],
                    role_relevance="Essential for identifying performance degradation, triaging production outages, and ensuring high system reliability.",
                    prerequisites=["fastapi", "docker"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Prometheus Official Documentation", "url": "https://prometheus.io/docs/introduction/overview/", "description": "Official guides to metrics collection, PromQL query language, and alerting."},
                        {"type": "YOUTUBE", "title": "Prometheus & Grafana Monitoring — TechWorld with Nana", "url": "https://www.youtube.com/watch?v=h4Sl21AK9g8", "description": "Full course on instrumenting applications, collecting metrics, and building Grafana dashboards."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="obs-prob-1",
                            title="Structured JSON Logging with Correlation IDs",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement structured JSON logging with unique trace IDs attached to all request logs.",
                            problem_statement="Configure a custom logging formatter that outputs machine-readable JSON logs containing timestamp, log level, request path, and an X-Correlation-ID.",
                            requirements=[
                                "Format log output as JSON using python-json-logger or structlog.",
                                "Extract or generate an X-Correlation-ID header in middleware and attach it to the logging context.",
                                "Verify that all log statements emitted during a single request share the exact same correlation ID."
                            ],
                            concepts_tested=["Structured Logging (JSON)", "Correlation IDs", "Log Context Propagation", "Middleware Injection"],
                            expected_outcome="Logs that can be indexed and searched by correlation ID in Datadog, ELK, or Loki to trace single requests.",
                            optional_hints=["Use contextvars to store correlation IDs in async Python safely."]
                        ),
                        make_problem(
                            problem_id="obs-prob-2",
                            title="Prometheus Metrics Instrumentation (RED Method)",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Instrument a web service with Prometheus metrics capturing Rate, Errors, and Duration.",
                            problem_statement="Add Prometheus metrics to a FastAPI app using prometheus-client and expose a /metrics endpoint.",
                            requirements=[
                                "Define a Counter for total requests labeled by method, path, and status code.",
                                "Define a Histogram with latency buckets measuring request duration.",
                                "Expose the metrics on /metrics for Prometheus scraping and write PromQL queries calculating error rate."
                            ],
                            concepts_tested=["Prometheus Metrics (Counter, Histogram)", "RED Method", "PromQL Queries", "/metrics Endpoint"],
                            expected_outcome="Actionable metrics showing 95th percentile latency and error rate percentages in real time.",
                            optional_hints=["Use prometheus-fastapi-instrumentator for automated route instrumentation."]
                        ),
                        make_problem(
                            problem_id="obs-prob-3",
                            title="Distributed Tracing with OpenTelemetry & Jaeger",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement distributed tracing across multiple microservices using OpenTelemetry and visualize in Jaeger.",
                            problem_statement="Instrument two communicating microservices with OpenTelemetry SDK to trace HTTP calls across service boundaries.",
                            requirements=[
                                "Configure OpenTelemetry TracerProvider and export traces via OTLP to a local Jaeger container.",
                                "Automatically instrument FastAPI and HTTP client calls (httpx/requests).",
                                "Verify that a request spanning Service A and Service B appears as a single unified trace in the Jaeger UI."
                            ],
                            concepts_tested=["OpenTelemetry (OTel)", "Distributed Tracing", "Trace Context Propagation", "Jaeger UI", "Span Creation"],
                            expected_outcome="End-to-end trace graphs highlighting exact bottleneck spans across distributed service calls.",
                            optional_hints=["W3C Trace Context headers (traceparent) carry the trace state across HTTP requests."]
                        ),
                    ],
                ),
                make_skill(
                    slug="github-actions-backend",
                    name="CI/CD Pipelines with GitHub Actions",
                    canonical_slug="github-actions",
                    difficulty="INTERMEDIATE",
                    description="Continuous Integration and Continuous Deployment: Automated linting, test suites, Docker image builds, vulnerability scans, and deployment workflows via GitHub Actions.",
                    key_topics=["Workflow Syntax & Event Triggers (push, pull_request)", "Job Matrices & Parallel Execution", "Secrets & Environment Management", "Automated Testing & Coverage Reporting", "Docker Buildx & Container Registry Publishing"],
                    role_relevance="Automates code quality enforcement, guarantees test passage before merges, and automates deployments to cloud environments.",
                    prerequisites=["git", "pytest", "docker"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "GitHub Actions Documentation", "url": "https://docs.github.com/en/actions", "description": "Official guides, reference, and examples for building automated CI/CD workflows."},
                        {"type": "YOUTUBE", "title": "GitHub Actions Tutorial — TechWorld with Nana", "url": "https://www.youtube.com/watch?v=R8_veQiYBjI", "description": "Complete walkthrough of building continuous integration and continuous deployment pipelines."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="actions-prob-1",
                            title="Automated Linting & Test Workflow",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build a GitHub Actions workflow that executes tests on pull requests.",
                            problem_statement="Create a .github/workflows/ci.yml pipeline that installs dependencies, runs linters, and executes Pytest on every pull request to main.",
                            requirements=[
                                "Trigger on pull_request to branch 'main'.",
                                "Set up Python 3.11 with actions/setup-python and cache pip dependencies.",
                                "Run Ruff / Flake8 linter and execute 'pytest tests/'."
                            ],
                            concepts_tested=["GitHub Actions Syntax", "pull_request Triggers", "actions/setup-python", "Dependency Caching", "Test Execution"],
                            expected_outcome="A pull request check that blocks merges if tests or linting checks fail.",
                            optional_hints=["Use 'cache: pip' in actions/setup-python to speed up CI runs."]
                        ),
                        make_problem(
                            problem_id="actions-prob-2",
                            title="Multi-Version Test Matrix with Service Containers",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Run automated integration tests across multiple Python versions with a PostgreSQL service container.",
                            problem_statement="Configure a matrix build testing Python 3.10, 3.11, and 3.12 with an active PostgreSQL service container in GitHub Actions.",
                            requirements=[
                                "Use 'strategy: matrix: python-version: [\"3.10\", \"3.11\", \"3.12\"]'.",
                                "Define a services: postgres container with health checks for database integration testing.",
                                "Run database migrations and integration test suite against the live Postgres service."
                            ],
                            concepts_tested=["Build Matrices", "Service Containers (services: postgres)", "Environment Variables in CI", "Integration Testing in CI"],
                            expected_outcome="Parallel test verification across 3 Python runtimes with real database interactions.",
                            optional_hints=["Access service container on host 'localhost' and port 5432 in GitHub Actions."]
                        ),
                        make_problem(
                            problem_id="actions-prob-3",
                            title="Buildx Multi-Arch Docker Build & Registry Publishing",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build, tag, and publish multi-architecture Docker images to GitHub Container Registry (GHCR) with caching.",
                            problem_statement="Build an automated CD workflow that packages a multi-platform Docker container (linux/amd64, linux/arm64) and pushes to GHCR on release tag creation.",
                            requirements=[
                                "Trigger on push of git tags (v*.*.*).",
                                "Use docker/setup-buildx-action and docker/login-action with GITHUB_TOKEN.",
                                "Use docker/build-push-action with GitHub Actions cache (type=gha) and push to ghcr.io."
                            ],
                            concepts_tested=["Docker Buildx", "Multi-Arch Images (amd64/arm64)", "GitHub Container Registry (GHCR)", "GHA Cache Export", "Release Tag Triggers"],
                            expected_outcome="An automated production pipeline delivering signed, cached container images ready for cloud deployment.",
                            optional_hints=["Use docker/metadata-action to generate semver tags automatically from git tags."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

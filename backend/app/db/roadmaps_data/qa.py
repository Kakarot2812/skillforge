"""QA / Test Automation Engineer roadmap definition with progressive practice problems."""
from typing import Any, Dict
from app.db.roadmaps_data.common import ROADMAP_IDS, make_problem, make_skill

QA_AUTOMATION_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["qa-automation-engineer"],
    "slug": "qa-automation-engineer",
    "role_id": None,
    "title": "QA / Test Automation Engineer",
    "domain": "QA / Test Automation",
    "category": "Quality Assurance & Engineering",
    "description": "Architect modern software quality assurance pipelines: test design heuristics, Python test automation frameworks (pytest), robust API testing, end-to-end browser automation with Playwright, mobile testing with Appium, high-load performance benchmarking with k6, and containerized CI/CD test orchestration.",
    "version": "v2.0",
    "has_market_data": False,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Testing Theory, Strategy & Scripting Foundations",
            "description": "Core test design heuristics, boundary value analysis, test pyramid strategies, and object-oriented Python test development.",
            "skills": [
                make_skill(
                    slug="testing-fundamentals",
                    name="Software Testing Fundamentals & Test Design",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Foundational test engineering: test pyramid, equivalence partitioning, boundary value analysis, decision tables, state transition testing, test plan creation, and exploratory testing.",
                    key_topics=["The Test Pyramid (Unit, Integration, E2E)", "Equivalence Partitioning & Boundary Value Analysis (BVA)", "Decision Tables & State Transition Testing", "Test Plan & Strategy Specification", "Defect Lifecycle & Severity vs Priority"],
                    role_relevance="Provides the scientific methodology and rigor required to design high-coverage test cases without wasteful redundancy.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "ISTQB Foundation Level Syllabus", "url": "https://www.istqb.org/certifications/certified-tester-foundation-level", "description": "Official international standard for software testing terminology, techniques, and lifecycle processes."},
                        {"type": "YOUTUBE", "title": "Software Testing Fundamentals — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive tutorial explaining test case design, black-box techniques, and defect reporting."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="qa-fund-prob-1",
                            title="Boundary Value Analysis & Equivalence Partitioning Matrix",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Design an exhaustive test suite using equivalence partitioning and 2-point / 3-point boundary value analysis.",
                            problem_statement="A financial loan eligibility engine accepts age (18 to 65 inclusive) and credit score (300 to 850 inclusive). Apply equivalence partitioning (valid and invalid classes) and 3-point boundary value analysis to derive the exact set of test inputs covering all boundaries.",
                            requirements=[
                                "Identify all valid and invalid equivalence classes for both age and credit score.",
                                "Derive test values at min-1, min, min+1, nominal, max-1, max, max+1.",
                                "Construct a structured test case matrix documenting test ID, description, inputs, and expected outcomes.",
                                "Justify why boundary values expose the majority of off-by-one coding defects."
                            ],
                            concepts_tested=["Equivalence Partitioning", "Boundary Value Analysis (BVA)", "Test Matrix Design", "Off-by-One Defect Detection"],
                            expected_outcome="A mathematically defensible test design matrix maximizing defect detection with minimal test count.",
                            optional_hints=["Boundary value analysis targets the edge conditions where relational comparison operators (< vs <=) fail."]
                        ),
                        make_problem(
                            problem_id="qa-fund-prob-2",
                            title="State Transition Matrix & E-Commerce Order Lifecycle",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Model a stateful software lifecycle using finite state machine state transition diagrams and test tables.",
                            problem_statement="An e-commerce order progresses through states: Cart -> Placed -> Paid -> Shipped -> Delivered, with branches for Cancelled and Refunded. Model the complete state machine, identify valid transitions and invalid transitions (e.g. attempting to Refund an unpaid order), and produce 100% transition-coverage test cases.",
                            requirements=[
                                "Draw or specify the finite state machine with states, inputs, and transitions.",
                                "Construct a state transition table testing all N valid state changes.",
                                "Identify negative test cases attempting illegal transitions and verify expected error states.",
                                "Document state transition test cases in a standard test management format."
                            ],
                            concepts_tested=["State Transition Testing", "Finite State Machines", "Negative Testing for Invalid Transitions", "Lifecycle Test Design"],
                            expected_outcome="A state transition test specification guaranteeing complete coverage of lifecycle states.",
                            optional_hints=["Testing invalid state transitions is essential for discovering unauthorized workflow bypasses."]
                        ),
                        make_problem(
                            problem_id="qa-fund-prob-3",
                            title="Enterprise Test Strategy & Risk-Based Quality Plan",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Formulate an enterprise-level test strategy document balancing risk, automation layers, and release criteria.",
                            problem_statement="For a mission-critical healthcare application undergoing modernization, author a comprehensive Test Strategy document defining: scope, test pyramid allocation (70% unit, 20% integration, 10% E2E), risk assessment matrix (Failure Probability vs Impact), environment topologies, entry/exit criteria, and automated quality gates for production release.",
                            requirements=[
                                "Calculate risk priority numbers (RPN) across business features to prioritize test automation.",
                                "Specify clear entry and exit criteria for QA staging sign-off (e.g. 0 blocker/critical bugs, 95% automated pass rate).",
                                "Define test data management strategy (sanitized production data vs synthetic factories).",
                                "Establish incident response and defect triage SLA workflows."
                            ],
                            concepts_tested=["Enterprise Test Strategy", "Risk-Based Testing (RPN)", "Release Quality Gates", "Test Data Management Strategy"],
                            expected_outcome="A professional quality assurance strategy ready for executive sign-off and audit compliance.",
                            optional_hints=["Risk-based testing focuses testing efforts on features with high financial impact and high defect likelihood."]
                        ),
                    ],
                ),
                make_skill(
                    slug="test-automation-python",
                    name="Test Automation Foundations with Python",
                    canonical_slug="python",
                    difficulty="BEGINNER",
                    description="Professional test automation using Python and pytest: test runners, fixtures, scopes (function, module, session), parametrization, mocking, assertions, and test structuring.",
                    key_topics=["Pytest Architecture & Test Discovery", "Fixtures & Teardown Lifecycle (yield, scope)", "Test Parametrization (@pytest.mark.parametrize)", "Mocking & Patching with unittest.mock", "Pytest Configuration (pytest.ini, conftest.py)"],
                    role_relevance="The programming backbone for modern automated testing, enabling clean, maintainable, and scalable test frameworks.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Pytest Official Documentation", "url": "https://docs.pytest.org/en/stable/", "description": "Official guides to fixtures, parametrization, plugins, and test configuration in pytest."},
                        {"type": "YOUTUBE", "title": "Pytest Tutorial for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on video course on writing modular tests, writing fixtures, and mock assertions."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="py-test-prob-1",
                            title="Pytest Parametrization & Custom Assertions",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write compact, data-driven unit tests using @pytest.mark.parametrize with comprehensive input matrices.",
                            problem_statement="Test a complex string validation and password policy checker. Using @pytest.mark.parametrize, test 15 distinct combinations of valid passwords, weak passwords (missing special chars, too short), and edge cases (unicode, extreme lengths), generating readable test failure output.",
                            requirements=[
                                "Use @pytest.mark.parametrize with descriptive test IDs.",
                                "Test expected boolean results and specific validation error message strings.",
                                "Group related test cases logically inside test classes.",
                                "Ensure all tests execute cleanly via pytest -v."
                            ],
                            concepts_tested=["Pytest Parametrization", "Data-Driven Testing", "Test ID Formatting", "Clear Assertion Messages"],
                            expected_outcome="A clean, concise parameterized test suite covering all input permutations.",
                            optional_hints=["Use ids=lambda val: f'case_{val}' to generate readable test report names."]
                        ),
                        make_problem(
                            problem_id="py-test-prob-2",
                            title="Modular Fixtures & Session Teardown Lifecycle",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Architect a modular fixture hierarchy in conftest.py supporting session-level databases and function-level rollbacks.",
                            problem_statement="Create a conftest.py file with tiered fixtures: a session-scoped fixture initializing a temporary SQLite database, a function-scoped fixture creating a clean database transaction that automatically rolls back after each test via yield, and a custom test data factory fixture generating mock user instances.",
                            requirements=[
                                "Implement session-scoped db_engine fixture with proper cleanup teardown.",
                                "Implement function-scoped db_session fixture rolling back uncommitted changes.",
                                "Create a factory fixture user_factory(**kwargs) that creates dynamic test entities.",
                                "Demonstrate complete test isolation: modifications in test_A do not leak into test_B."
                            ],
                            concepts_tested=["Pytest Fixture Scopes", "Yield Teardown Pattern", "Test Data Factories", "Test State Isolation"],
                            expected_outcome="A bulletproof test setup ensuring zero inter-test state contamination.",
                            optional_hints=["Yield inside a fixture acts as the boundary between setup and teardown."]
                        ),
                        make_problem(
                            problem_id="py-test-prob-3",
                            title="Mocking External APIs & Flaky Test Quarantine",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Isolate code under test from external HTTP dependencies using unittest.mock / responses and implement retry mechanisms.",
                            problem_statement="A service interacts with third-party payment gateways and email APIs. Write comprehensive tests using unittest.mock.patch and responses to mock successful payments, network timeouts, HTTP 500 errors, and malformed JSON. Add custom pytest markers to quarantine flaky tests and auto-retry transient failures via pytest-rerunfailures.",
                            requirements=[
                                "Mock HTTP responses and network exceptions without making real network calls.",
                                "Assert that mock calls occurred with exact expected payload and header parameters.",
                                "Configure custom pytest marker @pytest.mark.flaky(reruns=3) in pytest.ini.",
                                "Produce a JUnit XML report consumable by CI systems."
                            ],
                            concepts_tested=["API Mocking & Patching", "Side Effect Simulation (Timeouts/Errors)", "Flaky Test Management", "JUnit XML CI Reporting"],
                            expected_outcome="A 100% deterministic test suite executing instantly without external network calls.",
                            optional_hints=["Use mock.patch.object or the responses library to mock HTTP calls at the transport level."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Web & Mobile End-to-End Automation",
            "description": "API contract validation, Playwright browser automation, and cross-platform mobile testing with Appium.",
            "skills": [
                make_skill(
                    slug="api-testing-automation",
                    name="API Testing & Automation with Requests / Postman",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Automating RESTful and GraphQL API verification: status codes, response headers, JSON Schema contracts, authentication flows, response time validation, and chained workflows.",
                    key_topics=["HTTP Methods, Status Codes & Headers", "JSON Schema Validation (jsonschema)", "Chained API Workflows (Auth -> Create -> Verify -> Delete)", "Authentication (Bearer Token, OAuth, API Keys)", "Performance & Latency Assertions"],
                    role_relevance="API tests run faster and are far less brittle than UI tests, forming the critical middle layer of the test pyramid.",
                    prerequisites=["test-automation-python"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Requests: HTTP for Humans Documentation", "url": "https://requests.readthedocs.io/en/latest/", "description": "Official guide to sending HTTP requests, managing sessions, and handling cookies in Python."},
                        {"type": "YOUTUBE", "title": "API Testing with Python and Pytest — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on tutorial building a scalable API automation test framework in Python."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="api-test-prob-1",
                            title="JSON Schema Validation & Status Assertions",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Validate API response payloads against strict JSON Schema definitions using Python jsonschema.",
                            problem_statement="Write automated pytest tests against a public or mock REST API endpoint (e.g. GET /api/v1/users/{id}). Validate status code 200, Content-Type application/json, and validate the full JSON response body against a predefined JSON schema specifying required fields, string formats (email, uuid), and number constraints.",
                            requirements=[
                                "Define JSON schema with required fields, type checks, and format constraints.",
                                "Validate responses using jsonschema.validate(instance=res.json(), schema=schema).",
                                "Verify descriptive assertion errors when a required field is missing.",
                                "Assert response latency is under 200ms."
                            ],
                            concepts_tested=["JSON Schema Validation", "HTTP Response Inspection", "SLA Latency Assertions", "Contract Testing Basics"],
                            expected_outcome="An automated API test catching contract violations immediately upon backend schema changes.",
                            optional_hints=["JSON schema validation verifies the structural contract regardless of specific dynamic values."]
                        ),
                        make_problem(
                            problem_id="api-test-prob-2",
                            title="Chained CRUD Workflow & State Teardown",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Automate a stateful, end-to-end CRUD entity lifecycle with token authentication and guaranteed cleanup.",
                            problem_statement="Write a test class that authenticates via POST /auth/login, extracts the JWT token into a session, creates a new resource via POST, verifies its persistence via GET, updates an attribute via PATCH, verifies modification, and finally deletes the resource via DELETE, confirming 404 on subsequent read.",
                            requirements=[
                                "Maintain auth headers across requests using requests.Session().",
                                "Extract dynamic IDs from creation responses to parameterize subsequent requests.",
                                "Implement a try/finally or pytest fixture cleanup ensuring created resources are deleted even if tests fail.",
                                "Validate that deleting non-existent IDs returns 404 Not Found."
                            ],
                            concepts_tested=["Chained API Workflows", "requests.Session Management", "Stateful CRUD Lifecycle", "Guaranteed Teardown Cleanup"],
                            expected_outcome="A self-contained API test workflow leaving zero test data residue in the database.",
                            optional_hints=["Always place DELETE cleanup in a fixture teardown or finally block to prevent orphaned test records."]
                        ),
                        make_problem(
                            problem_id="api-test-prob-3",
                            title="Comprehensive REST API Automation Framework",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Architect an enterprise-grade API testing framework with environment configuration, logging, and metrics reporting.",
                            problem_statement="Develop an extensible API testing framework with: an abstract API client wrapper handling authentication, base URL configuration via environment variables, automatic request/response logging (headers, masked tokens, payloads, response times), schema validation utilities, and Allure report integration.",
                            requirements=[
                                "Create an ApiClient class encapsulating requests with retry logic on 503/504 errors.",
                                "Implement automated logging of all outbound requests and inbound responses.",
                                "Sanitize sensitive credentials (Authorization tokens) from logs.",
                                "Integrate Allure reporting with step annotations and attached response bodies."
                            ],
                            concepts_tested=["API Client Architecture", "Environment Configuration", "Sensitive Data Masking", "Allure Reporting Integration"],
                            expected_outcome="A production-ready API automation framework adaptable to any enterprise microservice fleet.",
                            optional_hints=["Use an interceptor/hook or wrapper method around session.request to log traffic centrally."]
                        ),
                    ],
                ),
                make_skill(
                    slug="e2e-playwright",
                    name="End-to-End Web UI Automation with Playwright",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Modern web browser automation with Microsoft Playwright: Page Object Model (POM), locator strategies, auto-waiting, network mocking, visual regression, and multi-browser execution.",
                    key_topics=["Playwright Architecture & Event-Driven Auto-Waiting", "Resilient Locators (Role, Text, TestId)", "Page Object Model (POM) Design Pattern", "Network Interception & API Route Mocking", "Visual Comparison & Trace Viewer Debugging"],
                    role_relevance="The premier modern framework for reliable, non-flaky end-to-end browser automation across Chromium, Firefox, and WebKit.",
                    prerequisites=["test-automation-python", "testing-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Playwright for Python Official Documentation", "url": "https://playwright.dev/python/docs/intro", "description": "Official documentation for installation, locators, page objects, and assertion libraries."},
                        {"type": "YOUTUBE", "title": "Playwright Automation Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive tutorial covering locators, Page Object Model, network interception, and CI execution."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="pw-prob-1",
                            title="Resilient Locators & Form Submission",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write automated browser tests using user-facing Playwright locators with built-in auto-waiting.",
                            problem_statement="Automate user registration on a dynamic web page. Fill in name, email, password, select country from a dropdown, check terms agreement checkbox, and submit the form. Assert that a success toast appears and redirects to the dashboard.",
                            requirements=[
                                "Use user-facing accessibility locators (page.get_by_role, page.get_by_label, page.get_by_test_id).",
                                "Avoid arbitrary hardcoded sleep statements (time.sleep()); rely exclusively on Playwright auto-waiting.",
                                "Assert navigation URL using expect(page).to_have_url(...).",
                                "Verify toast message visibility with expect(toast).to_be_visible()."
                            ],
                            concepts_tested=["User-Facing Locators (Roles, Labels)", "Auto-Waiting Mechanics", "Playwright Web Assertions", "Form Interaction"],
                            expected_outcome="A completely non-flaky test automating form submission and assertion.",
                            optional_hints=["Playwright automatically waits for elements to be visible, enabled, and stable before interacting."]
                        ),
                        make_problem(
                            problem_id="pw-prob-2",
                            title="Page Object Model (POM) Architecture",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Refactor raw Playwright scripts into a clean, maintainable Page Object Model architecture.",
                            problem_statement="Refactor an e-commerce checkout test suite into Page Object classes: LoginPage, CatalogPage, CartPage, and CheckoutPage. Encapsulate element locators and user interactions inside page methods so test specifications read like high-level business scenarios.",
                            requirements=[
                                "Create modular classes in pages/ directory accepting Playwright page fixture.",
                                "Encapsulate locator definitions as class properties or methods.",
                                "Implement fluent method chaining where appropriate (e.g. login.fill_credentials().click_submit()).",
                                "Write clean test functions in tests/ expressing business user journeys."
                            ],
                            concepts_tested=["Page Object Model (POM)", "Locator Encapsulation", "Test Code Reusability", "Fluent Interface Design"],
                            expected_outcome="A maintainable, modular test suite where UI changes require edits in only one page class.",
                            optional_hints=["Never expose raw selectors inside your test scripts; keep them isolated inside Page Objects."]
                        ),
                        make_problem(
                            problem_id="pw-prob-3",
                            title="Network Mocking, Visual Regression & Trace Diagnostics",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Intercept network API calls to test error states and capture Playwright execution traces for debugging.",
                            problem_statement="Test how a dashboard UI handles backend failures by intercepting /api/metrics using page.route() and returning HTTP 500. Assert the UI gracefully displays an error banner. Perform pixel-level visual regression comparison, and configure Playwright to record full execution traces on test failures.",
                            requirements=[
                                "Intercept network requests via page.route('**/api/metrics', lambda route: route.fulfill(status=500)).",
                                "Verify UI fallback error components appear without crashing the application.",
                                "Perform visual snapshot comparison using expect(page).to_have_screenshot().",
                                "Configure context tracing (tracing.start, tracing.stop(path='trace.zip')) and inspect with Playwright Trace Viewer."
                            ],
                            concepts_tested=["Network Route Interception & Mocking", "UI Error Resilience Testing", "Visual Regression Comparison", "Playwright Trace Viewer Diagnostics"],
                            expected_outcome="Advanced test validation covering edge-case network faults and visual fidelity.",
                            optional_hints=["Playwright's Trace Viewer records screencasts, DOM snapshots, and network waterfalls for post-mortem debugging."]
                        ),
                    ],
                ),
                make_skill(
                    slug="mobile-appium",
                    name="Mobile Test Automation with Appium",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Cross-platform native mobile test automation: Appium 2.0 architecture, UiAutomator2 (Android), XCUITest (iOS), mobile gestures (scroll, swipe, pinch), and device farm execution.",
                    key_topics=["Appium 2.0 Architecture & Drivers", "Desired Capabilities / Appium Options", "Mobile Locators (Accessibility ID, XPath, UIAutomator)", "Gestures & TouchActions (W3C Actions API)", "Real Device vs Emulator / Simulator Execution"],
                    role_relevance="Validates iOS and Android mobile app stability, performance, and touchscreen interaction flows on physical devices.",
                    prerequisites=["testing-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Appium Documentation", "url": "https://appium.io/docs/en/latest/", "description": "Official Appium 2.0 guides, drivers, plugins, and command reference."},
                        {"type": "YOUTUBE", "title": "Appium Mobile Testing Tutorial — Automation Step by Step", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Step-by-step tutorial setting up Appium server, Android emulators, and Python client scripts."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="appium-prob-1",
                            title="Appium Session Setup & Accessibility ID Locators",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Configure an Appium 2.0 session on an Android emulator and automate basic element interactions.",
                            problem_statement="Initialize an Appium session using UiAutomator2Options pointing to an Android APK. Locate elements using AppiumBy.ACCESSIBILITY_ID and AppiumBy.ID, input text into a search bar, and assert search results appear.",
                            requirements=[
                                "Configure platformName='Android', automationName='UiAutomator2', appPackage, and appActivity.",
                                "Prioritize accessibility IDs (content-desc) over fragile absolute XPaths.",
                                "Interact with mobile controls: click, send_keys, and clear.",
                                "Gracefully terminate Appium driver session on teardown."
                            ],
                            concepts_tested=["Appium Capabilities Setup", "UiAutomator2 Driver", "Accessibility ID Locators", "Session Lifecycle Management"],
                            expected_outcome="A reliable mobile automation script executing against an Android virtual device.",
                            optional_hints=["Accessibility IDs are the fastest, most reliable mobile locators and promote accessible UI design."]
                        ),
                        make_problem(
                            problem_id="appium-prob-2",
                            title="Mobile Gestures with W3C Actions API",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Automate complex touch gestures (vertical scrolling, horizontal swipe, drag-and-drop) using W3C Actions.",
                            problem_statement="In a long mobile product catalog, implement a reusable gesture utility using the W3C Actions API to scroll down until an off-screen item becomes visible, swipe right to delete a list item, and assert item removal.",
                            requirements=[
                                "Implement vertical scroll using pointer inputs with finger touch down, move, and up actions.",
                                "Build a scroll_to_element(locator, max_swipes=5) helper method.",
                                "Automate horizontal swipe-to-dismiss interaction.",
                                "Verify element disappears from DOM hierarchy after swipe action."
                            ],
                            concepts_tested=["W3C Touch Actions API", "Scroll-to-View Logic", "Swipe Gestures", "Dynamic Viewport Sizing"],
                            expected_outcome="A reusable mobile gestures library capable of interacting with complex touch interfaces.",
                            optional_hints=["Calculate swipe coordinates dynamically as percentages of driver.get_window_size() to support different screen resolutions."]
                        ),
                        make_problem(
                            problem_id="appium-prob-3",
                            title="Cross-Platform Test Execution on Cloud Device Farm",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Parameterize an Appium test suite to run identically across both Android and iOS devices on a cloud farm.",
                            problem_statement="Architect a cross-platform mobile test suite. Use abstract Page Objects that map unified actions to platform-specific locators (UiAutomator2 selectors for Android, XCUITest NSPredicate / Class Chain for iOS), and execute the suite in parallel on BrowserStack / Sauce Labs cloud device farms.",
                            requirements=[
                                "Define platform-agnostic page interfaces with platform-specific locator maps.",
                                "Configure cloud device farm connection capabilities and authentication credentials via environment variables.",
                                "Execute tests across Android and iOS targets in parallel.",
                                "Attach cloud video recording links and device logs to test artifacts."
                            ],
                            concepts_tested=["Cross-Platform Mobile Architecture", "XCUITest vs UiAutomator2 Locators", "Cloud Device Farm Integration", "Parallel Mobile Execution"],
                            expected_outcome="A scalable mobile automation framework running seamlessly on physical Android and iOS devices.",
                            optional_hints=["iOS Class Chains and Predicates provide high-speed XPath alternatives on XCUITest."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Non-Functional Testing & Performance",
            "description": "High-throughput performance benchmarking, stress testing, and concurrency metrics with k6.",
            "skills": [
                make_skill(
                    slug="perf-testing-k6",
                    name="Performance & Load Testing with k6",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Performance and load testing: Grafana k6, Virtual Users (VUs), test stages (ramp-up, steady-state, soak, stress), thresholds (p95, p99 latency), HTTP request metrics, and bottleneck diagnosis.",
                    key_topics=["Load Testing Concepts (Smoke, Load, Stress, Spike, Soak)", "k6 JavaScript Test Scripting", "Virtual Users (VUs) & Staged Ramping", "Performance Thresholds (p95, p99, Error Rate)", "Metrics Analysis & Bottleneck Identification"],
                    role_relevance="Ensures APIs and distributed backend services maintain sub-second response times under peak traffic surges.",
                    prerequisites=["api-testing-automation"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Grafana k6 Official Documentation", "url": "https://k6.io/docs/", "description": "Official guides to writing load tests, configuring execution stages, and defining thresholds in k6."},
                        {"type": "YOUTUBE", "title": "k6 Performance Testing Crash Course — Automation Step by Step", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on tutorial building load, stress, and spike test scripts using k6."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="k6-prob-1",
                            title="Smoke Test with Strict p95 Latency Thresholds",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write a basic k6 smoke test validating API functionality under minimal concurrency with performance assertions.",
                            problem_statement="Create a k6 script (smoke_test.js) simulating 5 concurrent virtual users for 1 minute hitting an authentication and search endpoint. Configure thresholds failing the test if p(95) response time exceeds 250ms or http_req_failed exceeds 1%.",
                            requirements=[
                                "Configure options: vus: 5, duration: '1m'.",
                                "Use check() assertions confirming status 200 and response body integrity.",
                                "Define thresholds: 'http_req_duration': ['p(95)<250'], 'http_req_failed': ['rate<0.01'].",
                                "Run test via k6 run smoke_test.js and verify pass/fail outcome."
                            ],
                            concepts_tested=["k6 Test Scripting", "Checks & Assertions", "p95 Latency Thresholds", "Error Rate Guardrails"],
                            expected_outcome="A fast, automated smoke test asserting API baseline responsiveness.",
                            optional_hints=["k6 returns exit code 0 on passing thresholds and non-zero on failed thresholds for CI integration."]
                        ),
                        make_problem(
                            problem_id="k6-prob-2",
                            title="Staged Ramp-Up Load Test with Custom Trend Metrics",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Model realistic user traffic patterns with ramp-up, sustained load, and cool-down stages tracking custom metrics.",
                            problem_statement="Develop a k6 load test simulating realistic traffic: ramp up from 0 to 100 VUs over 2 minutes, hold steady at 100 VUs for 5 minutes, ramp up to 250 VUs for 2 minutes, and cool down to 0. Create custom Trend and Counter metrics tracking checkout processing duration and failed payment counts.",
                            requirements=[
                                "Define staged ramping in options.stages.",
                                "Implement custom Trend metric: let checkoutDuration = new Trend('checkout_duration').",
                                "Simulate randomized user think time using sleep(randomIntBetween(1, 3)).",
                                "Validate that the system maintains <1% error rate during sustained 100 VU load."
                            ],
                            concepts_tested=["Staged Ramping Options", "Custom k6 Metrics (Trend, Counter)", "User Think Time Simulation", "Sustained Concurrency Testing"],
                            expected_outcome="A realistic load profile accurately simulating peak production traffic curves.",
                            optional_hints=["Always incorporate randomized sleep intervals to avoid artificial synchronized request bursts."]
                        ),
                        make_problem(
                            problem_id="k6-prob-3",
                            title="Spike & Soak Testing for Memory Leaks and Auto-Scaling",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Execute sudden spike tests and 4-hour soak tests to detect memory leaks, database connection pool exhaustion, and auto-scaling lag.",
                            problem_statement="Author two specialized performance test profiles: a Spike Test (jumping from 10 to 1,000 VUs in 10 seconds to test auto-scaler reaction time) and a Soak Test (running 50 VUs for 4 hours to detect memory leaks and connection exhaustion). Correlate k6 results with server CPU/RAM telemetry to pinpoint breaking points.",
                            requirements=[
                                "Configure steep spike stages and analyze latency degradation during pod scaling intervals.",
                                "Design a soak test script executing sustained iterative API calls.",
                                "Monitor server memory metrics to detect linear memory creep indicating leak defects.",
                                "Produce a capacity planning report documenting the maximum sustainable RPS (Requests Per Second)."
                            ],
                            concepts_tested=["Spike Testing", "Soak Testing & Memory Leak Detection", "Connection Pool Exhaustion", "Capacity Planning & Max RPS"],
                            expected_outcome="A comprehensive resilience profile identifying system breaking points and auto-scaling boundaries.",
                            optional_hints=["Soak tests expose subtle defects like unclosed database sessions and thread pool leaks that short tests miss."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Continuous Quality & Observability",
            "description": "Containerized CI/CD test pipelines, defect analytics, Allure dashboards, and test observability.",
            "skills": [
                make_skill(
                    slug="cicd-test-pipelines",
                    name="CI/CD Test Pipeline Integration",
                    canonical_slug="docker",
                    difficulty="INTERMEDIATE",
                    description="Automating test execution in CI/CD: containerized test runners (Docker), GitHub Actions / GitLab CI workflows, parallel test sharding, test caching, and pull request quality gates.",
                    key_topics=["Containerizing Test Suites with Docker", "GitHub Actions Test Workflows", "Test Sharding & Parallel Matrix Execution", "Dependency & Browser Binary Caching", "PR Quality Gates & Automated Merge Blocking"],
                    role_relevance="Transforms automated tests from local scripts into continuous guardrails protecting production code on every commit.",
                    prerequisites=["e2e-playwright", "api-testing-automation"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "GitHub Actions Documentation — Testing", "url": "https://docs.github.com/en/actions/automating-builds-and-tests", "description": "Official guides to building continuous integration workflows for automated testing."},
                        {"type": "YOUTUBE", "title": "CI/CD Pipeline with GitHub Actions — freeCodeCamp", "url": "https://www.youtube.com/watch?v=R8_veQiYBjI", "description": "Hands-on walkthrough building automated testing pipelines in GitHub Actions."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="cicd-prob-1",
                            title="Dockerized Test Runner Container",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Package a complete Python and Playwright test suite into a lightweight, hermetic Docker container.",
                            problem_statement="Write a Dockerfile that installs Python dependencies, installs Playwright browser binaries and OS dependencies (playwright install --with-deps chromium), copies test code, and executes pytest upon container run, mounting test results to a host volume.",
                            requirements=[
                                "Use official mcr.microsoft.com/playwright/python image as base.",
                                "Install project dependencies via requirements.txt.",
                                "Configure ENTRYPOINT ['pytest'] with volume mount for /reports.",
                                "Verify container executes headlessly and generates HTML test reports on the host."
                            ],
                            concepts_tested=["Dockerized Test Environments", "Hermetic Execution", "Headless Browser Configuration", "Volume Mounting for Reports"],
                            expected_outcome="A portable test container running identically on developer laptops and CI agents.",
                            optional_hints=["Official Playwright base images come pre-baked with all required Linux OS graphics libraries."]
                        ),
                        make_problem(
                            problem_id="cicd-prob-2",
                            title="GitHub Actions Workflow with Test Sharding",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Cut CI test execution time in half using GitHub Actions matrix strategy and Playwright test sharding.",
                            problem_statement="Configure a GitHub Actions workflow (.github/workflows/e2e.yml) that triggers on pull requests. Use a matrix strategy across 4 parallel runners (shard: [1/4, 2/4, 3/4, 4/4]), execute tests in parallel using pytest --shard, and merge all test reports into a consolidated artifact.",
                            requirements=[
                                "Configure pull_request trigger on main branch.",
                                "Define matrix: shard: ['1/4', '2/4', '3/4', '4/4'].",
                                "Cache pip dependencies and browser binaries using actions/cache.",
                                "Merge and publish unified test results as a PR status check."
                            ],
                            concepts_tested=["CI Matrix Strategy", "Test Sharding (Parallel Execution)", "Action Caching Optimization", "PR Status Check Integration"],
                            expected_outcome="A fast CI pipeline executing large test suites in a fraction of linear run time.",
                            optional_hints=["Test sharding divides test files across multiple identical runner nodes running concurrently."]
                        ),
                        make_problem(
                            problem_id="cicd-prob-3",
                            title="Ephemeral Staging Environment & Automated Merge Gate",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Spin up an ephemeral docker-compose staging environment in CI, run end-to-end smoke tests, and block PR merge on failure.",
                            problem_statement="Develop an end-to-end CI pipeline that boots the entire microservice application stack (frontend, backend, database) using docker compose up -d, polls a health check endpoint until healthy, executes full API and Playwright smoke tests against the live stack, tears down the environment, and blocks pull request merge if any test fails.",
                            requirements=[
                                "Deploy multi-container environment via docker compose in CI runner.",
                                "Implement curl health check loop waiting for service readiness.",
                                "Execute automated tests targeting http://localhost:3000.",
                                "Ensure docker compose down -v executes reliably in an always() cleanup step."
                            ],
                            concepts_tested=["Ephemeral Test Environments", "Docker Compose in CI", "Service Readiness Polling", "Automated Merge Gate Enforcement"],
                            expected_outcome="A zero-trust continuous quality gate ensuring broken code can never merge to main.",
                            optional_hints=["Use always() in GitHub Actions to guarantee container teardown even if test steps fail."]
                        ),
                    ],
                ),
                make_skill(
                    slug="test-reporting-observability",
                    name="Test Reporting, Observability & Defect Analytics",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Quality analytics and defect intelligence: Allure reporting, JUnit XML parsing, test execution dashboards, flake detection algorithms, and automated bug filing integrations.",
                    key_topics=["Rich Test Reporting with Allure Framework", "JUnit / TestNG XML Schema & Aggregation", "Flaky Test Detection & Quarantine Analytics", "Defect Root Cause Categorization", "Quality Metrics (Pass Rate, MTTR, Test Coverage)"],
                    role_relevance="Provides transparent visibility to engineering leadership on software stability, release readiness, and test suite health.",
                    prerequisites=["testing-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Allure Framework Official Documentation", "url": "https://allurereport.org/docs/", "description": "Official guide to generating rich interactive HTML test reports with steps, screenshots, and logs."},
                        {"type": "YOUTUBE", "title": "Allure Reporting with Pytest — Automation Step by Step", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on tutorial integrating Allure annotations, attachments, and generating web reports."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="rep-prob-1",
                            title="Rich Allure Report Integration with Attachments",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Enhance automated tests with Allure annotations, step descriptions, and failure screenshot attachments.",
                            problem_statement="Integrate allure-pytest into your test framework. Decorate tests with @allure.feature, @allure.story, and @allure.severity. Wrap test actions in with allure.step(): context blocks, and attach automatic full-page screenshots and network HAR files upon test failure.",
                            requirements=[
                                "Configure pytest-allure plugin in conftest.py.",
                                "Implement a pytest_runtest_makereport hook that captures screenshots on call failures.",
                                "Attach logs and screenshots via allure.attach().",
                                "Generate interactive HTML report via allure generate allure-results -o allure-report."
                            ],
                            concepts_tested=["Allure Annotations & Steps", "Pytest Hooks (makereport)", "Failure Screenshot Capture", "Interactive HTML Report Generation"],
                            expected_outcome="An executive-ready visual report detailing test steps, logs, and screenshots.",
                            optional_hints=["Use pytest_runtest_makereport hook to detect when report.failed is true and capture page.screenshot()."]
                        ),
                        make_problem(
                            problem_id="rep-prob-2",
                            title="Automated Flaky Test Diagnostic & Quarantine Engine",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Build an automated script analyzing historical JUnit XML test runs to identify and quarantine flaky tests.",
                            problem_statement="Write a Python utility parse_flaky_tests.py that ingests JUnit XML reports from the last 30 CI runs. Calculate the flakiness index (tests passing on retry after initial failure), generate a prioritized flaky test leaderboard, and automatically annotate flaky tests in code with @pytest.mark.quarantine.",
                            requirements=[
                                "Parse nested XML elements across multiple test suite files using xml.etree.ElementTree.",
                                "Compute metrics: total runs, initial failures, retry passes, and flake rate percentage.",
                                "Flag any test with flake rate > 5% as quarantined.",
                                "Output an executive markdown report listing top 10 flakiest test cases with stack traces."
                            ],
                            concepts_tested=["JUnit XML Parsing", "Flakiness Index Calculation", "Automated Test Quarantine", "Quality Health Analytics"],
                            expected_outcome="An automated test health monitoring script eliminating false alarms in CI builds.",
                            optional_hints=["A test that fails then passes on retry within the same commit is the textbook definition of a flaky test."]
                        ),
                        make_problem(
                            problem_id="rep-prob-3",
                            title="Automated Defect Filing Integration with GitHub / Jira APIs",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Automatically file rich defect tickets with system logs, reproduction steps, and stack traces upon test failure in CI.",
                            problem_statement="Develop a CI post-test webhook service. When scheduled nightly regression tests fail on the main branch, check if an open issue already exists for that test ID; if not, call GitHub Issues / Jira API to file a new bug ticket containing: failing test name, error message, stack trace, commit SHA, link to CI run, and attached failure screenshot.",
                            requirements=[
                                "Query issue tracker API to deduplicate against existing open tickets.",
                                "Format markdown issue body with reproduction steps, stack trace, and environment info.",
                                "Attach failure screenshot and video artifacts directly to the ticket.",
                                "Assign appropriate severity label based on the test's Allure severity annotation."
                            ],
                            concepts_tested=["Issue Tracker API Integration", "Defect Deduplication Logic", "Automated Bug Triage", "Reproduction Artifact Packaging"],
                            expected_outcome="A seamless defect triage bridge connecting automated CI failures to developer backlog tickets.",
                            optional_hints=["Search by unique test method identifier in issue title to prevent filing duplicate tickets for the same bug."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

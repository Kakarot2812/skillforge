"""Full Stack Engineer roadmap definition with progressive practice problems and market demand integration."""
from typing import Any, Dict
from app.db.roadmaps_data.common import CANONICAL_ROLE_IDS, ROADMAP_IDS, make_problem, make_skill

FULLSTACK_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["full-stack-engineer"],
    "slug": "full-stack-engineer",
    "role_id": CANONICAL_ROLE_IDS["full-stack-engineer"],
    "title": "Full Stack Engineer",
    "domain": "Full Stack Engineering",
    "category": "Engineering",
    "description": "Master end-to-end web engineering: frontend interfaces (React, TypeScript, Next.js, Tailwind), backend services (Node.js, REST APIs), relational databases (PostgreSQL), in-memory caching (Redis), authentication, and containerized deployment (Docker, CI/CD).",
    "version": "v2.0",
    "has_market_data": True,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Web Foundations",
            "description": "Master the core client-side technologies of the browser platform.",
            "skills": [
                make_skill(
                    slug="html-fs",
                    name="HTML",
                    canonical_slug="html",
                    difficulty="BEGINNER",
                    description="Standard markup language of the web: semantic structure, accessible forms, tables, and document hierarchy.",
                    key_topics=["Semantic Document Outline (header, main, footer)", "Form Controls (inputs, labels, select, textarea)", "Document Hierarchy & Headings", "Multimedia (img, picture)"],
                    role_relevance="The foundation of all web rendering and screen reader accessibility.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MDN HTML Documentation", "url": "https://developer.mozilla.org/en-US/docs/Web/HTML", "description": "Official guides and reference for semantic HTML elements and forms."},
                        {"type": "YOUTUBE", "title": "HTML Crash Course — Traversy Media", "url": "https://www.youtube.com/watch?v=UB1O30fR-EE", "description": "Concise overview of HTML elements, forms, and semantic document structures."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="html-fs-prob-1",
                            title="Semantic User Profile Document",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build a semantic HTML document with header, main, and sections.",
                            problem_statement="Author a valid HTML5 page containing user information, heading hierarchy, and descriptive metadata.",
                            requirements=[
                                "Use <!DOCTYPE html> with proper head meta tags.",
                                "Include semantic landmarks: header, main, section, and footer.",
                                "Include an accessible image with alt text."
                            ],
                            concepts_tested=["semantic HTML", "headings", "paragraphs", "images", "alt text", "metadata"],
                            expected_outcome="A clean, accessible semantic document outline verified with an HTML outliner.",
                            optional_hints=["Use meaningful text inside alt attributes for accessibility."]
                        ),
                        make_problem(
                            problem_id="html-fs-prob-2",
                            title="Full-Stack Feedback & Survey Form",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Construct an accessible form with inputs, select dropdown, and validation attributes.",
                            problem_statement="Build an accessible feedback form ready for submission to a backend POST endpoint.",
                            requirements=[
                                "Include text, email, number, select, and textarea fields.",
                                "Associate all inputs with explicit labels using 'for' and 'id'.",
                                "Use fieldset and legend to group related contact fields."
                            ],
                            concepts_tested=["forms", "labels", "inputs", "select", "textarea", "fieldset & legend", "accessibility basics"],
                            expected_outcome="An accessible form that can submit FormData to backend endpoints.",
                            optional_hints=["Use type='email' for native browser format validation."]
                        ),
                        make_problem(
                            problem_id="html-fs-prob-3",
                            title="Complete Accessible Portal Layout",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Author a full-featured accessible portal with tables, media, and navigation landmarks.",
                            problem_statement="Build an accessible web application shell with navigation, data tables, video tutorial, and contact form.",
                            requirements=[
                                "Incorporate nav, article, aside, and main semantic elements.",
                                "Build a data table with thead, th scope='col', and summary captions.",
                                "Embed accessible media with fallback captions."
                            ],
                            concepts_tested=["semantic HTML", "tables", "media", "landmarks (nav, aside)", "accessibility WCAG", "forms"],
                            expected_outcome="A production-ready HTML structure with 100% lighthouse accessibility compliance.",
                            optional_hints=["Always provide table headers with scope='col' or scope='row'."]
                        ),
                    ],
                ),
                make_skill(
                    slug="css-fs",
                    name="CSS",
                    canonical_slug="css",
                    difficulty="BEGINNER",
                    description="Cascading Style Sheets: Box model, Flexbox layout, CSS Grid, media queries, and CSS variables.",
                    key_topics=["Box Model & box-sizing", "Flexbox 1D Alignment & Distribution", "CSS Grid 2D Positioning", "CSS Custom Properties (Variables)", "Responsive Media Queries"],
                    role_relevance="Essential for structuring responsive web layouts that work flawlessly across desktop, tablet, and mobile screens.",
                    prerequisites=["html-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MDN CSS Documentation", "url": "https://developer.mozilla.org/en-US/docs/Web/CSS", "description": "Complete CSS reference, selectors, flexbox, and grid layout guides."},
                        {"type": "YOUTUBE", "title": "CSS Crash Course — Kevin Powell", "url": "https://www.youtube.com/watch?v=1PnVor36_40", "description": "Comprehensive practical guide to modern responsive CSS layouts."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="css-fs-prob-1",
                            title="Flexbox Navigation & Card Component",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Style a responsive navigation header and product card using Flexbox.",
                            problem_statement="Build a flexible navigation bar and a product card using display: flex, justify-content, and align-items.",
                            requirements=[
                                "Use 'box-sizing: border-box' globally and configure root color variables.",
                                "Align navigation brand and links using space-between and gap.",
                                "Style card container with padding, borders, and hover elevation."
                            ],
                            concepts_tested=["Box Model", "Flexbox", "justify-content & align-items", "CSS Variables", "Hover Effects"],
                            expected_outcome="A clean, responsive header and card component with fluid spacing.",
                            optional_hints=["Use 'gap' in flexbox to avoid manual margin calculations."]
                        ),
                        make_problem(
                            problem_id="css-fs-prob-2",
                            title="Responsive Application Dashboard Grid",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Construct a multi-area dashboard using CSS Grid and responsive breakpoints.",
                            problem_statement="Build an application dashboard with header, sidebar, main analytics panels, and footer using CSS Grid.",
                            requirements=[
                                "Define grid-template-areas for desktop and collapse to single column on mobile.",
                                "Use auto-fit and minmax(200px, 1fr) for dynamic analytics stat tiles.",
                                "Incorporate responsive media queries at 768px and 1024px."
                            ],
                            concepts_tested=["CSS Grid", "grid-template-areas", "minmax()", "Media Queries", "Responsive Layout"],
                            expected_outcome="An adaptive dashboard layout scaling smoothly across device widths.",
                            optional_hints=["minmax with auto-fit automatically handles responsive wrapping without media queries."]
                        ),
                        make_problem(
                            problem_id="css-fs-prob-3",
                            title="Themeable Design System with Dark Mode",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement an enterprise CSS token system with light and dark mode support.",
                            problem_statement="Create a theme system using CSS custom properties with automatic prefers-color-scheme and manual toggle overrides.",
                            requirements=[
                                "Define semantic color tokens (--bg-primary, --text-primary) on :root and [data-theme='dark'].",
                                "Incorporate @media (prefers-color-scheme: dark) default styling.",
                                "Include visible :focus-visible indicators for all interactive elements."
                            ],
                            concepts_tested=["CSS Custom Properties", "prefers-color-scheme", "Dark Mode Toggling", "Accessible Focus (:focus-visible)"],
                            expected_outcome="A themeable stylesheet supporting instant light/dark theme switching and accessible focus states.",
                            optional_hints=["Use custom properties on :root for global token distribution."]
                        ),
                    ],
                ),
                make_skill(
                    slug="javascript-fs",
                    name="JavaScript",
                    canonical_slug="javascript",
                    difficulty="BEGINNER",
                    description="Core ECMAScript programming: Closures, prototypes, array methods, DOM APIs, async/await, and Fetch API.",
                    key_topics=["ES6+ Syntax & Scope", "Array Manipulation (map, filter, reduce)", "DOM Manipulation & Event Bubbling", "Promises & async/await", "Fetch API & JSON Serialization"],
                    role_relevance="The universal runtime language shared across both client-side browser interfaces and server-side Node.js backends.",
                    prerequisites=["html-fs", "css-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MDN JavaScript Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "description": "The definitive guide to JavaScript language features and asynchronous programming."},
                        {"type": "YOUTUBE", "title": "JavaScript Tutorial for Beginners — Programming with Mosh", "url": "https://www.youtube.com/watch?v=W6NZfCO5SIk", "description": "Clear, practical introduction to JavaScript variables, functions, and control flow."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="js-fs-prob-1",
                            title="Interactive Data Filter with Array Methods",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Process and filter datasets using map, filter, and reduce.",
                            problem_statement="Write functions to filter an array of products by category, apply discounts with map, and compute total value with reduce.",
                            requirements=[
                                "Filter products with price > 20 using Array.prototype.filter.",
                                "Transform products into display strings using Array.prototype.map.",
                                "Calculate grand total cost using Array.prototype.reduce."
                            ],
                            concepts_tested=["Array Methods (map, filter, reduce)", "Arrow Functions", "Array Destructuring"],
                            expected_outcome="Clean functional data transformations producing exact calculated values.",
                            optional_hints=["Pass an initial accumulator value (0) to reduce."]
                        ),
                        make_problem(
                            problem_id="js-fs-prob-2",
                            title="Async Data Fetcher with DOM Rendering",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Fetch remote data asynchronously and render dynamic cards into the DOM.",
                            problem_statement="Build a client-side script that fetches users from a REST endpoint and renders user cards with loading and error handling.",
                            requirements=[
                                "Use async/await with fetch() and check response.ok.",
                                "Display a loading spinner while the request is in flight.",
                                "Render formatted card elements into the DOM and catch network errors with a user-friendly message."
                            ],
                            concepts_tested=["async/await", "Fetch API", "DOM Manipulation", "Error Handling (try-catch)", "Template Strings"],
                            expected_outcome="A robust frontend data widget handling success, loading, and error states gracefully.",
                            optional_hints=["Always check 'if (!response.ok)' because fetch does not reject on 404 or 500 status codes."]
                        ),
                        make_problem(
                            problem_id="js-fs-prob-3",
                            title="Event-Driven Client-Server WebSocket Client",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a resilient WebSocket client with automatic reconnection and heartbeat ping/pong.",
                            problem_statement="Implement a real-time messaging client using the browser WebSocket API that handles disconnections and reconnects automatically.",
                            requirements=[
                                "Create a RealtimeClient class wrapping new WebSocket(url).",
                                "Implement exponential backoff reconnection when onclose is triggered.",
                                "Send periodic ping heartbeats to maintain active connection and dispatch incoming messages to listener callbacks."
                            ],
                            concepts_tested=["WebSocket API", "Event Handlers (onopen, onmessage, onclose)", "Exponential Backoff Reconnection", "Heartbeat Ping/Pong", "Class Design"],
                            expected_outcome="A production-grade WebSocket client maintaining a live duplex connection across network interruptions.",
                            optional_hints=["Cap the maximum reconnect delay (e.g. 30 seconds) to prevent infinite backoff."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Modern Frontend & Typing",
            "description": "Build strongly-typed, component-driven client applications with TypeScript, Tailwind CSS, React, and Next.js.",
            "skills": [
                make_skill(
                    slug="typescript-fs",
                    name="TypeScript",
                    canonical_slug="typescript",
                    difficulty="BEGINNER",
                    description="Static typing for JavaScript: Interfaces, Generics, Union types, and type sharing between frontend and backend.",
                    key_topics=["Type Annotations & Type Inference", "Interfaces & Type Aliases", "Generics & Generic Functions", "Shared Full-Stack Type Contracts", "Utility Types (Partial, Pick, Omit)"],
                    role_relevance="Allows full-stack developers to share data contracts and models end-to-end between client and server.",
                    prerequisites=["javascript-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "TypeScript Handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "description": "The official handbook covering basic types, interfaces, and generics."},
                        {"type": "YOUTUBE", "title": "TypeScript Tutorial — Jack Herrington", "url": "https://www.youtube.com/watch?v=bc5uhfv5wYg", "description": "Practical TypeScript course covering real-world application typing and generics."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="ts-fs-prob-1",
                            title="Strongly-Typed Domain Models",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Define interfaces and types for a full-stack user and order model.",
                            problem_statement="Create type definitions for User, Order, and OrderStatus supporting discriminated union states.",
                            requirements=[
                                "Define User interface with id, email, role ('admin' | 'user'), and optional phone.",
                                "Define OrderStatus as a union: 'pending' | 'processing' | 'shipped' | 'cancelled'.",
                                "Write a function formatOrderSummary(order: Order): string with type annotations."
                            ],
                            concepts_tested=["Interfaces", "Union Types", "Type Aliases", "Function Signatures"],
                            expected_outcome="Compile-time verified models preventing typo bugs across the application.",
                            optional_hints=["Use string literal unions instead of enums for cleaner JavaScript output."]
                        ),
                        make_problem(
                            problem_id="ts-fs-prob-2",
                            title="Shared Full-Stack API Contract",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Share DTO interfaces between frontend client and backend API.",
                            problem_statement="Build a shared type contract module used by both Next.js frontend and backend API handlers.",
                            requirements=[
                                "Define CreateUserDTO using Omit<User, 'id' | 'createdAt'>.",
                                "Define UpdateUserDTO using Partial<CreateUserDTO>.",
                                "Create a generic ApiResponse<T> wrapper with success boolean and data/error payloads."
                            ],
                            concepts_tested=["Shared DTOs", "Utility Types (Omit, Partial)", "Generic Wrappers (ApiResponse<T>)", "Type Sharing"],
                            expected_outcome="Guaranteed contract alignment between client requests and server responses.",
                            optional_hints=["Organize shared types in a shared/types directory or npm package."]
                        ),
                        make_problem(
                            problem_id="ts-fs-prob-3",
                            title="Generic Database Query Mapper with Keyof",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement an advanced typed query filter using keyof and mapped types.",
                            problem_statement="Build a type-safe filter builder that validates allowed sort fields and filter criteria against an entity interface.",
                            requirements=[
                                "Define QueryFilter<T> where allowed filter keys are keyof T.",
                                "Implement a buildQuery<T>(entity: T, filter: QueryFilter<T>) function.",
                                "Verify that filtering by a nonexistent property triggers a compile-time TypeScript error."
                            ],
                            concepts_tested=["keyof Operator", "Mapped Types", "Generic Constraints", "Type-safe Query Builders"],
                            expected_outcome="A completely type-safe query abstraction eliminating runtime column name bugs.",
                            optional_hints=["Use 'keyof T' to restrict allowed property names to valid entity fields."]
                        ),
                    ],
                ),
                make_skill(
                    slug="tailwindcss-fs",
                    name="Tailwind CSS",
                    canonical_slug="tailwindcss",
                    difficulty="BEGINNER",
                    description="Utility-first CSS styling: Atomic classes, responsive layouts, dark mode, and UI component composition.",
                    key_topics=["Atomic Utility Classes", "Responsive Modifiers (sm:, md:, lg:)", "Dark Mode Variants (dark:)", "Component Composition with clsx / tailwind-merge"],
                    role_relevance="Enables rapid UI prototyping and consistent styling across full-stack applications.",
                    prerequisites=["css-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Tailwind CSS Official Docs", "url": "https://tailwindcss.com/docs", "description": "Complete guide to Tailwind utilities, configuration, and responsive design."},
                        {"type": "YOUTUBE", "title": "Tailwind CSS Crash Course — Traversy Media", "url": "https://www.youtube.com/watch?v=dFgzHOX84xQ", "description": "Quick tutorial on setting up and styling projects with Tailwind utility classes."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="tw-fs-prob-1",
                            title="Responsive Hero Section",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Style a responsive landing page hero section using Tailwind utilities.",
                            problem_statement="Build a hero section with title, subtitle, CTA buttons, and responsive layout.",
                            requirements=[
                                "Use flex and flex-col md:flex-row to arrange content.",
                                "Style CTA buttons with transition-all, hover:scale-105, and shadow-md.",
                                "Incorporate responsive typography with text-3xl md:text-5xl."
                            ],
                            concepts_tested=["Flexbox Utilities", "Responsive Prefixes (md:)", "Hover State Modifiers", "Typography Utilities"],
                            expected_outcome="A modern, high-converting hero banner that adapts fluidly across device widths.",
                            optional_hints=["Use 'max-w-6xl mx-auto px-4' to center container content."]
                        ),
                        make_problem(
                            problem_id="tw-fs-prob-2",
                            title="Interactive Data Table with Dark Mode",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Style an enterprise data table with zebra striping, status badges, and dark mode.",
                            problem_statement="Build an administrative user table with dark mode variants and status indicator badges.",
                            requirements=[
                                "Apply alternating background colors (even:bg-neutral-50 dark:even:bg-neutral-800).",
                                "Style status badges with rounded-full, px-2.5, py-0.5, and colored borders.",
                                "Incorporate dark: modifiers across all text and background classes."
                            ],
                            concepts_tested=["Pseudo-class Modifiers (even:)", "Dark Mode (dark:)", "Table Styling", "Badge Component Styling"],
                            expected_outcome="A polished administrative table supporting both light and dark mode viewing.",
                            optional_hints=["Wrap table in 'overflow-x-auto' for horizontal scrolling on mobile."]
                        ),
                        make_problem(
                            problem_id="tw-fs-prob-3",
                            title="Polished Accessible Modal Dialog Component",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Style a modal overlay with backdrop blur, entrance animations, and responsive dialog dimensions.",
                            problem_statement="Build a reusable modal dialog using Tailwind utilities with smooth backdrop and card entrance transitions.",
                            requirements=[
                                "Style overlay with fixed inset-0, bg-black/60, and backdrop-blur-sm.",
                                "Center the dialog container with max-w-lg, w-full, p-6, and rounded-2xl.",
                                "Add subtle keyframe or transition animations for dialog entrance."
                            ],
                            concepts_tested=["Fixed Positioning", "Backdrop Blur Utilities", "Dialog Centering", "Transitions & Opacity", "Accessible Focus States"],
                            expected_outcome="A sleek, modern modal dialog that elevates above page content seamlessly.",
                            optional_hints=["Use 'z-50' to ensure modal stays above all navigation bars."]
                        ),
                    ],
                ),
                make_skill(
                    slug="react-fs",
                    name="React",
                    canonical_slug="react",
                    difficulty="INTERMEDIATE",
                    description="Component architecture: Hooks (useState, useEffect, useMemo, useCallback), Custom Hooks, and Context API.",
                    key_topics=["Component Lifecycle & JSX", "Hooks (useState, useEffect)", "Custom Hooks Abstraction", "Performance Optimization (useMemo, useCallback)", "Forms & Controlled Components"],
                    role_relevance="The standard UI library powering modern full-stack web applications.",
                    prerequisites=["javascript-fs", "typescript-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "React Official Docs (react.dev)", "url": "https://react.dev/", "description": "The official documentation covering components, hooks, and state management."},
                        {"type": "YOUTUBE", "title": "React Course for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=bMknfKXIFA8", "description": "Full tutorial on React fundamentals, hooks, and building full-stack projects."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="react-fs-prob-1",
                            title="Controlled Form with Real-Time Validation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Manage controlled inputs and display validation feedback in React.",
                            problem_statement="Build a user registration form with controlled inputs, validating password strength and email format as the user types.",
                            requirements=[
                                "Use useState to track form values and validation error messages.",
                                "Validate input on change and display inline error messages.",
                                "Disable submit button when form inputs are invalid."
                            ],
                            concepts_tested=["useState", "Controlled Components", "Form Handling", "Inline Validation"],
                            expected_outcome="A reactive form providing instantaneous user feedback before submission.",
                            optional_hints=["Derive formIsValid from error states rather than storing another state variable."]
                        ),
                        make_problem(
                            problem_id="react-fs-prob-2",
                            title="Custom useLocalStorage Hook with Sync",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Extract reusable state persistence logic into a custom hook.",
                            problem_statement="Build a useLocalStorage<T>(key, initialValue) hook that synchronizes component state with window.localStorage.",
                            requirements=[
                                "Return [value, setValue] matching the standard useState API.",
                                "Catch JSON parsing errors gracefully and fall back to initialValue.",
                                "Listen to window 'storage' events to synchronize state across multiple open tabs."
                            ],
                            concepts_tested=["Custom Hooks", "useEffect", "localStorage API", "Cross-Tab Synchronization", "Generics in React"],
                            expected_outcome="A plug-and-play hook providing persistent reactive state across page refreshes and browser tabs.",
                            optional_hints=["Use lazy state initialization: useState(() => readFromLocalStorage())."]
                        ),
                        make_problem(
                            problem_id="react-fs-prob-3",
                            title="Full-Stack Data Grid with Sorting & Selection",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a complex data table with column sorting, row multi-selection, and memoized computation.",
                            problem_statement="Build a high-performance data table component handling sorting, filtering, and bulk action checkboxes.",
                            requirements=[
                                "Use useMemo to memoize sorted and filtered dataset results.",
                                "Manage multi-row selection with a Set<string> in state.",
                                "Use useCallback for row action handlers to prevent child re-renders."
                            ],
                            concepts_tested=["useMemo", "useCallback", "Set Data Structure in State", "Performance Optimization", "Bulk Actions"],
                            expected_outcome="A snappy data table maintaining 60fps rendering even with hundreds of rows.",
                            optional_hints=["Store selected IDs in a Set for O(1) membership lookups."]
                        ),
                    ],
                ),
                make_skill(
                    slug="nextjs-fs",
                    name="Next.js",
                    canonical_slug="nextjs",
                    difficulty="ADVANCED",
                    description="Full-stack React framework: App Router, React Server Components (RSC), Server Actions, Dynamic Routes, and Route Handlers.",
                    key_topics=["App Router Layouts & Pages", "Server Components vs Client Components", "Server Actions for Mutations", "Dynamic Routing ([id])", "Route Handlers (api/)"],
                    role_relevance="The flagship framework unifying frontend UI rendering and server-side backend logic into a single cohesive repository.",
                    prerequisites=["react-fs", "typescript-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Next.js Official Documentation", "url": "https://nextjs.org/docs", "description": "Official guides for Next.js App Router, Server Components, and Server Actions."},
                        {"type": "YOUTUBE", "title": "Next.js Full Course — Traversy Media", "url": "https://www.youtube.com/watch?v=wm5gMKuwSYk", "description": "Project-based course building complete full-stack web applications with Next.js App Router."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="nextjs-fs-prob-1",
                            title="Server Component Dashboard",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Fetch data directly in a React Server Component and render a dashboard.",
                            problem_statement="Build a dashboard page using React Server Components that fetches data from an API on the server.",
                            requirements=[
                                "Fetch data inside an async Server Component without client-side useEffect.",
                                "Render stats cards and recent activity list.",
                                "Configure dynamic metadata for SEO page titles."
                            ],
                            concepts_tested=["React Server Components (RSC)", "Server-side Data Fetching", "Dynamic Metadata", "Zero-JS Client Bundle"],
                            expected_outcome="Instant server-rendered HTML delivered to the browser with zero client-side fetch waterfalls.",
                            optional_hints=["Server Components can directly query databases or remote services."]
                        ),
                        make_problem(
                            problem_id="nextjs-fs-prob-2",
                            title="Full-Stack Form with Server Actions",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Execute database mutations using Next.js Server Actions with revalidatePath.",
                            problem_statement="Build a task creation form submitting data via a Server Action, validating with Zod and revalidating the page cache.",
                            requirements=[
                                "Define a Server Action marked with 'use server'.",
                                "Validate input fields using Zod and insert into database.",
                                "Call revalidatePath('/dashboard') to update cached UI instantly."
                            ],
                            concepts_tested=["Server Actions ('use server')", "revalidatePath", "Zod Validation", "Form Submission"],
                            expected_outcome="A seamless full-stack mutation flow eliminating the need for manual client fetch boilerplate.",
                            optional_hints=["Use useFormStatus in child components to show a submitting spinner."]
                        ),
                        make_problem(
                            problem_id="nextjs-fs-prob-3",
                            title="Edge Middleware Route Protection & Session Cookie Auth",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Protect private routes at the edge using Next.js Middleware and session cookies.",
                            problem_statement="Implement middleware.ts that inspects auth session cookies, redirecting unauthenticated users to /login.",
                            requirements=[
                                "Check for 'auth-token' session cookie in NextRequest.",
                                "Redirect unauthenticated users to /login with redirect URL param.",
                                "Allow public assets and public routes to bypass middleware using matcher configuration."
                            ],
                            concepts_tested=["Next.js Middleware", "Edge Runtime", "Cookie Inspection", "NextResponse.redirect", "Route Matchers"],
                            expected_outcome="Sub-millisecond route protection running at the edge before server components render.",
                            optional_hints=["Configure config = { matcher: ['/dashboard/:path*'] } to restrict execution scope."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Full-Stack Backend & Server Architecture",
            "description": "Design resilient server architectures, REST APIs, and full-stack authentication workflows.",
            "skills": [
                make_skill(
                    slug="nodejs-fs",
                    name="Node.js",
                    canonical_slug="nodejs",
                    difficulty="INTERMEDIATE",
                    description="Server-side JavaScript runtime: Event loop, asynchronous non-blocking I/O, File system, Express/Fastify frameworks, and process management.",
                    key_topics=["Event Loop & Asynchronous Architecture", "File System (fs/promises) & Streams", "HTTP Servers with Express / Fastify", "Environment Configuration (process.env)", "Error Handling Middleware"],
                    role_relevance="Enables JavaScript/TypeScript developers to build high-concurrency backend services and API backbones.",
                    prerequisites=["javascript-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Node.js Official Documentation", "url": "https://nodejs.org/en/docs/", "description": "Official documentation for Node.js APIs, event loop, and modules."},
                        {"type": "YOUTUBE", "title": "Node.js Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=Oe421EPjeBE", "description": "Complete tutorial on Node.js fundamentals, asynchronous architecture, and Express."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="node-fs-prob-1",
                            title="File Processing Script with Async Streams",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Read and write large files using Node.js fs/promises and streams.",
                            problem_statement="Build a CLI utility in Node.js that reads a CSV file, parses lines, and writes a filtered JSON output file.",
                            requirements=[
                                "Use fs/promises for asynchronous non-blocking file operations.",
                                "Parse comma-separated values into JavaScript objects.",
                                "Handle file read errors gracefully with try-catch."
                            ],
                            concepts_tested=["fs/promises", "Asynchronous I/O", "JSON Serialization", "Error Handling"],
                            expected_outcome="A fast, non-blocking file processing script.",
                            optional_hints=["Use stream.pipeline for massive multi-gigabyte files to avoid memory exhaustion."]
                        ),
                        make_problem(
                            problem_id="node-fs-prob-2",
                            title="Modular Express API with Middleware",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Structure a modular REST API using Express routers and custom middleware.",
                            problem_statement="Build an Express API with authentication middleware, request logging, and structured error handlers.",
                            requirements=[
                                "Use express.Router() to modularize /api/users and /api/orders routes.",
                                "Create an authentication middleware verifying Authorization Bearer tokens.",
                                "Implement a centralized error handling middleware (err, req, res, next)."
                            ],
                            concepts_tested=["Express Routers", "Custom Middleware", "Centralized Error Handling", "HTTP Headers"],
                            expected_outcome="A well-architected Express API where cross-cutting concerns are cleanly separated.",
                            optional_hints=["Error handling middleware in Express must accept exactly 4 arguments: (err, req, res, next)."]
                        ),
                        make_problem(
                            problem_id="node-fs-prob-3",
                            title="Graceful Shutdown & Connection Pool Manager",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Handle process signals (SIGTERM, SIGINT) and close database connections cleanly.",
                            problem_statement="Build a production Node.js server lifecycle manager that intercepts termination signals, stops accepting requests, finishes in-flight requests, and closes database connections.",
                            requirements=[
                                "Listen for process.on('SIGTERM') and process.on('SIGINT').",
                                "Call server.close() to reject new connections while finishing active requests.",
                                "Close database connection pools and exit with code 0 within a 10-second timeout window."
                            ],
                            concepts_tested=["Process Signals (SIGTERM, SIGINT)", "Graceful Server Shutdown", "Connection Pool Teardown", "Process Management"],
                            expected_outcome="Zero dropped requests during container deployments or server restarts.",
                            optional_hints=["Use setTimeout in the shutdown handler to force exit (process.exit(1)) if cleanup hangs."]
                        ),
                    ],
                ),
                make_skill(
                    slug="rest-apis-fs",
                    name="REST APIs",
                    canonical_slug="rest-apis",
                    difficulty="BEGINNER",
                    description="Designing robust HTTP interfaces: Verbs, status codes, query parameters, pagination, and error responses.",
                    key_topics=["HTTP Methods & Semantics", "Status Codes & Error Envelopes", "Pagination (Offset & Cursor)", "Idempotency & Safe Methods"],
                    role_relevance="The universal communication bridge connecting frontend clients to backend server services.",
                    prerequisites=["nodejs-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MDN HTTP & REST Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP", "description": "Complete documentation on HTTP methods, headers, and status codes."},
                        {"type": "YOUTUBE", "title": "REST APIs in 100 Seconds — Fireship", "url": "https://www.youtube.com/watch?v=-mN3VyJuCjM", "description": "Concise overview of REST architectural principles and conventions."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="rest-fs-prob-1",
                            title="Resource Endpoint Design",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Map business operations to RESTful HTTP verbs and status codes.",
                            problem_statement="Design endpoints for a blog application: articles, comments, and tags.",
                            requirements=[
                                "Map CRUD actions to GET, POST, PUT, PATCH, DELETE.",
                                "Assign appropriate status codes (200, 201, 204, 400, 404).",
                                "Specify consistent JSON response structures."
                            ],
                            concepts_tested=["HTTP Verbs", "HTTP Status Codes", "RESTful URIs", "JSON Formatting"],
                            expected_outcome="A consistent API specification following industry REST conventions.",
                            optional_hints=["Use plural nouns for resource paths (e.g. /articles, /users)."]
                        ),
                        make_problem(
                            problem_id="rest-fs-prob-2",
                            title="Paginated API Endpoint with Filtering",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an endpoint supporting pagination, search, and sorting query parameters.",
                            problem_statement="Build an endpoint GET /api/products?page=1&limit=20&search=shoes&sort=price_desc.",
                            requirements=[
                                "Parse and validate query parameters with default fallbacks.",
                                "Return metadata envelope with total, page, limit, and totalPages.",
                                "Enforce maximum limit caps to defend against excessive queries."
                            ],
                            concepts_tested=["Query Parameters", "Pagination Envelopes", "Defensive Limits", "Sorting & Searching"],
                            expected_outcome="A paginated API endpoint delivering fast, bounded query responses.",
                            optional_hints=["Always cap limit: Math.min(Number(limit) || 20, 100)."]
                        ),
                        make_problem(
                            problem_id="rest-fs-prob-3",
                            title="Idempotent Payment API with Idempotency-Key Header",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Guarantee idempotency for financial mutations using unique request keys.",
                            problem_statement="Implement POST /api/payments supporting 'Idempotency-Key' header, preventing duplicate credit card charges on network retries.",
                            requirements=[
                                "Check Redis for incoming Idempotency-Key header value.",
                                "If key exists, return the cached previous response immediately without charging again.",
                                "If key is new, acquire lock, process payment, cache response in Redis, and return."
                            ],
                            concepts_tested=["Idempotent Mutations", "Idempotency-Key Headers", "Atomic Locking", "Deduplication"],
                            expected_outcome="Guaranteed single-charge processing even when clients retry requests multiple times.",
                            optional_hints=["Store idempotency key with a 24-hour TTL in Redis."]
                        ),
                    ],
                ),
                make_skill(
                    slug="fullstack-auth",
                    name="Full-Stack Authentication & Security (NextAuth, JWT, Sessions)",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="End-to-end user authentication: Auth.js / NextAuth, JWT session cookies, OAuth social logins, password hashing, and CSRF protection.",
                    key_topics=["Auth.js / NextAuth Setup", "JWT vs Database Sessions", "OAuth Providers (Google, GitHub)", "Secure HTTP-Only Cookies & CSRF Protection", "Protecting Server Actions and API Routes"],
                    role_relevance="Secures user data, manages identity verification, and prevents account takeover attacks.",
                    prerequisites=["nextjs-fs", "nodejs-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Auth.js (NextAuth) Documentation", "url": "https://authjs.dev/", "description": "Official guides for authentication in Next.js and full-stack applications."},
                        {"type": "YOUTUBE", "title": "Next.js Authentication with Auth.js — Dave Gray", "url": "https://www.youtube.com/watch?v=b4OHTaWep5Y", "description": "Step-by-step tutorial implementing authentication, session cookies, and route guards."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="auth-fs-prob-1",
                            title="OAuth Login with Auth.js (NextAuth)",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Integrate GitHub OAuth authentication using Auth.js in Next.js.",
                            problem_statement="Configure Auth.js with GitHub Provider, rendering login/logout buttons and displaying the authenticated user's avatar.",
                            requirements=[
                                "Set up auth.ts with NextAuth and GitHub Provider credentials.",
                                "Create a SignIn component and SignOut component using server actions or signIn/signOut handlers.",
                                "Display user profile information when authenticated."
                            ],
                            concepts_tested=["Auth.js / NextAuth", "OAuth Providers", "Session Retrieval (auth())", "Conditional UI Rendering"],
                            expected_outcome="A functioning OAuth login flow redirecting back with active session cookies.",
                            optional_hints=["Set AUTH_SECRET environment variable in .env.local."]
                        ),
                        make_problem(
                            problem_id="auth-fs-prob-2",
                            title="Credentials Login with Password Hashing",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement email/password authentication with bcrypt verification and JWT session tokens.",
                            problem_statement="Build a credentials login system that queries a database, verifies passwords using bcrypt, and issues secure session cookies.",
                            requirements=[
                                "Configure CredentialsProvider validating user email and password against database.",
                                "Verify passwords using bcrypt.compare.",
                                "Store user ID and role in JWT session callback.",
                                "Enforce httpOnly, secure, and sameSite='lax' cookie attributes."
                            ],
                            concepts_tested=["CredentialsProvider", "Password Verification (bcrypt)", "JWT Session Callbacks", "Secure Cookies (httpOnly, sameSite)"],
                            expected_outcome="A secure username/password login flow that stores sessions in tamper-proof JWT cookies.",
                            optional_hints=["Never expose password hashes in JWT callbacks or frontend session objects."]
                        ),
                        make_problem(
                            problem_id="auth-fs-prob-3",
                            title="Multi-Tenant Role-Based Route & Action Guard",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Enforce multi-tenant role authorization across Server Actions, API routes, and page renders.",
                            problem_statement="Build a reusable authorization utility that verifies the user has the required role (e.g. 'admin') before executing Server Actions or rendering admin pages.",
                            requirements=[
                                "Create a requireAuth(requiredRole) helper function.",
                                "Protect Server Actions, throwing an error or returning { error: 'Unauthorized' } if role check fails.",
                                "Ensure tenant isolation so users can only view and mutate data belonging to their organization."
                            ],
                            concepts_tested=["Role-Based Access Control (RBAC)", "Server Action Authorization", "Tenant Isolation", "Security Auditing"],
                            expected_outcome="A unified authorization layer preventing cross-tenant data leaks and unauthorized actions.",
                            optional_hints=["Always check session and permissions on the server inside Server Actions; never rely solely on client UI hiding."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Persistence & Caching",
            "description": "Store persistent relational data and high-speed in-memory caches.",
            "skills": [
                make_skill(
                    slug="postgresql-fs",
                    name="PostgreSQL",
                    canonical_slug="postgresql",
                    difficulty="INTERMEDIATE",
                    description="Relational database: Schema modeling, foreign keys, indexes, transactions, and Prisma/Drizzle ORM integration.",
                    key_topics=["Relational Schema Design & Foreign Keys", "Indexes & Query Optimization", "ACID Transactions", "ORM Integration (Prisma / Drizzle)", "JSONB Document Columns"],
                    role_relevance="The premier database engine for storing transactional, business-critical application data.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PostgreSQL Documentation", "url": "https://www.postgresql.org/docs/", "description": "Official reference for PostgreSQL database administration, SQL, and indexing."},
                        {"type": "YOUTUBE", "title": "PostgreSQL Tutorial for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=qw--VYLpxG4", "description": "Comprehensive tutorial on schema design, tables, joins, and indexing."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="pg-fs-prob-1",
                            title="Relational Schema with Foreign Keys",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Design normalized tables with primary keys and foreign key constraints.",
                            problem_statement="Create a relational schema for users and orders with foreign keys, cascading deletes, and timestamps.",
                            requirements=[
                                "Create users table with UUID primary key and unique email.",
                                "Create orders table with foreign key references users(id) ON DELETE CASCADE.",
                                "Add created_at and updated_at timestamp columns with default now()."
                            ],
                            concepts_tested=["DDL Tables", "Foreign Keys", "CASCADE Deletion", "UUID Primary Keys"],
                            expected_outcome="A normalized database schema enforcing referential integrity.",
                            optional_hints=["Use gen_random_uuid() for UUID generation in modern Postgres."]
                        ),
                        make_problem(
                            problem_id="pg-fs-prob-2",
                            title="Prisma / Drizzle ORM Data Access Layer",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Interact with PostgreSQL using a modern TypeScript ORM (Prisma or Drizzle).",
                            problem_statement="Define schema models and implement CRUD functions using Prisma or Drizzle ORM.",
                            requirements=[
                                "Define User and Post models with 1-to-many relationship.",
                                "Execute relational queries using include or with (e.g. prisma.user.findMany({ include: { posts: true } })).",
                                "Handle unique constraint violation errors gracefully."
                            ],
                            concepts_tested=["Prisma / Drizzle ORM", "Type-safe Database Queries", "Relational Eager Loading", "Error Handling"],
                            expected_outcome="Type-safe database interactions with zero manual SQL string concatenation.",
                            optional_hints=["Use prisma.$transaction for multi-statement atomic operations."]
                        ),
                        make_problem(
                            problem_id="pg-fs-prob-3",
                            title="Optimistic Concurrency & Inventory Reservation",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Prevent inventory double-booking using database transactions and row locking.",
                            problem_statement="Implement an inventory reservation transaction that prevents race conditions when multiple users buy the last available item simultaneously.",
                            requirements=[
                                "Begin a transaction.",
                                "Acquire lock on product row using SELECT ... FOR UPDATE.",
                                "Verify stock > 0, decrement stock, insert order row, and commit transaction.",
                                "Simulate concurrent checkout requests and verify no overselling occurs."
                            ],
                            concepts_tested=["SELECT FOR UPDATE", "Database Transactions (ACID)", "Race Condition Prevention", "Concurrency Control"],
                            expected_outcome="Flawless transactional consistency guaranteeing exact stock counts under concurrent load.",
                            optional_hints=["SELECT ... FOR UPDATE locks the selected rows until transaction commit or rollback."]
                        ),
                    ],
                ),
                make_skill(
                    slug="redis-fs",
                    name="Redis",
                    canonical_slug="redis",
                    difficulty="INTERMEDIATE",
                    description="In-memory data store: Caching, session management, rate limiting, and pub/sub message broadcasting.",
                    key_topics=["Key-Value Caching with Expiration (TTL)", "Session Store Management", "Rate Limiting Algorithms", "Pub/Sub Real-time Messaging"],
                    role_relevance="Accelerates application performance, offloads database traffic, and enables microsecond lookups.",
                    prerequisites=["postgresql-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Redis Documentation", "url": "https://redis.io/docs/", "description": "Official documentation for Redis data structures, commands, and caching patterns."},
                        {"type": "YOUTUBE", "title": "Redis Crash Course — Traversy Media", "url": "https://www.youtube.com/watch?v=jgpVdJB2sKQ", "description": "Hands-on guide to using Redis for caching and session management."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="redis-fs-prob-1",
                            title="API Response Cache-Aside Wrapper",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement the Cache-Aside pattern with key expiration.",
                            problem_statement="Build a caching function in Node.js that checks Redis before querying PostgreSQL, caching results for 60 seconds.",
                            requirements=[
                                "Check Redis using redis.get(key).",
                                "On cache miss, fetch data from PostgreSQL and write to Redis using redis.setex(key, 60, JSON.stringify(data)).",
                                "On cache hit, parse JSON and return immediately."
                            ],
                            concepts_tested=["Cache-Aside Pattern", "redis.get / redis.setex", "TTL Expiration", "JSON Cache Serialization"],
                            expected_outcome="Sub-5ms response times on cached endpoints with automatic expiration.",
                            optional_hints=["Use ioredis or redis npm client."]
                        ),
                        make_problem(
                            problem_id="redis-fs-prob-2",
                            title="API Rate Limiter with Sliding Window",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Protect backend endpoints from abuse using a sliding window rate limiter in Redis.",
                            problem_statement="Build an Express/Next.js rate limiting middleware that restricts users to 60 requests per minute using Redis Sorted Sets.",
                            requirements=[
                                "Record request timestamps in a Redis Sorted Set per IP address.",
                                "Remove timestamps older than 60 seconds with zremrangebyscore.",
                                "Check count with zcard; return 429 Too Many Requests if count exceeds threshold."
                            ],
                            concepts_tested=["Sorted Sets (ZSET)", "Rate Limiting", "HTTP 429", "Sliding Window Algorithm"],
                            expected_outcome="A resilient rate limiter that prevents brute force and denial of service attacks.",
                            optional_hints=["Use Redis multi/exec transaction pipeline to ensure atomicity."]
                        ),
                        make_problem(
                            problem_id="redis-fs-prob-3",
                            title="Multi-Server Pub/Sub Chat Broadcaster",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Broadcast real-time messages across multiple server instances using Redis Pub/Sub.",
                            problem_statement="Implement a real-time message broadcasting system where WebSocket connections on Server A receive events published on Server B via Redis Pub/Sub.",
                            requirements=[
                                "Initialize distinct Redis publisher and subscriber clients.",
                                "Publish chat messages to a 'chat:room_id' channel using redis.publish.",
                                "Subscribe to channels and forward received messages to local connected WebSocket clients."
                            ],
                            concepts_tested=["Redis Pub/Sub", "publish & subscribe", "Horizontal Scaling for WebSockets", "Inter-process Communication"],
                            expected_outcome="Seamless real-time event distribution across multiple horizontal server replicas.",
                            optional_hints=["Redis subscriber clients enter subscriber mode and cannot execute regular commands; use a dedicated connection."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 5,
            "name": "Stage 5 — DevOps & Cloud Production",
            "description": "Containerize full-stack applications and automate deployment pipelines.",
            "skills": [
                make_skill(
                    slug="docker-fs",
                    name="Docker",
                    canonical_slug="docker",
                    difficulty="INTERMEDIATE",
                    description="Container virtualization: Multi-stage Dockerfiles for Next.js, container networking, and Docker Compose orchestration.",
                    key_topics=["Dockerfile Syntax & Multi-Stage Builds", "Next.js Standalone Output & Optimization", "Docker Compose Multi-Service Stacks", "Container Environment Variables & Volumes"],
                    role_relevance="Standardizes application runtime environments across development and production clouds.",
                    prerequisites=["nodejs-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Docker Official Documentation", "url": "https://docs.docker.com/", "description": "Official guides for Docker engine, multi-stage builds, and Compose."},
                        {"type": "YOUTUBE", "title": "Docker Crash Course — TechWorld with Nana", "url": "https://www.youtube.com/watch?v=3c-iBn73dDE", "description": "Complete beginner walkthrough of container concepts, images, and networking."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="docker-fs-prob-1",
                            title="Next.js Multi-Stage Dockerfile",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build a minimal production Docker image for a Next.js application.",
                            problem_statement="Create a multi-stage Dockerfile that builds Next.js using standalone output and runs as a non-root user.",
                            requirements=[
                                "Use node:20-alpine base image.",
                                "Stage 1 (deps), Stage 2 (builder), Stage 3 (runner).",
                                "Enable output: 'standalone' in next.config and copy only standalone server files to final image."
                            ],
                            concepts_tested=["Multi-stage Builds", "Next.js Standalone", "Image Optimization", "Alpine Linux"],
                            expected_outcome="A compact production container image under 120MB that boots in seconds.",
                            optional_hints=["Standalone output extracts only necessary node_modules into .next/standalone."]
                        ),
                        make_problem(
                            problem_id="docker-fs-prob-2",
                            title="Full-Stack Local Environment with Docker Compose",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Orchestrate web frontend, backend API, Postgres, and Redis with Docker Compose.",
                            problem_statement="Build a docker-compose.yml managing web, db, and redis services with shared networking and persistent volumes.",
                            requirements=[
                                "Configure web service depending on db and redis with service_healthy conditions.",
                                "Create named volume for postgres_data.",
                                "Inject environment variables from .env file."
                            ],
                            concepts_tested=["Docker Compose", "Service Health Checks", "Named Volumes", "Container Networking"],
                            expected_outcome="A full local development stack launching cleanly with a single 'docker compose up' command.",
                            optional_hints=["Use healthcheck on postgres using 'pg_isready -U postgres'."]
                        ),
                        make_problem(
                            problem_id="docker-fs-prob-3",
                            title="Production Container Hardening & Security Audit",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Harden a container against security vulnerabilities and run vulnerability scanning.",
                            problem_statement="Harden a Docker container: run as non-root user, make root filesystem read-only, and scan with Trivy for zero CVEs.",
                            requirements=[
                                "Create system user 'nextjs' with UID 1001 and switch with USER nextjs.",
                                "Configure docker run with --read-only and mount tmpfs on /tmp.",
                                "Run Trivy or Docker Scout vulnerability scanner and resolve all critical findings."
                            ],
                            concepts_tested=["Non-root Security", "Read-Only Root Filesystem", "Vulnerability Scanning (Trivy)", "Container Hardening"],
                            expected_outcome="A hardened production image passing enterprise security compliance scans.",
                            optional_hints=["Never run production web containers with root UID 0."]
                        ),
                    ],
                ),
                make_skill(
                    slug="cicd-fullstack",
                    name="CI/CD & Cloud Deployment with GitHub Actions",
                    canonical_slug="github-actions",
                    difficulty="INTERMEDIATE",
                    description="Continuous Integration and Continuous Deployment: Automated testing, linting, preview deployments, and cloud release automation.",
                    key_topics=["GitHub Actions Workflows", "Automated Linting & Test Runners", "Build Artifacts & Caching", "Cloud Deployments (Vercel / AWS / Docker)"],
                    role_relevance="Automates code verification, prevents production breakages, and enables continuous zero-downtime shipping.",
                    prerequisites=["docker-fs", "nodejs-fs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "GitHub Actions Documentation", "url": "https://docs.github.com/en/actions", "description": "Official guides for building CI/CD workflows and automation."},
                        {"type": "YOUTUBE", "title": "GitHub Actions CI/CD Full Course", "url": "https://www.youtube.com/watch?v=R8_veQiYBjI", "description": "Hands-on tutorial building automated CI/CD pipelines from scratch."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="cicd-fs-prob-1",
                            title="Automated Pull Request CI Pipeline",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a GitHub Actions workflow that runs typechecking, linting, and tests.",
                            problem_statement="Build a .github/workflows/ci.yml workflow that validates pull requests before they can be merged into main.",
                            requirements=[
                                "Trigger on pull_request to main.",
                                "Install dependencies with npm ci and cache node_modules.",
                                "Run 'npm run lint', 'npx tsc --noEmit', and 'npm test'."
                            ],
                            concepts_tested=["GitHub Actions Workflows", "npm ci & Caching", "Typecheck in CI", "Lint Verification"],
                            expected_outcome="An automated gate blocking merges if TypeScript errors or test failures occur.",
                            optional_hints=["Use actions/cache or 'cache: npm' in actions/setup-node."]
                        ),
                        make_problem(
                            problem_id="cicd-fs-prob-2",
                            title="Database Migration & Test Runner in CI",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Run integration tests against an active PostgreSQL service container in GitHub Actions.",
                            problem_statement="Configure a CI job with a PostgreSQL service container, running database migrations and integration tests.",
                            requirements=[
                                "Define a services: postgres container with health checks.",
                                "Run database migrations (prisma migrate deploy / alembic upgrade head).",
                                "Execute integration test suite against the live database container."
                            ],
                            concepts_tested=["Service Containers", "Database Migrations in CI", "Integration Test Pipelines", "Environment Secrets"],
                            expected_outcome="Automated integration test verification verifying schema migrations and database logic.",
                            optional_hints=["Expose PostgreSQL on port 5432 and connect via localhost."]
                        ),
                        make_problem(
                            problem_id="cicd-fs-prob-3",
                            title="Automated Docker Build & Zero-Downtime Deployment",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build, push, and deploy a containerized application to cloud infrastructure automatically.",
                            problem_statement="Build a CD pipeline that triggers on merge to main, builds a Docker image, pushes to a container registry, and deploys with health check verification.",
                            requirements=[
                                "Use docker/build-push-action with GitHub token and layer caching.",
                                "Push image tagged with git commit SHA and 'latest'.",
                                "Trigger webhook deployment and poll health check endpoint until 200 OK is verified."
                            ],
                            concepts_tested=["Docker Buildx", "Container Registry (GHCR/ECR)", "Commit SHA Tagging", "Automated Health Verification", "Zero-Downtime Deployment"],
                            expected_outcome="A fully automated CD workflow delivering verified production releases on every merge.",
                            optional_hints=["Tagging with the git commit SHA allows instant rollbacks to previous versions."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

"""Frontend Engineer roadmap definition with progressive practice problems and market demand integration."""
from typing import Any, Dict
from app.db.roadmaps_data.common import CANONICAL_ROLE_IDS, ROADMAP_IDS, make_problem, make_skill

FRONTEND_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["frontend-engineer"],
    "slug": "frontend-engineer",
    "role_id": CANONICAL_ROLE_IDS["frontend-engineer"],
    "title": "Frontend Engineer",
    "domain": "Frontend Engineering",
    "category": "Engineering",
    "description": "Master modern client-side engineering: semantic HTML, CSS architecture, JavaScript/TypeScript, React 19, Next.js App Router, state management, accessibility, testing, and web performance optimization.",
    "version": "v2.0",
    "has_market_data": True,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Core Web Technologies",
            "description": "The foundational building blocks of the web platform: structure, presentation, and dynamic interactivity.",
            "skills": [
                make_skill(
                    slug="html",
                    name="HTML",
                    canonical_slug="html",
                    difficulty="BEGINNER",
                    description="The standard markup language of the web platform: semantic elements, document outline, forms, media, and accessible structural markup.",
                    key_topics=["Semantic Elements (header, nav, main, article, section, footer)", "Form Controls (inputs, labels, select, textarea)", "Document Hierarchy & Headings (h1-h6)", "Multimedia (img, picture, audio, video)", "Accessible Markup & Metadata"],
                    role_relevance="The foundation of all web rendering, accessibility for screen readers, and search engine indexability.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MDN Web Docs — HTML", "url": "https://developer.mozilla.org/en-US/docs/Web/HTML", "description": "The definitive, comprehensive reference for HTML elements, attributes, and semantics."},
                        {"type": "YOUTUBE", "title": "HTML Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=kUMe1FH4CHE", "description": "Complete beginner tutorial covering semantic structure, forms, tables, and multimedia."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="html-prob-1",
                            title="Personal Profile Page",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master document hierarchy, text elements, media, and fundamental metadata.",
                            problem_statement="Build a valid HTML5 personal profile document incorporating proper document tags, headings, lists, images, and links.",
                            requirements=[
                                "Include valid <!DOCTYPE html>, <html>, <head> with charset/viewport meta tags, and <body>.",
                                "Structure content with a single <h1> and appropriate <h2>/<h3> subsections.",
                                "Include paragraphs, ordered and unordered lists, and anchor links.",
                                "Embed an image with a descriptive alt attribute."
                            ],
                            concepts_tested=["semantic document structure", "html/head/body", "headings", "paragraphs", "links", "images", "alt text", "lists", "basic metadata"],
                            expected_outcome="A fully valid W3C HTML5 document displaying a clean semantic profile outline.",
                            optional_hints=["Always provide meaningful text in the alt attribute for screen reader users."]
                        ),
                        make_problem(
                            problem_id="html-prob-2",
                            title="Product / Event Page with Structured Form",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Combine semantic sectioning, tabular data display, and accessible form controls.",
                            problem_statement="Build a comprehensive product or conference event registration page featuring a schedule table and interactive form.",
                            requirements=[
                                "Use semantic headings, paragraphs, and list items.",
                                "Build an accessible <table> with <thead>, <tbody>, <th> with scope attributes, and <td> cells.",
                                "Construct an accessible <form> with explicit <label for='...'> associations.",
                                "Include diverse input types (text, email, date, number), a <select> dropdown, a <textarea>, and submit <button>."
                            ],
                            concepts_tested=["headings", "paragraphs", "images", "links", "ordered/unordered lists", "tables", "semantic HTML", "forms", "labels", "inputs", "buttons", "select", "textarea", "accessibility basics"],
                            expected_outcome="An accessible event registration page with interactive inputs linked to matching labels.",
                            optional_hints=["Never use placeholder text as a replacement for visible <label> elements."]
                        ),
                        make_problem(
                            problem_id="html-prob-3",
                            title="Complete Accessible Multi-Section Website",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a complete accessible website uniting landmark elements, media, forms, and tables.",
                            problem_statement="Author a complete multi-section website containing all major semantic HTML5 landmarks and accessible content structures.",
                            requirements=[
                                "Incorporate <header>, <nav>, <main>, <article>, <section>, <aside>, and <footer> landmarks.",
                                "Include responsive images using <picture> and embedded <audio> or <video> media with fallback text.",
                                "Include a contact form with accessible fieldsets, legends, and input validation attributes (required, pattern).",
                                "Maintain an unbroken, logical heading hierarchy (h1 through h4) verified with an HTML5 outliner."
                            ],
                            concepts_tested=["semantic HTML", "headings", "paragraphs", "links", "images", "lists", "tables", "forms", "accessibility", "media", "header", "navigation", "main", "sections", "article", "aside", "footer"],
                            expected_outcome="A production-standard HTML5 website that passes WCAG automated audits with 100% semantic compliance.",
                            optional_hints=["Use <main> only once per document to define central content."]
                        ),
                    ],
                ),
                make_skill(
                    slug="css",
                    name="CSS",
                    canonical_slug="css",
                    difficulty="BEGINNER",
                    description="Modern Cascading Style Sheets: Box model, Flexbox, Grid, custom properties (CSS variables), responsive design, and CSS transitions.",
                    key_topics=["Box Model (content, padding, border, margin, box-sizing)", "Flexbox Alignment & Distribution", "CSS Grid 2D Layouts & Areas", "CSS Custom Properties (Variables)", "Responsive Media Queries & Fluid Typography (clamp())"],
                    role_relevance="Governs all visual styling, layout responsiveness, and aesthetic presentation across devices and viewport sizes.",
                    prerequisites=["html"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MDN Web Docs — CSS", "url": "https://developer.mozilla.org/en-US/docs/Web/CSS", "description": "Complete CSS reference, tutorials, selectors, and layout specifications."},
                        {"type": "YOUTUBE", "title": "CSS Crash Course — Kevin Powell", "url": "https://www.youtube.com/watch?v=1PnVor36_40", "description": "Essential guide to modern CSS layouts, flexbox, grid, and responsive techniques."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="css-prob-1",
                            title="Responsive Card Component with Flexbox",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master the CSS box model, box-sizing, typography, and Flexbox alignment.",
                            problem_statement="Style a responsive product card component with image, tags, pricing, and button using Flexbox.",
                            requirements=[
                                "Apply 'box-sizing: border-box' and set up CSS custom properties for colors and spacing.",
                                "Use display: flex to align card elements with proper gap and justify-content.",
                                "Add subtle hover transitions for box-shadow and transform: translateY(-4px)."
                            ],
                            concepts_tested=["Box Model", "box-sizing", "Flexbox (justify, align, gap)", "CSS Variables", "Hover Transitions"],
                            expected_outcome="A clean, interactive card component that resizes fluidly without layout overflow.",
                            optional_hints=["Use 'overflow: hidden' on the card container to clip rounded image borders."]
                        ),
                        make_problem(
                            problem_id="css-prob-2",
                            title="Complex Dashboard Grid Layout",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Build a multi-column responsive dashboard using CSS Grid and grid-template-areas.",
                            problem_statement="Construct a responsive dashboard with header, sidebar, stats cards, chart section, and activity feed using CSS Grid.",
                            requirements=[
                                "Define grid-template-areas: 'header header' 'sidebar main' for desktop.",
                                "Use auto-fit and minmax(250px, 1fr) for an adaptive stats card sub-grid.",
                                "Collapse to a single-column layout on mobile devices using @media query breakpoints."
                            ],
                            concepts_tested=["CSS Grid", "grid-template-areas", "minmax() & auto-fit", "Media Queries", "Responsive Breakpoints"],
                            expected_outcome="A responsive dashboard layout that adapts seamlessly between desktop, tablet, and mobile screens.",
                            optional_hints=["minmax(min, 1fr) combined with auto-fit automatically wraps columns without media queries."]
                        ),
                        make_problem(
                            problem_id="css-prob-3",
                            title="Themeable Design System with Dark Mode & Fluid Typography",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a production CSS architecture with design tokens, fluid clamp() scales, and prefers-color-scheme.",
                            problem_statement="Develop a zero-dependency CSS design system with light/dark theme switching, fluid typography, and accessible focus states.",
                            requirements=[
                                "Define design tokens with CSS custom properties on :root and [data-theme='dark'].",
                                "Incorporate @media (prefers-color-scheme: dark) automatic theme detection.",
                                "Use clamp() for fluid typography (font-size: clamp(1rem, 2.5vw, 2.5rem)) across viewport widths.",
                                "Provide highly visible custom :focus-visible outlines for keyboard accessibility."
                            ],
                            concepts_tested=["CSS Custom Properties", "prefers-color-scheme (Dark Mode)", "Fluid Typography (clamp())", ":focus-visible Accessibility", "Modern Selectors (:has, :is)"],
                            expected_outcome="A robust, themeable stylesheet supporting light/dark themes and fluid scaling without layout jumps.",
                            optional_hints=["Never use outline: none without providing an accessible :focus-visible replacement."]
                        ),
                    ],
                ),
                make_skill(
                    slug="javascript",
                    name="JavaScript",
                    canonical_slug="javascript",
                    difficulty="BEGINNER",
                    description="Modern ECMAScript programming: Variables, functions, closures, array methods, DOM manipulation, asynchronous promises, and async/await.",
                    key_topics=["ES6+ Syntax (let/const, arrow functions, destructuring, spread)", "DOM Selection & Event Listeners", "Array Higher-Order Methods (map, filter, reduce)", "Asynchronous JS: Promises & async/await", "Fetch API & Error Handling"],
                    role_relevance="The universal programming language of browsers, driving client-side logic, interactivity, and network communication.",
                    prerequisites=["html", "css"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "JavaScript Reference — MDN Web Docs", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript", "description": "Standard guide to JavaScript language specification, Web APIs, and async patterns."},
                        {"type": "YOUTUBE", "title": "JavaScript Full Course — Bro Code", "url": "https://www.youtube.com/watch?v=lfmg-EJ8gm4", "description": "Hands-on course covering JS fundamentals, DOM manipulation, and asynchronous programming."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="js-prob-1",
                            title="Interactive Todo App with DOM Manipulation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Manipulate DOM elements, handle events, and store data in localStorage.",
                            problem_statement="Build a vanilla JavaScript task list where users can add, toggle completion, and delete tasks with persistence.",
                            requirements=[
                                "Use document.querySelector and addEventListener to handle form submissions.",
                                "Dynamically create and append DOM elements for new tasks.",
                                "Save tasks array as JSON in window.localStorage and reload on page load."
                            ],
                            concepts_tested=["DOM Manipulation", "Event Listeners (submit, click)", "localStorage Persistence", "Array Methods (push, filter)"],
                            expected_outcome="A functional task manager that remembers items across browser page refreshes.",
                            optional_hints=["Use e.preventDefault() on form submit to prevent browser reload."]
                        ),
                        make_problem(
                            problem_id="js-prob-2",
                            title="Async Data Fetcher with Search & Debounce",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Combine async/await, fetch API, array transformations, and debounce timing.",
                            problem_statement="Build a search widget that queries a mock REST API as the user types, debouncing keystrokes and rendering cards.",
                            requirements=[
                                "Implement a custom debounce(fn, delay) function using closures and setTimeout.",
                                "Fetch data using async/await with try-catch block for network errors.",
                                "Filter and map results into HTML templates with loading and empty state indicators."
                            ],
                            concepts_tested=["async/await", "Fetch API", "Debounce Pattern", "Closures & setTimeout", "Template Literals"],
                            expected_outcome="A smooth search interface that minimizes network calls and renders formatted result cards.",
                            optional_hints=["Clear the previous timer with clearTimeout inside the debounce closure."]
                        ),
                        make_problem(
                            problem_id="js-prob-3",
                            title="Event-Driven State Store (Pub/Sub Pattern)",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement an in-browser state management container with Pub/Sub event dispatching.",
                            problem_statement="Build a lightweight, framework-free state store with subscribe, getState, and dispatch methods modeled after Redux.",
                            requirements=[
                                "Implement a createStore(reducer, initialState) function.",
                                "Allow UI components to subscribe to state change notifications via callback listeners.",
                                "Ensure state is immutable by enforcing updates via pure reducer functions.",
                                "Build two decoupled DOM widgets that communicate solely through store dispatches."
                            ],
                            concepts_tested=["Pub/Sub Pattern", "Immutable State", "Pure Functions (Reducers)", "Closures", "Custom Events"],
                            expected_outcome="A modular, decoupled state architecture coordinating multiple UI components without tight coupling.",
                            optional_hints=["Use object spread {...state, ...update} to guarantee immutability in reducers."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Type Systems & Modern Styling",
            "description": "Enforce strict static typing and rapid, responsive UI composition with TypeScript and Tailwind CSS.",
            "skills": [
                make_skill(
                    slug="typescript",
                    name="TypeScript",
                    canonical_slug="typescript",
                    difficulty="BEGINNER",
                    description="Typed JavaScript superset: Interfaces, type aliases, union & intersection types, generics, utility types, and strict compiler configurations.",
                    key_topics=["Primitive Types & Type Inference", "Interfaces vs Type Aliases", "Union & Intersection Types, Discriminated Unions", "Generics (<T>) & Generic Constraints", "Utility Types (Partial, Pick, Omit, Record)"],
                    role_relevance="Industry requirement for large-scale frontend development, preventing runtime type errors and enhancing IDE autocomplete.",
                    prerequisites=["javascript"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "TypeScript Official Handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "description": "The authoritative handbook covering basic types, generics, and type manipulation."},
                        {"type": "YOUTUBE", "title": "TypeScript Course for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=BwuLxPH8IDs", "description": "Full course on TypeScript fundamentals, configuration, and practical coding patterns."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="ts-prob-1",
                            title="Typed Data Models & Discriminated Unions",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Model domain entities with interfaces and pattern-match with discriminated unions.",
                            problem_statement="Model an asynchronous API response system using discriminated unions to guarantee compile-time type safety.",
                            requirements=[
                                "Define ApiResponse<T> as a discriminated union: { status: 'loading' } | { status: 'success', data: T } | { status: 'error', error: string }.",
                                "Implement a handleResponse function that narrows the type using a switch statement.",
                                "Verify that accessing data in the error branch triggers a compile-time TypeScript error."
                            ],
                            concepts_tested=["Interfaces & Types", "Discriminated Unions", "Type Narrowing", "Generics (<T>)"],
                            expected_outcome="Type-safe code where invalid property access is caught during compilation rather than at runtime.",
                            optional_hints=["The shared 'status' literal string property acts as the discriminant."]
                        ),
                        make_problem(
                            problem_id="ts-prob-2",
                            title="Generic API Client with Utility Types",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Use Generics and TypeScript utility types to create a type-safe HTTP client wrapper.",
                            problem_statement="Build a generic apiClient.get<T>(url) and apiClient.post<T, B>(url, body) function using utility types.",
                            requirements=[
                                "Use generic type parameters for request payload and expected response data.",
                                "Use Partial<T> for update payloads and Pick<T, K> / Omit<T, K> for sanitizing entity models.",
                                "Define strict Record<string, string> mappings for HTTP headers."
                            ],
                            concepts_tested=["Generics with Constraints", "Partial<T>", "Pick<T, K> and Omit<T, K>", "Record<K, V>", "Type Assertions"],
                            expected_outcome="A reusable HTTP fetcher where response data is automatically typed as the requested interface.",
                            optional_hints=["Use generic constraint 'extends object' if you need to enforce object payloads."]
                        ),
                        make_problem(
                            problem_id="ts-prob-3",
                            title="Type-Safe Event Bus with Keyof & Mapped Types",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Construct an advanced strongly-typed event emitter with keyof, typeof, and conditional mapped types.",
                            problem_statement="Build a type-safe EventBus where subscribing to an event name automatically enforces the exact payload type for that specific event.",
                            requirements=[
                                "Define an interface AppEvents mapping event names to their payload interfaces.",
                                "Implement emit<K extends keyof AppEvents>(event: K, payload: AppEvents[K]): void.",
                                "Implement on<K extends keyof AppEvents>(event: K, listener: (payload: AppEvents[K]) => void): void.",
                                "Verify that passing the wrong payload type to an event triggers compile-time errors."
                            ],
                            concepts_tested=["keyof Operator", "Indexed Access Types", "Mapped Types", "Generic Event Emitter", "Conditional Types"],
                            expected_outcome="A completely type-safe event bus with autocomplete for event names and strict payload verification.",
                            optional_hints=["keyof AppEvents extracts all valid event name strings as a union type."]
                        ),
                    ],
                ),
                make_skill(
                    slug="tailwindcss",
                    name="Tailwind CSS",
                    canonical_slug="tailwindcss",
                    difficulty="BEGINNER",
                    description="Utility-first CSS framework: Atomic utility classes, responsive prefixes, dark mode, arbitrary values, and design token configuration.",
                    key_topics=["Utility-First Fundamentals & Core Classes", "Responsive Design (sm:, md:, lg:, xl:)", "State Modifiers (hover:, focus:, active:, disabled:)", "Dark Mode Variants (dark:)", "Tailwind Configuration & Theme Extensions"],
                    role_relevance="Accelerates frontend styling velocity and enforces design system consistency across modern web applications.",
                    prerequisites=["css"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Official Tailwind CSS Documentation", "url": "https://tailwindcss.com/docs", "description": "Complete utility reference, configuration guides, and design token documentation."},
                        {"type": "YOUTUBE", "title": "Tailwind CSS Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=ft30zcMlFao", "description": "Comprehensive tutorial covering Tailwind utilities, flex, grid, responsive variants, and dark mode."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="tailwind-prob-1",
                            title="Responsive Pricing Card with Hover Effects",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build a styled pricing card using utility classes and responsive modifiers.",
                            problem_statement="Build a modern SaaS pricing tier card using only Tailwind CSS utility classes.",
                            requirements=[
                                "Style card container with rounded-2xl, p-6, shadow-lg, and border.",
                                "Add hover effects using transition-all, hover:-translate-y-1, and hover:shadow-2xl.",
                                "Make layout responsive: full width on mobile (w-full), max-w-sm on desktop."
                            ],
                            concepts_tested=["Atomic Utilities", "Spacing & Typography", "Flexbox Utilities", "Hover State Modifiers", "Transitions & Shadows"],
                            expected_outcome="A sleek, interactive pricing card with smooth hover animations styled entirely with Tailwind.",
                            optional_hints=["Use 'group' and 'group-hover:' to coordinate animations between card and button."]
                        ),
                        make_problem(
                            problem_id="tailwind-prob-2",
                            title="Dark-Mode Ready Navigation Bar with Mobile Drawer",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement responsive navigation with dark: variants and backdrop blur effects.",
                            problem_statement="Build a sticky navigation bar with brand logo, desktop links, dark mode toggle, and mobile menu button.",
                            requirements=[
                                "Use sticky top-0, backdrop-blur-md, and bg-white/80 with dark:bg-neutral-900/80.",
                                "Hide navigation links on mobile (hidden md:flex) and show a hamburger icon.",
                                "Apply dark: modifier across text, background, and border classes seamlessly."
                            ],
                            concepts_tested=["Sticky Positioning", "Backdrop Blur & Opacity", "dark: Variants", "Responsive Hiding (hidden md:flex)", "Flex Alignment"],
                            expected_outcome="A responsive navbar that transitions between light and dark themes and adapts to all screen sizes.",
                            optional_hints=["Add 'dark' class to the root HTML element to test dark mode variants."]
                        ),
                        make_problem(
                            problem_id="tailwind-prob-3",
                            title="Custom Design Tokens & Reusable Component Classes",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Extend Tailwind's theme configuration with custom brand colors, animations, and custom utility classes.",
                            problem_statement="Configure custom brand colors and a keyframe animation in tailwind.config or CSS theme, and build a reusable component library.",
                            requirements=[
                                "Extend theme with custom brand color palette (brand-50 through brand-900).",
                                "Add a custom pulse-glow keyframe animation in Tailwind configuration.",
                                "Build a polished button component supporting variants (primary, secondary, danger) and sizes (sm, md, lg)."
                            ],
                            concepts_tested=["Theme Extension", "Custom Color Palettes", "Custom Keyframe Animations", "Component Composition", "Arbitrary Values"],
                            expected_outcome="A scalable Tailwind setup delivering consistent brand tokens and interactive animated components.",
                            optional_hints=["Use clsx or tailwind-merge in JavaScript/TypeScript for dynamic class joining."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Component Frameworks & State Architecture",
            "description": "Build scalable, declarative user interfaces with React 19, custom hooks, and modern state management.",
            "skills": [
                make_skill(
                    slug="react",
                    name="React",
                    canonical_slug="react",
                    difficulty="INTERMEDIATE",
                    description="Component-based declarative UI library: JSX, Props, State (useState), Effects (useEffect), Custom Hooks, Context API, and Performance Optimization (useMemo, useCallback).",
                    key_topics=["JSX & Component Lifecycle", "State & Props Management (useState)", "Side Effects & Cleanup (useEffect)", "Custom Hooks Abstraction", "Performance (useMemo, useCallback, React.memo)", "Context API for Global State"],
                    role_relevance="The world's most widely used frontend library, providing the foundation for modern web application frontends.",
                    prerequisites=["javascript", "typescript"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "React Official Documentation (react.dev)", "url": "https://react.dev/", "description": "The official documentation with deep interactive tutorials on thinking in React and modern hooks."},
                        {"type": "YOUTUBE", "title": "React Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=bMknfKXIFA8", "description": "Comprehensive tutorial on React components, hooks, state, and building real-world projects."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="react-prob-1",
                            title="Interactive Filterable List Component",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master JSX rendering, props passing, and local state with useState.",
                            problem_statement="Build a searchable product catalog component that filters a list of products in real time based on user search input.",
                            requirements=[
                                "Create a ProductList parent component and ProductItem child component passing data via props.",
                                "Manage search query state with useState and derive filtered items during render.",
                                "Display an empty state message when no products match the search query."
                            ],
                            concepts_tested=["JSX Syntax", "Props", "useState", "Derived State", "Conditional Rendering"],
                            expected_outcome="A reactive UI where typing immediately updates the rendered product cards without page reloads.",
                            optional_hints=["Calculate filtered items directly in the render body rather than in a separate useEffect."]
                        ),
                        make_problem(
                            problem_id="react-prob-2",
                            title="Custom useFetch Hook with AbortController",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Extract reusable asynchronous logic into a custom hook with proper effect cleanup.",
                            problem_statement="Develop a reusable useFetch<T>(url) custom hook that manages data, loading, and error states with cancellation on unmount.",
                            requirements=[
                                "Return { data: T | null, loading: boolean, error: string | null } from useFetch.",
                                "Use useEffect with AbortController to cancel in-flight HTTP requests when the component unmounts or URL changes.",
                                "Handle network failures and non-200 HTTP responses by updating error state."
                            ],
                            concepts_tested=["Custom Hooks", "useEffect Cleanup", "AbortController", "Asynchronous State", "Generics in React"],
                            expected_outcome="A clean, reusable hook that prevents race conditions and memory leak warnings on unmounted components.",
                            optional_hints=["Return () => abortController.abort() from the useEffect cleanup function."]
                        ),
                        make_problem(
                            problem_id="react-prob-3",
                            title="Modal & Toast System with Context & Portals",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build an enterprise toast and modal notification system using Context API and ReactDOM.createPortal.",
                            problem_statement="Build a global notification provider allowing any nested component to trigger dismissible toasts and modal dialogs.",
                            requirements=[
                                "Create a NotificationContext and useNotification hook exposing showToast(message, type) and showModal(content).",
                                "Render modal dialogs outside the root DOM tree using ReactDOM.createPortal.",
                                "Implement auto-dismiss timers for toasts (5 seconds) with manual dismiss buttons.",
                                "Ensure focus trapping within open modals for keyboard accessibility."
                            ],
                            concepts_tested=["Context API", "ReactDOM.createPortal", "Focus Trapping", "Custom Hook Providers", "Timers & Cleanup"],
                            expected_outcome="A global UI overlay system that renders properly above all z-index layers with accessible keyboard controls.",
                            optional_hints=["Create a <div id='modal-root'> in index.html as the portal target."]
                        ),
                    ],
                ),
                make_skill(
                    slug="state-management-query",
                    name="State Management & Server State (Zustand & TanStack Query)",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Modern client and server state architecture: Client store management with Zustand, and server cache synchronization, background refetching, and mutations with TanStack Query.",
                    key_topics=["Client State vs Server State Separation", "Zustand Store Creation & Selectors", "TanStack Query (useQuery & Query Keys)", "Data Mutations (useMutation) & Cache Invalidation", "Optimistic UI Updates"],
                    role_relevance="Eliminates prop drilling and boilerplate Redux code while automating background data synchronization and cache management.",
                    prerequisites=["react", "typescript"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "TanStack Query Documentation", "url": "https://tanstack.com/query/latest", "description": "Official guides for asynchronous state management, query keys, mutations, and caching."},
                        {"type": "YOUTUBE", "title": "TanStack Query & Zustand Tutorial — Cosden Solutions", "url": "https://www.youtube.com/watch?v=r8Dg0KVnfMA", "description": "Hands-on guide comparing client state with Zustand and server caching with TanStack Query."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="state-prob-1",
                            title="Zustand Shopping Cart Store with Selectors",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Manage global client-side state with a Zustand store and fine-grained selectors.",
                            problem_statement="Build a global shopping cart store with Zustand that supports adding, removing, and computing total prices.",
                            requirements=[
                                "Create useCartStore with items: CartItem[], addItem, removeItem, and clearCart actions.",
                                "Use fine-grained selectors (e.g. useCartStore(s => s.items.length)) to prevent unnecessary re-renders.",
                                "Persist the cart state to localStorage using Zustand's persist middleware."
                            ],
                            concepts_tested=["Zustand create()", "State Selectors", "Zustand Persist Middleware", "Immutable Updates"],
                            expected_outcome="A high-performance global state store with automatic local storage persistence and zero boilerplate.",
                            optional_hints=["Always select primitive values or use shallow comparison for complex selector returns."]
                        ),
                        make_problem(
                            problem_id="state-prob-2",
                            title="Server State Caching with TanStack Query",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Fetch and cache remote data with useQuery, handling loading, error, and background re-fetching.",
                            problem_statement="Implement a paginated user list using useQuery with query keys, staleTime configuration, and automatic refetching on window focus.",
                            requirements=[
                                "Configure QueryClientProvider and useQuery with query key ['users', page].",
                                "Configure staleTime: 60000 (1 minute) to prevent duplicate background refetches.",
                                "Render loading skeletons, error states with retry buttons, and cached data seamlessly."
                            ],
                            concepts_tested=["useQuery", "Query Keys", "staleTime vs gcTime", "Query Invalidation", "Loading Skeletons"],
                            expected_outcome="Instant UI rendering from cache with automated background data synchronization.",
                            optional_hints=["Include all reactive variables (like 'page') in the queryKey array."]
                        ),
                        make_problem(
                            problem_id="state-prob-3",
                            title="Optimistic UI Mutations with Cache Rollback",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement instant UI feedback using TanStack Query useMutation with optimistic updates and error rollback.",
                            problem_statement="Build a 'Like Post' toggle button that updates the UI count immediately and rolls back if the network request fails.",
                            requirements=[
                                "Use useMutation with onMutate callback to cancel outgoing queries and snapshot previous post state.",
                                "Optimistically update the QueryClient cache using queryClient.setQueryData.",
                                "Implement onError callback restoring the previous snapshot if the network mutation rejects.",
                                "Call queryClient.invalidateQueries in onSettled to re-sync with the true server state."
                            ],
                            concepts_tested=["useMutation", "Optimistic Updates", "Cache Rollback (onMutate/onError)", "queryClient.setQueryData", "onSettled Invalidation"],
                            expected_outcome="Zero-latency UI updates with guaranteed eventual consistency and automatic error recovery.",
                            optional_hints=["Return { previousPost } from onMutate to pass context to the onError handler."]
                        ),
                    ],
                ),
                make_skill(
                    slug="web-accessibility",
                    name="Web Accessibility (WCAG 2.1 AA & ARIA)",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Inclusive frontend engineering: WCAG 2.1 guidelines, semantic HTML landmarks, ARIA attributes (roles, states, properties), keyboard navigation, color contrast, and screen reader testing.",
                    key_topics=["WCAG 2.1 AA Four Principles (POUR)", "ARIA Landmarks, Roles & Attributes (aria-expanded, aria-hidden)", "Accessible Keyboard Navigation & Focus Trapping", "Color Contrast Ratios (4.5:1 normal, 3:1 large)", "Automated Accessibility Auditing (axe-core, Lighthouse)"],
                    role_relevance="Mandatory for legal compliance (ADA, Section 508, EAA) and ensuring web applications are accessible to users with disabilities.",
                    prerequisites=["html", "css", "react"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "W3C Web Accessibility Initiative (WAI)", "url": "https://www.w3.org/WAI/", "description": "Official W3C guidelines, tutorials, and WCAG standards for accessible web experiences."},
                        {"type": "YOUTUBE", "title": "Web Accessibility Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=20SHvU2PKsM", "description": "Complete guide to building accessible websites, keyboard navigation, ARIA, and screen reader testing."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="a11y-prob-1",
                            title="Accessible Form with Live Error Announcements",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build an accessible form with associated labels, helper descriptions, and live validation announcements.",
                            problem_statement="Create a signup form with email and password inputs where validation errors are announced immediately to screen readers.",
                            requirements=[
                                "Associate inputs with labels using 'htmlFor' and 'id'.",
                                "Link helper text and validation errors using 'aria-describedby' and 'aria-invalid'.",
                                "Use 'aria-live=\"polite\"' on an error summary container to announce validation errors dynamically."
                            ],
                            concepts_tested=["label association", "aria-describedby", "aria-invalid", "aria-live regions", "Error Accessibility"],
                            expected_outcome="A form that guides screen reader users effortlessly through validation errors.",
                            optional_hints=["Use aria-live='polite' rather than 'assertive' to avoid interrupting user actions."]
                        ),
                        make_problem(
                            problem_id="a11y-prob-2",
                            title="Keyboard-Navigable Accordion Component",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an accordion component adhering strictly to WAI-ARIA design patterns.",
                            problem_statement="Build a multi-section accordion where headers can be toggled using Space/Enter and traversed via Arrow keys.",
                            requirements=[
                                "Use <button> headers with aria-expanded='true/false' and aria-controls='panel-id'.",
                                "Link content panels using role='region' and aria-labelledby='header-id'.",
                                "Implement keyboard navigation: ArrowDown/ArrowUp moves focus between accordion headers, Home/End jumps to first/last header."
                            ],
                            concepts_tested=["WAI-ARIA Accordion Pattern", "aria-expanded & aria-controls", "Keyboard Event Handling (Arrow keys)", "Focus Management"],
                            expected_outcome="An accordion fully operable using keyboard alone that communicates expanded states to screen readers.",
                            optional_hints=["Refer to the W3C ARIA Authoring Practices Guide (APG) for accordion specs."]
                        ),
                        make_problem(
                            problem_id="a11y-prob-3",
                            title="Automated Accessibility CI Audit with Axe-Core",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Integrate automated accessibility testing into a component test suite using axe-core / jest-axe.",
                            problem_statement="Configure automated accessibility testing across key UI components to detect and prevent contrast, labeling, and ARIA violations.",
                            requirements=[
                                "Integrate @axe-core/react or jest-axe into your test suite.",
                                "Run axe audits on complex modal, dropdown, and form components.",
                                "Assert zero WCAG 2.1 AA violations in CI automated test runs."
                            ],
                            concepts_tested=["Automated Accessibility Auditing", "axe-core", "jest-axe", "CI Accessibility Gates", "WCAG AA Compliance"],
                            expected_outcome="Automated test enforcement blocking pull requests that introduce accessibility regressions.",
                            optional_hints=["Combine automated axe tests with manual keyboard testing for 100% compliance."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Full-Stack React & Enterprise Frameworks",
            "description": "Build high-performance web applications with Next.js App Router, Server Components, and Server Actions.",
            "skills": [
                make_skill(
                    slug="nextjs",
                    name="Next.js",
                    canonical_slug="nextjs",
                    difficulty="ADVANCED",
                    description="Full-stack React framework: Next.js App Router, React Server Components (RSC), Server Actions, Dynamic Routes, Metadata API, and Route Handlers.",
                    key_topics=["App Router Directory Conventions (page, layout, loading, error)", "React Server Components (RSC) vs Client Components ('use client')", "Server Actions for Form Submissions & Mutations", "Dynamic & Catch-all Routes ([slug], [...catchall])", "Route Handlers (api/ routes) & Middleware"],
                    role_relevance="The industry-leading React framework for production web applications, offering superior SEO, performance, and full-stack capabilities.",
                    prerequisites=["react", "typescript"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Next.js Official Documentation", "url": "https://nextjs.org/docs", "description": "Official guides for the Next.js App Router, Server Components, Server Actions, and deployment."},
                        {"type": "YOUTUBE", "title": "Next.js 14/15 Full Course — CodeWithAntonio", "url": "https://www.youtube.com/watch?v=WymcmDVQpY4", "description": "In-depth project-based course building production full-stack apps with Next.js App Router."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="nextjs-prob-1",
                            title="Server Component Blog with Dynamic Routes",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build an SEO-friendly blog using React Server Components and dynamic route parameters.",
                            problem_statement="Create a Next.js App Router project displaying a list of articles on /blog and individual articles on /blog/[slug].",
                            requirements=[
                                "Fetch blog data directly inside an async Server Component without useEffect.",
                                "Implement app/blog/[slug]/page.tsx reading params.slug.",
                                "Export generateMetadata({ params }) for dynamic page titles and OpenGraph tags."
                            ],
                            concepts_tested=["React Server Components (RSC)", "Dynamic Routes ([slug])", "generateMetadata API", "Server-Side Data Fetching"],
                            expected_outcome="A high-speed, server-rendered blog delivering fully populated HTML for immediate search engine indexing.",
                            optional_hints=["Server Components do not ship JavaScript to the client bundle."]
                        ),
                        make_problem(
                            problem_id="nextjs-prob-2",
                            title="Form Submission with Server Actions & Revalidation",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Execute database mutations using Next.js Server Actions with automatic cache revalidation.",
                            problem_statement="Build a guestbook feature where users submit messages via a Server Action, validating input with Zod and revalidating the page cache.",
                            requirements=[
                                "Define an async function createMessage(formData: FormData) marked with 'use server'.",
                                "Validate input fields using Zod schema parsing.",
                                "Call revalidatePath('/guestbook') to refresh the server component cache immediately.",
                                "Handle pending submission states using the React useActionState / useFormStatus hook."
                            ],
                            concepts_tested=["Server Actions ('use server')", "revalidatePath / revalidateTag", "Zod Validation", "useActionState", "Optimistic Cache Invalidation"],
                            expected_outcome="A full-stack mutation flow that works even with JavaScript disabled and updates instantaneously when enabled.",
                            optional_hints=["Server Actions can be passed directly to the 'action' attribute of a <form>."]
                        ),
                        make_problem(
                            problem_id="nextjs-prob-3",
                            title="Route Handlers & Edge Middleware Authentication",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Protect routes and manage sessions using Next.js Edge Middleware and Route Handlers.",
                            problem_statement="Implement middleware.ts that checks for session auth cookies, redirecting unauthenticated users away from /dashboard.",
                            requirements=[
                                "Implement middleware(request: NextRequest) evaluating session cookies.",
                                "Redirect unauthenticated requests to /login?from=/dashboard.",
                                "Build an API Route Handler (app/api/auth/session/route.ts) returning current user session JSON.",
                                "Configure matcher: ['/dashboard/:path*', '/settings/:path*'] to restrict middleware execution scope."
                            ],
                            concepts_tested=["Next.js Middleware", "Route Handlers (GET/POST)", "Cookie Inspection", "Edge Runtime", "Route Matchers"],
                            expected_outcome="High-performance route protection executing at the edge before rendering or routing occurs.",
                            optional_hints=["Use NextResponse.redirect(new URL('/login', request.url)) in middleware."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 5,
            "name": "Stage 5 — Testing, Performance & Tooling",
            "description": "Automated unit and integration testing, Web Vitals performance optimization, and modern build tooling.",
            "skills": [
                make_skill(
                    slug="frontend-testing",
                    name="Frontend Testing & Quality (Vitest, RTL & Playwright)",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Comprehensive testing for web applications: Unit and component testing with Vitest and React Testing Library (RTL), and end-to-end browser automation with Playwright.",
                    key_topics=["Testing Philosophy: Testing User Behavior vs Implementation", "Vitest Test Runner & Assertions", "React Testing Library Queries (getByRole, findByText)", "User Event Simulation (@testing-library/user-event)", "End-to-End Browser Journeys with Playwright"],
                    role_relevance="Prevents UI regressions, validates interactive user journeys, and guarantees critical business flows function across releases.",
                    prerequisites=["react", "typescript"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "React Testing Library Documentation", "url": "https://testing-library.com/docs/react-testing-library/intro/", "description": "Official guides for testing React components from the end-user perspective."},
                        {"type": "YOUTUBE", "title": "React Testing Crash Course — Traversy Media", "url": "https://www.youtube.com/watch?v=7dTTFW7yACQ", "description": "Hands-on guide to testing components, mocking API calls, and user interactions with RTL."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="testing-prob-1",
                            title="Component Unit Testing with React Testing Library",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write component unit tests verifying rendering and user interactions using userEvent.",
                            problem_statement="Test a login form component with Vitest and React Testing Library, verifying validation errors and submit callback.",
                            requirements=[
                                "Render component with render(<LoginForm onSubmit={mockSubmit} />).",
                                "Query elements using screen.getByRole('textbox', { name: /email/i }) and screen.getByRole('button').",
                                "Simulate typing and clicking with userEvent.setup().",
                                "Assert that mockSubmit is called with input credentials."
                            ],
                            concepts_tested=["React Testing Library", "getByRole Queries", "userEvent Simulation", "Vitest vi.fn() Mocks", "Assertions"],
                            expected_outcome="Deterministic component test executing in milliseconds verifying user interaction behavior.",
                            optional_hints=["Always prioritize getByRole queries over getByTestId or container queries."]
                        ),
                        make_problem(
                            problem_id="testing-prob-2",
                            title="Mocking API Requests with MSW (Mock Service Worker)",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Intercept and mock network calls during component integration tests using Mock Service Worker.",
                            problem_statement="Test an asynchronous user profile component that fetches data on mount, mocking network success and 500 error states with MSW.",
                            requirements=[
                                "Configure MSW server with http.get('/api/user') handler.",
                                "Use findByText (async query) to wait for the loaded user profile to appear.",
                                "Override MSW handler in a secondary test with server.use() returning HTTP 500 and verify error message rendering."
                            ],
                            concepts_tested=["Mock Service Worker (MSW)", "Async Queries (findBy...)", "Network Error Simulation", "Integration Testing"],
                            expected_outcome="Robust tests validating component behavior against real network-like responses without hitting real backends.",
                            optional_hints=["findBy* queries return promises that automatically retry until elements appear or timeout."]
                        ),
                        make_problem(
                            problem_id="testing-prob-3",
                            title="End-to-End E-Commerce Checkout with Playwright",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Author a complete end-to-end browser automation test covering a multi-step user journey.",
                            problem_statement="Write a Playwright test simulating a user adding a product to the cart, navigating to checkout, filling the form, and confirming the order.",
                            requirements=[
                                "Launch browser with Playwright and navigate to home page.",
                                "Locate and click 'Add to Cart' button, asserting cart badge count increments to '1'.",
                                "Navigate to /checkout, fill name, address, and credit card fields.",
                                "Submit order and assert navigation to /order-confirmation with order ID visible."
                            ],
                            concepts_tested=["Playwright Automation", "End-to-End User Journeys", "Page Locators & Actions", "Web Assertions (expect(page).toHaveURL)", "Visual Regression"],
                            expected_outcome="A headless browser test verifying that the full multi-page purchase funnel functions flawlessly in Chromium, Firefox, and WebKit.",
                            optional_hints=["Use 'npx playwright test --ui' for interactive debugging."]
                        ),
                    ],
                ),
                make_skill(
                    slug="web-performance-vitals",
                    name="Web Performance & Core Web Vitals (LCP, INP, CLS)",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Web performance engineering: Core Web Vitals optimization (Largest Contentful Paint, Interaction to Next Paint, Cumulative Layout Shift), code-splitting, bundle analysis, and resource prioritization.",
                    key_topics=["Core Web Vitals Metrics (LCP, INP, CLS)", "Image Optimization (next/image, WebP/AVIF, responsive sizes)", "Code-Splitting & Dynamic Imports (React.lazy, next/dynamic)", "Font Optimization (next/font, display: swap)", "Bundle Analysis & Tree Shaking"],
                    role_relevance="Directly impacts conversion rates, search engine rankings (Google SEO), and user retention by delivering fast, stutter-free user experiences.",
                    prerequisites=["react", "nextjs"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "web.dev — Core Web Vitals", "url": "https://web.dev/explore/learn-core-web-vitals", "description": "Google's official guide to measuring and optimizing LCP, INP, and CLS metrics."},
                        {"type": "YOUTUBE", "title": "Core Web Vitals Optimization Guide — Web Dev Simplified", "url": "https://www.youtube.com/watch?v=AQqIZg_N1fg", "description": "Practical walkthrough of diagnosing slow LCP, layout shifts (CLS), and sluggish interactions (INP)."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="vitals-prob-1",
                            title="Eliminate Cumulative Layout Shift (CLS)",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Diagnose and eliminate layout instability caused by unsized images and dynamic content.",
                            problem_statement="Refactor a web page with a high CLS score (> 0.25) to achieve a near-zero CLS (< 0.05).",
                            requirements=[
                                "Add explicit width and height (or aspect-ratio) attributes to all images to reserve layout space.",
                                "Reserve space for dynamic advertisements or third-party widgets using min-height containers.",
                                "Use CSS font-display: optional or next/font to eliminate layout shifts caused by font swaps (FOUT)."
                            ],
                            concepts_tested=["Cumulative Layout Shift (CLS)", "Aspect Ratio & Image Dimensions", "Reserved Layout Space", "Font Swapping (FOUT)"],
                            expected_outcome="A rock-solid layout that never jumps or shifts content unexpectedly while assets download.",
                            optional_hints=["CSS 'aspect-ratio: 16 / 9' reserves container space before images finish downloading."]
                        ),
                        make_problem(
                            problem_id="vitals-prob-2",
                            title="Code Splitting & Dynamic Imports with React.lazy",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Reduce initial JavaScript bundle size by lazily loading heavy libraries on demand.",
                            problem_statement="Optimize an application containing a heavy data visualization chart library (e.g. Chart.js, 150KB) to load only when the user opens the analytics tab.",
                            requirements=[
                                "Refactor the Chart component using React.lazy() and dynamic import: React.lazy(() => import('./Chart')).",
                                "Wrap the component in <Suspense fallback={<ChartSkeleton />}>.",
                                "Run a webpack or Next.js bundle analyzer to verify the chart library was extracted into a separate asynchronous chunk."
                            ],
                            concepts_tested=["Code Splitting", "Dynamic Imports", "React.lazy & Suspense", "Bundle Size Reduction", "Async Chunks"],
                            expected_outcome="A 40%+ reduction in initial page load bundle size and significantly faster Largest Contentful Paint.",
                            optional_hints=["In Next.js, use 'next/dynamic' with ssr: false for browser-only dynamic components."]
                        ),
                        make_problem(
                            problem_id="vitals-prob-3",
                            title="Interaction to Next Paint (INP) Optimization with Web Workers",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Eliminate main-thread blocking tasks (> 50ms) to achieve excellent Interaction to Next Paint (INP < 200ms).",
                            problem_statement="Diagnose a slow UI freezing during a heavy data calculation (sorting 100,000 records) and offload the computation to a Web Worker.",
                            requirements=[
                                "Profile the interaction in Chrome DevTools Performance panel, identifying Long Tasks (> 50ms).",
                                "Move the computation into a dedicated Web Worker using workerize or Comlink.",
                                "Communicate between main thread and worker via postMessage and onmessage.",
                                "Verify in Chrome Performance panel that main thread remains completely unblocked during computation."
                            ],
                            concepts_tested=["Interaction to Next Paint (INP)", "Long Tasks Optimization", "Web Workers", "Comlink", "Performance Profiling"],
                            expected_outcome="Silky-smooth user interactions with INP well under 100ms even while massive datasets process in the background.",
                            optional_hints=["Use startTransition in React 19 to mark non-urgent state updates."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

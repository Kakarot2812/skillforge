"""UI/UX Product Designer roadmap definition with progressive practice problems."""
from typing import Any, Dict
from app.db.roadmaps_data.common import ROADMAP_IDS, make_problem, make_skill

UI_UX_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["ui-ux-engineer"],
    "slug": "ui-ux-engineer",
    "role_id": None,
    "title": "UI/UX Product Designer",
    "domain": "Design & Creative",
    "category": "Product & Design",
    "description": "Craft intuitive, accessible, and high-impact digital experiences: user research methodologies, information architecture, systematic visual hierarchy, production Figma component architectures, micro-interactions, WCAG 2.2 accessibility, design tokens for engineering handoff, and data-driven A/B testing validation.",
    "version": "v2.0",
    "has_market_data": False,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Design Foundations, Research & Visual Hierarchy",
            "description": "Qualitative/quantitative user discovery, information architecture, user journeys, typography, and visual systems.",
            "skills": [
                make_skill(
                    slug="user-research",
                    name="User Research & Usability Testing",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="User research methods: user interviews, contextual inquiry, surveys, persona creation, empathy mapping, user journey mapping, and qualitative usability test moderation.",
                    key_topics=["Qualitative vs Quantitative Research", "User Interviewing & Non-Biased Questioning", "Persona & Empathy Map Synthesis", "End-to-End User Journey Mapping", "Moderated & Unmoderated Usability Testing"],
                    role_relevance="Ensures product decisions are grounded in real customer mental models rather than internal team assumptions.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Nielsen Norman Group — User Research Methods", "url": "https://www.nngroup.com/articles/which-ux-research-methods/", "description": "Authoritative guide to selecting qualitative and quantitative user research methods across product lifecycles."},
                        {"type": "YOUTUBE", "title": "UX Research for Beginners — CareerFoundry", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive tutorial covering interview techniques, empathy mapping, and user testing synthesis."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="ux-res-prob-1",
                            title="User Interview Protocol & Empathy Map",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Draft an unbiased user interview guide and synthesize raw observations into an Empathy Map.",
                            problem_statement="For a mobile budgeting application targeting freelance gig workers, formulate a 10-question semi-structured interview script avoiding leading questions. Synthesize simulated interview notes into an Empathy Map (Says, Thinks, Does, Feels) identifying top user pain points and goals.",
                            requirements=[
                                "Formulate open-ended questions eliminating confirmation bias (e.g. avoid 'Do you find budgeting hard?').",
                                "Structure the interview into warmup, core exploration, and wrap-up sections.",
                                "Categorize raw user responses into Says, Thinks, Does, and Feels quadrants.",
                                "Extract at least 3 distinct unmet user needs and emotional friction points."
                            ],
                            concepts_tested=["Interview Script Design", "Unbiased Questioning Techniques", "Empathy Mapping", "Pain Point Extraction"],
                            expected_outcome="A research artifact mapping emotional realities and friction points of target users.",
                            optional_hints=["Ask questions about specific past behavior ('Tell me about the last time you...') rather than hypothetical futures."]
                        ),
                        make_problem(
                            problem_id="ux-res-prob-2",
                            title="End-to-End Customer Journey Map",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Map a comprehensive multi-stage customer journey with touchpoints, emotional curves, and opportunity areas.",
                            problem_statement="Create a visual customer journey map for a telemedicine patient booking and attending a virtual doctor appointment. Chart stages: Discovery, Account Setup, Doctor Selection, Pre-Consultation Waiting, Live Video Call, and Post-Visit Follow-Up.",
                            requirements=[
                                "Define user goals and expectations for each journey stage.",
                                "Map digital and physical touchpoints across devices.",
                                "Plot an emotional experience curve (delight vs frustration) across stages.",
                                "Identify critical friction drop-off risks and propose high-impact UX opportunity interventions."
                            ],
                            concepts_tested=["Customer Journey Mapping", "Touchpoint Analysis", "Emotional Dip Identification", "UX Opportunity Formulation"],
                            expected_outcome="A strategic journey map highlighting the exact moments of user anxiety and drop-off risks.",
                            optional_hints=["The lowest dip in the emotional curve represents the highest-priority product opportunity."]
                        ),
                        make_problem(
                            problem_id="ux-res-prob-3",
                            title="Moderated Usability Test Plan & System Usability Scale (SUS) Audit",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Conduct a moderated usability study on a prototype and quantify satisfaction using the System Usability Scale (SUS).",
                            problem_statement="Develop a moderated usability testing protocol with 4 goal-directed task scenarios for an investment onboarding flow. Formulate a facilitator guide with Think-Aloud instructions, measure task completion rates and time-on-task across 5 participants, and compute the standardized SUS usability score.",
                            requirements=[
                                "Design task scenarios that avoid revealing interface terminology.",
                                "Define the Think-Aloud moderation script and observer note-taking rubric.",
                                "Calculate task completion rate, average time-on-task, and error frequency.",
                                "Administer the 10-question SUS questionnaire and calculate the final composite score (out of 100)."
                            ],
                            concepts_tested=["Moderated Usability Testing", "Think-Aloud Protocol", "Task Completion Metrics", "System Usability Scale (SUS) Scoring"],
                            expected_outcome="A quantitative and qualitative usability evaluation report validating prototype readiness.",
                            optional_hints=["A SUS score above 68 is considered average; above 80 represents exceptional usability."]
                        ),
                    ],
                ),
                make_skill(
                    slug="info-architecture",
                    name="Information Architecture & Wireframing",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Structuring digital products: card sorting, sitemaps, user task flows, low-fidelity wireframing, and cognitive load reduction.",
                    key_topics=["Information Architecture Principles (Chunking, Hierarchy)", "Card Sorting (Open & Closed) with Users", "Sitemaps & Global Navigation Hierarchies", "User Task Flows & Decision Tree Diagrams", "Low-Fidelity Wireframing & Content Scaffolding"],
                    role_relevance="Prevents confusing navigation mazes by organizing complex digital content into intuitive, discoverable hierarchies.",
                    prerequisites=["user-research"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Information Architecture Basics — Usability.gov", "url": "https://www.usability.gov/what-and-why/information-architecture.html", "description": "Authoritative guide to sitemaps, taxonomy, navigation systems, and labeling."},
                        {"type": "YOUTUBE", "title": "Information Architecture Tutorial — CareerFoundry", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on walkthrough of card sorting, tree testing, and creating sitemaps."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="ia-prob-1",
                            title="Card Sorting Analysis & Sitemapping",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Analyze user card sorting results to establish an intuitive navigation sitemap for a multi-category store.",
                            problem_statement="Given 30 diverse product categories from an outdoor equipment retailer, analyze open card sorting data from 20 participants, identify natural conceptual cluster groups, and design a hierarchical website sitemap with primary, secondary, and utility navigation tiers.",
                            requirements=[
                                "Cluster cards based on similarity matrix groupings.",
                                "Establish clear taxonomy labels avoiding industry jargon.",
                                "Diagram a sitemap with primary navigation (max 7 top-level categories adhering to Miller's Law).",
                                "Include breadcrumb trails and footer utility links."
                            ],
                            concepts_tested=["Card Sorting Analysis", "Taxonomy & Labeling", "Miller's Law (Cognitive Chunking)", "Hierarchical Sitemap Design"],
                            expected_outcome="A structured sitemap minimizing navigational depth and cognitive search friction.",
                            optional_hints=["Limit top-level navigation items to 5-7 categories to prevent decision paralysis."]
                        ),
                        make_problem(
                            problem_id="ia-prob-2",
                            title="Multi-Branch User Flow & Decision Tree",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Map a complete user task flow with edge cases, error states, and conditional decision branching.",
                            problem_statement="Design a detailed user flow diagram for a customer filing an insurance claim on a mobile app. Detail decision nodes: photo upload success/failure, estimated repair quote thresholds (<$500 instant approval vs manual adjuster review), and missing document notifications.",
                            requirements=[
                                "Use standard flowchart notation (Rectangles for screens, Diamonds for decisions, Ovals for start/end).",
                                "Map the 'happy path' alongside at least 3 distinct error and branch paths.",
                                "Indicate automated system actions vs explicit user inputs.",
                                "Verify zero dead-end screens: every path reaches a terminal confirmation or recovery screen."
                            ],
                            concepts_tested=["User Task Flow Modeling", "Conditional Branching Logic", "Edge Case & Error State Mapping", "Decision Tree Architecture"],
                            expected_outcome="A comprehensive user flow diagram leaving zero ambiguity for engineering implementation.",
                            optional_hints=["Every diamond decision node must have at least two clearly labeled outgoing branches (Yes/No)."]
                        ),
                        make_problem(
                            problem_id="ia-prob-3",
                            title="Low-Fidelity Responsive Wireframe Suite",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Create responsive low-fidelity wireframes exploring layout hierarchy across mobile, tablet, and desktop breakpoints.",
                            problem_statement="Design low-fidelity wireframes for a content publishing dashboard across 3 breakpoints (Mobile 375px, Tablet 768px, Desktop 1440px). Emphasize information hierarchy, content chunking, and responsive adaptations (collapsible side drawer on mobile -> persistent sidebar on desktop) without visual distractions (color, detailed photography).",
                            requirements=[
                                "Design layouts in grayscale using wireframe placeholders and typography scale.",
                                "Demonstrate responsive reflow: how navigation, data tables, and metrics adapt across breakpoints.",
                                "Establish clear focal points directing user attention to primary calls to action (CTAs).",
                                "Document layout grid annotations (column count, gutter width, margin)."
                            ],
                            concepts_tested=["Responsive Content Scaffolding", "Visual Hierarchy in Grayscale", "Breakpoint Reflow Strategies", "Grid System Specifications"],
                            expected_outcome="A responsive wireframe blueprint ready for high-fidelity visual styling.",
                            optional_hints=["Designing in grayscale forces you to fix structural hierarchy issues rather than masking them with color."]
                        ),
                    ],
                ),
                make_skill(
                    slug="design-systems-visual",
                    name="Design Systems, Typography & Visual Hierarchy",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Visual design foundations: typographic scale, modular spacing systems, color theory (contrast, semantic palettes), grid systems, visual weight, and atomic design methodology.",
                    key_topics=["Typography Systems (Scale, Leading, Kerning, Hierarchy)", "8pt Spacing & Layout Grid Systems", "Color Harmonies & Accessible Contrast (WCAG)", "Visual Hierarchy (Size, Contrast, Proximity, Alignment)", "Atomic Design (Atoms, Molecules, Organisms, Templates)"],
                    role_relevance="Establishes brand consistency, aesthetic polish, and scalable modularity across multi-platform product suites.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Atomic Design by Brad Frost", "url": "https://atomicdesign.bradfrost.com/", "description": "Definitive methodology for creating design systems and modular UI components."},
                        {"type": "YOUTUBE", "title": "Visual Design & Typography Masterclass — Flux Academy", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on tutorial covering typographic scale, grid systems, spacing rules, and visual weight."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="vis-prob-1",
                            title="Modular Typographic & 8pt Spacing Scale",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Establish a mathematical typographic type scale and an 8pt spatial grid for an enterprise web application.",
                            problem_statement="Develop a design foundation system. Define a Major Third (1.250) or Perfect Fourth (1.333) typographic scale from 12px caption up to 48px display heading with matched proportional line-heights. Pair it with an 8pt spacing scale (4, 8, 16, 24, 32, 48, 64px) for margins and padding.",
                            requirements=[
                                "Calculate explicit font sizes, weights, and line-heights for H1, H2, H3, Body, and Caption.",
                                "Ensure line-heights align cleanly with the 4pt/8pt baseline grid.",
                                "Define spacing scale tokens (space-1 through space-8).",
                                "Produce a specimen sheet showing typography and spacing in action across sample UI cards."
                            ],
                            concepts_tested=["Typographic Scale Ratios", "Baseline Grid Alignment", "8pt Spacing System", "Vertical Rhythm"],
                            expected_outcome="A harmonious typographic and spacing specification sheet.",
                            optional_hints=["Proportional line-heights should decrease as font size increases (e.g. 1.5 for body, 1.15 for large display titles)."]
                        ),
                        make_problem(
                            problem_id="vis-prob-2",
                            title="Semantic Color Palette with WCAG AAA Contrast",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Create a complete semantic color system with accessible contrast ratios for both light and dark modes.",
                            problem_statement="Construct a digital product color palette: Brand Primary, Secondary, Neutral Slate (50 to 900), and Semantic states (Success, Warning, Error, Info). Ensure every text-on-background pairing achieves a minimum 4.5:1 contrast (WCAG AA) and 7:1 (WCAG AAA) for normal text, and specify dark mode token mappings.",
                            requirements=[
                                "Generate 10-shade tint and shade scales for each color family (50, 100, ... 900).",
                                "Verify contrast ratios using APCA or WCAG 2.2 color contrast calculators.",
                                "Define semantic functional tokens (e.g. text-primary, bg-surface, border-subtle).",
                                "Map tokens to dark mode alternatives preserving visual hierarchy and perceived contrast."
                            ],
                            concepts_tested=["Semantic Color Systems", "WCAG Contrast Ratios (AA / AAA)", "Tint / Shade Scale Generation", "Dark Mode Semantic Mapping"],
                            expected_outcome="A bulletproof, accessible color system ready for production theme tokens.",
                            optional_hints=["Never use pure pitch black (#000000) for dark mode backgrounds; use deep neutral grays (#121212) to reduce eye strain."]
                        ),
                        make_problem(
                            problem_id="vis-prob-3",
                            title="Atomic Design Component Library Specification",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Structure a comprehensive component library adhering to Atomic Design principles from atoms to organisms.",
                            problem_statement="Specify an atomic design component hierarchy for a SaaS billing dashboard. Build Atoms (Button, Input, Avatar, Badge, Icon), compose into Molecules (FormField, SearchBar, UserSnippet), assemble into Organisms (NavigationBar, PricingCardTable, InvoiceModal), and document component props and variant states.",
                            requirements=[
                                "Document all component states: default, hover, active, focus-visible, disabled, and loading.",
                                "Demonstrate strict modular composition: organisms must be composed exclusively of child molecules and atoms.",
                                "Specify interactive behavior and focus indicator styling.",
                                "Create a comprehensive component catalog specimen showing all variants."
                            ],
                            concepts_tested=["Atomic Design Methodology", "Component State Matrices", "Modular Composition", "Design System Scalability"],
                            expected_outcome="A fully structured atomic UI component architecture ready for high-fidelity prototyping.",
                            optional_hints=["Focus states must have prominent visible focus rings for keyboard accessibility compliance."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — High-Fidelity UI Design & Prototyping",
            "description": "Mastery of Figma auto-layout, component variants, interactive prototyping, and micro-animations.",
            "skills": [
                make_skill(
                    slug="figma-prototyping",
                    name="High-Fidelity UI Design & Prototyping with Figma",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Professional Figma craftsmanship: Auto Layout 5.0, Component Properties, Variants, Component Sets, Variables (color, number, string, boolean), and advanced interactive prototyping with smart animate.",
                    key_topics=["Figma Auto Layout (Resizing, Min/Max, Hug/Fill)", "Component Variants & Component Properties", "Figma Variables & Mode Switching (Light/Dark)", "Interactive Components & Hover/Press States", "Smart Animate & Transition Easing Curves"],
                    role_relevance="The industry-standard collaborative design tool for crafting responsive, interactive, production-ready interfaces.",
                    prerequisites=["design-systems-visual", "info-architecture"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Figma Help Center — Auto Layout & Components", "url": "https://help.figma.com/hc/en-us/articles/360040451373-Explore-auto-layout-properties", "description": "Official Figma guide to auto-layout, responsive constraints, and component architecture."},
                        {"type": "YOUTUBE", "title": "Figma for Beginners Tutorial — Figma Official", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Official masterclass covering frames, auto-layout, component properties, and smart animate prototyping."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="figma-prob-1",
                            title="Responsive Auto-Layout Card with Min/Max Constraints",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Construct a fully responsive card component in Figma using nested Auto Layout and Hug/Fill constraints.",
                            problem_statement="Build a responsive travel accommodation card in Figma. Include a hero image with fixed aspect ratio, favorite heart icon button, badge pills, property title, star rating snippet, price calculation, and primary button. Ensure the card flexes seamlessly from 300px to 600px width with content reflowing naturally without clipping.",
                            requirements=[
                                "Use nested Auto Layout frames with 0 absolute coordinates.",
                                "Set horizontal resizing to 'Fill container' for fluid text elements.",
                                "Apply min-width and max-width constraints on the parent card frame.",
                                "Verify zero text truncation when card is resized across widths."
                            ],
                            concepts_tested=["Figma Auto Layout", "Hug vs Fill Sizing Constraints", "Min / Max Width Constraints", "Responsive Content Reflow"],
                            expected_outcome="A completely responsive Figma card component adapting dynamically to parent frame sizes.",
                            optional_hints=["Use 'Fill container' on text layers inside auto layout to make them wrap automatically when width shrinks."]
                        ),
                        make_problem(
                            problem_id="figma-prob-2",
                            title="Interactive Component Set with Component Properties & Variables",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Architect an enterprise Button component set utilizing Component Properties and Figma Variables.",
                            problem_statement="Build a production Button component set in Figma supporting variants: Type (Primary, Secondary, Ghost, Danger), Size (Sm, Md, Lg), and State (Default, Hover, Active, Disabled, Loading). Utilize Component Properties (boolean icon show/hide, text content, instance swap) and Figma Variables for instant Light/Dark mode switching.",
                            requirements=[
                                "Consolidate variants using Component Properties (Boolean, Text, Instance Swap).",
                                "Map colors and padding to Figma Variables.",
                                "Set up 'While Hovering' and 'While Pressing' interactive component connections with 150ms ease-out transitions.",
                                "Demonstrate instant light/dark mode switching on a test artboard via Variable Modes."
                            ],
                            concepts_tested=["Figma Component Properties", "Variant Matrices", "Figma Variables & Modes", "Interactive Component Prototyping"],
                            expected_outcome="A highly efficient, single-source-of-truth component set replacing dozens of redundant frames.",
                            optional_hints=["Component properties reduce variant count by up to 70% by handling icon toggles and text dynamically."]
                        ),
                        make_problem(
                            problem_id="figma-prob-3",
                            title="High-Fidelity Mobile App Prototype with Smart Animate & Variables",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build an advanced interactive prototype simulating real application logic using Figma Variables and Smart Animate.",
                            problem_statement="Create an end-to-end interactive mobile food delivery prototype. Implement a persistent shopping cart with dynamic item counters and price math driven by Figma Variables (cartCount, totalPrice), expandable bottom sheet modals with drag gestures, and smooth hero image transitions between menu list and item detail views using Smart Animate.",
                            requirements=[
                                "Use Figma Variables with 'Set variable' and conditional 'If/Else' logic on button tap.",
                                "Implement dynamic cart badge incrementing and subtotal calculations.",
                                "Use Smart Animate with custom cubic-bezier easing curves for modal transitions.",
                                "Ensure prototype can be demoed seamlessly in Figma Mirror on a physical device."
                            ],
                            concepts_tested=["Advanced Figma Prototyping", "Variable Logic (Set Variable, Conditions)", "Smart Animate Coordination", "Mobile Device Testing"],
                            expected_outcome="An astonishing high-fidelity prototype indistinguishable from a native mobile application.",
                            optional_hints=["Matching layer names and hierarchical structures across frames is required for Smart Animate to interpolate smoothly."]
                        ),
                    ],
                ),
                make_skill(
                    slug="interaction-design-animation",
                    name="Interaction Design & Micro-Animations",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Motion design and digital feedback: physics-based animations (springs, friction), easing curves (cubic-bezier), micro-interactions, skeleton loading transitions, and choreography.",
                    key_topics=["The 12 Principles of Animation Applied to UI", "Easing Curves (Ease-In, Ease-Out, Spring Physics)", "Micro-Interactions & Instant Sensory Feedback", "Choreography & Staggered Page Reveals", "Skeleton Screens & Perceived Performance"],
                    role_relevance="Elevates software from sterile utility to a delightful, living product that intuitively communicates state changes.",
                    prerequisites=["figma-prototyping"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Material Design 3 — Motion & Animation", "url": "https://m3.material.io/styles/motion/overview", "description": "Official Google guide to choreography, easing, duration tokens, and expressive motion in UI."},
                        {"type": "YOUTUBE", "title": "Micro-Interactions & UI Animation — Flux Academy", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Practical guide to designing delight-inducing micro-interactions and transitions in web and mobile apps."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="motion-prob-1",
                            title="Playful Like Button Micro-Interaction",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Design a rewarding micro-interaction with scale popping, color morphing, and particle bursts.",
                            problem_statement="Design a Twitter/Instagram-style like button interaction. When clicked, the heart icon shrinks slightly (0.8x), bursts outward (1.3x) with spring overshoot, fills with vibrant crimson gradient, and emits 6 tiny dispersing particle dots that fade out.",
                            requirements=[
                                "Define keyframe states: idle, press (anticipation), burst (overshoot), and settled.",
                                "Specify precise cubic-bezier or spring parameters (stiffness, damping).",
                                "Keep total animation duration under 400ms to avoid delaying user action.",
                                "Prototype the interaction in Figma using Smart Animate or create a CSS keyframe specification."
                            ],
                            concepts_tested=["Micro-Interaction Lifecycle", "Anticipation & Overshoot (Spring Physics)", "Particle FX in UI", "Duration Optimization (<400ms)"],
                            expected_outcome="A delightfully tactile micro-interaction that provides immediate sensory gratification.",
                            optional_hints=["UI animations should feel snappy and energetic; never make micro-interactions longer than 400ms."]
                        ),
                        make_problem(
                            problem_id="motion-prob-2",
                            title="Skeleton Screen Shimmer & Staggered Content Reveal",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Design perceived-performance loading states with skeleton shimmers and orchestrated content fades.",
                            problem_statement="For a slow data-loading newsfeed, design an animated skeleton loading screen with a subtle diagonal light shimmer. When data resolves, smoothly morph skeleton rectangles into rich images and text using staggered cascade transitions (20ms delay between cards) rather than abrupt popping.",
                            requirements=[
                                "Design skeleton shapes matching the exact geometry of incoming content.",
                                "Specify a continuous 1.5-second looping gradient shimmer across skeleton blocks.",
                                "Choreograph a staggered entrance animation (cards slide up 8px and fade in with 30ms offset).",
                                "Explain how perceived load time improves over generic spinning wheels."
                            ],
                            concepts_tested=["Skeleton Loading Design", "Shimmer Wave Effects", "Staggered Choreography", "Perceived Performance Optimization"],
                            expected_outcome="A fluid loading transition that significantly reduces perceived wait times for users.",
                            optional_hints=["Skeleton screens give users an instant cognitive anchor of the upcoming content structure."]
                        ),
                        make_problem(
                            problem_id="motion-prob-3",
                            title="Complex Bottom Sheet Gesture Physics & Sheet Snapping",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Specify fluid touch-gesture physics for an interactive bottom sheet with velocity-based snap points.",
                            problem_statement="Design an interactive bottom sheet modal with 3 snap points: Minimized (80px preview), Half-Expanded (50% viewport), and Fully Expanded (95% viewport). Specify gesture handling: sheet tracks user finger 1:1, calculates release velocity (fling) to snap to the nearest target, and applies rubber-banding resistance if pulled beyond bounds.",
                            requirements=[
                                "Define math and states for 3 discrete snap point thresholds.",
                                "Specify velocity threshold (>500px/s) triggering snap-to-next regardless of current position.",
                                "Define rubber-banding resistance curve (decay factor 0.5) when dragged past 95% height.",
                                "Provide developer-ready motion specs including spring damping ratios and mass coefficients."
                            ],
                            concepts_tested=["Gesture-Driven Motion", "Velocity-Based Snap Points", "Rubber-Banding Physics", "Developer Motion Specifications"],
                            expected_outcome="A complete gesture motion specification ready for production iOS and Android implementation.",
                            optional_hints=["A fast downward flick should dismiss the sheet even if released in the top third of the screen."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Accessibility, Inclusivity & Engineering Handoff",
            "description": "WCAG 2.2 accessibility compliance, screen reader mental models, design tokens, and developer collaboration.",
            "skills": [
                make_skill(
                    slug="accessibility-inclusive-design",
                    name="Digital Accessibility (WCAG 2.2) & Inclusive Design",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Designing for all abilities: WCAG 2.2 guidelines (Perceivable, Operable, Understandable, Robust), color blindness considerations, screen reader accessibility trees, keyboard navigation focus indicators, and touch target sizes.",
                    key_topics=["WCAG 2.2 Guidelines (Level A, AA, AAA)", "Accessible Color Contrast & Colorblind Simulations", "Keyboard Navigation Flow & Visible Focus Rings", "Accessible Form Inputs & Error Announcements", "Minimum Touch Targets (48x48px / 44x44pt)"],
                    role_relevance="Guarantees that digital products are legally compliant, ethically sound, and universally usable by people of all abilities.",
                    prerequisites=["design-systems-visual"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "W3C Web Content Accessibility Guidelines (WCAG) 2.2", "url": "https://www.w3.org/TR/WCAG22/", "description": "Official international standard for web and digital interface accessibility specifications."},
                        {"type": "YOUTUBE", "title": "Accessibility in UI/UX Design — CareerFoundry", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive tutorial on designing accessible color palettes, touch targets, and keyboard flows."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="a11y-prob-1",
                            title="Accessibility Audit & Colorblindness Simulation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Audit an existing UI screen for WCAG violations and simulate multiple forms of color vision deficiency.",
                            problem_statement="Take a dense dashboard screen showing status indicators and financial charts. Run a color blindness simulation (Protanopia, Deuteranopia, Tritanopia). Identify information conveyed solely through color (e.g. green for profit, red for loss), and redesign indicators to include secondary cues (icons, text labels, line patterns).",
                            requirements=[
                                "Identify all violations of WCAG 1.4.1 (Use of Color).",
                                "Simulate views under red-green and blue-yellow color deficiencies using Figma plugins (Stark, Color Blind).",
                                "Incorporate redundant visual cues (shapes, icons, distinct stroke patterns).",
                                "Ensure text contrast meets minimum 4.5:1 ratio across all revised elements."
                            ],
                            concepts_tested=["WCAG 1.4.1 (Use of Color)", "Color Vision Deficiency Simulation", "Redundant Visual Coding", "Contrast Verification"],
                            expected_outcome="A redesigned dashboard fully decipherable regardless of color perception capabilities.",
                            optional_hints=["Never rely on color alone to communicate state, warnings, or differences."]
                        ),
                        make_problem(
                            problem_id="a11y-prob-2",
                            title="Keyboard Navigation Flow & Focus Indicator Specification",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Map logical tab order and design high-visibility focus indicators across an interactive modal dialog.",
                            problem_statement="Design an accessible checkout modal dialog. Map the exact sequential Tab and Shift-Tab keyboard navigation order, specify focus traps preventing keyboard focus from escaping the modal behind the scrim, specify ESC key dismissal, and design high-contrast visible focus indicators for all interactive elements.",
                            requirements=[
                                "Annotate keyboard tab order sequence across all form fields and buttons.",
                                "Specify focus trap behavior: tabbing past the last button wraps focus back to the first field.",
                                "Design a 2px offset focus ring with a 3:1 contrast ratio against both component and background.",
                                "Document aria-label and aria-describedby annotations for screen readers."
                            ],
                            concepts_tested=["Keyboard Tab Order Navigation", "Focus Traps in Modals", "Visible Focus Ring Design (WCAG 2.4.7)", "ARIA Annotation Specifications"],
                            expected_outcome="A comprehensive keyboard accessibility spec ensuring 100% mouse-free usability.",
                            optional_hints=["Focus rings must stand out against both the component and the surrounding background surface."]
                        ),
                        make_problem(
                            problem_id="a11y-prob-3",
                            title="Full Accessibility Spec & Screen Reader Hierarchy",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Create a complete accessibility handoff specification detailing heading hierarchies, alt text, and live regions.",
                            problem_statement="Produce an enterprise accessibility handoff document for a complex product page. Specify: semantic heading hierarchy (H1 -> H2 -> H3 with zero skipped levels), descriptive alt text for product imagery, aria-live announcements for dynamic price updates, and verify that all interactive touch targets meet minimum 48x48px boundaries.",
                            requirements=[
                                "Map heading hierarchy ensuring logical document outline.",
                                "Write contextual alt text distinguishing informative images from purely decorative graphics.",
                                "Specify aria-live='polite' regions for cart updates and error banners.",
                                "Audit touch target bounding boxes to ensure minimum 48x48px (or 44x44pt on iOS) spacing."
                            ],
                            concepts_tested=["Semantic Heading Hierarchies", "Screen Reader Alt Text Strategy", "ARIA Live Regions", "Touch Target Size Compliance"],
                            expected_outcome="A formal accessibility handoff package eliminating compliance ambiguity for engineering teams.",
                            optional_hints=["Decorative graphics should have empty alt='' attributes so screen readers silently ignore them."]
                        ),
                    ],
                ),
                make_skill(
                    slug="developer-handoff-tokens",
                    name="Developer Handoff, Design Tokens & Component Specs",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Bridging design and engineering: Design Tokens (W3C community group standard), token tiers (global, semantic, component), Figma Dev Mode, redlining, and component specification documentation.",
                    key_topics=["Design Tokens Architecture (Global, Semantic, Component Tiers)", "W3C Design Token JSON Format", "Figma Dev Mode & Code Generation", "Redlining, Layout Grids & Spacing Annotations", "Managing Design System Versioning & Deprecations"],
                    role_relevance="Transforms static mockups into a shared, machine-readable language connecting Figma directly to CSS and native codebases.",
                    prerequisites=["figma-prototyping", "design-systems-visual"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Design Tokens Community Group (W3C)", "url": "https://design-tokens.github.io/community-group/format/", "description": "Official community standard specification for defining design tokens in JSON."},
                        {"type": "YOUTUBE", "title": "Design Tokens & Developer Handoff — Femke Design", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Practical guide to setting up design tokens in Figma and exporting to GitHub for frontend developers."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="hand-prob-1",
                            title="W3C Design Token JSON Architecture",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Structure a three-tier design token architecture formatted in standard W3C Design Token JSON.",
                            problem_statement="Author a design token JSON file defining a 3-tier hierarchy: Tier 1 Global tokens (colors.blue.500: #3b82f6), Tier 2 Semantic tokens (color.brand.primary: { $value: '{colors.blue.500}' }), and Tier 3 Component tokens (button.primary.bg: { $value: '{color.brand.primary}' }).",
                            requirements=[
                                "Follow the official W3C Design Tokens Community Group JSON schema format.",
                                "Use alias references ({parent.child}) to link semantic tokens to primitive values.",
                                "Include $type ('color', 'dimension', 'duration') attributes on all token definitions.",
                                "Validate JSON structure against standard design token schema validators."
                            ],
                            concepts_tested=["Design Token Tier Architecture", "W3C Token JSON Schema", "Token Aliasing & Inheritance", "Type Specification"],
                            expected_outcome="A machine-readable design token file capable of compilation into CSS variables and iOS Swift enums.",
                            optional_hints=["Three-tier token architectures allow global color palette updates without touching individual component tokens."]
                        ),
                        make_problem(
                            problem_id="hand-prob-2",
                            title="Interactive Component Specification Sheet",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Create a comprehensive developer handoff spec sheet with redlines, token mappings, and edge cases.",
                            problem_statement="Produce a comprehensive developer handoff spec for an avatar upload component. Annotate exact pixel dimensions, auto-layout padding, border-radius tokens, typography styles, file size error validation messages, hover/loading states, and responsive behavior.",
                            requirements=[
                                "Annotate every visual property with its corresponding design token name (never hardcoded hex/pixels).",
                                "Provide clear layout redlines and spacing callouts.",
                                "Document edge case behaviors (e.g. extremely long file names, non-square image cropping).",
                                "Specify accessibility attributes and keyboard focus indicator parameters."
                            ],
                            concepts_tested=["Developer Redlining", "Design Token Mapping", "Edge Case Specification", "Component Handoff Documentation"],
                            expected_outcome="A flawless handoff specification enabling engineers to build the component with zero guesswork.",
                            optional_hints=["Always map measurements directly to token names (e.g. 'space-4') rather than raw numbers ('16px')."]
                        ),
                        make_problem(
                            problem_id="hand-prob-3",
                            title="Automated Token Sync Pipeline: Figma to GitHub",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build an automated CI/CD synchronization pipeline exporting tokens from Figma to GitHub as CSS and TypeScript variables.",
                            problem_statement="Configure a pipeline using Tokens Studio or Figma Variables REST API. When design tokens update in Figma, trigger an automated GitHub Action workflow using Style Dictionary to transform token JSON into compiled CSS custom properties (--color-brand-primary) and TypeScript type definitions, opening an automated pull request.",
                            requirements=[
                                "Configure Style Dictionary configuration (config.json) for CSS and TypeScript platforms.",
                                "Set up GitHub Action workflow triggered via repository dispatch or webhook.",
                                "Generate output files: dist/tokens.css and dist/tokens.ts.",
                                "Ensure build creates an automated, documented Pull Request with token diffs."
                            ],
                            concepts_tested=["Style Dictionary Compilation", "Figma to Code Automation", "GitHub Actions CI/CD for Design", "Automated Token Pull Requests"],
                            expected_outcome="A continuous design-to-code pipeline ensuring codebases automatically reflect Figma token updates.",
                            optional_hints=["Style Dictionary transforms token JSON into CSS, SCSS, Android XML, and iOS Swift formats in one build."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Product Analytics & Growth Experimentation",
            "description": "Data-informed product design: UX metrics, behavioral analytics, A/B testing design, and hypothesis validation.",
            "skills": [
                make_skill(
                    slug="product-metrics-ab-testing",
                    name="Product Metrics, A/B Testing & Design Validation",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Data-informed product design: Google HEART framework, qualitative vs quantitative feedback, conversion funnels, heatmaps/session replays, and designing statistically valid A/B test experiments.",
                    key_topics=["Google HEART Framework (Happiness, Engagement, Adoption, Retention, Task Success)", "Funnel Analysis & Drop-Off Diagnosis", "Heatmaps & Session Recording Analysis (Hotjar, PostHog)", "A/B Testing Hypothesis Formulation & MDE", "Ethical Growth Design vs Dark Patterns"],
                    role_relevance="Empowers designers to measure real user impact, defend design decisions with data, and drive measurable business outcomes.",
                    prerequisites=["user-research", "figma-prototyping"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Google Research — Measuring the User Experience with HEART", "url": "https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-an-approach-to-a-scale-product-metric/", "description": "Authoritative paper detailing Google's HEART framework for large-scale UX metrics."},
                        {"type": "YOUTUBE", "title": "A/B Testing & Product Metrics for Designers — Product Faculty", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on guide to defining UX metrics, designing experiment variants, and analyzing results."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="metric-prob-1",
                            title="HEART Framework UX Metric Specification",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Apply the Google HEART framework to define actionable goals, signals, and metrics for a SaaS collaboration tool.",
                            problem_statement="For a team messaging application, construct a complete HEART framework matrix covering all 5 dimensions (Happiness, Engagement, Adoption, Retention, Task Success). For each dimension, define 1 Goal, 1 Observable Signal, and 1 Concrete Metric tracked via product analytics.",
                            requirements=[
                                "Define clear user-centric Goals (avoiding purely internal revenue goals).",
                                "Specify the lower-level behavioral Signals that indicate goal achievement.",
                                "Formulate concrete, measurable Metrics (e.g. 7-day active user ratio, CSAT score, task completion time).",
                                "Prioritize the top 2 north-star metrics that best represent product health."
                            ],
                            concepts_tested=["Google HEART Framework", "Goals-Signals-Metrics Process", "Behavioral Product Analytics", "North Star Metric Identification"],
                            expected_outcome="A complete UX measurement framework aligning user satisfaction with business growth.",
                            optional_hints=["Goals express what user experience should look like; Signals are the observable behaviors indicating it."]
                        ),
                        make_problem(
                            problem_id="metric-prob-2",
                            title="Conversion Funnel Diagnosis & Qualitative Triangulation",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Diagnose severe drop-offs in a checkout conversion funnel by triangulating funnel metrics with session recordings.",
                            problem_statement="An analytics dashboard reveals a 60% drop-off between 'Shipping Address' and 'Payment Selection'. Review simulated heatmap click patterns and session recording notes to uncover the root cause (unclear shipping fee disclosures and broken autofill), and propose a validated UX redesign resolving the friction.",
                            requirements=[
                                "Analyze drop-off percentages across all funnel stages.",
                                "Identify user rage clicks and dead clicks from heatmap data.",
                                "Formulate a diagnostic hypothesis explaining why users abandon at this specific stage.",
                                "Design a revised checkout step eliminating hidden fees and streamlining address input."
                            ],
                            concepts_tested=["Funnel Drop-Off Analysis", "Heatmap & Session Replay Interpretation", "Rage Click Diagnosis", "Checkout Flow Optimization"],
                            expected_outcome="A data-backed UX redesign directly addressing validated user drop-off causes.",
                            optional_hints=["Rage clicks (repeated rapid clicking on the same spot) strongly indicate broken elements or misleading affordances."]
                        ),
                        make_problem(
                            problem_id="metric-prob-3",
                            title="A/B Test Experiment Design & Sample Size Calculation",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Formulate a statistically sound A/B test proposal with hypothesis, variants, sample size, and guardrail metrics.",
                            problem_statement="Design a comprehensive A/B test to improve freemium-to-paid conversion. Draft a formal hypothesis, design Control (current layout) vs Variant (interactive pricing calculator with social proof), calculate required sample size based on baseline conversion rate (3%) and Minimum Detectable Effect (15% relative lift) at 95% statistical power, and define guardrail metrics to prevent unintended churn.",
                            requirements=[
                                "Structure formal hypothesis: 'If we [change], then [outcome] because [rationale]'.",
                                "Design Control and Variant artboards in Figma.",
                                "Calculate required sample size and experiment duration based on traffic volume.",
                                "Define primary metric (paid conversion) and guardrail metrics (support ticket volume, refund requests)."
                            ],
                            concepts_tested=["A/B Test Design Methodology", "Statistical Power & Minimum Detectable Effect (MDE)", "Sample Size Calculation", "Guardrail Metric Safeguards"],
                            expected_outcome="A rigorous experimentation brief ready for engineering feature flagging and execution.",
                            optional_hints=["Guardrail metrics ensure an experiment that improves conversion doesn't secretly increase refund rates or complaints."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

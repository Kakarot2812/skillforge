"""Android Developer roadmap definition with deep modern tech stack and progressive practice problems."""
from typing import Any, Dict
from app.db.roadmaps_data.common import ROADMAP_IDS, make_problem, make_skill

ANDROID_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["android-developer"],
    "slug": "android-developer",
    "role_id": None,
    "title": "Android Developer",
    "domain": "Mobile Development",
    "category": "Engineering",
    "description": "Master modern Android development using Kotlin, Jetpack Compose, Material 3, Coroutines & Flow, Hilt dependency injection, Room persistence, and production testing.",
    "version": "v2.0",
    "has_market_data": False,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Kotlin & Mobile Foundations",
            "description": "Master Kotlin syntax, expressive functional paradigms, null safety, and asynchronous concurrency fundamentals.",
            "skills": [
                make_skill(
                    slug="kotlin-fundamentals",
                    name="Kotlin Fundamentals",
                    difficulty="BEGINNER",
                    description="Idiomatic Kotlin programming covering type inference, null safety, higher-order functions, lambdas, data classes, collections, and generics.",
                    key_topics=["Null Safety & Smart Casts", "Data Classes & Sealed Interfaces", "Higher-Order Functions & Lambdas", "Collections & Transformations (map, filter, fold)", "Generics & Variance"],
                    role_relevance="The premier first-class language for modern Android application engineering, eliminating NullPointerExceptions and boilerplate.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Kotlin Official Documentation & Tour", "url": "https://kotlinlang.org/docs/home.html", "description": "Official language guide, standard library API reference, and interactive tutorials."},
                        {"type": "YOUTUBE", "title": "Kotlin Course for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=F9UC9DY-vIU", "description": "Comprehensive walkthrough of Kotlin syntax, object-oriented principles, and functional features."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="kotlin-fundamentals-prob-1",
                            title="Safe Inventory Tracker",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master Kotlin null safety, smart casts, and basic control flow.",
                            problem_statement="Build a command-line inventory processor in Kotlin that handles nullable inputs without crashing.",
                            requirements=[
                                "Define an Item data class with nullable properties: id: String, name: String, price: Double?, stock: Int?.",
                                "Implement a function calculateTotalValue(items: List<Item?>): Double that safely skips null items using the safe call operator and Elvis operator.",
                                "Use smart casting with 'when' expressions to categorize item status based on stock count."
                            ],
                            concepts_tested=["Null Safety", "Safe Call Operator", "Elvis Operator", "Smart Casts", "Data Classes"],
                            expected_outcome="A robust calculation function that returns 0.0 for empty or entirely null lists and exact totals for valid items.",
                            optional_hints=["Use items.filterNotNull() or items.mapNotNull { it.price?.times(it.stock ?: 0) }."]
                        ),
                        make_problem(
                            problem_id="kotlin-fundamentals-prob-2",
                            title="Functional Order Processing Pipeline",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Combine higher-order functions, lambdas, and sealed interfaces for stateful domain modeling.",
                            problem_statement="Create an order processing pipeline that transforms raw orders, computes discounts, and models status using sealed hierarchies.",
                            requirements=[
                                "Create a sealed interface OrderResult with subclasses: Success(total: Double), DiscountApplied(original: Double, discounted: Double), and Rejected(reason: String).",
                                "Implement a processing pipeline utilizing higher-order functions: map, filter, groupBy, and fold.",
                                "Apply custom discount lambdas passed into the processing function dynamically."
                            ],
                            concepts_tested=["Sealed Interfaces", "Higher-Order Functions", "Lambdas", "Collection Transformations", "Pattern Matching"],
                            expected_outcome="A functional pipeline that outputs strongly-typed OrderResult instances verified with comprehensive unit assertions.",
                            optional_hints=["Sealed interfaces allow exhaustive 'when' statements without an 'else' branch."]
                        ),
                        make_problem(
                            problem_id="kotlin-fundamentals-prob-3",
                            title="Generic Observable Repository Store",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement an in-memory generic entity store with covariance/contravariance and custom DSL builders.",
                            problem_statement="Develop a production-style in-memory repository store supporting generic entity types with CRUD operations and filtering criteria.",
                            requirements=[
                                "Define a generic interface Repository<T : Identifiable> with add, findById, update, and delete methods.",
                                "Implement an InMemoryRepository<T> using thread-safe collections and Kotlin reified inline types for class inspection.",
                                "Build a custom Kotlin DSL function repositoryQuery { filter { ... }; sortBy { ... } } using extension functions with receiver."
                            ],
                            concepts_tested=["Generics & Type Constraints", "Inline Functions & Reified Types", "DSL Builders", "Extension Functions with Receiver"],
                            expected_outcome="A reusable, type-safe in-memory storage component supporting complex queries through idiomatic Kotlin DSL syntax.",
                            optional_hints=["Use inline fun <reified T> to preserve generic type information at runtime."]
                        ),
                    ],
                ),
                make_skill(
                    slug="git-mobile",
                    name="Git & Version Control for Android",
                    difficulty="BEGINNER",
                    description="Version control practices tailored for Android projects, including .gitignore standards, branching strategies, and handling Gradle merge conflicts.",
                    key_topics=["Android .gitignore Standards", "Feature Branching & Trunk-Based Development", "Handling Gradle & XML Merge Conflicts", "Git Tags & Release Semantic Versioning"],
                    role_relevance="Essential for team collaboration, managing continuous integration pipelines, and tracking multi-version mobile app releases.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Git Official Documentation", "url": "https://git-scm.com/doc", "description": "Complete manual for Git commands, workflows, and branching."},
                        {"type": "YOUTUBE", "title": "Git for Android Developers", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "description": "Hands-on guide to Git workflows, ignoring build caches, and managing Android projects."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="git-mobile-prob-1",
                            title="Standard Android Repository Setup",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Configure an Android Git repository with proper build exclusions and initial commits.",
                            problem_statement="Initialize an Android project git repository and configure .gitignore to ignore all IDE caches, Gradle wrappers, and build artifacts.",
                            requirements=[
                                "Initialize a Git repository and configure user details.",
                                "Create an production-ready .gitignore file excluding .gradle/, build/, local.properties, and .idea/.",
                                "Execute an initial structured commit following Conventional Commits format."
                            ],
                            concepts_tested=["Git Init", "Android .gitignore", "Staging", "Conventional Commits"],
                            expected_outcome="A clean repository where build artifacts and secrets (local.properties) are never tracked by Git.",
                            optional_hints=["Reference github/gitignore repository for Android standards."]
                        ),
                        make_problem(
                            problem_id="git-mobile-prob-2",
                            title="Feature Branching & Conflict Resolution",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Simulate concurrent feature development and resolve conflicting dependency declarations in build.gradle.kts.",
                            problem_statement="Manage two divergent feature branches modifying build.gradle.kts dependencies and resolve the resulting merge conflict cleanly.",
                            requirements=[
                                "Create feature/upgrade-compose and feature/add-retrofit branches from main.",
                                "Introduce conflicting version numbers for a shared dependency on both branches.",
                                "Merge feature/upgrade-compose into main, then merge main into feature/add-retrofit and manually resolve the conflict.",
                                "Verify project builds cleanly following resolution."
                            ],
                            concepts_tested=["Branching", "Merging", "Merge Conflict Resolution", "Gradle Script Tracking"],
                            expected_outcome="A merged commit history with both features integrated and no corrupted Gradle syntax.",
                            optional_hints=["Use 'git merge --no-ff' or interactive rebase to observe branch graph structure."]
                        ),
                        make_problem(
                            problem_id="git-mobile-prob-3",
                            title="Interactive Rebase & Release Tagging Workflow",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Clean feature branch commit histories and create cryptographically signed release tags for Google Play deployment.",
                            problem_statement="Clean a messy commit history of 'fix typo' and 'WIP' commits using interactive rebase, then produce a tagged release v1.0.0.",
                            requirements=[
                                "Use 'git rebase -i' to squash 5 development commits into 2 atomic, semantic commits.",
                                "Tag the release commit with an annotated tag 'v1.0.0' with release notes in the tag message.",
                                "Verify the git log graph visually matches clean trunk-based development standards."
                            ],
                            concepts_tested=["Interactive Rebase", "Squashing Commits", "Annotated Tags", "Release Management"],
                            expected_outcome="A spotless Git history with clear atomic commits and an annotated semantic release tag.",
                            optional_hints=["Use 'git log --oneline --graph --decorate' to inspect the clean commit history."]
                        ),
                    ],
                ),
                make_skill(
                    slug="kotlin-coroutines-flow",
                    name="Kotlin Coroutines & Flow",
                    difficulty="INTERMEDIATE",
                    description="Asynchronous programming with structured concurrency, CoroutineScope, Dispatchers, suspend functions, Flow, StateFlow, and SharedFlow.",
                    key_topics=["Structured Concurrency & CoroutineScope", "Dispatchers (Main, IO, Default)", "Suspend Functions & Exception Handling", "Cold Streams with Flow", "Hot Streams: StateFlow vs SharedFlow"],
                    role_relevance="The backbone of non-blocking Android development, replacing callbacks and RxJava for network calls, database queries, and reactive UI state.",
                    prerequisites=["kotlin-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Kotlin Coroutines Official Guide", "url": "https://kotlinlang.org/docs/coroutines-overview.html", "description": "Official guides to coroutines, channels, and flows with interactive examples."},
                        {"type": "YOUTUBE", "title": "Kotlin Coroutines & Flow — Philipp Lackner", "url": "https://www.youtube.com/watch?v=6manrgZXgTo", "description": "Practical mobile deep dive into Dispatchers, structured concurrency, and Flow operators."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="kotlin-coroutines-flow-prob-1",
                            title="Async Data Fetcher with Cancellation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Use suspend functions and Dispatchers to execute background tasks safely.",
                            problem_statement="Implement a suspend function that fetches user profile data off the main thread with proper cancellation support.",
                            requirements=[
                                "Create a suspend fun fetchUserData(userId: String): UserData that switches to Dispatchers.IO.",
                                "Incorporate cooperative cancellation using yield() or ensureActive().",
                                "Simulate network delay and handle CancellationException properly."
                            ],
                            concepts_tested=["Suspend Functions", "Dispatchers.IO", "Cooperative Cancellation", "Exception Handling"],
                            expected_outcome="A non-blocking function that returns data when active and terminates immediately when cancelled without leaking resources.",
                            optional_hints=["Never catch CancellationException and swallow it; rethrow or let it propagate."]
                        ),
                        make_problem(
                            problem_id="kotlin-coroutines-flow-prob-2",
                            title="Reactive Search Query Flow",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Build a reactive text search stream using Flow operators for debouncing and deduplication.",
                            problem_statement="Create a search flow that takes raw user typing events and produces debounced, distinct API search queries.",
                            requirements=[
                                "Accept an input Flow<String> representing typing input.",
                                "Apply debounce(300L) to prevent spamming search requests.",
                                "Apply filter { it.isNotBlank() } and distinctUntilChanged() to discard duplicate queries.",
                                "Use flatMapLatest to cancel previous in-flight searches when a new query arrives."
                            ],
                            concepts_tested=["Flow Transformation", "debounce", "distinctUntilChanged", "flatMapLatest", "Backpressure"],
                            expected_outcome="A resilient search pipeline that emits only valid, debounced query terms and automatically cancels obsolete queries.",
                            optional_hints=["flatMapLatest cancels the previous collection block as soon as a new emission arrives."]
                        ),
                        make_problem(
                            problem_id="kotlin-coroutines-flow-prob-3",
                            title="Production StateFlow Store with Error Recovery",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement an event-driven StateFlow store managing UI state, one-off events, and automatic retry policies.",
                            problem_statement="Build a state management container exposing StateFlow<UiState> and SharedFlow<UiEvent> with exponential backoff retry.",
                            requirements=[
                                "Define UiState (Loading, Success, Error) and one-time UiEvent (ShowToast, Navigate).",
                                "Expose private MutableStateFlow as public read-only StateFlow.",
                                "Implement a retry policy with exponential backoff on network failures using the retryWhen Flow operator.",
                                "Emit one-time snackbar/toast events via SharedFlow without state replay."
                            ],
                            concepts_tested=["StateFlow", "SharedFlow", "retryWhen Exponential Backoff", "Unidirectional Data Flow", "Coroutine Exception Handlers"],
                            expected_outcome="A production-grade reactive store that maintains UI state reliably through network interruptions.",
                            optional_hints=["Use MutableSharedFlow(replay = 0) for one-off events to prevent replay on configuration changes."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Android Core Fundamentals",
            "description": "Understand the Android runtime, application lifecycle, system components, manifest configuration, and Gradle build automation.",
            "skills": [
                make_skill(
                    slug="android-sdk-studio",
                    name="Android Studio & Android SDK",
                    difficulty="BEGINNER",
                    description="Essential Android system architecture: Activities, Activity Lifecycle, Intents, Manifest permissions, resources, configuration changes, and Logcat debugging.",
                    key_topics=["Activity Lifecycle & State Restoration", "AndroidManifest.xml & Runtime Permissions", "Explicit & Implicit Intents", "Resource Qualifiers (strings, drawables, layouts)", "Logcat & Android Profiler Debugging"],
                    role_relevance="Fundamental understanding of the Android OS environment and process lifecycle necessary to prevent crashes and memory leaks.",
                    prerequisites=["kotlin-fundamentals", "git-mobile"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Android Developers — Core Fundamentals", "url": "https://developer.android.com/guide", "description": "Official documentation covering activities, tasks, resources, and application architecture."},
                        {"type": "YOUTUBE", "title": "Android Development for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=fis26HvvDII", "description": "Comprehensive tutorial on Android Studio, activities, intents, and runtime behavior."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="android-sdk-studio-prob-1",
                            title="Lifecycle Logger & State Preserver",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Track Activity lifecycle transitions and survive device screen rotations without data loss.",
                            problem_statement="Build an Android Activity that logs every lifecycle callback with Logcat and restores user input across configuration changes.",
                            requirements=[
                                "Implement onCreate, onStart, onResume, onPause, onStop, onDestroy, and onRestart with detailed Logcat logging.",
                                "Save a counter and text input state in onSaveInstanceState(outState: Bundle).",
                                "Restore the saved state in onCreate or onRestoreInstanceState."
                            ],
                            concepts_tested=["Activity Lifecycle", "Configuration Changes", "Bundle State Restoration", "Logcat"],
                            expected_outcome="An activity that retains counter values when rotated between portrait and landscape modes.",
                            optional_hints=["Test by enabling 'Don't keep activities' in Developer Options."]
                        ),
                        make_problem(
                            problem_id="android-sdk-studio-prob-2",
                            title="Intent & Runtime Permission Coordinator",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Request dangerous runtime permissions and coordinate explicit and implicit Intents.",
                            problem_statement="Create a multi-activity flow that checks camera/gallery permissions and launches an implicit Intent to share text or images.",
                            requirements=[
                                "Declare CAMERA permission in AndroidManifest.xml and request it at runtime using ActivityResultContracts.RequestPermission.",
                                "Handle permission granted, denied, and 'shouldShowRequestPermissionRationale' UI flows gracefully.",
                                "Launch an implicit Intent with Intent.ACTION_SEND to share a text message across third-party apps."
                            ],
                            concepts_tested=["Runtime Permissions", "ActivityResultContracts", "Explicit Intents", "Implicit Intents", "Permission Rationale"],
                            expected_outcome="A permission-compliant flow that educates users on rationale and shares data seamlessly via Android's system chooser.",
                            optional_hints=["Use Intent.createChooser() for a consistent sharing dialog across OEM devices."]
                        ),
                        make_problem(
                            problem_id="android-sdk-studio-prob-3",
                            title="Deep Link & Task Stack Navigator",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Configure deep links with custom schemes and manage backstack navigation tasks.",
                            problem_statement="Configure intent filters for deep linking (e.g. skillforge://item/{id}) and construct a synthetic backstack using TaskStackBuilder.",
                            requirements=[
                                "Configure an <intent-filter> in AndroidManifest.xml handling a custom URI scheme with host and path prefixes.",
                                "Parse the target entity ID from the incoming deep link Intent in onCreate / onNewIntent.",
                                "Construct a proper backstack using TaskStackBuilder so pressing the system back button returns to the home screen rather than exiting."
                            ],
                            concepts_tested=["Deep Linking", "Intent Filters", "TaskStackBuilder", "Backstack Management", "SingleTop Launch Mode"],
                            expected_outcome="Clicking a test deep link URL launches the target detail screen and maintains proper hierarchical backstack navigation.",
                            optional_hints=["Test deep links from terminal using: adb shell am start -W -a android.intent.action.VIEW -d \"skillforge://item/42\"."]
                        ),
                    ],
                ),
                make_skill(
                    slug="gradle-build-system",
                    name="Gradle Build System & Configuration",
                    difficulty="INTERMEDIATE",
                    description="Automate Android builds with Gradle Kotlin DSL (build.gradle.kts), version catalogs (libs.versions.toml), build variants, and ProGuard/R8 rules.",
                    key_topics=["Gradle Kotlin DSL (build.gradle.kts)", "Version Catalogs (libs.versions.toml)", "Build Types (Debug, Release) & Product Flavors", "ProGuard & R8 Code Shrinking Rules", "Dependency Management & Configurations (implementation vs api)"],
                    role_relevance="Crucial for managing dependencies, multi-environment builds (dev/staging/prod), and optimizing APK/AAB size for distribution.",
                    prerequisites=["android-sdk-studio"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Configure Your Build — Android Developers", "url": "https://developer.android.com/build", "description": "Official documentation for Gradle Kotlin DSL, version catalogs, and build variants."},
                        {"type": "YOUTUBE", "title": "Mastering Gradle for Android — Android Developers", "url": "https://www.youtube.com/watch?v=0kH3GvW0Q_w", "description": "Deep dive into Gradle build lifecycle, caching, and version catalogs."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="gradle-build-system-prob-1",
                            title="Version Catalog Migration",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Centralize dependencies using Gradle Version Catalogs in libs.versions.toml.",
                            problem_statement="Refactor hardcoded build.gradle dependencies into a centralized gradle/libs.versions.toml catalog.",
                            requirements=[
                                "Create gradle/libs.versions.toml declaring [versions], [libraries], and [plugins] blocks.",
                                "Map AndroidX Core, Compose BOM, and Lifecycle dependencies to type-safe accessors.",
                                "Update app/build.gradle.kts to consume dependencies via libs.androidx.core, libs.compose.bom, etc."
                            ],
                            concepts_tested=["Version Catalogs", "libs.versions.toml", "Type-safe Accessors", "Dependency Centralization"],
                            expected_outcome="A build script with zero hardcoded version strings that compiles cleanly with Gradle 8+.",
                            optional_hints=["Group related libraries (like Compose or Retrofit) into bundles in libs.versions.toml."]
                        ),
                        make_problem(
                            problem_id="gradle-build-system-prob-2",
                            title="Multi-Environment Build Flavors",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Configure flavor dimensions and build types for dev, staging, and production environments.",
                            problem_statement="Configure Gradle product flavors and build types to generate distinct package names, app icons, and backend base URLs.",
                            requirements=[
                                "Define a flavorDimension 'environment' with 'dev', 'staging', and 'prod' flavors.",
                                "Configure applicationIdSuffix '.dev' and '.staging' for non-production flavors.",
                                "Inject flavor-specific BASE_URL constants into BuildConfig using buildConfigField."
                            ],
                            concepts_tested=["Product Flavors", "Flavor Dimensions", "Build Types", "BuildConfig Fields", "Application ID Suffixes"],
                            expected_outcome="Simultaneous installation of dev and prod variants on a single device with distinct icons and API targets.",
                            optional_hints=["Enable buildFeatures { buildConfig = true } in app/build.gradle.kts."]
                        ),
                        make_problem(
                            problem_id="gradle-build-system-prob-3",
                            title="R8 Optimization & ProGuard Rules Configuration",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Configure R8 full-mode shrinking, obfuscation, and keep rules for reflection and serialization.",
                            problem_statement="Enable code shrinking and obfuscation in release builds and write custom ProGuard rules to prevent data class serialization crashes.",
                            requirements=[
                                "Enable isMinifyEnabled = true and isShrinkResources = true on the release build type.",
                                "Configure proguard-rules.pro with keep rules for Moshi / Kotlinx Serialization data classes.",
                                "Analyze the generated mapping.txt and APK analyzer output to verify size reduction without runtime crashes."
                            ],
                            concepts_tested=["R8 Shrinking", "Resource Shrinking", "Obfuscation", "ProGuard Keep Rules", "APK Analyzer"],
                            expected_outcome="A production release build with significantly reduced binary size that parses network JSON models without reflection crashes.",
                            optional_hints=["Use @Keep annotation or -keepclassmembers rules for models accessed reflectively."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Modern UI with Jetpack Compose",
            "description": "Build modern, reactive, declarative user interfaces with Jetpack Compose, Material 3 design systems, and Navigation Compose.",
            "skills": [
                make_skill(
                    slug="jetpack-compose-fundamentals",
                    name="Jetpack Compose Fundamentals & State",
                    difficulty="BEGINNER",
                    description="Declarative UI development: Composable functions, State hoisting, Recomposition lifecycle, Modifiers, remember, derivedStateOf, and Lazy layouts.",
                    key_topics=["Declarative UI Paradigm vs Views", "State Hoisting & Unidirectional Data Flow", "Recomposition Lifecycle & remember", "Modifiers & Layout Constraints", "LazyColumn & LazyRow with Stable Keys"],
                    role_relevance="The modern official standard for Android UI development, replacing XML layouts with reactive, maintainable Kotlin code.",
                    prerequisites=["kotlin-fundamentals", "android-sdk-studio"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Jetpack Compose Documentation", "url": "https://developer.android.com/jetpack/compose", "description": "Official guides, codelabs, and API reference for Compose UI."},
                        {"type": "YOUTUBE", "title": "Jetpack Compose Crash Course — Philipp Lackner", "url": "https://www.youtube.com/watch?v=D3nhzxceGqY", "description": "Hands-on walkthrough of Composable basics, layouts, and state management."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="compose-fundamentals-prob-1",
                            title="Interactive Counter & Form Screen",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Master state hoisting, rememberSaveable, and fundamental layout composables.",
                            problem_statement="Build a Compose screen with text input, increment/decrement controls, and a toggle button with proper state hoisting.",
                            requirements=[
                                "Create a stateless CounterScreen that accepts count, onIncrement, and onDecrement callbacks.",
                                "Use rememberSaveable in the parent container to survive orientation changes.",
                                "Use Column, Row, Spacer, and Modifier.padding to arrange the controls neatly."
                            ],
                            concepts_tested=["State Hoisting", "rememberSaveable", "Column & Row", "Modifiers", "Stateless Composables"],
                            expected_outcome="A clean, interactive screen that increments/decrements count and maintains state through screen rotation.",
                            optional_hints=["Differentiate between remember (recomposition-safe) and rememberSaveable (process-death/rotation-safe)."]
                        ),
                        make_problem(
                            problem_id="compose-fundamentals-prob-2",
                            title="High-Performance Lazy List with Sticky Headers",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an optimized LazyColumn with stable keys, item animations, and sticky headers.",
                            problem_statement="Build an categorized contact directory with 1,000 items that scrolls at a silky 60/120 FPS without unnecessary recompositions.",
                            requirements=[
                                "Use LazyColumn with explicit item keys (key = { it.id }) to optimize list diffing.",
                                "Implement stickyHeader composables for category group headers (A, B, C...).",
                                "Use derivedStateOf to observe scroll offset and show a floating 'Scroll to Top' button only after scrolling past 5 items."
                            ],
                            concepts_tested=["LazyColumn", "Stable Keys", "stickyHeader", "derivedStateOf", "Recomposition Optimization"],
                            expected_outcome="A high-performance list that skips redundant item recompositions during rapid fling scrolling.",
                            optional_hints=["Wrap complex calculated states in derivedStateOf to prevent recomposing on every single pixel scrolled."]
                        ),
                        make_problem(
                            problem_id="compose-fundamentals-prob-3",
                            title="Custom Layout with Swipe-to-Dismiss & Gestures",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Create a custom layout modifier and gesture-driven swipe-to-action list item.",
                            problem_statement="Build a production-grade SwipeToDismissBox component with custom gesture thresholds, background color interpolation, and delete callbacks.",
                            requirements=[
                                "Implement swipe gestures using AnchoredDraggable or SwipeToDismissBox APIs.",
                                "Interpolate background color and icon scale dynamically based on swipe offset progress.",
                                "Trigger an undoable deletion action with an animated exit transition (AnimatedVisibility)."
                            ],
                            concepts_tested=["Gesture Handling", "AnchoredDraggable", "Custom Modifiers", "AnimatedVisibility", "Offset Transitions"],
                            expected_outcome="A fluid, physics-based swipe-to-delete item that transitions smoothly with undo snackbar integration.",
                            optional_hints=["Use Modifier.graphicsLayer to apply translationX and avoid relayout passes during swipe gestures."]
                        ),
                    ],
                ),
                make_skill(
                    slug="material3-design-system",
                    name="Material 3 & Adaptive Design Systems",
                    difficulty="INTERMEDIATE",
                    description="Implement Material You (Material 3) design guidelines: dynamic color, color schemes, typography scales, shape tokens, dark mode, and adaptive layouts for foldable/tablet window size classes.",
                    key_topics=["Material 3 ColorScheme & Dynamic Theming", "Typography Scales & Custom Font Families", "Material 3 Components (Scaffold, TopAppBar, ModalBottomSheet)", "WindowSizeClass (Compact, Medium, Expanded)", "Dark Theme & High Contrast Support"],
                    role_relevance="Enforces Google's premier design language and delivers responsive, beautiful mobile experiences across phones, foldables, and tablets.",
                    prerequisites=["jetpack-compose-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Material 3 in Jetpack Compose", "url": "https://developer.android.com/develop/ui/compose/designsystems/material3", "description": "Official guides to theming, typography, dynamic color, and components."},
                        {"type": "YOUTUBE", "title": "Material 3 Theming in Jetpack Compose", "url": "https://www.youtube.com/watch?v=nTa_u1QWz6o", "description": "Full guide to dynamic color, dark theme switching, and custom typography scales."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="material3-design-prob-1",
                            title="Custom Theme & Dynamic Color Palette",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a cohesive Material 3 theme supporting dynamic color and manual dark mode toggling.",
                            problem_statement="Build a Theme.kt setup supporting Android 12+ dynamic theming with fallback brand color schemes for dark and light modes.",
                            requirements=[
                                "Define lightColorScheme and darkColorScheme with primary, secondary, tertiary, and surface colors.",
                                "Conditionally apply dynamicLightColorScheme / dynamicDarkColorScheme on Android 12+ (Build.VERSION.SDK_INT >= S).",
                                "Provide a custom Typography scale using custom Google Fonts."
                            ],
                            concepts_tested=["MaterialTheme", "ColorScheme", "Dynamic Color", "Typography Tokens", "Dark Mode"],
                            expected_outcome="An app theme that adapts dynamically to the user's wallpaper on Android 12+ and respects system dark mode.",
                            optional_hints=["Use MaterialTheme.colorScheme and MaterialTheme.typography across all child composables."]
                        ),
                        make_problem(
                            problem_id="material3-design-prob-2",
                            title="Scaffold with ModalBottomSheet & Navigation Bar",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Construct a standard Material 3 application shell using Scaffold, NavigationBar, and ModalBottomSheet.",
                            problem_statement="Assemble a multi-tab application shell containing a TopAppBar, bottom NavigationBar, FloatingActionButton, and an animated ModalBottomSheet.",
                            requirements=[
                                "Use Scaffold with topBar, bottomBar, floatingActionButton, and snackbarHost slots.",
                                "Implement a NavigationBar with NavigationBarItem icons, badges, and labels.",
                                "Show an accessible ModalBottomSheet with rememberModalBottomSheetState upon clicking the FAB."
                            ],
                            concepts_tested=["Scaffold", "ModalBottomSheet", "NavigationBar", "TopAppBar", "Slot API"],
                            expected_outcome="A fully accessible Material 3 app frame supporting keyboard navigation and smooth sheet animations.",
                            optional_hints=["Ensure Scaffold padding is applied to the content container to avoid UI clipping under bars."]
                        ),
                        make_problem(
                            problem_id="material3-design-prob-3",
                            title="Adaptive Two-Pane Layout for Tablets & Foldables",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement an adaptive layout that renders a single list on phones and a side-by-side ListDetailPaneScaffold on foldables/tablets.",
                            problem_statement="Use AndroidX Compose Material 3 Adaptive library to create an adaptive list-detail interface responding to WindowSizeClass.",
                            requirements=[
                                "Calculate current WindowWidthSizeClass (Compact, Medium, Expanded).",
                                "Render single-pane list navigation on Compact screens (phones).",
                                "Render dual-pane side-by-side list and detail views on Expanded screens (tablets/foldables).",
                                "Preserve selected item state seamlessly when unfolding the device or rotating screens."
                            ],
                            concepts_tested=["WindowSizeClass", "Adaptive Layouts", "ListDetailPaneScaffold", "Foldable Support", "Two-Pane Layout"],
                            expected_outcome="A responsive UI that transforms fluidly from single-pane to dual-pane when resized or unfolded.",
                            optional_hints=["Use the official compose-material3-adaptive library."]
                        ),
                    ],
                ),
                make_skill(
                    slug="navigation-compose",
                    name="Navigation Compose & App Flow",
                    difficulty="INTERMEDIATE",
                    description="Type-safe navigation between screens using Navigation Compose: NavHost, NavController, type-safe route serializable objects, backstack management, and deep links.",
                    key_topics=["NavHost & NavController Setup", "Type-Safe Routing with Kotlin Serialization", "Passing Arguments & Custom Parcelable Types", "Nested Navigation Graphs", "Deep Links with Navigation Compose"],
                    role_relevance="Enables structured multi-screen architecture and seamless deep linking across modern Compose-only codebases.",
                    prerequisites=["jetpack-compose-fundamentals", "material3-design-system"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Navigation in Jetpack Compose", "url": "https://developer.android.com/guide/navigation/design", "description": "Official documentation covering type-safe navigation, deep links, and backstack."},
                        {"type": "YOUTUBE", "title": "Type-Safe Navigation Compose Tutorial", "url": "https://www.youtube.com/watch?v=AIC_6XmF_vQ", "description": "Guide to modern Kotlinx Serialization type-safe routes in Navigation Compose 2.8+."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="navigation-compose-prob-1",
                            title="Two-Screen Type-Safe Flow",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement type-safe screen transitions with NavHost and NavController.",
                            problem_statement="Build a two-screen flow (Home to Detail) passing a strongly typed argument without string path concatenation.",
                            requirements=[
                                "Define @Serializable data object HomeRoute and @Serializable data class DetailRoute(val itemId: String).",
                                "Configure a NavHost with NavController managing transitions between the two destinations.",
                                "Navigate from Home to Detail passing the clicked item ID and display it on the Detail screen."
                            ],
                            concepts_tested=["NavHost", "NavController", "Type-Safe Routes", "@Serializable", "Navigation Arguments"],
                            expected_outcome="A compile-time verified navigation flow that cannot crash due to typo in URL strings.",
                            optional_hints=["Ensure Kotlinx Serialization plugin is applied in build.gradle.kts."]
                        ),
                        make_problem(
                            problem_id="navigation-compose-prob-2",
                            title="Bottom Navigation with Nested Graphs",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Coordinate multiple bottom navigation tabs with isolated nested backstacks.",
                            problem_statement="Build a 3-tab application (Feed, Search, Profile) where each tab maintains its own nested sub-destinations.",
                            requirements=[
                                "Configure a bottom NavigationBar with 3 primary tab destinations.",
                                "Use navigation() builder to create nested sub-graphs for each tab.",
                                "Implement popUpTo(navController.graph.findStartDestination().id) { saveState = true } to preserve tab backstacks when switching."
                            ],
                            concepts_tested=["Nested Navigation Graphs", "Backstack Preservation", "Bottom Navigation Integration", "saveState & restoreState"],
                            expected_outcome="Switching between tabs preserves user scroll and navigation depth within each individual tab.",
                            optional_hints=["Always use launchSingleTop = true when navigating to bottom nav destinations."]
                        ),
                        make_problem(
                            problem_id="navigation-compose-prob-3",
                            title="Deep Link Handler with Custom Transition Animations",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Configure deep links with external URL patterns and animated screen transitions.",
                            problem_statement="Add deep link handling for web URLs (https://example.com/item/{id}) and configure custom slide and fade enter/exit animations.",
                            requirements=[
                                "Define navDeepLink with uriPattern matching external web URLs.",
                                "Configure enterTransition and exitTransition using slideInHorizontally and fadeOut animations.",
                                "Verify that clicking a deep link opens the destination and back navigation pops smoothly to the home tab."
                            ],
                            concepts_tested=["Deep Links", "Animated Navigation Transitions", "slideInHorizontally", "Synthetic Backstack in Compose"],
                            expected_outcome="External URLs deep-link seamlessly into the Compose destination with professional transition animations.",
                            optional_hints=["Use NavDeepLinkRequest or test via ADB shell intent dispatching."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Architecture & Dependency Injection",
            "description": "Architect scalable Android apps adhering to Unidirectional Data Flow, Clean Architecture, and enterprise Dependency Injection with Dagger & Hilt.",
            "skills": [
                make_skill(
                    slug="android-architecture-viewmodel",
                    name="Modern Android Architecture & ViewModel",
                    difficulty="INTERMEDIATE",
                    description="Google's recommended app architecture: MVVM / MVI, UI Layer, ViewModel, UI State modeling, StateFlow, Repository Pattern, and Clean Architecture separation.",
                    key_topics=["Unidirectional Data Flow (UDF) Principles", "ViewModel & viewModelScope Lifecycle", "UiState Modeling with Sealed Interfaces", "Repository Pattern & Data Layer Abstraction", "Offline-First Clean Architecture Layers"],
                    role_relevance="The foundation of scalable, maintainable enterprise Android engineering, separating UI presentation from business logic.",
                    prerequisites=["kotlin-coroutines-flow", "jetpack-compose-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Guide to App Architecture — Android Developers", "url": "https://developer.android.com/topic/architecture", "description": "Google's official guide to UI, Domain, and Data layer separation and best practices."},
                        {"type": "YOUTUBE", "title": "Modern Android Architecture — Philipp Lackner", "url": "https://www.youtube.com/watch?v=cM_QnK_B_0k", "description": "In-depth tutorial on Clean Architecture, Repositories, ViewModels, and StateFlow in Compose."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="architecture-viewmodel-prob-1",
                            title="StateFlow ViewModel with UDF",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement a ViewModel exposing an immutable StateFlow following Unidirectional Data Flow.",
                            problem_statement="Create a ViewModel that loads data, handles errors, and exposes a single UiState sealed interface to a Compose screen.",
                            requirements=[
                                "Define a sealed interface UiState (Loading, Success, Error).",
                                "Maintain private MutableStateFlow and expose public val uiState: StateFlow<UiState>.",
                                "Consume the state in Compose using collectAsStateWithLifecycle()."
                            ],
                            concepts_tested=["ViewModel", "Unidirectional Data Flow", "collectAsStateWithLifecycle", "StateFlow", "UiState Modeling"],
                            expected_outcome="A UI layer that automatically handles screen rotation and configuration changes without reloading data.",
                            optional_hints=["Always use collectAsStateWithLifecycle() to stop flow collection when the app is in the background."]
                        ),
                        make_problem(
                            problem_id="architecture-viewmodel-prob-2",
                            title="Repository Pattern with Error Wrapping",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Decouple data sources from ViewModels using an abstract Repository interface and Result wrappers.",
                            problem_statement="Build a Clean Architecture data layer with an ItemRepository interface and an implementation that catches network/database errors into a Result<T> wrapper.",
                            requirements=[
                                "Define interface ItemRepository { fun getItems(): Flow<Result<List<Item>>> }.",
                                "Implement ItemRepositoryImpl handling network errors and mapping exceptions to meaningful domain errors.",
                                "Inject the repository into a ViewModel and handle Loading, Success, and Error states."
                            ],
                            concepts_tested=["Repository Pattern", "Data Layer Separation", "Result Wrapper", "Flow Error Handling", "Domain Modeling"],
                            expected_outcome="A clean separation of concerns where UI code has zero knowledge of network libraries or database queries.",
                            optional_hints=["Use kotlin.Result or a custom sealed class NetworkResult<T>."]
                        ),
                        make_problem(
                            problem_id="architecture-viewmodel-prob-3",
                            title="Complete Clean Architecture Feature with Use Cases",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement an enterprise Clean Architecture feature across Presentation, Domain, and Data layers.",
                            problem_statement="Build a complete feature with a Domain Use Case (ValidateAndSubmitOrderUseCase), Repository, and MVI ViewModel managing intents and states.",
                            requirements=[
                                "Create a Domain Use Case class with an 'operator fun invoke()' performing business validation before repository submission.",
                                "Implement an MVI pattern where the UI dispatches sealed UiAction intents to the ViewModel.",
                                "Ensure the Domain layer has zero dependencies on Android framework SDK classes."
                            ],
                            concepts_tested=["Clean Architecture", "Domain Use Cases", "MVI Architecture", "Dependency Inversion", "Business Validation"],
                            expected_outcome="A decoupled, 100% unit-testable feature architecture ready for enterprise multi-module codebases.",
                            optional_hints=["Domain layer should only depend on pure Kotlin, not Android SDK imports."]
                        ),
                    ],
                ),
                make_skill(
                    slug="hilt-dependency-injection",
                    name="Dependency Injection with Dagger & Hilt",
                    difficulty="INTERMEDIATE",
                    description="Enterprise dependency injection for Android: Hilt annotations (@HiltAndroidApp, @AndroidEntryPoint, @Inject), Modules (@Module, @InstallIn), Scopes (@Singleton, @ViewModelScoped), and testing with Hilt test fakes.",
                    key_topics=["Dependency Injection Principles & Service Locator Pitfalls", "@HiltAndroidApp & Application Component Graph", "@AndroidEntryPoint & @HiltViewModel", "@Provides & @Binds in Hilt Modules", "Hilt Qualifiers (@Named, Custom Qualifiers)", "Testing with @HiltAndroidTest and Test Fakes"],
                    role_relevance="The mandatory industry standard for managing object graphs, decoupling dependencies, and writing modular, testable Android applications.",
                    prerequisites=["android-architecture-viewmodel"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Dependency Injection with Hilt — Android Developers", "url": "https://developer.android.com/training/dependency-injection/hilt-android", "description": "Official guide for Dagger Hilt integration, modules, and testing."},
                        {"type": "YOUTUBE", "title": "Hilt Dependency Injection Course — Philipp Lackner", "url": "https://www.youtube.com/watch?v=bbMsuI2p1DQ", "description": "Comprehensive tutorial covering Hilt setup, modules, qualifiers, and ViewModel injection."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="hilt-di-prob-1",
                            title="Hilt Setup & ViewModel Injection",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Configure Hilt in an Android app and inject dependencies into a ViewModel.",
                            problem_statement="Set up Hilt from scratch, annotate the Application class, and inject an analytics service into a ViewModel using @Inject constructor.",
                            requirements=[
                                "Annotate the Application class with @HiltAndroidApp and MainActivity with @AndroidEntryPoint.",
                                "Create an AnalyticsService class and provide it via @Inject constructor.",
                                "Inject AnalyticsService into MyViewModel annotated with @HiltViewModel and instantiate it in Compose with hiltViewModel()."
                            ],
                            concepts_tested=["@HiltAndroidApp", "@AndroidEntryPoint", "@HiltViewModel", "@Inject", "hiltViewModel()"],
                            expected_outcome="An operational dependency injection graph where ViewModels receive dependencies without manual factories.",
                            optional_hints=["Include hilt-android and hilt-compiler KSP plugins in your build scripts."]
                        ),
                        make_problem(
                            problem_id="hilt-di-prob-2",
                            title="Hilt Modules with @Binds and Qualifiers",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Provide interface abstractions with @Binds and distinguish multiple instances with custom @Qualifier annotations.",
                            problem_statement="Configure a Hilt module that binds an interface to its implementation and uses custom qualifiers for public vs authenticated HTTP clients.",
                            requirements=[
                                "Create a @Module installed in SingletonComponent using @Binds to bind AuthRepository interface to AuthRepositoryImpl.",
                                "Create two custom @Qualifier annotations: @PublicApi and @AuthenticatedApi.",
                                "Provide two distinct OkHttpClient instances in a NetworkModule distinguished by the qualifiers."
                            ],
                            concepts_tested=["@Module", "@InstallIn", "@Binds vs @Provides", "Custom Qualifiers", "SingletonComponent"],
                            expected_outcome="A compile-time validated dependency graph where components request specific qualified dependencies without ambiguity.",
                            optional_hints=["@Binds is preferred over @Provides for interface binding because it generates less code."]
                        ),
                        make_problem(
                            problem_id="hilt-di-prob-3",
                            title="Hilt Testing with Replaced Test Modules",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Write automated tests using @HiltAndroidTest and replace production modules with test doubles using @TestInstallIn.",
                            problem_statement="Build an integration test setup that replaces the real NetworkModule with a FakeNetworkModule using @TestInstallIn.",
                            requirements=[
                                "Create a FakeItemRepository test double returning predefined in-memory items.",
                                "Configure a test module annotated with @TestInstallIn(components = [SingletonComponent::class], replaces = [ItemModule::class]).",
                                "Write an instrumentation test annotated with @HiltAndroidTest verifying ViewModel consumes the fake data correctly."
                            ],
                            concepts_tested=["@HiltAndroidTest", "@TestInstallIn", "Test Doubles & Fakes", "HiltTestRunner", "Integration Testing"],
                            expected_outcome="An automated test that runs with zero network dependencies by injecting in-memory test doubles via Hilt.",
                            optional_hints=["Use HiltTestRunner in build.gradle.kts testInstrumentationRunner."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 5,
            "name": "Stage 5 — Networking & Local Data",
            "description": "Connect to backend REST services and store local application state using Retrofit, OkHttp, Room database, and DataStore preferences.",
            "skills": [
                make_skill(
                    slug="retrofit-okhttp-networking",
                    name="Networking with Retrofit & OkHttp",
                    difficulty="INTERMEDIATE",
                    description="REST API integration in Android: Retrofit interfaces, OkHttp client, Interceptors (Auth tokens, logging), Kotlinx Serialization/Moshi converters, and network state monitoring.",
                    key_topics=["Retrofit Service Interfaces & HTTP Verbs", "OkHttp Interceptors (Bearer Auth & Chucker/Logging)", "Serialization with Kotlinx.serialization / Moshi", "Handling HTTP Errors & Network Response Wrappers", "Network Connectivity Monitoring (ConnectivityManager)"],
                    role_relevance="The universal standard for connecting mobile clients to remote cloud APIs, handling authentication, and recovering from network failures.",
                    prerequisites=["kotlin-coroutines-flow", "android-architecture-viewmodel"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Retrofit Official Documentation — Square", "url": "https://square.github.io/retrofit/", "description": "Type-safe HTTP client for Android and Java by Square."},
                        {"type": "YOUTUBE", "title": "Retrofit with Kotlin Coroutines in Android", "url": "https://www.youtube.com/watch?v=t6RalBq4G2M", "description": "Step-by-step tutorial on Retrofit setup, interceptors, error handling, and Kotlin serialization."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="retrofit-networking-prob-1",
                            title="Type-Safe REST Client with Retrofit",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a Retrofit API interface using Kotlin suspend functions and JSON converters.",
                            problem_statement="Set up a Retrofit client that fetches a list of articles from a mock REST API and deserializes JSON into data classes.",
                            requirements=[
                                "Define an Article data class annotated with Kotlinx Serialization (@Serializable).",
                                "Create an ApiService interface with @GET(\"articles\") suspend fun getArticles(): List<Article>.",
                                "Instantiate Retrofit with a baseUrl and kotlinx.serialization converter factory."
                            ],
                            concepts_tested=["Retrofit @GET", "Suspend API Functions", "Kotlinx Serialization", "ConverterFactory"],
                            expected_outcome="A working network call that parses remote JSON into strongly-typed Kotlin data classes on Dispatchers.IO.",
                            optional_hints=["Never call Retrofit suspend functions on Dispatchers.Main directly."]
                        ),
                        make_problem(
                            problem_id="retrofit-networking-prob-2",
                            title="Auth Token Interceptor & Refresh Flow",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an OkHttp Interceptor that attaches bearer tokens and transparently refreshes expired tokens.",
                            problem_statement="Build an OkHttp AuthInterceptor that adds Authorization headers to outgoing requests and an Authenticator that handles 401 Unauthorized by refreshing tokens.",
                            requirements=[
                                "Implement an Interceptor that adds 'Authorization: Bearer <token>' to every outgoing request.",
                                "Implement OkHttp Authenticator that intercepts HTTP 401 responses, calls a refreshToken endpoint, and retries the original request.",
                                "Ensure thread-safe synchronization so multiple concurrent requests don't trigger duplicate token refresh calls."
                            ],
                            concepts_tested=["OkHttp Interceptor", "OkHttp Authenticator", "Bearer Authentication", "Token Refresh", "Thread Synchronization"],
                            expected_outcome="A seamless authentication pipeline where expired tokens refresh automatically without kicking the user out of the app.",
                            optional_hints=["Check response.request.header(\"Authorization\") in Authenticator to prevent infinite 401 retry loops."]
                        ),
                        make_problem(
                            problem_id="retrofit-networking-prob-3",
                            title="Offline-Aware Network Cache & Connectivity Monitor",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement OkHttp offline caching with Cache-Control headers and real-time connectivity observation via ConnectivityManager.",
                            problem_statement="Build a network layer that serves cached responses when offline and exposes a StateFlow<Boolean> of real-time internet connectivity status.",
                            requirements=[
                                "Configure an OkHttp Cache directory with max size 10MB.",
                                "Implement a cache interceptor specifying max-age when online and max-stale when offline.",
                                "Implement a NetworkMonitor using ConnectivityManager.NetworkCallback emitting network status as a Flow."
                            ],
                            concepts_tested=["OkHttp Cache", "Cache-Control Headers", "ConnectivityManager.NetworkCallback", "Flow Connectivity Stream"],
                            expected_outcome="An app that loads previously fetched articles instantly when in airplane mode and displays a reconnection banner when network restores.",
                            optional_hints=["Use callbackFlow to wrap ConnectivityManager.NetworkCallback."]
                        ),
                    ],
                ),
                make_skill(
                    slug="room-datastore-persistence",
                    name="Local Persistence with Room & DataStore",
                    difficulty="INTERMEDIATE",
                    description="Offline-first data persistence: Room SQLite ORM (@Entity, @Dao, @Database), type converters, relational queries, automated database migrations, and Preferences DataStore for key-value settings.",
                    key_topics=["Room Entities, DAOs & TypeConverters", "Reactive Queries with Flow", "Database Migrations (Automated & Manual)", "Room Relationships (@Embedded, @Relation)", "Preferences DataStore vs SharedPreferences", "Offline-First Repository Architecture"],
                    role_relevance="Enables responsive, offline-first mobile applications that function seamlessly without constant internet connectivity.",
                    prerequisites=["kotlin-coroutines-flow", "android-architecture-viewmodel"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Save Data in a Local Database Using Room", "url": "https://developer.android.com/training/data-storage/room", "description": "Official documentation for Room database, DAOs, migrations, and testing."},
                        {"type": "YOUTUBE", "title": "Room Database & DataStore Full Course — Philipp Lackner", "url": "https://www.youtube.com/watch?v=bOd3wO0PKnM", "description": "Complete guide to Room entities, DAOs, migrations, and Preferences DataStore."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="room-datastore-prob-1",
                            title="Preferences DataStore Key-Value Storage",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Store and observe user preferences asynchronously using Jetpack Preferences DataStore.",
                            problem_statement="Implement a UserPreferencesRepository that stores dark mode preference and user auth tokens with DataStore.",
                            requirements=[
                                "Create a Context.dataStore delegate for preferencesDataStore.",
                                "Implement suspend functions to save boolean and string preference keys.",
                                "Expose a Flow<UserPreferences> that emits updated values whenever preferences change."
                            ],
                            concepts_tested=["Preferences DataStore", "DataStore Keys", "Reactive Flow Preference", "Asynchronous Persistence"],
                            expected_outcome="A modern, non-blocking replacement for SharedPreferences that eliminates UI-thread disk I/O.",
                            optional_hints=["Use dataStore.data.catch { ... } to handle potential IOException during file reads."]
                        ),
                        make_problem(
                            problem_id="room-datastore-prob-2",
                            title="Reactive Room Database with Relations",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Build a Room database with one-to-many relationships and reactive Flow queries.",
                            problem_statement="Create a task management database with User and Task entities, modeling a one-to-many relationship with reactive observation.",
                            requirements=[
                                "Define UserEntity and TaskEntity with foreign key constraints and indices.",
                                "Define a UserWithTasks relational data class using @Embedded and @Relation annotations.",
                                "Implement a Dao method @Query returning Flow<List<UserWithTasks>> that automatically updates whenever tasks change."
                            ],
                            concepts_tested=["Room @Entity", "Foreign Keys", "@Embedded & @Relation", "Reactive DAO Flow", "RoomDatabase"],
                            expected_outcome="A reactive local database where any insert/delete automatically triggers UI recomposition via Flow emission.",
                            optional_hints=["Ensure foreign keys specify ondelete = ForeignKey.CASCADE."]
                        ),
                        make_problem(
                            problem_id="room-datastore-prob-3",
                            title="Automated Room Database Migration with Schema Verification",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Execute and test a non-destructive database schema migration from version 1 to version 2.",
                            problem_statement="Upgrade a production database schema by adding a new column and a new table, writing an explicit Migration and verifying with MigrationTestHelper.",
                            requirements=[
                                "Increment database version from 1 to 2 and declare an AutoMigration or manual Migration(1, 2).",
                                "Add an 'isArchived: Boolean' column to TaskEntity with default value false.",
                                "Write an automated migration test using MigrationTestHelper verifying all existing data survives the migration intact."
                            ],
                            concepts_tested=["Database Migrations", "Migration(1, 2)", "MigrationTestHelper", "Schema Export", "Data Preservation"],
                            expected_outcome="A verified database migration that guarantees zero user data loss or SQLite table format crashes during app updates.",
                            optional_hints=["Configure room.schemaLocation in build.gradle.kts to export schema JSONs for automated verification."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 6,
            "name": "Stage 6 — Background Processing & Platform Services",
            "description": "Execute deferred, guaranteed background tasks, periodic syncs, and notifications using WorkManager and system services.",
            "skills": [
                make_skill(
                    slug="workmanager-background-tasks",
                    name="WorkManager & Background Tasks",
                    difficulty="INTERMEDIATE",
                    description="Guaranteed background execution: WorkManager, CoroutineWorker, Constraints (Network, Battery, Storage), OneTimeWorkRequest, PeriodicWorkRequest, Work chaining, and system Notifications.",
                    key_topics=["WorkManager Architecture & Execution Guarantees", "CoroutineWorker & doWork Implementation", "Work Constraints (NetworkType, Charging, StorageNotLow)", "Work Chaining (beginWith -> then -> enqueue)", "Expedited Work & Foreground Services", "Posting User Notifications with NotificationCompat"],
                    role_relevance="The mandatory Android solution for deferrable, guaranteed background work that survives process death and device reboots.",
                    prerequisites=["kotlin-coroutines-flow", "android-sdk-studio", "room-datastore-persistence"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Schedule Tasks with WorkManager — Android Developers", "url": "https://developer.android.com/topic/libraries/architecture/workmanager", "description": "Official guides for background task scheduling, constraints, and chaining."},
                        {"type": "YOUTUBE", "title": "WorkManager in Android — Philipp Lackner", "url": "https://www.youtube.com/watch?v=84u2v_pA_Q0", "description": "Practical guide to CoroutineWorker, expedited tasks, and periodic background syncs."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="workmanager-prob-1",
                            title="One-Time File Upload Worker with Constraints",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a CoroutineWorker that executes an image upload task only when connected to unmetered Wi-Fi.",
                            problem_statement="Build a background worker that compresses and uploads a local file with battery and network constraints.",
                            requirements=[
                                "Implement ImageUploadWorker extending CoroutineWorker.",
                                "Configure Constraints requiring NetworkType.UNMETERED and BatteryNotLow.",
                                "Enqueue a OneTimeWorkRequestBuilder<ImageUploadWorker> and observe WorkInfo state."
                            ],
                            concepts_tested=["CoroutineWorker", "Constraints", "OneTimeWorkRequest", "WorkInfo Observation"],
                            expected_outcome="A background task that waits for Wi-Fi and automatically executes even if the app process is closed.",
                            optional_hints=["Return Result.success() on completion, or Result.retry() on transient network failures."]
                        ),
                        make_problem(
                            problem_id="workmanager-prob-2",
                            title="Sequential Work Chaining with Data Passing",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Chain multiple workers sequentially, passing intermediate output data between processing steps.",
                            problem_statement="Build a multi-step data pipeline: DownloadWorker -> FilterWorker -> SaveToDatabaseWorker using WorkManager chaining.",
                            requirements=[
                                "Pass input and output data between workers using workDataOf().",
                                "Chain workers using WorkManager.getInstance(context).beginWith(downloadRequest).then(filterRequest).then(saveRequest).enqueue().",
                                "Handle failure in any stage so downstream workers are marked as CANCELLED."
                            ],
                            concepts_tested=["Work Chaining", "Data Passing (Data / workDataOf)", "Sequential Execution", "Work Failure Propagation"],
                            expected_outcome="A robust 3-stage pipeline where output from step N becomes input for step N+1 with unified cancellation.",
                            optional_hints=["Input data is accessible in worker via inputData.getString(\"key\")."]
                        ),
                        make_problem(
                            problem_id="workmanager-prob-3",
                            title="Periodic Background Sync with Notifications",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement a periodic background sync worker that displays a system notification with progress updates.",
                            problem_statement="Configure a PeriodicWorkRequest running every 12 hours that syncs remote data, saves to Room, and posts a notification using NotificationCompat.",
                            requirements=[
                                "Build a PeriodicWorkRequestBuilder with repeat interval 12 hours and 15-minute flex interval.",
                                "Create a NotificationChannel and build a NotificationCompat notification with a pending intent to open the app.",
                                "Post the notification on completion with updated item counts."
                            ],
                            concepts_tested=["PeriodicWorkRequest", "NotificationChannel", "NotificationCompat", "PendingIntent", "Background Data Sync"],
                            expected_outcome="A recurring sync task that updates local storage in the background and notifies the user with deep-link navigation.",
                            optional_hints=["PeriodicWorkRequest minimum repeat interval is 15 minutes."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 7,
            "name": "Stage 7 — Testing & Quality Assurance",
            "description": "Write automated unit tests, ViewModel tests with Turbine, Compose UI tests with test tags, and mock repository dependencies.",
            "skills": [
                make_skill(
                    slug="android-testing-quality",
                    name="Android Testing & Quality Assurance",
                    difficulty="INTERMEDIATE",
                    description="Comprehensive testing for Android: JUnit 5, MockK, Coroutines testing (TestDispatcher, runTest), Turbine for Flow testing, and Compose UI testing (createComposeRule, semantics tree, testTag).",
                    key_topics=["Unit Testing Fundamentals with JUnit & MockK", "Testing Coroutines with runTest & StandardTestDispatcher", "Testing Flow & StateFlow with Turbine", "Compose UI Testing with createComposeRule & Semantics", "UI Test Assertions & Node Matching (hasText, hasTestTag)"],
                    role_relevance="Ensures regression-free application logic, verifies complex state transitions, and validates UI behavior across releases.",
                    prerequisites=["android-architecture-viewmodel", "hilt-dependency-injection", "room-datastore-persistence"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Test Apps on Android — Android Developers", "url": "https://developer.android.com/training/testing", "description": "Official guides for unit, integration, and UI testing in modern Android."},
                        {"type": "YOUTUBE", "title": "Android Testing Course — Philipp Lackner", "url": "https://www.youtube.com/watch?v=bD_6s62P408", "description": "Complete guide to unit testing ViewModels, Coroutines, Turbine, and Compose UI tests."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="android-testing-prob-1",
                            title="ViewModel Unit Testing with TestDispatcher",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Unit test an Android ViewModel handling asynchronous coroutine state transitions.",
                            problem_statement="Write unit tests for a ViewModel using runTest and a MainDispatcherRule to verify loading and success states.",
                            requirements=[
                                "Implement a JUnit Rule setting Dispatchers.setMain(StandardTestDispatcher()) before each test.",
                                "Use MockK to mock repository responses.",
                                "Execute test using runTest and verify ViewModel state transitions from Loading to Success."
                            ],
                            concepts_tested=["runTest", "StandardTestDispatcher", "MainDispatcherRule", "MockK", "ViewModel Testing"],
                            expected_outcome="Fast, deterministic unit tests running on the local JVM in milliseconds without needing an emulator.",
                            optional_hints=["Use advanceUntilIdle() to execute pending coroutines under test."]
                        ),
                        make_problem(
                            problem_id="android-testing-prob-2",
                            title="Reactive Flow Testing with Turbine",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Test cold and hot Kotlin Flows with the Turbine testing library.",
                            problem_statement="Verify emissions, debounce behavior, and error handling of a complex search Flow using Turbine's test { } block.",
                            requirements=[
                                "Use flow.test { ... } to capture and assert emitted values sequentially.",
                                "Verify that intermediate emissions match expected values using awaitItem().",
                                "Verify proper error propagation using awaitError()."
                            ],
                            concepts_tested=["Turbine Library", "Flow Testing", "awaitItem", "awaitError", "Hot vs Cold Stream Verification"],
                            expected_outcome="Thorough test coverage of reactive streams guaranteeing exact emission order and error resilience.",
                            optional_hints=["Turbine ensures no emissions are missed during asynchronous testing."]
                        ),
                        make_problem(
                            problem_id="android-testing-prob-3",
                            title="Compose UI Component & Interaction Testing",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Write automated UI tests for Jetpack Compose using createComposeRule and semantics matching.",
                            problem_statement="Build Compose UI tests verifying that typing into an input field updates text, and clicking a button displays the expected result node.",
                            requirements=[
                                "Use createComposeRule() to mount the Composable under test.",
                                "Locate nodes using onNodeWithTag(\"input_field\") and performTextReplacement(\"Hello\").",
                                "Perform click via performClick() on button node and assert node with text \"Submitted: Hello\" exists."
                            ],
                            concepts_tested=["createComposeRule", "Modifier.testTag", "onNodeWithTag", "performClick", "Semantics Tree Assertions"],
                            expected_outcome="Automated UI tests verifying component rendering and interactive user behavior without manual QA.",
                            optional_hints=["Use Modifier.testTag() to give composables unique identifiers for testing."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 8,
            "name": "Stage 8 — Security, Optimization & Release",
            "description": "Harden mobile security, optimize app performance and memory usage, and publish production builds to the Google Play Store.",
            "skills": [
                make_skill(
                    slug="android-security-hardening",
                    name="Android Security & Storage Hardening",
                    difficulty="ADVANCED",
                    description="Mobile application security: Android Keystore, EncryptedSharedPreferences, Network Security Configuration, Certificate Pinning, API key protection, and secure inter-process communication.",
                    key_topics=["Android Keystore System (Hardware-backed keys)", "EncryptedSharedPreferences (Jetpack Security)", "Network Security Config & Certificate Pinning", "API Key Protection & NDK / BuildConfig Safety", "Preventing Tapjacking, Root Detection & Code Obfuscation"],
                    role_relevance="Protects user credentials, financial data, and intellectual property from extraction, man-in-the-middle attacks, and tampering.",
                    prerequisites=["android-sdk-studio", "retrofit-okhttp-networking", "room-datastore-persistence"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "App Security Best Practices — Android Developers", "url": "https://developer.android.com/privacy-and-security/best-practices", "description": "Official guide to mobile security, encryption, and network configuration."},
                        {"type": "YOUTUBE", "title": "Android App Security — Android Developers", "url": "https://www.youtube.com/watch?v=F0O5vA8mX_c", "description": "In-depth presentation on Keystore, encryption, and securing Android apps against attacks."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="android-security-prob-1",
                            title="Encrypted Credentials Storage with Keystore",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Store sensitive auth tokens using EncryptedSharedPreferences backed by Android Keystore.",
                            problem_statement="Build a SecureStorageManager that stores JWT access tokens encrypted using AES-256 GCM backed by the MasterKey API.",
                            requirements=[
                                "Create a MasterKey using MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build().",
                                "Initialize EncryptedSharedPreferences with the master key.",
                                "Implement saveToken and getToken methods ensuring plain-text tokens are never written to disk unencrypted."
                            ],
                            concepts_tested=["EncryptedSharedPreferences", "MasterKey API", "AES-256 Encryption", "Keystore Protection"],
                            expected_outcome="Tokens written to disk are completely unreadable even if the device filesystem is inspected via ADB.",
                            optional_hints=["Use androidx.security:security-crypto library."]
                        ),
                        make_problem(
                            problem_id="android-security-prob-2",
                            title="Certificate Pinning & Network Security Config",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Defend mobile network traffic against Man-in-the-Middle (MITM) proxy attacks using Certificate Pinning.",
                            problem_statement="Configure Android Network Security Config and OkHttp CertificatePinner to prevent traffic inspection by rogue certificates.",
                            requirements=[
                                "Create res/xml/network_security_config.xml disabling cleartext traffic and binding domains to certificate hashes.",
                                "Configure OkHttp CertificatePinner with SHA-256 public key pins for the production API domain.",
                                "Write a unit/integration test verifying that requests to an untrusted domain fail with SSLPeerUnverifiedException."
                            ],
                            concepts_tested=["Certificate Pinning", "Network Security Configuration", "SSL/TLS Pinning", "MITM Protection"],
                            expected_outcome="Network connections fail safely when intercepted by proxy tools (Charles/Proxyman/Burp Suite) without proper pinned certificates.",
                            optional_hints=["Always provide a primary pin and at least one backup pin to prevent lockouts when certificates rotate."]
                        ),
                        make_problem(
                            problem_id="android-security-prob-3",
                            title="Biometric Authentication & Cryptographic Signature",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Protect sensitive user operations using BiometricPrompt integrated with Android Keystore signature verification.",
                            problem_statement="Build a biometric payment confirmation flow where successful fingerprint/face authentication unlocks a Keystore cryptographic signature.",
                            requirements=[
                                "Generate a Keystore private key requiring KeyProperties.AUTH_BIOMETRIC_STRONG user authentication.",
                                "Initialize a Cipher/Signature object and pass it to BiometricPrompt.CryptoObject.",
                                "Present BiometricPrompt and sign a transaction payload upon successful authentication."
                            ],
                            concepts_tested=["BiometricPrompt", "BiometricPrompt.CryptoObject", "Hardware-backed Keystore", "Cryptographic Authentication"],
                            expected_outcome="A banking-grade biometric authentication prompt that cryptographically validates user presence before executing transactions.",
                            optional_hints=["Use BiometricManager.from(context).canAuthenticate() to check hardware capability first."]
                        ),
                    ],
                ),
                make_skill(
                    slug="gradle-build-optimization-release",
                    name="Gradle Build Optimization & Play Store Release",
                    difficulty="ADVANCED",
                    description="Production app delivery: Release signing keys, Android App Bundle (AAB), Play Console track management, Gradle build caching, and performance profiling (Macrobenchmark).",
                    key_topics=["Android App Bundle (AAB) & Dynamic Delivery", "Release Keystore Generation & Secure CI Signing", "Gradle Build Cache & Configuration Cache Optimization", "Performance Profiling with Macrobenchmark", "Google Play Console Tracks (Internal, Closed, Open, Production)"],
                    role_relevance="The capstone skill required to package, sign, optimize, and publish high-performance Android applications to millions of global users.",
                    prerequisites=["gradle-build-system", "android-testing-quality", "android-security-hardening"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Publish Your App — Android Developers", "url": "https://developer.android.com/distribute", "description": "Official guides for signing, building App Bundles, and managing Play Store releases."},
                        {"type": "YOUTUBE", "title": "Publish Android App to Google Play Store", "url": "https://www.youtube.com/watch?v=fpeWq3mN684", "description": "Step-by-step walkthrough of generating keystores, creating App Bundles, and setting up Play Console tracks."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="release-prob-1",
                            title="Secure Keystore & Release Signing Configuration",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Configure release signing without checking passwords or private keystores into source control.",
                            problem_statement="Generate a release keystore and configure app/build.gradle.kts to read passwords from environment variables or local properties.",
                            requirements=[
                                "Generate a release keystore using keytool.",
                                "Configure signingConfigs.create(\"release\") in Gradle reading keystore path and passwords from System.getenv() or local.properties.",
                                "Ensure debug builds continue using the default debug keystore without requiring manual credentials."
                            ],
                            concepts_tested=["Keytool", "Signing Configurations", "Environment Variables", "Secret Protection in Gradle"],
                            expected_outcome="A build script capable of producing signed release APKs/AABs locally and in CI without leaking credentials.",
                            optional_hints=["Never commit .jks or .keystore files to public Git repositories."]
                        ),
                        make_problem(
                            problem_id="release-prob-2",
                            title="Gradle Build Cache & Speed Optimization",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Optimize Gradle build speeds using configuration caching, build caching, and modularization.",
                            problem_statement="Diagnose and optimize a slow Android build by enabling Gradle configuration cache and build cache in gradle.properties.",
                            requirements=[
                                "Enable org.gradle.caching=true and org.gradle.configuration-cache=true in gradle.properties.",
                                "Run a build with --scan to generate a Gradle Build Scan identifying bottleneck tasks.",
                                "Eliminate tasks that violate configuration cache contracts."
                            ],
                            concepts_tested=["Gradle Build Cache", "Configuration Cache", "Gradle Build Scan", "Build Performance Optimization"],
                            expected_outcome="A 40-60% reduction in incremental build times on subsequent local compilations.",
                            optional_hints=["Run ./gradlew --configuration-cache build to detect incompatible plugins."]
                        ),
                        make_problem(
                            problem_id="release-prob-3",
                            title="Macrobenchmark Startup Profiling & Baseline Profiles",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Generate and verify Baseline Profiles to reduce app cold startup time by 30%+.",
                            problem_statement="Create a Macrobenchmark module that profiles app cold startup and generates a Baseline Profile (baseline-prof.txt) for pre-compilation.",
                            requirements=[
                                "Create an Android Benchmark module using the androidx.benchmark macrobenchmark library.",
                                "Write a startup benchmark test measuring cold startup latency (StartupMode.COLD).",
                                "Generate a Baseline Profile using BaselineProfileRule and package it into the release App Bundle.",
                                "Verify cold startup speedup comparing before and after benchmark metrics."
                            ],
                            concepts_tested=["Baseline Profiles", "Macrobenchmark", "Cold Startup Optimization", "AOT Pre-compilation", "Play Store Delivery"],
                            expected_outcome="An optimized App Bundle pre-compiled with Baseline Profiles for dramatically faster app launch speeds on user devices.",
                            optional_hints=["Run benchmarks on a physical test device with non-debuggable build for accurate metrics."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

"""iOS Developer roadmap definition with progressive practice problems."""
from typing import Any, Dict
from app.db.roadmaps_data.common import ROADMAP_IDS, make_problem, make_skill

IOS_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["ios-developer"],
    "slug": "ios-developer",
    "role_id": None,
    "title": "iOS Developer",
    "domain": "Mobile Development",
    "category": "Mobile & Client Engineering",
    "description": "Build high-performance, polished native Apple applications: modern Swift language features, declarative UI with SwiftUI, clean architecture (MVVM, @Observable), structured async/await concurrency, modern persistence with SwiftData, and networking with URLSession.",
    "version": "v2.0",
    "has_market_data": False,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Swift Language & Platform Foundations",
            "description": "Idiomatic Swift programming, type safety, memory management (ARC), Xcode environment, and application lifecycle states.",
            "skills": [
                make_skill(
                    slug="swift-fundamentals",
                    name="Swift Programming Language Fundamentals",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Modern Swift programming: optionals and optional binding, structs vs classes, protocols and protocol extensions, generics, closures, and Automatic Reference Counting (ARC).",
                    key_topics=["Type Safety & Optional Binding (guard let, if let)", "Structs vs Classes (Value vs Reference Semantics)", "Protocols, Extensions & Protocol-Oriented Programming", "Closures & Escaping Closures", "Memory Management (ARC, strong, weak, unowned)"],
                    role_relevance="The foundation of Apple platform development, providing safe, expressive, and high-performance native code.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "The Swift Programming Language Book", "url": "https://docs.swift.org/swift-book/documentation/the-swift-programming-language/", "description": "Official Apple guide to Swift language syntax, types, concurrency, and best practices."},
                        {"type": "YOUTUBE", "title": "Swift Programming Tutorial — Sean Allen", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive tutorial covering Swift fundamentals, optionals, structs, and closures."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="swift-fund-prob-1",
                            title="Safe Financial Currency Calculator with Optionals",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write idiomatic Swift using optionals, guard let early exits, and custom error types.",
                            problem_statement="Create a CurrencyConverter struct. Implement a method convert(amountString: String, rate: Double?) throws -> Double that safely unwraps the amount string and exchange rate using guard let, validates that amounts are non-negative, and throws custom ConverterError cases on failure.",
                            requirements=[
                                "Define enum ConverterError: Error with cases invalidAmount, missingRate, and negativeValue.",
                                "Use guard let to safely unwrap string to Double and optional rate parameter.",
                                "Use do-catch blocks in caller code to handle all thrown error cases cleanly.",
                                "Write unit tests asserting proper error throwing on invalid inputs."
                            ],
                            concepts_tested=["Swift Optionals", "Guard Let Early Exit", "Custom Swift Errors", "Do-Catch Error Handling"],
                            expected_outcome="Type-safe Swift conversion functions with zero force unwraps (!).",
                            optional_hints=["Avoid force unwrapping with '!' entirely; always prefer guard let or optional chaining."]
                        ),
                        make_problem(
                            problem_id="swift-fund-prob-2",
                            title="Protocol-Oriented Cache with Generic Eviction",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Design a generic in-memory cache utilizing Swift protocols, associated types, and value semantics.",
                            problem_statement="Define a protocol Cacheable with associatedtype Key: Hashable and associatedtype Value. Implement an InMemoryCache struct conforming to Cacheable that stores key-value pairs, enforces a maximum count capacity, and evicts least-recently-used items when capacity is reached.",
                            requirements=[
                                "Use protocol with associated types (Key, Value).",
                                "Implement generic struct InMemoryCache<Key: Hashable, Value>: Cacheable.",
                                "Manage thread-safe state or demonstrate clean value-type mutation with mutating funcs.",
                                "Provide default protocol implementation extensions where applicable."
                            ],
                            concepts_tested=["Protocol-Oriented Programming (POP)", "Associated Types", "Swift Generics", "Mutating Methods"],
                            expected_outcome="A reusable generic caching component conforming to protocol-oriented design.",
                            optional_hints=["Protocol extensions allow providing default method implementations across conforming types."]
                        ),
                        make_problem(
                            problem_id="swift-fund-prob-3",
                            title="ARC Retain Cycle Elimination & Memory Profiling",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Diagnose and eliminate strong reference cycles in closure callbacks using weak and unowned capture lists.",
                            problem_statement="Given a service class with escaping closure completion handlers that inadvertently creates a retain cycle with a parent coordinator, diagnose the memory leak using Xcode Memory Graph Debugger or Instruments Leaks, refactor closures using [weak self] capture lists, and write a XCTest verifying deinit execution.",
                            requirements=[
                                "Demonstrate how strong reference cycles prevent class deinit from firing.",
                                "Refactor closure capture lists to use [weak self] and guard let self = self else { return }.",
                                "Write a unit test verifying that setting instance to nil immediately executes deinit.",
                                "Document the distinct use cases for weak vs unowned references."
                            ],
                            concepts_tested=["Automatic Reference Counting (ARC)", "Strong Reference Retain Cycles", "Closure Capture Lists ([weak self])", "Memory Deallocation Verification"],
                            expected_outcome="A leak-free component verified to properly deallocate from memory.",
                            optional_hints=["A weak reference is always optional and becomes nil when the referenced instance deallocates."]
                        ),
                    ],
                ),
                make_skill(
                    slug="ios-sdk-lifecycle",
                    name="iOS SDK, Xcode & Application Lifecycle",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="The Apple development ecosystem: Xcode IDE, iOS SDK, App/Scene lifecycle events, Info.plist permissions, assets catalogs, Swift Package Manager (SPM), and debugging with lldb.",
                    key_topics=["Xcode Project Structure & Targets", "Swift Package Manager (SPM) Dependencies", "App & Scene Lifecycle (Active, Inactive, Background)", "Info.plist Permissions & Privacy Declarations", "Debugging with Breakpoints & LLDB Commands"],
                    role_relevance="Navigating the native Apple tooling environment and handling platform lifecycle transitions properly.",
                    prerequisites=["swift-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apple Developer Documentation — App Lifecycle", "url": "https://developer.apple.com/documentation/uikit/app_and_environment/managing_your_app_s_life_cycle", "description": "Official Apple guide to application states, scene transitions, and background execution."},
                        {"type": "YOUTUBE", "title": "Xcode & iOS App Lifecycle — Paul Hudson (Hacking with Swift)", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on walkthrough of Xcode, scene phases, asset catalogs, and debugging tools."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sdk-prob-1",
                            title="Scene Phase Transition Handler & State Preservation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Monitor scene phase changes in SwiftUI to persist transient state when the app moves to background.",
                            problem_statement="Build a SwiftUI application that tracks @Environment(\\.scenePhase). When the app transitions from .active to .background, save user draft input to UserDefaults and log timestamps; upon return to .active, restore draft data seamlessly.",
                            requirements=[
                                "Observe scenePhase using @Environment(\\.scenePhase).",
                                "Implement .onChange(of: scenePhase) handling active, inactive, and background phases.",
                                "Persist draft text automatically when moving to background.",
                                "Restore persisted draft state when returning to active."
                            ],
                            concepts_tested=["ScenePhase Lifecycle", "State Preservation", "@Environment Property Wrappers", "Background State Transitions"],
                            expected_outcome="An iOS app that preserves user work across application minimize and multitasking events.",
                            optional_hints=["Apps can be terminated by iOS at any time while in the background without prior warning."]
                        ),
                        make_problem(
                            problem_id="sdk-prob-2",
                            title="Swift Package Integration & Custom Privacy Declaration",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Integrate third-party dependencies using SPM and configure required Apple Privacy Manifest declarations.",
                            problem_statement="Create an Xcode project with an external dependency integrated via Swift Package Manager (e.g. KeychainAccess). Configure PrivacyInfo.xcprivacy with appropriate Privacy Accessed API Types and reasons (NSPrivacyAccessedAPITypeUserDefaults, etc.) adhering to Apple App Store privacy mandates.",
                            requirements=[
                                "Add dependency via Package.swift / Xcode SPM manager.",
                                "Create PrivacyInfo.xcprivacy file declaring required reason APIs.",
                                "Declare runtime permissions in Info.plist (e.g. NSCameraUsageDescription with meaningful rationale).",
                                "Verify project builds cleanly without privacy warnings."
                            ],
                            concepts_tested=["Swift Package Manager (SPM)", "Apple Privacy Manifest (PrivacyInfo.xcprivacy)", "Info.plist Permissions", "App Store Compliance"],
                            expected_outcome="A project adhering to modern Apple privacy declaration and dependency management rules.",
                            optional_hints=["Apple requires explicit Privacy Manifest declarations for apps accessing specific system APIs."]
                        ),
                        make_problem(
                            problem_id="sdk-prob-3",
                            title="LLDB Debugging & Crash Log Symbolication",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Diagnose complex runtime crashes using LLDB commands, symbolic breakpoints, and dSYM symbolication.",
                            problem_statement="Given an intentionally crashing iOS app exhibiting an EXC_BAD_ACCESS memory exception, set up symbolic exception breakpoints in Xcode, inspect stack frames and register values using LLDB commands (po, p, expr, bt), locate the exact memory corruption, and symbolicate a raw crash log using atos and dSYM files.",
                            requirements=[
                                "Configure an Exception Breakpoint catching all Objective-C and Swift exceptions.",
                                "Execute LLDB commands to inspect variable values and evaluate expressions at runtime.",
                                "Symbolicate an un-symbolicated crash log using the atos command-line tool.",
                                "Produce a root-cause explanation and commit the verified fix."
                            ],
                            concepts_tested=["LLDB Debugging Commands (po, expr, bt)", "Symbolic Breakpoints", "EXC_BAD_ACCESS Analysis", "Crash Log Symbolication with atos"],
                            expected_outcome="A resolved memory exception with verified post-mortem symbolication report.",
                            optional_hints=["Use 'po' in LLDB to print object descriptions and 'expr' to execute live Swift code in frame context."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Declarative UI & Reactive Architecture",
            "description": "Building modern interfaces with SwiftUI, responsive layouts, animations, and the @Observable MVVM pattern.",
            "skills": [
                make_skill(
                    slug="swiftui-development",
                    name="Declarative UI Development with SwiftUI",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Modern declarative user interfaces: Views, ViewModifiers, Stacks (VStack, HStack, ZStack), LazyVGrid, Lists, NavigationStack, forms, animations, and custom shapes.",
                    key_topics=["Declarative View Composition & Body Property", "Layout Containers (VStack, HStack, ZStack, LazyVStack)", "View Modifiers & Custom Reusable Modifiers", "NavigationStack & NavigationPath", "Implicit & Explicit Animations (withAnimation)"],
                    role_relevance="The modern standard UI framework for all Apple platforms (iOS, iPadOS, macOS, watchOS, visionOS).",
                    prerequisites=["swift-fundamentals", "ios-sdk-lifecycle"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apple Developer Documentation — SwiftUI", "url": "https://developer.apple.com/documentation/swiftui", "description": "Official Apple SwiftUI documentation, tutorials, and view component references."},
                        {"type": "YOUTUBE", "title": "100 Days of SwiftUI — Paul Hudson", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive, hands-on masterclass building production iOS applications with SwiftUI."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sui-prob-1",
                            title="Interactive Profile Card with Custom Modifiers",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Compose reusable SwiftUI views using Stacks, images, SF Symbols, and custom ViewModifiers.",
                            problem_statement="Build a user profile summary card view. Display an avatar image with circular clipping and subtle shadow, user full name, verified badge SF Symbol, bio text, and interactive action buttons (Follow, Message) styled with custom ViewModifiers.",
                            requirements=[
                                "Use VStack, HStack, and ZStack for layout alignment.",
                                "Load system icons using Image(systemName:).",
                                "Create a custom ViewModifier for card container styling (background, corner radius, drop shadow).",
                                "Support light and dark mode colors seamlessly using asset catalog color sets."
                            ],
                            concepts_tested=["SwiftUI View Composition", "Custom ViewModifiers", "SF Symbols Integration", "Light / Dark Mode Adaptation"],
                            expected_outcome="A pixel-perfect, reusable SwiftUI component that automatically adapts to system color schemes.",
                            optional_hints=["Create an extension on View: func cardStyle() -> some View { modifier(CardModifier()) }."]
                        ),
                        make_problem(
                            problem_id="sui-prob-2",
                            title="Adaptive Product Grid with NavigationStack Routing",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Construct an adaptive two-column grid that navigates to detail views using type-safe NavigationStack.",
                            problem_statement="Build an e-commerce product catalog. Render items in an adaptive LazyVGrid(columns: [GridItem(.adaptive(minimum: 150))]), implement search filtering with .searchable(), and navigate to ProductDetailView using NavigationLink(value:) and .navigationDestination(for:).",
                            requirements=[
                                "Implement dynamic grid using LazyVGrid and GridItem(.adaptive).",
                                "Add search bar filtering using the .searchable(text:) modifier.",
                                "Use value-based navigation with .navigationDestination(for: Product.self).",
                                "Verify smooth scrolling performance on large item lists."
                            ],
                            concepts_tested=["LazyVGrid Adaptive Layouts", "Type-Safe NavigationStack", "Searchable Modifier", "Scrolling Optimization"],
                            expected_outcome="A fluid product browsing screen with type-safe routing to detail destinations.",
                            optional_hints=["Value-based navigation with navigationDestination is the modern replacement for deprecated NavigationLink(destination:)."]
                        ),
                        make_problem(
                            problem_id="sui-prob-3",
                            title="Fluid Micro-Interactions & MatchedGeometryEffect",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Create high-polish hero animations and expandable modal cards using matchedGeometryEffect.",
                            problem_statement="Develop an App Store-style card transition. When tapping a compact card in a list, smoothly expand it into a full-screen detailed article view using matchedGeometryEffect(id:in:) with spring physics animations, and handle drag-down gestures to dismiss.",
                            requirements=[
                                "Use @Namespace to coordinate animations across view hierarchies.",
                                "Apply .matchedGeometryEffect on card container, image, and title elements.",
                                "Animate state changes using .spring(response: 0.5, dampingFraction: 0.8).",
                                "Implement a DragGesture allowing users to swipe down to dismiss the expanded card."
                            ],
                            concepts_tested=["matchedGeometryEffect", "@Namespace Animation Coordination", "Spring Physics Animation", "Interactive Drag Gestures"],
                            expected_outcome="A premium, state-of-the-art native iOS animation mimicking Apple's flagship App Store UI.",
                            optional_hints=["Ensure matching IDs and namespaces are applied symmetrically to both collapsed and expanded views."]
                        ),
                    ],
                ),
                make_skill(
                    slug="ios-mvvm-state",
                    name="Architecture & State Management (MVVM, Observable)",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Modern iOS architecture: the Observation framework (@Observable), Model-View-ViewModel (MVVM), State and Binding properties, dependency injection, and clean separation of concerns.",
                    key_topics=["Swift Observation Framework (@Observable, @Bindable)", "Model-View-ViewModel (MVVM) Pattern in SwiftUI", "State Management (@State, @Binding, @Environment)", "Dependency Injection & Service Protocols", "Unit Testing ViewModels & Mocking Dependencies"],
                    role_relevance="Ensures large iOS codebases remain modular, easily testable, and decoupled from UI rendering logic.",
                    prerequisites=["swiftui-development"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apple Developer Documentation — Observation Framework", "url": "https://developer.apple.com/documentation/observation", "description": "Official Apple guide to the modern @Observable macro and state tracking."},
                        {"type": "YOUTUBE", "title": "SwiftUI Architecture (MVVM with @Observable) — Sean Allen", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on tutorial refactoring ObservableObject to the modern Swift Observation framework in iOS 17+."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="mvvm-prob-1",
                            title="Modern @Observable Counter & Form Binding",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Migrate from legacy ObservableObject to modern Swift @Observable macro with @Bindable UI inputs.",
                            problem_statement="Create a UserSettingsViewModel decorated with @Observable containing username, notificationEnabled, and theme. Bind these properties to SwiftUI TextField and Toggle controls using @Bindable, verifying real-time reactivity without @Published boilerplate.",
                            requirements=[
                                "Decorate ViewModel class with @Observable macro (iOS 17+).",
                                "Instantiate ViewModel in SwiftUI view with @State.",
                                "Use @Bindable var viewModel = viewModel inside the view body for two-way bindings.",
                                "Verify zero usage of legacy ObservableObject and @Published."
                            ],
                            concepts_tested=["Swift @Observable Macro", "@Bindable Property Wrapper", "Two-Way Data Binding", "Observation Framework"],
                            expected_outcome="A clean, modern SwiftUI view bound directly to an @Observable ViewModel.",
                            optional_hints=["@Observable tracks property accesses automatically at runtime without needing @Published on each field."]
                        ),
                        make_problem(
                            problem_id="mvvm-prob-2",
                            title="MVVM ViewModel with Dependency Injection & UI States",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an MVVM ViewModel managing distinct loading, error, and success states with protocol-injected services.",
                            problem_statement="Build a NewsFeedViewModel that accepts a protocol NewsServiceProtocol. Model UI state as an enum ViewState { case idle, loading, success([Article]), error(String) }. Implement loadArticles() fetching data, updating state, and writing unit tests using a mock service.",
                            requirements=[
                                "Define NewsServiceProtocol and mock implementation MockNewsService.",
                                "Inject service via ViewModel initializer with default production parameter.",
                                "Expose state enum: idle, loading, success, failure.",
                                "Write unit tests verifying ViewModel transitions from loading to success when service succeeds."
                            ],
                            concepts_tested=["MVVM Design Pattern", "Explicit UI State Modeling", "Protocol-Based Dependency Injection", "ViewModel Unit Testing"],
                            expected_outcome="A completely decoupled and testable ViewModel driving predictable UI states.",
                            optional_hints=["Modeling UI states as explicit enums prevents illegal states (e.g. showing both loading spinner and error banner)."]
                        ),
                        make_problem(
                            problem_id="mvvm-prob-3",
                            title="Modular Feature Package & Coordinator Navigation",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Decompose a monolithic app into a modular Swift Package with coordinator-pattern navigation.",
                            problem_statement="Extract an authentication feature (Login, Register, Forgot Password) into an isolated Swift Package module. Implement a flow coordinator managing a NavigationPath stack, ensuring individual views remain completely ignorant of navigation destinations and communicate solely via delegate closures or actions.",
                            requirements=[
                                "Create a separate local Swift Package for the feature module.",
                                "Implement an AuthFlowCoordinator managing NavigationPath.",
                                "Decouple views: LoginView communicates intent via onLoginSuccess: () -> Void closure.",
                                "Demonstrate running the feature module in an isolated sample app."
                            ],
                            concepts_tested=["Modular Swift Package Architecture", "Coordinator Navigation Pattern", "Feature Decoupling", "NavigationPath Manipulation"],
                            expected_outcome="A modular, reusable feature package ready for enterprise multi-target apps.",
                            optional_hints=["Coordinators take navigation responsibilities away from individual views, making views 100% reusable."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Asynchronous Swift & Modern Persistence",
            "description": "Structured concurrency with async/await, Task, Actors, and local database persistence with SwiftData.",
            "skills": [
                make_skill(
                    slug="swift-concurrency",
                    name="Asynchronous Programming with Swift Concurrency",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Modern Swift concurrency: async/await, Task, TaskGroup, structured concurrency, Actors for data race safety, and the @MainActor attribute.",
                    key_topics=["async/await Syntax & Continuation Resumes", "Structured Concurrency with Task & TaskGroup", "Actors & Data Race Elimination", "@MainActor for UI Thread Guarantees", "AsyncSequence & AsyncStream"],
                    role_relevance="Prevents data races and thread deadlocks while providing clear, sequential asynchronous code without callback hell.",
                    prerequisites=["swift-fundamentals"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Swift Documentation — Concurrency", "url": "https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/", "description": "Official guide to async/await, tasks, task cancellation, and actor isolation in Swift."},
                        {"type": "YOUTUBE", "title": "Swift Concurrency Full Course — Paul Hudson", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive video course on async/await, actors, TaskGroup, and thread safety in Swift."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="async-prob-1",
                            title="Async/Await Network Fetcher with @MainActor Dispatch",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Replace completion handler callbacks with async/await and ensure UI state updates dispatch to @MainActor.",
                            problem_statement="Refactor an old callback-based API method fetchUser(completion: @escaping (Result<User, Error>) -> Void) into an asynchronous method func fetchUser() async throws -> User. Ensure the calling ViewModel is decorated with @MainActor so published UI state updates are guaranteed to run on the main thread.",
                            requirements=[
                                "Convert callback API to async throws function using URLSession.shared.data(from:).",
                                "Decorate ViewModel with @MainActor.",
                                "Invoke async method from SwiftUI using the .task { await viewModel.load() } modifier.",
                                "Verify zero compile-time Swift 6 concurrency warnings."
                            ],
                            concepts_tested=["async/await Syntax", "@MainActor Annotation", "SwiftUI .task Lifecycle Modifier", "Swift 6 Strict Concurrency"],
                            expected_outcome="Clean sequential async code completely eliminating completion handler nesting.",
                            optional_hints=[".task modifier automatically cancels the asynchronous task if the view disappears before completion."]
                        ),
                        make_problem(
                            problem_id="async-prob-2",
                            title="Parallel Batch Fetching with TaskGroup",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Fetch multiple independent API resources concurrently using structured TaskGroup.",
                            problem_statement="Write a function fetchDashboardData(itemIDs: [String]) async throws -> [DashboardItem] that fetches data for 10 distinct IDs simultaneously using withThrowingTaskGroup. Aggregate completed results as they finish and cancel all pending tasks if any single request throws a fatal error.",
                            requirements=[
                                "Use withThrowingTaskGroup(of: DashboardItem.self) to spawn concurrent child tasks.",
                                "Stream results using for try await item in group.",
                                "Demonstrate that cancellation propagates to all pending child tasks upon error.",
                                "Verify total execution duration equals max(task_duration) rather than sum(task_durations)."
                            ],
                            concepts_tested=["TaskGroup & Structured Concurrency", "Concurrent Parallel Execution", "Cooperative Task Cancellation", "Async Sequence Consumption"],
                            expected_outcome="A high-throughput parallel data loader that drastically minimizes screen load latency.",
                            optional_hints=["Structured concurrency guarantees that child tasks never outlive their parent TaskGroup scope."]
                        ),
                        make_problem(
                            problem_id="async-prob-3",
                            title="Thread-Safe Cache with Actor Isolation & AsyncStream",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Prevent data races in shared state using Swift Actors and build a real-time event pipeline using AsyncStream.",
                            problem_statement="Build an ImageCache actor that provides synchronized, data-race-free in-memory caching for downloaded images. Additionally, implement an AsyncStream producing simulated real-time WebSocket stock price updates, and consume the stream in a SwiftUI view with smooth UI transitions.",
                            requirements=[
                                "Implement actor ImageCache with isolated internal storage dictionary.",
                                "Prevent duplicate in-flight requests for the same URL using cached Task objects.",
                                "Create an AsyncStream<StockQuote> that emits continuous price updates.",
                                "Consume stream via for await quote in stockStream within a @MainActor task."
                            ],
                            concepts_tested=["Swift Actors (Thread Safety)", "Task Deduplication in Actors", "AsyncStream Event Streaming", "Data Race Elimination"],
                            expected_outcome="A bulletproof actor-isolated caching engine completely safe under heavy concurrent load.",
                            optional_hints=["Actors serialize access to their internal mutable state, making data races impossible by design."]
                        ),
                    ],
                ),
                make_skill(
                    slug="swiftdata-persistence",
                    name="Local Persistence with SwiftData & Core Data",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Apple's modern persistence framework: @Model macro, ModelContainer, ModelContext, @Query property wrapper, predicates, schema migrations, and relationships.",
                    key_topics=["SwiftData Architecture (@Model Macro)", "ModelContainer & ModelContext Lifecycle", "SwiftUI Integration with @Query & #Predicate", "Relationships & Delete Rules (Cascade, Nullify)", "Schema Versioning & Lightweight Migrations"],
                    role_relevance="Provides fast, type-safe local data caching, offline-first functionality, and relational persistence.",
                    prerequisites=["swiftui-development", "swift-concurrency"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apple Developer Documentation — SwiftData", "url": "https://developer.apple.com/documentation/swiftdata", "description": "Official guide to configuring models, queries, contexts, and containers in SwiftData."},
                        {"type": "YOUTUBE", "title": "SwiftData in SwiftUI — Paul Hudson", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Complete tutorial on setting up SwiftData models, relationships, predicates, and migrations."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sd-prob-1",
                            title="SwiftData Task Tracker with @Query & CRUD",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a relational SwiftData model and bind it directly to a SwiftUI List with @Query.",
                            problem_statement="Build a personal task manager. Define a @Model class TodoItem with id, title, isCompleted, and createdAt. Configure .modelContainer(for: TodoItem.self) on the App struct, query items sorted by date using @Query, and implement add, toggle completion, and swipe-to-delete.",
                            requirements=[
                                "Define model class using @Model macro.",
                                "Inject container into app root via .modelContainer(for:).",
                                "Query sorted items using @Query(sort: \\TodoItem.createdAt, order: .reverse).",
                                "Perform CRUD operations via modelContext.insert() and modelContext.delete()."
                            ],
                            concepts_tested=["@Model Macro", "@Query Property Wrapper", "ModelContext Operations", "SwiftUI SwiftData Integration"],
                            expected_outcome="A persistent local task manager that persists data seamlessly across app launches.",
                            optional_hints=["SwiftData automatically saves modelContext modifications to disk without needing explicit save() calls."]
                        ),
                        make_problem(
                            problem_id="sd-prob-2",
                            title="Relational Models with Cascade Delete & #Predicate Filtering",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Model 1-to-Many relationships with cascade deletion rules and filter results using Swift #Predicate macros.",
                            problem_statement="Create a Project and Task model hierarchy where each Project has @Relationship(deleteRule: .cascade) var tasks: [Task]. Write dynamic queries filtering tasks using #Predicate<Task> { $0.isCompleted == false && $0.priority > 2 }.",
                            requirements=[
                                "Define 1-to-many relationship with .cascade delete rule.",
                                "Verify deleting a project automatically deletes all its associated child tasks.",
                                "Filter queried results using type-safe #Predicate macro expressions.",
                                "Support dynamic predicate swapping based on user filter chips in the UI."
                            ],
                            concepts_tested=["1-to-Many Model Relationships", "Cascade Delete Rules", "#Predicate Macro Syntax", "Dynamic Query Filtering"],
                            expected_outcome="A relational local database enforcing referential integrity and performant filtering.",
                            optional_hints=["#Predicate expressions are checked at compile-time and translated to SQLite queries under the hood."]
                        ),
                        make_problem(
                            problem_id="sd-prob-3",
                            title="SwiftData Schema Migration Plan & Versioning",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Execute an automated multi-stage database schema migration between model versions using SchemaMigrationPlan.",
                            problem_statement="Evolve an app's data model from V1 to V2: rename user field 'fullName' to separate 'firstName' and 'lastName' attributes. Define SchemaV1, SchemaV2, implement a custom MigrationStage.custom stage in a SchemaMigrationPlan, and verify zero data loss during user app update.",
                            requirements=[
                                "Declare VersionedSchema for SchemaV1 and SchemaV2.",
                                "Create a custom SchemaMigrationPlan defining MigrationStage.custom from V1 to V2.",
                                "Write migration logic splitting existing full names into first and last name columns.",
                                "Verify database migrates cleanly without crashing or dropping user records."
                            ],
                            concepts_tested=["VersionedSchema Protocol", "SchemaMigrationPlan", "Custom Migration Stages", "Zero-Downtime Data Evolution"],
                            expected_outcome="A verified migration pipeline ensuring seamless data preservation during app upgrades.",
                            optional_hints=["Versioned schemas isolate historical model definitions so migrations can transform data reliably."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Networking, Security & App Store Delivery",
            "description": "Network integration with URLSession, secure Keychain storage, and App Store preparation.",
            "skills": [
                make_skill(
                    slug="ios-networking-apis",
                    name="Networking & REST APIs with URLSession",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Communicating with remote services: URLSession data tasks, JSONDecoder/JSONEncoder, Codable protocol, OAuth token interceptors, Keychain secure credential storage, and offline caching.",
                    key_topics=["URLSession Data & Download Tasks", "Codable Protocol & Custom Date/Key Strategies", "Authentication Interceptors & Token Refresh", "Secure Storage with iOS Keychain Services", "Network Reachability & Offline Caching"],
                    role_relevance="Connects native iOS applications to cloud microservices securely, efficiently, and resiliently.",
                    prerequisites=["swift-concurrency", "ios-mvvm-state"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apple Developer Documentation — URLSession", "url": "https://developer.apple.com/documentation/foundation/urlsession", "description": "Official guide to uploading, downloading, and configuring network sessions in Apple platforms."},
                        {"type": "YOUTUBE", "title": "Networking in Swift (URLSession & Codable) — Sean Allen", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "In-depth tutorial on async/await networking, JSON decoding, and custom error handling."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="net-ios-prob-1",
                            title="Generic API Client with Codable & Custom Key Strategies",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build a generic, reusable network request method that decodes arbitrary JSON models via Codable.",
                            problem_statement="Write a NetworkClient class with a generic method func request<T: Decodable>(endpoint: Endpoint) async throws -> T. Configure JSONDecoder with keyDecodingStrategy = .convertFromSnakeCase and custom ISO-8601 date decoding strategies.",
                            requirements=[
                                "Define Endpoint protocol with path, HTTPMethod, headers, and queryItems.",
                                "Validate HTTP response status code (200...299), throwing custom NetworkError on HTTP errors.",
                                "Configure JSONDecoder to parse snake_case JSON into camelCase Swift structs automatically.",
                                "Handle network connection offline errors gracefully."
                            ],
                            concepts_tested=["Generic URLSession Client", "Codable Protocol", "keyDecodingStrategy (.convertFromSnakeCase)", "HTTP Status Code Validation"],
                            expected_outcome="A reusable network client capable of fetching and decoding any API model in a single line of code.",
                            optional_hints=["Using .convertFromSnakeCase avoids writing tedious manual CodingKeys enums."]
                        ),
                        make_problem(
                            problem_id="net-ios-prob-2",
                            title="Keychain Storage Wrapper & Token Interceptor",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Store authentication tokens in the encrypted iOS Keychain and implement automatic token refresh interceptors.",
                            problem_statement="Create a KeychainManager wrapper around SecItemAdd, SecItemCopyMatching, and SecItemDelete. In your network client, intercept requests requiring authentication, inject the Bearer token from Keychain, and if an endpoint returns 401 Unauthorized, automatically call refresh token endpoint and retry the original request.",
                            requirements=[
                                "Implement secure Keychain CRUD with kSecClassGenericPassword and kSecAttrAccessibleAfterFirstUnlock.",
                                "Intercept outbound requests to append Authorization: Bearer <token> headers.",
                                "Implement automatic token refresh on 401 Unauthorized responses.",
                                "Re-execute the original request seamlessly upon successful token refresh."
                            ],
                            concepts_tested=["iOS Keychain Services", "Token Interception Pattern", "Automatic 401 Token Refresh", "Secure Credential Storage"],
                            expected_outcome="A production network layer providing transparent authentication and secure cryptographic key storage.",
                            optional_hints=["Never store access or refresh tokens in UserDefaults; always use the encrypted iOS Keychain."]
                        ),
                        make_problem(
                            problem_id="net-ios-prob-3",
                            title="Offline-First Sync Engine & Network Monitor",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build an offline-first syncing engine utilizing NWPathMonitor and SwiftData local caches.",
                            problem_statement="Develop an offline-first architecture for an iOS notes app. When offline (detected via NWPathMonitor), route modifications directly to local SwiftData storage with a syncStatus = .pendingUpload flag. When connectivity restores, automatically execute a background sync queue that uploads pending changes and reconciles conflicts.",
                            requirements=[
                                "Monitor network reachability changes using Network framework NWPathMonitor.",
                                "Queue pending offline mutations in local SwiftData storage.",
                                "Process pending upload queue sequentially upon network reconnection.",
                                "Implement conflict resolution strategy (e.g. server-wins or timestamp-based last-write-wins)."
                            ],
                            concepts_tested=["Offline-First Architecture", "NWPathMonitor Reachability", "Background Mutation Queues", "Conflict Resolution Strategies"],
                            expected_outcome="An application providing instant local responsiveness even when completely disconnected from the internet.",
                            optional_hints=["NWPathMonitor provides real-time callbacks whenever WiFi/cellular connectivity toggles."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

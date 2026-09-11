"""Data Engineer roadmap definition with progressive practice problems."""
from typing import Any, Dict
from app.db.roadmaps_data.common import ROADMAP_IDS, make_problem, make_skill

DATA_ENGINEER_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["data-engineer"],
    "slug": "data-engineer",
    "role_id": None,
    "title": "Data Engineer",
    "domain": "Data Engineering",
    "category": "Engineering",
    "description": "Architect scalable data pipelines, analytical warehouses, and lakehouses: distributed computing with Apache Spark, pipeline orchestration with Airflow, stream processing with Kafka, modular modeling with dbt, and enterprise data quality governance.",
    "version": "v2.0",
    "has_market_data": False,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Data Foundations & Analytical SQL",
            "description": "Core programming, memory-efficient data manipulation, and advanced relational analytical querying.",
            "skills": [
                make_skill(
                    slug="python-de",
                    name="Python for Data Engineering",
                    canonical_slug="python",
                    difficulty="BEGINNER",
                    description="Idiomatic Python for data pipelines: generators, memory-efficient file streaming (CSV/Parquet/JSON), typing, and packaging.",
                    key_topics=["Generators & Streaming Iterators", "Typing & Pydantic Data Models", "File Format Parsing (Parquet/Arrow/CSV)", "Subprocess & OS Interaction", "Packaging & CLI Utilities"],
                    role_relevance="The lingua franca for data ingestion scripts, ETL orchestration frameworks, and Spark API bindings.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Python Official Documentation", "url": "https://docs.python.org/3/", "description": "Official Python 3 language specifications and standard library reference."},
                        {"type": "YOUTUBE", "title": "Python for Data Engineers — freeCodeCamp", "url": "https://www.youtube.com/watch?v=LHBE6Q9XlzI", "description": "Hands-on data processing, generator patterns, and batch file manipulation in Python."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="py-de-prob-1",
                            title="Memory-Bounded Log Parser",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Stream and parse multi-gigabyte log files in constant memory using Python generators.",
                            problem_statement="Write a generator function stream_log_records(filepath: str) that reads access logs line by line, parses IP/timestamp/status using regex, and yields validated record dictionaries without loading the entire file into RAM.",
                            requirements=[
                                "Use yield to stream records one at a time.",
                                "Verify memory footprint remains under 50MB regardless of file size.",
                                "Extract client IP, ISO-8601 timestamp, HTTP method, path, status code, and response bytes.",
                                "Handle malformed log lines gracefully by writing to a rejected_records counter."
                            ],
                            concepts_tested=["Python Generators", "File Streaming", "Regular Expressions", "Memory Optimization", "Exception Handling"],
                            expected_outcome="A robust log streaming utility capable of handling arbitrarily large files with constant memory.",
                            optional_hints=["Avoid using readlines(); iterate directly over the file object."]
                        ),
                        make_problem(
                            problem_id="py-de-prob-2",
                            title="Pydantic Ingestion Pipeline & Schema Enforcement",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Build a type-safe batch ingestion pipeline that validates incoming JSON payloads against strict schema contracts.",
                            problem_statement="Create a DataIngestionPipeline class using Pydantic models that ingests raw telemetry events, validates required fields and value ranges, and outputs clean PyArrow Table partitions.",
                            requirements=[
                                "Define Pydantic schema models with custom field validators (e.g. timestamp ranges, enum statuses).",
                                "Implement dead-letter routing for invalid payloads with detailed validation error reasons.",
                                "Convert validated records into Apache Arrow Tables and write snappy-compressed Parquet files."
                            ],
                            concepts_tested=["Pydantic Schema Validation", "Dead-Letter Queue Pattern", "PyArrow Integration", "Parquet Serialization"],
                            expected_outcome="A production ingestion stage producing pristine columnar Parquet files and isolated dead-letter files.",
                            optional_hints=["Use pyarrow.Table.from_pylist and pyarrow.parquet.write_table with compression='snappy'."]
                        ),
                        make_problem(
                            problem_id="py-de-prob-3",
                            title="Multi-Threaded REST API Extractor & Incremental Syncer",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Develop a production-grade multi-threaded API data extractor that syncs records incrementally with rate limiting and checkpointing.",
                            problem_statement="Build an API extractor that queries a paginated REST API, tracks high-watermark timestamps in SQLite/local JSON state, uses ThreadPoolExecutor with exponential backoff retry, and emits deduplicated event batches.",
                            requirements=[
                                "Support cursor-based and timestamp-based incremental synchronization.",
                                "Implement rate-limiting and exponential backoff retry on HTTP 429/500 errors using tenacity or urllib3.",
                                "Persist sync high-watermark state atomically to allow resume on failure without duplicating data.",
                                "Write complete unit tests with mocked API responses validating failure recovery."
                            ],
                            concepts_tested=["Incremental Synchronization", "High-Watermark Checkpointing", "Rate Limiting & Retries", "Concurrency & ThreadPool", "Idempotency"],
                            expected_outcome="A production-ready data extractor that seamlessly resumes after network cuts and guarantees at-least-once extraction.",
                            optional_hints=["Store checkpoint state in an atomic write file (write to temp file then os.replace)."]
                        ),
                    ],
                ),
                make_skill(
                    slug="sql-warehousing",
                    name="Advanced SQL & Analytical Warehousing",
                    canonical_slug="postgresql",
                    difficulty="INTERMEDIATE",
                    description="Advanced SQL for data warehousing: window functions, analytical rollups, CTEs, indexing, execution plan analysis, and partition pruning.",
                    key_topics=["Window Functions (LEAD/LAG, DENSE_RANK)", "Recursive CTEs & Hierarchies", "GROUPING SETS & Rollups", "EXPLAIN ANALYZE & Query Optimization", "Partitioning & Sorting Keys"],
                    role_relevance="The fundamental querying language used across all cloud warehouses (Snowflake, BigQuery, Redshift, PostgreSQL).",
                    prerequisites=["python-de"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PostgreSQL Documentation — Window Functions", "url": "https://www.postgresql.org/docs/current/tutorial-window.html", "description": "Official guide to analytical queries, frames, and partition clauses in PostgreSQL."},
                        {"type": "YOUTUBE", "title": "Advanced SQL Tutorial — Alex The Analyst", "url": "https://www.youtube.com/watch?v=7mz73uXD9DA", "description": "Hands-on walkthrough of window functions, CTEs, subqueries, and execution plans."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sql-wh-prob-1",
                            title="User Retention & Churn Cohort Query",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write advanced analytical SQL using window functions to calculate monthly cohort retention curves.",
                            problem_statement="Given a table of user logins (user_id, login_timestamp), construct a SQL query that computes the signup cohort month for each user and calculates month-over-month retention percentages for 12 consecutive months.",
                            requirements=[
                                "Use FIRST_VALUE or MIN() OVER (PARTITION BY user_id) to assign each user to their signup cohort.",
                                "Calculate elapsed months between login and cohort month using DATE_TRUNC.",
                                "Pivot or aggregate retention rates per cohort month with percentage calculations rounded to 2 decimals."
                            ],
                            concepts_tested=["Window Functions", "Cohort Analysis", "Date Truncation & Math", "Pivot Aggregation"],
                            expected_outcome="A clean cohort retention matrix displaying percentage active users across retention periods.",
                            optional_hints=["Use EXTRACT(year FROM age) * 12 + EXTRACT(month FROM age) for precise month diffs."]
                        ),
                        make_problem(
                            problem_id="sql-wh-prob-2",
                            title="Sessionization & Inactivity Gap Detection",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Reconstruct user browsing sessions from clickstream events using LAG and running cumulative sums.",
                            problem_statement="Given a clickstream table with (user_id, event_time, page_url), group events into distinct sessions where any inactivity gap greater than 30 minutes triggers a new session_id.",
                            requirements=[
                                "Use LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) to compute event intervals.",
                                "Apply a CASE statement flagging 1 when interval > 30 mins (or on first event), else 0.",
                                "Calculate a running SUM() over the flag to generate monotonic session_id integers per user."
                            ],
                            concepts_tested=["LAG Function", "Running Total / Cumulative Sum", "Sessionization Pattern", "Partition Ordering"],
                            expected_outcome="A clickstream query that correctly assigns session IDs and computes total session durations.",
                            optional_hints=["A running SUM over a binary flag creates incrementing group IDs whenever the flag is 1."]
                        ),
                        make_problem(
                            problem_id="sql-wh-prob-3",
                            title="Data Warehouse Query Optimization & Partition Pruning",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Diagnose performance bottlenecks using EXPLAIN ANALYZE and restructure slow queries for partition pruning.",
                            problem_statement="Given a 100M-row partitioned sales table, analyze an expensive sequential scan query, re-index with composite keys, partition by date range, and rewrite the query to eliminate spill-to-disk sorting.",
                            requirements=[
                                "Interpret EXPLAIN ANALYZE output (Seq Scan vs Bitmap Index Scan vs Hash Join).",
                                "Implement declarative table range partitioning on sale_date.",
                                "Demonstrate partition pruning where the query plan scans only target partition boundaries.",
                                "Achieve a minimum 10x query execution speedup and verify zero disk temp file usage."
                            ],
                            concepts_tested=["EXPLAIN ANALYZE", "Partition Pruning", "Composite Indexes", "Hash Join Optimization", "Memory Spill Diagnosis"],
                            expected_outcome="A documented optimization report showing the before/after execution plans with order-of-magnitude latency reduction.",
                            optional_hints=["Ensure WHERE filters match the partition key without wrapping it in function calls (sargable queries)."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Data Modeling & Batch Lakehouse Processing",
            "description": "Dimensional warehouse architecture and massive distributed processing with Apache Spark.",
            "skills": [
                make_skill(
                    slug="data-modeling",
                    name="Data Modeling & Dimensional Architecture",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Kimball dimensional modeling: star schema, snowflake schema, fact tables (transaction, snapshot, accumulating), slowly changing dimensions (SCD Type 1, 2, 3), and surrogate key generation.",
                    key_topics=["Kimball Dimensional Modeling", "Star vs Snowflake Schemas", "Fact Types (Transaction, Periodic, Accumulating)", "Slowly Changing Dimensions (SCD Type 1, 2, 3)", "Surrogate Keys & Conformed Dimensions"],
                    role_relevance="The blueprint that transforms messy operational logs into intuitive, performant analytical datamarts for business intelligence.",
                    prerequisites=["sql-warehousing"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "The Kimball Group Dimensional Modeling Techniques", "url": "https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/", "description": "Authoritative guide to star schema, facts, dimensions, and grain definition."},
                        {"type": "YOUTUBE", "title": "Data Modeling for Data Engineers — Seattle Data Guy", "url": "https://www.youtube.com/watch?v=hB9iI7kLd34", "description": "Practical architectural walkthrough of star schemas, normalization, and SCD Type 2 handling."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="dm-prob-1",
                            title="E-Commerce Star Schema Design",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Design a star schema datamart from an operational normalized e-commerce database.",
                            problem_statement="Given a 3NF relational schema (Users, Orders, LineItems, Products, Categories, Addresses), design a dimensional star schema with a FactSales table and appropriate dimension tables (DimCustomer, DimProduct, DimDate, DimLocation).",
                            requirements=[
                                "Define the exact grain of FactSales (e.g. one row per order line item).",
                                "Include surrogate keys (customer_sk, product_sk) and natural business keys.",
                                "Flatten product hierarchy (Category -> Subcategory -> Product) into a denormalized DimProduct dimension.",
                                "Produce a DDL SQL file creating all fact and dimension tables with foreign key relationships."
                            ],
                            concepts_tested=["Grain Definition", "Star Schema Denormalization", "Surrogate Keys", "Fact vs Dimension Separation"],
                            expected_outcome="A clean star schema DDL ready for deployment to any analytical relational engine.",
                            optional_hints=["A DimDate table should include calendar attributes like quarter, day_of_week, and is_holiday."]
                        ),
                        make_problem(
                            problem_id="dm-prob-2",
                            title="Automated SCD Type 2 Pipeline",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an idempotent Slowly Changing Dimension Type 2 update pipeline in SQL.",
                            problem_statement="Build a pipeline that takes daily snapshots of employee departmental assignments, detects changes, expires previous records with is_current=FALSE and end_date, and inserts new versions with valid_from/valid_to timestamps.",
                            requirements=[
                                "Detect row modifications using hash comparisons (MD5 / SHA256 of tracked attributes).",
                                "Expire existing active records where differences are detected by updating valid_to and setting is_current = FALSE.",
                                "Insert updated records with valid_from = CURRENT_TIMESTAMP, valid_to = '9999-12-31', and is_current = TRUE.",
                                "Ensure complete idempotency: running twice with identical input produces zero redundant versions."
                            ],
                            concepts_tested=["SCD Type 2 Implementation", "Hash-Based Change Detection", "Temporal Validity Modeling", "Pipeline Idempotency"],
                            expected_outcome="A verified SCD Type 2 transformation script preserving historical attribute audit trails.",
                            optional_hints=["Use an explicit staging table and MERGE or CTE-based UPDATE + INSERT statements."]
                        ),
                        make_problem(
                            problem_id="dm-prob-3",
                            title="Accumulating Snapshot Fact Table for Fulfillment",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Model and build an accumulating snapshot fact table tracking multi-stage order fulfillment pipelines.",
                            problem_statement="Create FactOrderFulfillment tracking orders through milestone lifecycle dates (Order Placed -> Payment Confirmed -> Picked -> Shipped -> Delivered -> Returned) with duration metrics across milestones.",
                            requirements=[
                                "Design the fact table with date surrogate keys for each lifecycle milestone.",
                                "Include lag duration columns (e.g. hours_to_ship, days_to_deliver).",
                                "Write update logic that updates in-flight order rows as lifecycle events arrive asynchronously over weeks.",
                                "Validate that downstream queries can instantly aggregate median fulfillment duration by shipping carrier."
                            ],
                            concepts_tested=["Accumulating Snapshot Facts", "Milestone Lifecycle Tracking", "Asynchronous In-Flight Updates", "Duration Metric Modeling"],
                            expected_outcome="A fully modeled accumulating snapshot pipeline capable of continuous lifecycle updates.",
                            optional_hints=["Accumulating snapshot fact rows are updated multiple times until the business process reaches its terminal state."]
                        ),
                    ],
                ),
                make_skill(
                    slug="distributed-spark",
                    name="Distributed Data Processing with Apache Spark",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Distributed batch processing with PySpark: Catalyst optimizer, DataFrame API, caching strategies, shuffling, partition tuning, and broadcast joins.",
                    key_topics=["Spark Architecture (Driver, Executor, Cluster Manager)", "PySpark DataFrame & SQL API", "Catalyst Optimizer & Tungsten Engine", "Shuffling, Skew Handling & Broadcast Joins", "Partitioning, Coalesce & Repartition Strategies"],
                    role_relevance="The standard industry engine for petabyte-scale data transformations, distributed aggregations, and lakehouse pipelines.",
                    prerequisites=["python-de", "sql-warehousing"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apache Spark Official Documentation", "url": "https://spark.apache.org/docs/latest/", "description": "Comprehensive documentation for Spark Core, DataFrames, SQL, and cluster deployment."},
                        {"type": "YOUTUBE", "title": "PySpark Tutorial for Beginners — freeCodeCamp", "url": "https://www.youtube.com/watch?v=_C8kWso4ne4", "description": "Hands-on PySpark walkthrough: transformations, actions, joins, and performance tuning."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="spark-prob-1",
                            title="PySpark Log Aggregator & Columnar Export",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Process distributed datasets using PySpark DataFrames and export partitioned Parquet.",
                            problem_statement="Write a PySpark script that ingests 10 million simulated web event rows, cleans missing values, computes top 10 URLs per geographic country using window functions, and writes output partitioned by date and country.",
                            requirements=[
                                "Initialize a SparkSession with proper memory allocations.",
                                "Filter invalid rows and cast data types explicitly.",
                                "Use Window.partitionBy('country').orderBy(desc('count')) to rank URLs.",
                                "Write output using dataframe.write.partitionBy('date', 'country').parquet()."
                            ],
                            concepts_tested=["SparkSession Initialization", "PySpark DataFrame API", "Spark Window Functions", "Partitioned Parquet Writing"],
                            expected_outcome="A distributed PySpark script outputting cleanly partitioned Parquet datasets on disk.",
                            optional_hints=["Use pyspark.sql.functions import col, desc, rank."]
                        ),
                        make_problem(
                            problem_id="spark-prob-2",
                            title="Broadcast Joins & Data Skew Remediation",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Eliminate expensive shuffle operations using broadcast joins and solve severe key skew via salting.",
                            problem_statement="Given a 100GB transaction dataset joined with a 20MB lookup table and exhibiting 90% key concentration on a single merchant ID, optimize the join execution to eliminate out-of-memory executor failures.",
                            requirements=[
                                "Apply broadcast(lookup_df) to prevent shuffle exchange on the small table.",
                                "Inspect Spark UI execution DAG to confirm BroadcastHashJoin instead of SortMergeJoin.",
                                "Implement key salting: append random salt (0..N) to skewed merchant keys, explode lookup table accordingly, and join without executor OOM."
                            ],
                            concepts_tested=["BroadcastHashJoin", "Key Salting Pattern", "Data Skew Remediation", "Spark UI DAG Analysis"],
                            expected_outcome="A tuned join job running in balanced executor time without spill-to-disk or skew bottlenecks.",
                            optional_hints=["Salting distributes a single hot key across multiple partitions by appending a pseudo-random integer suffix."]
                        ),
                        make_problem(
                            problem_id="spark-prob-3",
                            title="Custom PySpark UDF & Memory Optimization",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Optimize distributed processing with vectorized Pandas UDFs (PyArrow) and partition tuning.",
                            problem_statement="Develop a complex geo-distance and entity resolution pipeline that applies vectorized Arrow UDFs over geospatial coordinates, tunes spark.sql.shuffle.partitions dynamically, and avoids executor garbage collection pauses.",
                            requirements=[
                                "Implement a vectorized Pandas UDF using @pandas_udf(DoubleType()) with Haversine distance formulas.",
                                "Benchmark execution speed: compare standard Python UDF vs Pandas Arrow Vectorized UDF.",
                                "Tune executor memory, off-heap memory, and dynamic partition count to achieve linear scaling."
                            ],
                            concepts_tested=["Vectorized Pandas UDF", "Apache Arrow In-Memory Bridge", "Executor Memory Tuning", "Dynamic Shuffle Partitions"],
                            expected_outcome="A high-performance PySpark job executing 5-10x faster than standard row-by-row Python UDFs.",
                            optional_hints=["Pandas UDFs transfer batches of records across JVM and Python processes in zero-copy Arrow buffers."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Orchestration & Stream Ingestion",
            "description": "Workflow scheduling with Apache Airflow and real-time event streaming with Apache Kafka.",
            "skills": [
                make_skill(
                    slug="airflow-orchestration",
                    name="Data Pipeline Orchestration with Apache Airflow",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Orchestrating complex data pipelines: Directed Acyclic Graphs (DAGs), Operators, Sensors, TaskFlow API, dynamic task mapping, XComs, and SLA monitoring.",
                    key_topics=["DAG Design Principles & Idempotency", "TaskFlow API (@task, @dag)", "Sensors & Custom Operators", "Dynamic Task Mapping (expand / partial)", "XComs, Connection Secrets & Backfilling"],
                    role_relevance="The enterprise standard for scheduling, monitoring, and orchestrating dependencies across heterogeneous data systems.",
                    prerequisites=["python-de", "data-modeling"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apache Airflow Official Documentation", "url": "https://airflow.apache.org/docs/apache-airflow/stable/", "description": "Official Airflow architecture, TaskFlow API, and production deployment guides."},
                        {"type": "YOUTUBE", "title": "Airflow 2 Tutorial for Beginners — Marc Lamberti", "url": "https://www.youtube.com/watch?v=IH1-0hwFBRQ", "description": "Comprehensive walkthrough of DAG creation, TaskFlow API, dynamic mapping, and backfills."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="airflow-prob-1",
                            title="Daily ETL DAG with TaskFlow API",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Create a modular, idempotent daily batch ETL workflow using modern Airflow TaskFlow API.",
                            problem_statement="Define an Airflow DAG with schedule_interval='@daily' and catchup=False that extracts daily exchange rates, transforms currency values, and loads into PostgreSQL with proper error notifications.",
                            requirements=[
                                "Use @dag and @task decorators exclusively.",
                                "Pass data between tasks using typed XCom arguments.",
                                "Implement an on_failure_callback that logs alert details.",
                                "Verify DAG parses cleanly with zero cycle errors."
                            ],
                            concepts_tested=["Airflow TaskFlow API", "XCom Data Exchange", "Failure Callbacks", "DAG Scheduling Configuration"],
                            expected_outcome="A fully working Airflow DAG file adhering to modern Airflow 2 best practices.",
                            optional_hints=["Never place heavyweight data in XComs; pass metadata references (e.g. S3 URIs) instead."]
                        ),
                        make_problem(
                            problem_id="airflow-prob-2",
                            title="Dynamic Task Mapping & File Partition Sensor",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Use dynamic task mapping to process variable batches of incoming data files concurrently.",
                            problem_statement="Construct an Airflow pipeline with an S3KeySensor that detects newly arrived partition files, dynamically spawns a worker task per file using .expand(), and joins results in a summary aggregation task.",
                            requirements=[
                                "Implement a sensor waiting for upstream trigger flags.",
                                "Use dynamic task mapping (task.expand()) to generate worker instances at runtime based on discovered file counts.",
                                "Set proper max_active_tis_per_dag limits to prevent overloading external databases."
                            ],
                            concepts_tested=["Dynamic Task Mapping", "Airflow Sensors", "Concurrency Throttling", "Fan-Out / Fan-In Topology"],
                            expected_outcome="An elastic DAG that dynamically adapts its task count to input file volume.",
                            optional_hints=["Use Python task returning a list of paths, then pass that list to target_task.expand(file_path=...)."]
                        ),
                        make_problem(
                            problem_id="airflow-prob-3",
                            title="Idempotent Historical Backfill & SLA Pipeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Execute an idempotent historical backfill spanning 1 year of data with strict SLA alerts and retries.",
                            problem_statement="Develop a mission-critical billing pipeline with strict 2-hour SLA thresholds, automated Slack notification hooks on delay, exponential retry on database deadlocks, and CLI-driven backfill verification.",
                            requirements=[
                                "Design tasks to be strictly idempotent across execution_date / logical_date parameters.",
                                "Configure sla=timedelta(hours=2) and sla_miss_callback to trigger alerts on SLA breach.",
                                "Simulate backfilling 365 days of partitions via CLI airflow dags backfill without data duplication."
                            ],
                            concepts_tested=["Historical Backfilling", "Logical Date Parameterization", "SLA Monitoring & Callbacks", "Idempotent Data Overwrites"],
                            expected_outcome="A production pipeline validated for seamless historical re-runs without side effects.",
                            optional_hints=["Always use execution_date / data_interval_start in partition paths to prevent backfills writing to 'current date'."]
                        ),
                    ],
                ),
                make_skill(
                    slug="kafka-streaming",
                    name="Stream Processing with Apache Kafka",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Real-time event streaming: Kafka architecture (topics, partitions, brokers), producer semantics (acks, idempotence), consumer groups (rebalancing, offsets), and stream processing concepts.",
                    key_topics=["Broker, Topic & Partition Architecture", "Producer Semantics (acks=all, Idempotence)", "Consumer Groups, Offset Commits & Rebalancing", "Schema Registry & Avro Serialization", "Exactly-Once Semantics (EOS) Concepts"],
                    role_relevance="The backbone of real-time data architectures, decoupled microservice communication, and real-time analytical ingestion.",
                    prerequisites=["python-de", "distributed-spark"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apache Kafka Official Documentation", "url": "https://kafka.apache.org/documentation/", "description": "Comprehensive Kafka architecture, producer/consumer configurations, and performance tuning."},
                        {"type": "YOUTUBE", "title": "Apache Kafka in 6 Minutes — Confluent", "url": "https://www.youtube.com/watch?v=Ch5VhJzaoaI", "description": "Clear conceptual overview of Kafka topics, partitions, consumer groups, and replication."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="kafka-prob-1",
                            title="Idempotent Kafka Producer with Key Partitioning",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build a fault-tolerant Python Kafka producer with strict ordering guarantees per entity.",
                            problem_statement="Write a Python script using confluent-kafka that publishes financial transactions to a multi-partition topic with enable.idempotence=True, acks='all', and message keys ensuring all transactions for an account land on the same partition.",
                            requirements=[
                                "Configure producer with acks='all' and retries=5 for zero message loss.",
                                "Use account_id as the message key to preserve per-account transaction ordering.",
                                "Implement delivery report callbacks to confirm message offset and partition."
                            ],
                            concepts_tested=["Producer Idempotence", "Message Key Partitioning", "Delivery Callbacks", "Zero Message Loss Configuration"],
                            expected_outcome="A dependable producer emitting ordered, partitioned events with guaranteed durability.",
                            optional_hints=["Kafka hashes the message key to determine the partition ID: murmur2(key) % num_partitions."]
                        ),
                        make_problem(
                            problem_id="kafka-prob-2",
                            title="Consumer Group with Manual Offset Management",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an at-least-once consumer group with manual offset commits after successful database persistence.",
                            problem_statement="Develop a consumer service that subscribes to an orders topic, processes batches of messages into a database transaction, and commits Kafka offsets manually only after the database transaction succeeds.",
                            requirements=[
                                "Disable enable.auto.commit=False to prevent data loss on worker crash.",
                                "Process records in batches of 100 or 1-second maximum wait.",
                                "Commit offsets synchronously (commitSync) or asynchronously with fallback upon database transaction commit.",
                                "Handle consumer group rebalance events gracefully with ConsumerRebalanceListener."
                            ],
                            concepts_tested=["Manual Offset Commits", "At-Least-Once Semantics", "Consumer Rebalance Listeners", "Batch Processing"],
                            expected_outcome="A robust consumer resilient to crashes that never loses or drops uncommitted records.",
                            optional_hints=["Always commit the offset of the LAST successfully processed record + 1."]
                        ),
                        make_problem(
                            problem_id="kafka-prob-3",
                            title="End-to-End Real-Time Stream Enrichment Pipeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a real-time streaming pipeline that enriches raw click events with reference data and detects fraud anomalies.",
                            problem_statement="Construct an event streaming application (using Faust or PySpark Structured Streaming) that reads a stream of click events, joins with a cached merchant dimension, detects velocity spikes (>10 transactions / 5 seconds per card), and emits alerts to a fraud-alerts topic.",
                            requirements=[
                                "Implement tumbling or sliding time windowing (5-second window).",
                                "Maintain low-latency stateful aggregation per credit card ID.",
                                "Emit enriched alert payloads containing window start/end timestamps and transaction counts.",
                                "Write integration tests with an embedded or testcontainers Kafka cluster."
                            ],
                            concepts_tested=["Sliding Time Windows", "Stateful Stream Processing", "Real-Time Fraud Anomaly Detection", "Stream Enrichment"],
                            expected_outcome="A live event stream processor executing sub-second windowed fraud detection.",
                            optional_hints=["Use PySpark Structured Streaming readStream.format('kafka') or Faust Python framework."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Storage, Transformation & Quality",
            "description": "Cloud object lakes, modular dbt modeling, data quality contracts, and modern lakehouse architecture.",
            "skills": [
                make_skill(
                    slug="cloud-data-lakes",
                    name="Cloud Data Lakes & Object Storage",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Cloud storage architecture for analytics: S3 / GCS / Azure ADLS Gen2, object lifecycle policies, multi-part uploads, bucket policies, and columnar format layouts.",
                    key_topics=["Object Storage Fundamentals (S3, GCS, ADLS Gen2)", "Partition Layouts & Hive Metastore Directory Formats", "Storage Classes & Lifecycle Archival Rules", "IAM Bucket Policies & KMS Encryption", "High-Throughput Multipart Uploads"],
                    role_relevance="The physical storage substrate for modern data lakes, decoupling storage from compute for cost-effective scale.",
                    prerequisites=["data-modeling"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "AWS S3 Documentation — Data Lake Architecture", "url": "https://docs.aws.amazon.com/whitepapers/latest/building-data-lakes/building-data-lakes.html", "description": "Official whitepaper on designing scalable, secure data lakes on Amazon S3."},
                        {"type": "YOUTUBE", "title": "Building a Data Lake from Scratch — AWS Events", "url": "https://www.youtube.com/watch?v=F03kFwVb4pY", "description": "Hands-on architectural guide to folder partitioning, lifecycle management, and querying S3."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="lake-prob-1",
                            title="Partitioned Lake File Layout & Multipart Uploader",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Organize analytics data into standard Hive partitioning directory structures on cloud object storage.",
                            problem_statement="Write a Python script using boto3 / minio that takes local parquet files and uploads them to an S3 data lake bucket adhering to year=YYYY/month=MM/day=DD/ prefix conventions with multipart upload for large files.",
                            requirements=[
                                "Implement Hive-compatible key prefixes (year=YYYY/month=MM/day=DD/).",
                                "Use TransferConfig with multipart_threshold=10MB for parallelized uploads.",
                                "Tag uploaded objects with data classification (e.g. env=prod, sensitivity=internal)."
                            ],
                            concepts_tested=["Hive Partitioning Structure", "S3 Multipart Uploads", "Object Tagging", "Boto3 Client Configuration"],
                            expected_outcome="A structured data lake storage layout optimized for downstream partition discovery.",
                            optional_hints=["Hive-compatible prefixes enable engines like Athena, Presto, and Spark to automatically discover partitions."]
                        ),
                        make_problem(
                            problem_id="lake-prob-2",
                            title="Automated Lifecycle & Glacier Tiering Policy",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Configure automated storage tiering rules to reduce data lake costs across raw, staging, and archive layers.",
                            problem_statement="Develop an infrastructure-as-code or Boto3 script that applies lifecycle rules to an analytics bucket: transitioning raw logs to Infrequent Access after 30 days, Glacier Flexible Retrieval after 90 days, and permanent expiration after 365 days.",
                            requirements=[
                                "Define prefix-specific lifecycle rules for /raw, /stage, and /curated prefixes.",
                                "Configure transition actions to Standard-IA and Glacier tiers.",
                                "Enable non-current version expiration for buckets with versioning enabled."
                            ],
                            concepts_tested=["Storage Lifecycle Rules", "Cost Optimization", "Glacier Archival Tiering", "Bucket Versioning Management"],
                            expected_outcome="A formal storage policy reducing cold data storage costs by up to 70%.",
                            optional_hints=["Ensure small files under 128KB are not transitioned to IA to avoid per-request transition fees."]
                        ),
                        make_problem(
                            problem_id="lake-prob-3",
                            title="Secure Lakehouse Access Control & KMS Encryption",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Secure a data lake with customer-managed encryption keys, VPC endpoints, and least-privilege IAM policies.",
                            problem_statement="Architect and implement the security perimeter for an enterprise data lake: enforce AWS KMS SSE-KMS encryption with key rotation, restrict bucket access to specific VPC Endpoints, and write granular IAM policies for read-only analysts vs write-enabled ETL roles.",
                            requirements=[
                                "Enforce bucket policy rejecting any PutObject request lacking s3:x-amz-server-side-encryption: aws:kms.",
                                "Deny all traffic that does not originate from a designated VPC Endpoint (aws:sourceVpce).",
                                "Define IAM roles separating ETL Writer permissions from BI Reader permissions."
                            ],
                            concepts_tested=["SSE-KMS Encryption", "VPC Endpoint Policy Enforcement", "Least-Privilege IAM", "Data Lake Security Architecture"],
                            expected_outcome="A zero-trust data lake bucket compliant with SOC2 / HIPAA storage standards.",
                            optional_hints=["Use Condition: {StringNotEquals: {aws:sourceVpce: 'vpce-xxx'}} to enforce private network routing."]
                        ),
                    ],
                ),
                make_skill(
                    slug="dbt-transformation",
                    name="Data Transformation with dbt",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Modern analytical engineering with dbt: Jinja templating, incremental models, materializations (view, table, incremental, ephemeral), snapshots, tests, and documentation.",
                    key_topics=["dbt Project Architecture (Sources, Staging, Marts)", "Materializations (View, Table, Incremental, Ephemeral)", "Incremental Strategies (merge, delete+insert, append)", "Jinja Templating, Macros & Packages", "dbt Schema Testing & Generic Tests"],
                    role_relevance="The industry standard for in-warehouse data transformation, version-controlled modeling, and analytical documentation.",
                    prerequisites=["sql-warehousing", "data-modeling"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "dbt Documentation — What is dbt?", "url": "https://docs.getdbt.com/docs/introduction", "description": "Official dbt core guide, project structure, modeling guides, and testing references."},
                        {"type": "YOUTUBE", "title": "dbt Tutorial for Beginners — Kahan Data Solutions", "url": "https://www.youtube.com/watch?v=5rNquRnNb4E", "description": "Complete hands-on dbt tutorial: staging models, macros, testing, and documentation generation."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="dbt-prob-1",
                            title="Staging Models & Schema Documentation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build clean staging models adhering to dbt best practices with full schema documentation and tests.",
                            problem_statement="Create a dbt project with sources.yml pointing to raw database tables, build stg_orders and stg_customers models with standardized naming conventions and data casts, and write documentation with unique and not_null tests.",
                            requirements=[
                                "Configure source freshness checks in sources.yml.",
                                "Cast timestamps, rename cryptic column names to snake_case, and sanitize text.",
                                "Apply unique, not_null, and accepted_values tests in schema.yml.",
                                "Verify dbt run and dbt test pass with 100% success."
                            ],
                            concepts_tested=["dbt Sources & Staging Layer", "Schema YAML Definition", "Generic dbt Tests (unique, not_null)", "Data Cleansing Conventions"],
                            expected_outcome="A clean, documented, and tested dbt staging layer establishing reliable upstream models.",
                            optional_hints=["Use {{ source('source_name', 'table_name') }} to ensure dependency tracking."]
                        ),
                        make_problem(
                            problem_id="dbt-prob-2",
                            title="Incremental Fact Model with Merge Strategy",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement an incremental dbt model processing only newly updated records using merge strategies.",
                            problem_statement="Develop an fct_orders incremental model that processes millions of rows. On initial run, build full historical tables; on subsequent runs, use is_incremental() macro to process only records modified in the last 3 days.",
                            requirements=[
                                "Configure materialization='incremental' with unique_key='order_id'.",
                                "Specify incremental_strategy='merge' with on_schema_change='sync_all_columns'.",
                                "Add WHERE updated_at > (select max(updated_at) from {{ this }}) - interval '3 days' inside is_incremental() block.",
                                "Demonstrate zero duplicate keys upon repeated incremental runs."
                            ],
                            concepts_tested=["Incremental Materialization", "is_incremental() Macro", "Merge Strategy", "Lookback Window for Late-Arriving Data"],
                            expected_outcome="An optimized incremental fact model running in seconds rather than hours on daily syncs.",
                            optional_hints=["A 3-day lookback window inside is_incremental() protects against late-arriving updates."]
                        ),
                        make_problem(
                            problem_id="dbt-prob-3",
                            title="Custom dbt Macros & Snapshot Table",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Create reusable Jinja macros for dynamic currency conversion and build a dbt snapshot tracking SCD Type 2 changes.",
                            problem_statement="Write a custom dbt macro convert_currency(amount_col, from_currency_col, target_currency) that generates dynamic SQL CASE statements joining an exchange rate table. Additionally, configure a dbt snapshot file tracking status changes in raw_users using check strategy.",
                            requirements=[
                                "Develop the macro in macros/convert_currency.sql with parameter validation.",
                                "Apply the macro across multiple downstream finance mart models.",
                                "Define snapshots/snap_users.sql using strategy='check' and check_cols=['subscription_status', 'billing_tier'].",
                                "Validate that dbt snapshot creates dbt_valid_from, dbt_valid_to, and dbt_scd_id columns automatically."
                            ],
                            concepts_tested=["Custom Jinja Macros", "dbt Snapshots (SCD2)", "Reusable SQL Modularization", "Automated Historical Tracking"],
                            expected_outcome="A sophisticated dbt project leveraging reusable metaprogramming macros and automated SCD2 snapshotting.",
                            optional_hints=["dbt snapshots handle all the tedious SCD2 temporal validity logic automatically."]
                        ),
                    ],
                ),
                make_skill(
                    slug="great-expectations",
                    name="Data Quality, Testing & Great Expectations",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Data quality frameworks: Great Expectations, data contracts, anomaly detection in pipeline inputs, automated profiling, and continuous quality gates in CI/CD.",
                    key_topics=["Data Quality Dimensions (Completeness, Uniqueness, Validity, Timeliness)", "Great Expectations (Expectations, Suites, Checkpoints)", "Automated Data Profiling", "Data Quality Gates in CI/CD", "Data Contracts & Schema Evolution"],
                    role_relevance="Prevents silent data corruption from propagating downstream to executive dashboards and machine learning models.",
                    prerequisites=["dbt-transformation"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Great Expectations Official Documentation", "url": "https://docs.greatexpectations.io/docs/", "description": "Official guide to configuring Data Contexts, Expectation Suites, and Checkpoints."},
                        {"type": "YOUTUBE", "title": "Data Quality with Great Expectations — DataTalksClub", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on walkthrough of creating suites, running checkpoints, and publishing data docs."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="ge-prob-1",
                            title="Essential Expectation Suite for Customer Ingestion",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Define and execute an Expectation Suite validating completeness, uniqueness, and value distributions.",
                            problem_statement="Create a Great Expectations suite for raw customer signups. Test that email is non-null and matches regex, user_id is unique, age is between 18 and 120, and signup_country belongs to an allowed ISO code list.",
                            requirements=[
                                "Use expect_column_values_to_not_be_null and expect_column_values_to_be_unique.",
                                "Enforce regex validation on email format with expect_column_values_to_match_regex.",
                                "Enforce allowed categories with expect_column_values_to_be_in_set.",
                                "Generate and view static Data Docs HTML reports summarizing test results."
                            ],
                            concepts_tested=["Expectation Suite Creation", "Data Docs Generation", "Completeness & Validity Assertions", "Value Set Expectations"],
                            expected_outcome="A published Data Docs quality report validating incoming customer datasets.",
                            optional_hints=["Run great_expectations checkpoint run to trigger validation and doc generation in one command."]
                        ),
                        make_problem(
                            problem_id="ge-prob-2",
                            title="Pipeline Quality Gate with Airflow Operator",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Halt an automated data pipeline when incoming data violates quality contracts using GreatExpectationsOperator.",
                            problem_statement="Integrate Great Expectations with Apache Airflow. Add a checkpoint task between the Raw Ingestion and Curated Mart tasks that halts the pipeline and alerts engineers if row count drops by >20% or null rate exceeds 1%.",
                            requirements=[
                                "Implement GreatExpectationsOperator in an Airflow DAG.",
                                "Configure expect_table_row_count_to_be_between with dynamic thresholds.",
                                "Configure fail_task_on_validation_failure=True so bad data never reaches production marts."
                            ],
                            concepts_tested=["Airflow Quality Gate Integration", "Automated Pipeline Failure on Data Bug", "Row Count Anomaly Detection", "Threshold Alerting"],
                            expected_outcome="An automated pipeline that acts as a circuit breaker against poisoned or empty upstream data files.",
                            optional_hints=["Set fail_task_on_validation_failure=True to break downstream DAG execution."]
                        ),
                        make_problem(
                            problem_id="ge-prob-3",
                            title="Data Contract Enforcement & Automated Slack Alerting",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Enforce strict JSON schema data contracts at producer boundary with automated Slack alerting on violations.",
                            problem_statement="Build a data contract validation gateway for upstream software engineering teams emitting event webhooks. Verify incoming payloads against versioned schemas; on contract violation, reject the payload, route to dead-letter storage, and post a Slack alert with root-cause diffs.",
                            requirements=[
                                "Define JSON Schema data contracts versioned in Git (v1.0, v2.0).",
                                "Validate contract adherence programmatically before writing to the data lake.",
                                "Construct rich Slack alert webhook messages displaying the exact schema diff and offending payload IDs."
                            ],
                            concepts_tested=["Data Contracts Enforcement", "Schema Evolution Management", "Dead-Letter Quarantine", "Automated Incident Alerting"],
                            expected_outcome="A data contract boundary preventing upstream app breaking changes from breaking analytics.",
                            optional_hints=["Include schema version in payload headers to decouple publisher migrations from consumer processing."]
                        ),
                    ],
                ),
                make_skill(
                    slug="modern-lakehouse",
                    name="Modern Data Platform Architecture & Lakehouses",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Open table formats (Delta Lake, Apache Iceberg, Apache Hudi): ACID transactions on object storage, time travel, schema evolution, compaction, and data governance.",
                    key_topics=["Open Table Formats (Delta Lake, Apache Iceberg, Apache Hudi)", "ACID Transactions on Object Storage", "Time Travel & Audit Snapshots", "Partition Evolution & Hidden Partitioning", "File Compaction (OPTIMIZE, Z-ORDER) & Garbage Collection"],
                    role_relevance="The cutting edge of modern enterprise data platforms, combining the flexibility of data lakes with the reliability of data warehouses.",
                    prerequisites=["distributed-spark", "cloud-data-lakes", "dbt-transformation"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Apache Iceberg Official Documentation", "url": "https://iceberg.apache.org/docs/latest/", "description": "Official guide to Iceberg table architecture, metadata trees, and Spark/Trino integration."},
                        {"type": "YOUTUBE", "title": "Apache Iceberg: The Definitive Guide — Dremio", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Comprehensive explanation of metadata layers, snapshots, manifests, and ACID guarantees on object storage."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="lakehouse-prob-1",
                            title="ACID Merge & Time Travel on Apache Iceberg",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Perform transactional UPSERT operations and historical time-travel queries on Iceberg tables.",
                            problem_statement="Using PySpark with Apache Iceberg catalog, create an Iceberg table, perform an atomic MERGE INTO updating customer balances, and execute a time-travel SELECT query referencing the table snapshot ID prior to the update.",
                            requirements=[
                                "Configure SparkSession with org.apache.iceberg.spark.SparkSessionCatalog.",
                                "Execute MERGE INTO target_table USING source_updates ON target.id = source.id.",
                                "Query table history using table_name.history and execute SELECT * FROM target_table VERSION AS OF <snapshot_id>.",
                                "Verify that historical records reflect pre-merge values accurately."
                            ],
                            concepts_tested=["Iceberg Spark Configuration", "ACID MERGE INTO", "Time Travel Queries", "Snapshot History Inspection"],
                            expected_outcome="Demonstrated ACID transactional guarantees and zero-copy historical time travel on cloud storage.",
                            optional_hints=["Iceberg stores immutable snapshot metadata trees enabling instant point-in-time reads."]
                        ),
                        make_problem(
                            problem_id="lakehouse-prob-2",
                            title="Automated Compaction & Small File Elimination",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Eliminate small-file lakehouse performance degradation via automated file compaction and Z-ordering.",
                            problem_statement="Simulate a streaming ingestion job creating 10,000 tiny 50KB Parquet files. Write a maintenance job using Iceberg/Delta optimization utilities that compacts small files into optimal 256MB chunks and re-clusters data using Z-ordering on query filter columns.",
                            requirements=[
                                "Demonstrate slow query latency across 10,000 uncompacted files.",
                                "Run table compaction procedures (e.g. rewrite_data_files in Iceberg or OPTIMIZE in Delta).",
                                "Apply Z-order or sorting on frequently filtered columns (e.g. user_id, timestamp).",
                                "Measure and document post-compaction query speedup (target 5-10x improvement)."
                            ],
                            concepts_tested=["Small File Problem", "Table Compaction", "Z-Order Clustering", "Query Pruning Optimization"],
                            expected_outcome="A healthy lakehouse table with optimal file sizes and minimized manifest scanning overhead.",
                            optional_hints=["Z-ordering clusters multidimensional data so columnar engines can skip reading non-relevant files via min/max stats."]
                        ),
                        make_problem(
                            problem_id="lakehouse-prob-3",
                            title="Hidden Partition Evolution & Zero-Downtime Migration",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Evolve lakehouse table partitioning without rewriting historical data or breaking existing queries.",
                            problem_statement="Take an Iceberg table partitioned by month. Evolve the partition scheme to day without rewriting terabytes of existing month-partitioned historical Parquet files. Verify that queries on both old and new data transparently benefit from partition pruning.",
                            requirements=[
                                "Demonstrate Iceberg hidden partitioning: queries filter on timestamp without explicit partition key references.",
                                "Execute ALTER TABLE ... ADD PARTITION FIELD days(timestamp) to evolve partitioning dynamically.",
                                "Insert new day-level records and verify that execution plans prune partitions correctly for both old and new data.",
                                "Document how hidden partitioning prevents user query breakage during platform schema evolution."
                            ],
                            concepts_tested=["Hidden Partitioning", "Partition Scheme Evolution", "Zero-Downtime Data Migration", "Manifest File Metadata Architecture"],
                            expected_outcome="A modernized lakehouse architecture where table physical layouts evolve dynamically without user downtime.",
                            optional_hints=["Unlike Hive, Iceberg does not encode partition values into file paths, allowing instant partition evolution in metadata."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

"""Data Scientist roadmap definition with progressive practice problems."""
from typing import Any, Dict
from app.db.roadmaps_data.common import ROADMAP_IDS, make_problem, make_skill

DATA_SCIENTIST_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["data-scientist"],
    "slug": "data-scientist",
    "role_id": None,
    "title": "Data Scientist",
    "domain": "Data Science",
    "category": "Science & Analytics",
    "description": "Transform messy data into predictive insights and automated decision systems: statistical inference, exploratory data analysis, predictive modeling (Scikit-Learn, XGBoost), deep learning (PyTorch), explainable AI (SHAP), and production data product deployment.",
    "version": "v2.0",
    "has_market_data": False,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Scientific Programming & Exploratory Analytics",
            "description": "Data wrangling, hypothesis testing, exploratory visualization, and complex relational analysis.",
            "skills": [
                make_skill(
                    slug="python-ds",
                    name="Python for Data Science",
                    canonical_slug="python",
                    difficulty="BEGINNER",
                    description="Core scientific Python stack: NumPy vectorization, Pandas DataFrame manipulation, missing data imputation, and efficient memory types.",
                    key_topics=["NumPy N-Dimensional Arrays & Broadcasting", "Pandas DataFrames, Series & Indexing", "Handling Missing Data (NaN, Imputation)", "Categorical & Datetime Types", "Vectorized Apply vs Iterative Processing"],
                    role_relevance="The foundational programming ecosystem for data cleaning, statistical modeling, and experimental prototyping.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Pandas Official Documentation", "url": "https://pandas.pydata.org/docs/", "description": "Complete reference manual for Pandas DataFrame operations, grouping, and indexing."},
                        {"type": "YOUTUBE", "title": "Data Analysis with Python — freeCodeCamp", "url": "https://www.youtube.com/watch?v=r-uOLxNrNk8", "description": "In-depth course on NumPy arrays, Pandas DataFrames, and exploratory data manipulation."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="py-ds-prob-1",
                            title="Vectorized Financial Return Calculator",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Compute daily log returns and rolling volatility on time-series prices using pure NumPy and Pandas.",
                            problem_statement="Given a DataFrame of historical daily closing stock prices, compute percentage daily returns, logarithmic returns, and 30-day rolling annualized volatility using vectorized methods without iterative loops.",
                            requirements=[
                                "Compute pct_change() and np.log(price / price.shift(1)).",
                                "Compute rolling 30-day standard deviation multiplied by np.sqrt(252) for annualized volatility.",
                                "Drop initial NaN warmup periods cleanly without forward filling stale values."
                            ],
                            concepts_tested=["Vectorized Operations", "Time Series Shifting", "Rolling Window Aggregation", "NumPy Math Functions"],
                            expected_outcome="A clean DataFrame with accurate daily returns and rolling annualized volatility indicators.",
                            optional_hints=["Avoid row-by-row iteration (for loops / apply); use built-in vectorized Series operations."]
                        ),
                        make_problem(
                            problem_id="py-ds-prob-2",
                            title="Multi-File Sensor Telemetry Normalizer",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Merge, clean, and downsample heterogeneous sensor readings from multiple nested JSON files.",
                            problem_statement="Ingest 50 IoT device log files with varying timestamps and nested metadata, normalize JSON payloads into a unified DataFrame, resample high-frequency readings to 1-minute averages, and impute missing intervals using linear interpolation.",
                            requirements=[
                                "Use pd.json_normalize to flatten nested sensor attributes.",
                                "Parse ISO-8601 timestamps and set as DatetimeIndex.",
                                "Resample to 1-minute intervals (.resample('1T').mean()) and interpolate missing gaps under 5 minutes.",
                                "Convert object columns to categorical dtype to reduce memory consumption by >50%."
                            ],
                            concepts_tested=["JSON Normalization", "DatetimeIndex Resampling", "Time-Series Interpolation", "Memory Optimization with Categoricals"],
                            expected_outcome="A compacted, clean 1-minute resampled telemetry dataset ready for predictive modeling.",
                            optional_hints=["Use df.memory_usage(deep=True) to quantify memory reductions after categorical conversion."]
                        ),
                        make_problem(
                            problem_id="py-ds-prob-3",
                            title="Memory-Efficient Chunker for Big Datasets",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Process a 10GB CSV file in a memory-constrained 2GB RAM environment using chunked iteration and running aggregations.",
                            problem_statement="Write a data processing pipeline that reads a massive transactional CSV in 50,000-row chunks via pd.read_csv(chunksize=...), maintains running statistics (mean, standard deviation, min, max, category counts), and outputs summary metrics without exceeding 500MB peak RAM.",
                            requirements=[
                                "Use Welford's algorithm or running sum/sum of squares to calculate running variance accurately.",
                                "Profile peak RAM usage using memory_profiler or tracemalloc to prove <500MB ceiling.",
                                "Save the final consolidated summary table to Parquet."
                            ],
                            concepts_tested=["Chunked Ingestion", "Running Statistical Aggregation (Welford's Algorithm)", "Memory Profiling", "Bounded RAM Execution"],
                            expected_outcome="Accurate global descriptive statistics computed over multi-gigabyte data within tight memory limits.",
                            optional_hints=["Welford's algorithm avoids catastrophic cancellation when updating variance across chunks."]
                        ),
                    ],
                ),
                make_skill(
                    slug="eda-statistics",
                    name="Exploratory Data Analysis & Statistical Inference",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Exploratory visualization and hypothesis testing: distribution analysis, correlation vs causation, t-tests, ANOVA, Chi-square tests, p-values, and statistical power.",
                    key_topics=["Distribution Analysis (Normal, Skewed, Kurtosis)", "Hypothesis Testing (t-test, Mann-Whitney U, ANOVA)", "Chi-Square Test of Independence", "Statistical Significance (p-values, Type I/II Errors)", "Visual Exploration (Seaborn, Matplotlib, Boxplots, Pairplots)"],
                    role_relevance="Enables data scientists to validate business hypotheses with mathematical rigor before training predictive models.",
                    prerequisites=["python-ds"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "SciPy Statistical Functions (scipy.stats)", "url": "https://docs.scipy.org/doc/scipy/reference/stats.html", "description": "Official reference for distributions, hypothesis tests, and statistical formulas."},
                        {"type": "YOUTUBE", "title": "Statistics for Data Science — freeCodeCamp", "url": "https://www.youtube.com/watch?v=xxpc-HPKN28", "description": "Comprehensive course on probability distributions, hypothesis testing, and statistical significance."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="eda-prob-1",
                            title="A/B Test Significance Analysis",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Determine if a website conversion rate improvement is statistically significant using a two-proportion z-test.",
                            problem_statement="Given user engagement data from Control (10,000 visitors, 450 conversions) and Variant (10,200 visitors, 530 conversions), conduct hypothesis testing, compute the z-score, p-value, and 95% confidence interval, and provide an actionable business conclusion.",
                            requirements=[
                                "Formulate null hypothesis (H0) and alternative hypothesis (H1).",
                                "Compute pooled conversion probability and standard error.",
                                "Calculate two-tailed p-value; reject H0 if p < 0.05.",
                                "Compute 95% confidence interval for the conversion lift."
                            ],
                            concepts_tested=["Two-Proportion Z-Test", "Hypothesis Formulation", "P-Value Interpretation", "Confidence Intervals"],
                            expected_outcome="A rigorous statistical decision confirming whether the variant creates a genuine conversion lift.",
                            optional_hints=["Use statsmodels.stats.proportion.proportions_ztest to verify manual calculations."]
                        ),
                        make_problem(
                            problem_id="eda-prob-2",
                            title="Non-Parametric Multi-Group Comparison",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Analyze customer lifetime value across 4 acquisition channels using Kruskal-Wallis and Dunn post-hoc tests.",
                            problem_statement="Customer spending data is heavily right-skewed and violates normal distribution assumptions. Conduct Shapiro-Wilk normality tests, apply the Kruskal-Wallis H-test across the 4 acquisition cohorts, and run Dunn post-hoc pairwise comparisons with Bonferroni correction to isolate which channels differ significantly.",
                            requirements=[
                                "Test normality using scipy.stats.shapiro and visualize Q-Q plots.",
                                "Execute Kruskal-Wallis H-test on non-normal distributions.",
                                "Execute post-hoc pairwise testing with Dunn's test and Bonferroni p-value adjustment.",
                                "Create clear Seaborn boxplots with overlaid significance asterisks."
                            ],
                            concepts_tested=["Non-Parametric Testing", "Normality Assessment", "Kruskal-Wallis H-Test", "Multiple Testing Correction (Bonferroni)"],
                            expected_outcome="Statistically sound channel comparison unaffected by skewed outliers.",
                            optional_hints=["Use scikit-posthocs or pingouin library for Dunn's test with Bonferroni correction."]
                        ),
                        make_problem(
                            problem_id="eda-prob-3",
                            title="Automated Data Quality & Outlier Detection Diagnostic",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build an automated EDA diagnostic suite detecting multivariate outliers, multicollinearity, and covariate shift.",
                            problem_statement="Develop a Python EDA diagnostic class that takes an arbitrary tabular dataset and generates an executive report flagging: multicollinear features (VIF > 5), multivariate anomalies via Isolation Forest and Mahalanobis distance, and feature skewness requiring Box-Cox or Yeo-Johnson power transformation.",
                            requirements=[
                                "Calculate Variance Inflation Factor (VIF) for all continuous numeric predictors.",
                                "Detect multivariate anomalies comparing Mahalanobis distance with Chi-square critical values.",
                                "Automate power transform suggestions for features with skewness > 1.0.",
                                "Output an executive diagnostic report with automated recommendations."
                            ],
                            concepts_tested=["Multicollinearity (VIF)", "Multivariate Outlier Detection", "Mahalanobis Distance", "Power Transformations"],
                            expected_outcome="A production-ready exploratory diagnostic toolkit usable across any tabular analytics project.",
                            optional_hints=["statsmodels.stats.outliers_influence.variance_inflation_factor computes VIF for a design matrix."]
                        ),
                    ],
                ),
                make_skill(
                    slug="sql-ds",
                    name="Applied SQL & Relational Analytics",
                    canonical_slug="postgresql",
                    difficulty="INTERMEDIATE",
                    description="SQL for data science: aggregations, analytical joins, cohort extraction, rolling user activity metrics, and direct database extraction into Pandas DataFrames.",
                    key_topics=["Aggregations & Filter Clauses (FILTER, HAVING)", "Window Functions (NTILE, PERCENT_RANK)", "Cohort Feature Extraction Queries", "SQL to Pandas / SQLAlchemy Engine Integration", "Query Optimization for Large Datasets"],
                    role_relevance="Extracts clean, pre-aggregated feature sets directly from production databases without overloading local memory.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PostgreSQL Documentation — Aggregate Functions", "url": "https://www.postgresql.org/docs/current/functions-aggregate.html", "description": "Official PostgreSQL documentation for standard and statistical aggregations."},
                        {"type": "YOUTUBE", "title": "SQL for Data Science — freeCodeCamp", "url": "https://www.youtube.com/watch?v=HXV3zeRR3nw", "description": "Comprehensive tutorial covering analytical SQL, subqueries, and statistical aggregations."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sql-ds-prob-1",
                            title="Feature Extraction Query for Customer Churn",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write an analytical SQL query extracting tabular features for downstream churn machine learning.",
                            problem_statement="Given tables for users, orders, and support_tickets, write a query that generates one feature row per user containing: total lifetime spend, orders count, days since last order, average order value, and count of support tickets in the last 30 days.",
                            requirements=[
                                "Join users with orders and tickets using LEFT JOIN.",
                                "Aggregate metrics per user_id using COALESCE to handle zero orders/tickets.",
                                "Calculate recency: EXTRACT(day FROM CURRENT_TIMESTAMP - MAX(order_date)).",
                                "Export query output directly into a Pandas DataFrame using pd.read_sql()."
                            ],
                            concepts_tested=["Feature Engineering SQL", "LEFT JOIN Aggregation", "Recency Calculation", "Pandas SQL Extraction"],
                            expected_outcome="A machine-learning-ready feature matrix extracted directly from relational tables.",
                            optional_hints=["Use COALESCE(COUNT(orders.id), 0) to ensure non-buyers have 0 rather than NULL."]
                        ),
                        make_problem(
                            problem_id="sql-ds-prob-2",
                            title="RFM (Recency, Frequency, Monetary) Segmentation",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement customer RFM segmentation using NTILE(5) window functions in SQL.",
                            problem_statement="Calculate Recency, Frequency, and Monetary scores for all customers over the past 12 months, divide customers into quintiles (1-5) using NTILE, concatenate scores into an RFM segment (e.g. '555' for champions), and assign marketing personas.",
                            requirements=[
                                "Compute R, F, and M raw values per customer.",
                                "Apply NTILE(5) OVER (ORDER BY ...) to rank R (reversed), F, and M.",
                                "Map RFM composite scores to persona labels (Champions, Loyalists, At Risk, Lost) using CASE WHEN.",
                                "Aggregate customer count and total revenue generated per persona."
                            ],
                            concepts_tested=["NTILE Window Function", "RFM Segmentation", "Composite Scoring", "Customer Persona Mapping"],
                            expected_outcome="A complete RFM customer segmentation dataset powering personalized marketing actions.",
                            optional_hints=["For Recency, lower days elapsed should map to a higher quintile score (5)."]
                        ),
                        make_problem(
                            problem_id="sql-ds-prob-3",
                            title="Rolling Feature Window Query for Fraud Detection",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Construct point-in-time features with rolling time-based window frames to prevent temporal data leakage.",
                            problem_statement="For a credit card fraud detection model, compute features for each transaction at timestamp T: count of transactions and sum of amounts by the same card in the preceding 1 hour, 24 hours, and 7 days. Ensure the window strictly excludes future transactions to prevent leakage.",
                            requirements=[
                                "Use window frames with RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND '1 second' PRECEDING.",
                                "Compute multiple rolling windows (1h, 24h, 7d) in a single optimized SQL query.",
                                "Verify zero target leakage: the current transaction's own amount must not be included in preceding aggregates.",
                                "Test query plan execution on a 10M-row table to ensure index utilization on (card_id, transaction_time)."
                            ],
                            concepts_tested=["Time-Based Window Frames (RANGE)", "Point-in-Time Feature Consistency", "Leakage Prevention", "Temporal Index Tuning"],
                            expected_outcome="Point-in-time correct fraud features with strictly zero future-information leakage.",
                            optional_hints=["RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND '1 millisecond' PRECEDING strictly excludes the current row."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Classical Machine Learning & Feature Engineering",
            "description": "Supervised modeling, unsupervised clustering, and advanced feature transformation pipelines.",
            "skills": [
                make_skill(
                    slug="supervised-ml-ds",
                    name="Supervised Machine Learning with Scikit-Learn",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Supervised learning algorithms and validation: Linear/Logistic Regression, Random Forests, Gradient Boosted Trees (XGBoost, LightGBM), cross-validation, and hyperparameter optimization.",
                    key_topics=["Regression & Classification Algorithms", "Ensemble Methods (Random Forest, XGBoost, LightGBM)", "Stratified K-Fold Cross-Validation", "Hyperparameter Tuning (Optuna, GridSearchCV)", "Scikit-Learn Pipeline & ColumnTransformer"],
                    role_relevance="The workhorse tool for enterprise predictive modeling, churn prediction, credit scoring, and demand forecasting.",
                    prerequisites=["python-ds", "eda-statistics"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Scikit-Learn Official User Guide", "url": "https://scikit-learn.org/stable/user_guide.html", "description": "Official guides to algorithms, pipelines, cross-validation, and metrics."},
                        {"type": "YOUTUBE", "title": "Machine Learning with Python & Scikit-Learn — freeCodeCamp", "url": "https://www.youtube.com/watch?v=i_LwzRVP7bg", "description": "Full course covering classification, regression, tree ensembles, and model evaluation."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sml-prob-1",
                            title="End-to-End Scikit-Learn Pipeline for Housing Prices",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build a leak-free Scikit-Learn Pipeline with ColumnTransformer for regression prediction.",
                            problem_statement="Construct an end-to-end regression pipeline that imputes missing numerical values using Median, scales features with StandardScaler, encodes categorical features with OneHotEncoder(handle_unknown='ignore'), and fits a Ridge regression model.",
                            requirements=[
                                "Separate numeric and categorical features cleanly using ColumnTransformer.",
                                "Encapsulate preprocessing and estimator in a single Pipeline object.",
                                "Evaluate on held-out test data reporting RMSE and R-squared metrics.",
                                "Confirm preprocessing transformers fit strictly on training data to prevent data leakage."
                            ],
                            concepts_tested=["Scikit-Learn Pipeline", "ColumnTransformer", "Data Leakage Prevention", "Regression Evaluation Metrics"],
                            expected_outcome="A robust, modular pipeline object capable of taking raw uncleaned DataFrames and returning predictions.",
                            optional_hints=["Never call fit_transform on test data; only call pipeline.predict(X_test)."]
                        ),
                        make_problem(
                            problem_id="sml-prob-2",
                            title="Imbalanced Churn Classifier with XGBoost & Optuna",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Train an XGBoost classifier on an imbalanced dataset (95:5) tuned via Bayesian optimization with Optuna.",
                            problem_statement="Develop a customer churn prediction model on a highly imbalanced dataset. Use StratifiedKFold cross-validation optimizing PR-AUC (Average Precision), configure scale_pos_weight, and tune hyperparameters (max_depth, learning_rate, colsample_bytree, subsample) using Optuna.",
                            requirements=[
                                "Use StratifiedKFold(n_splits=5, shuffle=True) to preserve class balance across folds.",
                                "Define an Optuna study minimizing negative Average Precision score.",
                                "Set scale_pos_weight dynamically based on class frequency ratio.",
                                "Plot precision-recall curves and select an optimal classification threshold for business ROI."
                            ],
                            concepts_tested=["Imbalanced Classification", "XGBoost scale_pos_weight", "Bayesian Optimization with Optuna", "Precision-Recall Optimization"],
                            expected_outcome="A high-performing churn classifier optimized for minority-class detection with minimal false alarms.",
                            optional_hints=["In imbalanced problems, ROC-AUC can be deceptively optimistic; optimize Average Precision (PR-AUC) instead."]
                        ),
                        make_problem(
                            problem_id="sml-prob-3",
                            title="Cost-Sensitive Model Tuning & Profit Curve Calibration",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Calibrate model prediction probabilities and determine decision thresholds based on asymmetrical business cost matrices.",
                            problem_statement="In credit default prediction, a False Negative costs $10,000 in loan default, while a False Positive costs $200 in lost customer interest. Calibrate predicted probabilities using CalibratedClassifierCV (isotonic regression) and determine the decision threshold that maximizes expected financial profit.",
                            requirements=[
                                "Calibrate probabilities using CalibratedClassifierCV(method='isotonic').",
                                "Verify calibration improvement using Brier score and reliability diagrams.",
                                "Construct a custom business cost utility function evaluating profit across thresholds (0.01 to 0.99).",
                                "Identify the exact optimal threshold maximizing net dollar profit."
                            ],
                            concepts_tested=["Probability Calibration", "Isotonic Regression", "Cost-Sensitive Learning", "Profit Curve Optimization", "Reliability Diagrams"],
                            expected_outcome="A calibrated decision engine delivering maximum monetary value under asymmetric cost constraints.",
                            optional_hints=["Use sklearn.calibration.calibration_curve to plot predicted vs observed frequencies."]
                        ),
                    ],
                ),
                make_skill(
                    slug="unsupervised-ds",
                    name="Unsupervised Learning & Dimensionality Reduction",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Clustering and dimensionality reduction: K-Means, DBSCAN, Hierarchical clustering, PCA, t-SNE, UMAP, and silhouette validation.",
                    key_topics=["K-Means Clustering & Elbow / Silhouette Analysis", "Density-Based Clustering (DBSCAN)", "Principal Component Analysis (PCA)", "Non-Linear Dimensionality Reduction (t-SNE, UMAP)", "Hierarchical Clustering & Dendrograms"],
                    role_relevance="Discovers latent patterns, segments customers, detects anomalies, and visualizes high-dimensional feature spaces.",
                    prerequisites=["supervised-ml-ds"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Scikit-Learn Clustering Documentation", "url": "https://scikit-learn.org/stable/modules/clustering.html", "description": "Official guide to clustering algorithms, parameter choices, and evaluation metrics."},
                        {"type": "YOUTUBE", "title": "StatQuest: PCA Main Ideas — Josh Starmer", "url": "https://www.youtube.com/watch?v=FgakZw6K1QQ", "description": "Intuitive, visual explanation of eigenvectors, eigenvalues, and variance decomposition in PCA."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="unsup-prob-1",
                            title="Customer Behavioral Clustering & Silhouette Validation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Segment customer purchase behaviors using K-Means and determine optimal cluster count via silhouette analysis.",
                            problem_statement="Given customer transaction features (spend, visit frequency, discount usage, basket size), standardize features, run K-Means across k=2..10, compute silhouette scores, and identify the optimal cluster count.",
                            requirements=[
                                "Standardize features using StandardScaler.",
                                "Plot the inertia Elbow curve and average Silhouette Score across k=2..10.",
                                "Fit K-Means with optimal k and extract cluster centroid profiles.",
                                "Assign descriptive business labels to each cluster based on centroid attribute values."
                            ],
                            concepts_tested=["K-Means Algorithm", "Elbow Method", "Silhouette Score", "Feature Standardization", "Centroid Interpretation"],
                            expected_outcome="A validated customer segmentation model with clear behavioral cluster personas.",
                            optional_hints=["StandardScaler is mandatory for distance-based clustering algorithms like K-Means."]
                        ),
                        make_problem(
                            problem_id="unsup-prob-2",
                            title="PCA Dimensionality Reduction & Variance Scree Plot",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Reduce a 100-variable genomic or sensor dataset to essential components retaining 90% cumulative explained variance.",
                            problem_statement="Perform Principal Component Analysis on high-dimensional data, generate a Scree plot of explained variance ratios, determine the minimum components required to retain 90% variance, and interpret principal component loadings.",
                            requirements=[
                                "Fit PCA(n_components=None) and compute cumulative explained variance.",
                                "Identify the elbow cutoff and minimum components for 90% variance threshold.",
                                "Visualize principal component loadings heatmap to identify which original features drive PC1 and PC2.",
                                "Project data into 2D PC space and color by target labels to check class separability."
                            ],
                            concepts_tested=["Principal Component Analysis", "Cumulative Explained Variance", "Scree Plot", "Component Loadings Interpretation"],
                            expected_outcome="A dramatically compressed feature representation preserving core information without collinear noise.",
                            optional_hints=["pca.explained_variance_ratio_.cumsum() gives cumulative variance at each component count."]
                        ),
                        make_problem(
                            problem_id="unsup-prob-3",
                            title="DBSCAN Density Anomaly Detection & UMAP Projection",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Detect non-linear spatial fraud clusters and isolated anomalies using DBSCAN combined with UMAP visualization.",
                            problem_statement="Given a complex dataset with arbitrary geometric cluster shapes and ambient noise, apply DBSCAN to identify arbitrary cluster boundaries and isolate noise points (outliers with label -1). Visualize clusters and anomalies in 2D using UMAP.",
                            requirements=[
                                "Use k-distance graph to determine optimal eps neighborhood radius.",
                                "Execute DBSCAN(eps=..., min_samples=...) identifying clusters and noise points (-1).",
                                "Project high-dimensional space into 2D using umap-learn and plot DBSCAN labels.",
                                "Evaluate anomaly characteristics: inspect why noise points were rejected from dense clusters."
                            ],
                            concepts_tested=["DBSCAN Density Clustering", "Eps Parameter Tuning (K-Distance Graph)", "Noise / Outlier Identification", "UMAP Non-Linear Projection"],
                            expected_outcome="Accurate anomaly isolation on complex non-spherical data distributions.",
                            optional_hints=["Sort distances of k-nearest neighbors and find the 'knee' point to set eps."]
                        ),
                    ],
                ),
                make_skill(
                    slug="feature-eng-ds",
                    name="Feature Engineering & Selection Techniques",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Transforming raw signals into high-impact model inputs: target encoding, polynomial features, interaction terms, cyclical encoding, feature selection (SHAP, Mutual Info, LASSO), and feature stores.",
                    key_topics=["Target Encoding & Out-of-Fold Regularization", "Cyclical Date/Time Transformations (sin/cos)", "Interaction Features & Polynomial Expansions", "Feature Selection (Mutual Information, LASSO, Permutation Importance)", "Preventing Target Leakage in Transformations"],
                    role_relevance="The single highest-leverage skill determining the real-world accuracy and predictive power of machine learning models.",
                    prerequisites=["supervised-ml-ds"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Category Encoders Documentation", "url": "https://contrib.scikit-learn.org/category_encoders/", "description": "Official guides to TargetEncoder, CatBoostEncoder, and Weight of Evidence encodings."},
                        {"type": "YOUTUBE", "title": "Feature Engineering for Machine Learning — Krish Naik", "url": "https://www.youtube.com/watch?v=6WDFfaYtN6D", "description": "Hands-on tutorials on handling high-cardinality categoricals, scaling, and feature selection."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="fe-prob-1",
                            title="Cyclical Temporal Encodings & Interaction Terms",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Encode cyclical time features (hour of day, day of week) using trigonometric sine and cosine functions.",
                            problem_statement="Transform a datetime column into continuous cyclical features so hour 23 and hour 0 are mathematically adjacent. In addition, engineer interaction terms between temperature and humidity to compute heat index features.",
                            requirements=[
                                "Compute sin_hour = np.sin(2 * np.pi * hour / 24) and cos_hour = np.cos(2 * np.pi * hour / 24).",
                                "Verify Euclidean distance between 23:00 and 00:00 matches distance between 12:00 and 13:00.",
                                "Create non-linear interaction terms multiplying continuous environmental features.",
                                "Verify feature correlations with the target variable increase."
                            ],
                            concepts_tested=["Cyclical Trigonometric Encoding", "Temporal Continuity", "Feature Interaction Terms", "Non-Linear Transformations"],
                            expected_outcome="Feature set preserving continuous cyclical patterns without artificial boundary discontinuities.",
                            optional_hints=["Trigonometric transformation maps cyclical features onto a 2D circle with period T."]
                        ),
                        make_problem(
                            problem_id="fe-prob-2",
                            title="Out-of-Fold Target Encoding for High-Cardinality Categoricals",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Encode high-cardinality categorical variables (ZIP code, product SKU) using out-of-fold target encoding without leakage.",
                            problem_statement="Implement an out-of-fold target encoder for a categorical feature with 5,000 distinct levels. Compute target averages within K-fold partitions with smoothing priors, preventing direct label memorization and target leakage.",
                            requirements=[
                                "Use KFold cross-validation splits to compute out-of-fold target means for the training set.",
                                "Apply m-estimate smoothing: smoothed_stat = (count * mean + m * global_mean) / (count + m).",
                                "Encode test set using global target averages calculated strictly from training data.",
                                "Demonstrate zero target leakage and improved model validation score."
                            ],
                            concepts_tested=["Target Encoding", "Out-of-Fold Computation", "M-Estimate Smoothing", "High-Cardinality Categoricals"],
                            expected_outcome="A high-cardinality encoding yielding dense predictive numerical features without overfitting.",
                            optional_hints=["Smoothing with m-estimates pulls categories with very low sample counts toward the global prior."]
                        ),
                        make_problem(
                            problem_id="fe-prob-3",
                            title="Automated Feature Selection via Boruta & Permutation Importance",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Prune hundreds of redundant features down to confirmed predictive predictors using Boruta shadow feature testing.",
                            problem_statement="Given a dataset with 300 engineered features (many noisy or collinear), implement the Boruta feature selection algorithm: generate randomized shadow features, fit a Random Forest, compare feature importance against the maximum shadow feature importance, and iteratively filter confirmed predictive features.",
                            requirements=[
                                "Create shadow features by shuffling each original feature column randomly.",
                                "Train Random Forest and compute Gini / Permutation importances.",
                                "Perform statistical binomial tests: confirm features with importance significantly higher than shadow features.",
                                "Eliminate confirmed uninformative features and demonstrate improved out-of-sample test accuracy."
                            ],
                            concepts_tested=["Boruta Algorithm", "Shadow Feature Generation", "Permutation Feature Importance", "Statistical Feature Selection"],
                            expected_outcome="A trimmed feature set that eliminates noise, speeds up training, and prevents overfitting.",
                            optional_hints=["Use boruta_py library or implement custom shadow feature permutation loops."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Specialized Analytics & Deep Learning",
            "description": "Temporal modeling, forecasting, and deep neural architectures for tabular, text, and sequence data.",
            "skills": [
                make_skill(
                    slug="time-series-ds",
                    name="Time Series Analysis & Forecasting",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Forecasting and temporal dynamics: stationarity, autocorrelation (ACF/PACF), ARIMA/SARIMAX, Facebook Prophet, backtesting with expanding windows, and temporal cross-validation.",
                    key_topics=["Stationarity & Augmented Dickey-Fuller Test", "ACF & PACF Diagnostics", "ARIMA, SARIMA & Exogenous Variables (SARIMAX)", "Additive Models (Facebook Prophet)", "Rolling Expanding-Window TimeSeriesSplit"],
                    role_relevance="Essential for supply chain forecasting, financial projections, retail inventory planning, and demand capacity.",
                    prerequisites=["supervised-ml-ds", "eda-statistics"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Statsmodels Time Series Analysis (tsa)", "url": "https://www.statsmodels.org/stable/tsa.html", "description": "Official documentation for ARIMA, SARIMAX, and decomposition models."},
                        {"type": "YOUTUBE", "title": "Time Series Forecasting with Python — Rob Mulla", "url": "https://www.youtube.com/watch?v=vV12dGe_Fho", "description": "Comprehensive tutorial on building time series forecasting models with Pandas, Prophet, and XGBoost."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="ts-prob-1",
                            title="Stationarity Testing & SARIMA Electricity Forecasting",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Test time series stationarity, identify seasonal orders from ACF/PACF, and fit a SARIMA model.",
                            problem_statement="Analyze hourly electricity consumption data. Perform an Augmented Dickey-Fuller test, apply seasonal differencing to achieve stationarity, inspect ACF and PACF plots to identify p, d, q and P, D, Q orders, and fit a SARIMAX model.",
                            requirements=[
                                "Run statsmodels.tsa.stattools.adfuller and verify p-value < 0.05.",
                                "Plot seasonal decomposition (Trend, Seasonality, Residual).",
                                "Fit SARIMAX(order=(p,d,q), seasonal_order=(P,D,Q,24)).",
                                "Generate 48-hour out-of-sample forecasts with 95% confidence intervals."
                            ],
                            concepts_tested=["Augmented Dickey-Fuller Test", "Seasonal Differencing", "ACF / PACF Interpretation", "SARIMAX Model Fitting"],
                            expected_outcome="Accurate 48-hour energy load forecasts with quantified confidence bands.",
                            optional_hints=["A sharp cutoff in PACF suggests an AR signature, while cutoff in ACF suggests an MA signature."]
                        ),
                        make_problem(
                            problem_id="ts-prob-2",
                            title="Prophet Multi-Seasonality Model with Holiday Effects",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Forecast retail revenue using Facebook Prophet with multiple seasonalities and custom promotional holidays.",
                            problem_statement="Develop a 90-day daily revenue forecast for a retail chain. Model daily, weekly, and yearly seasonalities, add promotional discount events as custom holidays, and tune changepoint_prior_scale to avoid overfitting trend shifts.",
                            requirements=[
                                "Format data into 'ds' and 'y' Prophet columns.",
                                "Add custom holiday DataFrame for promotional flash-sale dates.",
                                "Tune changepoint_prior_scale across a parameter grid evaluating cross-validated MAPE.",
                                "Decompose and visualize forecast trend, weekly, and yearly seasonal components."
                            ],
                            concepts_tested=["Prophet Additive Modeling", "Custom Holiday Effects", "Changepoint Tuning", "Component Decomposition"],
                            expected_outcome="A robust business forecast accounting for both annual seasonality and sudden promotional spikes.",
                            optional_hints=["Use prophet.diagnostics.cross_validation and performance_metrics for rolling evaluation."]
                        ),
                        make_problem(
                            problem_id="ts-prob-3",
                            title="Lagged Machine Learning Forecasting with Temporal Cross-Validation",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Frame multi-step demand forecasting as a supervised tabular regression problem with lag features and TimeSeriesSplit.",
                            problem_statement="Convert a time series into a supervised machine learning dataset using 7-day, 14-day, and 28-day lags and rolling statistics. Train a LightGBM regressor using expanding-window TimeSeriesSplit to forecast demand 7 days ahead without lookahead bias.",
                            requirements=[
                                "Generate lagged target features (t-1, t-7, t-14) and rolling means (7d, 28d).",
                                "Implement TimeSeriesSplit(n_splits=5) with expanding training windows.",
                                "Implement recursive or direct multi-step forecasting for a 7-day horizon.",
                                "Benchmark LightGBM against a naive persistence baseline (MAE improvement > 25%)."
                            ],
                            concepts_tested=["Lag Feature Engineering", "TimeSeriesSplit (Expanding Window)", "Lookahead Bias Prevention", "Multi-Step Forecasting"],
                            expected_outcome="A high-performance machine learning forecaster outperforming classical univariate time series models.",
                            optional_hints=["Never use standard train_test_split or KFold on time series; always respect temporal ordering."]
                        ),
                    ],
                ),
                make_skill(
                    slug="deep-learning-ds",
                    name="Deep Learning with PyTorch",
                    canonical_slug="pytorch",
                    difficulty="ADVANCED",
                    description="Neural networks for tabular, text, and sequential data: PyTorch tensors, autograd, nn.Module, Dataset/DataLoader, loss functions, optimizers, and transfer learning.",
                    key_topics=["Tensors, Autograd & Computational Graphs", "Custom nn.Module & Layer Architectures", "Dataset & DataLoader Batching", "Loss Functions & Adam/AdamW Optimizers", "Embeddings for High-Cardinality Tabular Data"],
                    role_relevance="Enables solving complex non-linear problems, unstructured text classification, embeddings, and deep tabular representations.",
                    prerequisites=["supervised-ml-ds"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PyTorch Official Documentation & Tutorials", "url": "https://pytorch.org/docs/stable/index.html", "description": "Official PyTorch guides, autograd mechanics, and neural network modules."},
                        {"type": "YOUTUBE", "title": "PyTorch for Deep Learning Bootcamp — Daniel Bourke", "url": "https://www.youtube.com/watch?v=V_xro1bcAuA", "description": "Hands-on PyTorch course covering tensors, workflow fundamentals, classification, and neural architectures."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="dl-ds-prob-1",
                            title="PyTorch Multi-Layer Perceptron from Scratch",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement, train, and evaluate a multi-layer perceptron using PyTorch nn.Module and DataLoader.",
                            problem_statement="Build a neural network classifier for credit risk. Create a custom Dataset class, batch samples with DataLoader, define an nn.Module with Linear, BatchNorm, Dropout, and ReLU activations, and implement the complete training loop.",
                            requirements=[
                                "Subclass torch.utils.data.Dataset with __len__ and __getitem__ methods.",
                                "Construct model with Linear -> BatchNorm1d -> ReLU -> Dropout layers.",
                                "Write training and validation loops with optimizer.zero_grad(), loss.backward(), and optimizer.step().",
                                "Track epoch loss and early stopping when validation loss plateaus."
                            ],
                            concepts_tested=["PyTorch Dataset & DataLoader", "nn.Module Architecture", "Autograd Training Loop", "Early Stopping Mechanics"],
                            expected_outcome="A functional PyTorch training pipeline with early stopping and validation tracking.",
                            optional_hints=["Remember to call model.train() before training and model.eval() with torch.no_grad() during evaluation."]
                        ),
                        make_problem(
                            problem_id="dl-ds-prob-2",
                            title="Entity Embeddings for Categorical Tabular Data",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Train neural entity embeddings for high-cardinality categories and extract learned latent vectors.",
                            problem_statement="Implement an embedding neural network for tabular data containing categorical variables (e.g. store ID, department). Map each categorical level to a dense continuous vector via nn.Embedding, concatenate with numeric features, and train to predict store sales.",
                            requirements=[
                                "Calculate embedding dimension rule-of-thumb: min(50, (num_classes + 1) // 2).",
                                "Define nn.Module combining multiple nn.Embedding layers with numerical dense layers.",
                                "Extract trained embedding weight matrices and visualize store similarities in 2D using PCA/t-SNE."
                            ],
                            concepts_tested=["Entity Embeddings (nn.Embedding)", "Deep Tabular Architectures", "Latent Vector Extraction", "High-Cardinality Representation"],
                            expected_outcome="Dense learned embedding vectors capturing rich semantic relationships between categorical entities.",
                            optional_hints=["Entity embeddings pioneered by Guo & Berkhahn dramatically boost tabular neural network performance."]
                        ),
                        make_problem(
                            problem_id="dl-ds-prob-3",
                            title="Customer Support Intent Classifier with Fine-Tuned Transformer",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Fine-tune a pretrained Hugging Face transformer model for multi-class customer support text classification.",
                            problem_statement="Fine-tune a DistilBERT model on customer support chat tickets to classify issue intents (Billing, Technical, Account, Refund). Tokenize text using AutoTokenizer, configure Trainer with PyTorch backend, compute multi-class F1 scores, and export optimized weights.",
                            requirements=[
                                "Tokenize text with dynamic padding and truncation using Hugging Face AutoTokenizer.",
                                "Configure AutoModelForSequenceClassification with num_labels=4.",
                                "Train using TrainingArguments with fp16 mixed precision and warmup steps.",
                                "Evaluate on held-out test set reporting per-class precision, recall, and macro F1."
                            ],
                            concepts_tested=["Transformer Fine-Tuning", "Hugging Face Ecosystem", "Tokenization & Padding", "Mixed Precision Training (fp16)"],
                            expected_outcome="A production-ready NLP text classifier achieving >90% intent classification accuracy.",
                            optional_hints=["DistilBERT provides 97% of BERT's performance with 40% fewer parameters and 60% faster inference."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Interpretability, Evaluation & Deployment",
            "description": "Model explainability with SHAP, business calibration, and interactive dashboard deployment.",
            "skills": [
                make_skill(
                    slug="model-interp-ds",
                    name="Model Evaluation, Interpretability & SHAP",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Explainable AI (XAI) and governance: SHAP (Shapley Additive exPlanations), TreeExplainer, feature attributions, partial dependence plots, fairness metrics, and model bias auditing.",
                    key_topics=["Shapley Values & Game-Theoretic Foundations", "TreeExplainer & KernelExplainer", "Global Explanations (Summary & Dependence Plots)", "Local Explanations (Force & Waterfall Plots)", "Fairness Metrics (Disparate Impact, Demographic Parity)"],
                    role_relevance="Critical for regulatory compliance (GDPR, Fair Lending), executive stakeholder buy-in, and debugging model predictions.",
                    prerequisites=["supervised-ml-ds"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "SHAP (SHapley Additive exPlanations) Documentation", "url": "https://shap.readthedocs.io/en/latest/", "description": "Official documentation for TreeExplainer, Waterfall plots, and force plots."},
                        {"type": "YOUTUBE", "title": "SHAP Values Explained — StatQuest", "url": "https://www.youtube.com/watch?v=VB9QevNZU3Y", "description": "Clear conceptual breakdown of Shapley values, local feature attributions, and global summary plots."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="shap-prob-1",
                            title="Global Feature Importance & Dependence with SHAP",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Compute and interpret global SHAP summary and feature dependence plots for an XGBoost model.",
                            problem_statement="Fit an XGBoost classifier on a loan approval dataset. Compute SHAP values using shap.TreeExplainer, generate a global summary beeswarm plot, and analyze dependence plots to uncover non-linear interactions.",
                            requirements=[
                                "Initialize shap.TreeExplainer on the trained XGBoost model.",
                                "Generate shap.summary_plot (beeswarm) showing directionality and magnitude of feature impacts.",
                                "Generate shap.dependence_plot for credit score showing interaction with income.",
                                "Write an executive summary explaining the top 3 drivers of model predictions."
                            ],
                            concepts_tested=["SHAP TreeExplainer", "Beeswarm Summary Plot", "SHAP Dependence Plots", "Directional Feature Attribution"],
                            expected_outcome="A visual explanation of global model behavior ready for non-technical executive stakeholders.",
                            optional_hints=["TreeExplainer computes exact Shapley values in polynomial time for tree ensembles."]
                        ),
                        make_problem(
                            problem_id="shap-prob-2",
                            title="Adverse Action Reason Generator for Loan Rejections",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Generate individualized local explanation waterfall plots to provide legally compliant rejection reasons.",
                            problem_statement="Financial regulations require adverse action notices detailing why an applicant was denied a loan. For any rejected applicant, compute local Shapley values and generate a waterfall explanation showing the exact positive and negative contributors pushing their score below the threshold.",
                            requirements=[
                                "Extract individual row shap_values[applicant_idx].",
                                "Generate a shap.plots.waterfall visualization displaying baseline E[f(x)] and final f(x).",
                                "Extract top 4 negative contributors and format into human-readable rejection reasons.",
                                "Verify additivity: sum of SHAP contributions plus base value exactly equals model output."
                            ],
                            concepts_tested=["Local Explanations (Waterfall Plot)", "Adverse Action Notice Generation", "Shapley Additivity Axiom", "Regulatory Compliance"],
                            expected_outcome="An automated adverse action reason generator satisfying fair lending transparency mandates.",
                            optional_hints=["Shapley values possess the efficiency/additivity property: sum(shap_values) + expected_value = prediction."]
                        ),
                        make_problem(
                            problem_id="shap-prob-3",
                            title="Fairness & Demographic Parity Bias Audit",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Audit a machine learning model for algorithmic bias across protected demographic attributes using Fairlearn.",
                            problem_statement="Audit a hiring or credit scoring algorithm across protected demographic attributes (gender, age cohort). Calculate Disparate Impact Ratio, Equalized Odds, and Demographic Parity Difference. If bias exceeds the 80% rule (disparate impact < 0.8), apply post-processing threshold calibration to mitigate disparate impact.",
                            requirements=[
                                "Compute Demographic Parity Difference and Equalized Odds using fairlearn.metrics.",
                                "Calculate Disparate Impact Ratio across sensitive groups.",
                                "Apply fairlearn.postprocessing.ThresholdOptimizer to achieve fair acceptance rates.",
                                "Compare model performance vs fairness tradeoff before and after mitigation."
                            ],
                            concepts_tested=["Algorithmic Bias Auditing", "Disparate Impact (80% Rule)", "Demographic Parity & Equalized Odds", "ThresholdOptimizer Bias Mitigation"],
                            expected_outcome="A documented fairness audit report and debiased model adhering to regulatory equity standards.",
                            optional_hints=["The four-fifths (80%) rule flags adverse impact if selection rate for a protected group is <80% of the highest group."]
                        ),
                    ],
                ),
                make_skill(
                    slug="deployment-ds",
                    name="Data Product Deployment with Streamlit & FastAPI",
                    canonical_slug="fastapi",
                    difficulty="INTERMEDIATE",
                    description="Deploying data science solutions: interactive prototypes with Streamlit, real-time prediction microservices with FastAPI, Docker containerization, and model artifact serialization (Joblib/ONNX).",
                    key_topics=["Interactive Dashboards with Streamlit", "REST APIs with FastAPI & Pydantic Contracts", "Model Serialization (Joblib, ONNX, BentoML)", "Docker Packaging for Data Science Apps", "Inference Latency & Batching"],
                    role_relevance="Bridges the gap between a standalone Jupyter notebook and an interactive enterprise software solution.",
                    prerequisites=["supervised-ml-ds"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Streamlit Documentation", "url": "https://docs.streamlit.io/", "description": "Official guide to building interactive web apps for machine learning in pure Python."},
                        {"type": "YOUTUBE", "title": "Deploy Machine Learning Models with FastAPI — freeCodeCamp", "url": "https://www.youtube.com/watch?v=h5wLuVDr0oc", "description": "Step-by-step tutorial deploying trained models as production REST APIs with FastAPI and Docker."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="dep-ds-prob-1",
                            title="Interactive ML Prediction Dashboard with Streamlit",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build an interactive web application allowing users to input features, view real-time predictions, and inspect SHAP plots.",
                            problem_statement="Create a Streamlit application (app.py) that loads a pre-trained customer churn model, presents input sliders and dropdowns for user attributes, displays churn probability with color-coded risk badges, and renders an interactive SHAP waterfall explanation.",
                            requirements=[
                                "Use st.slider, st.selectbox, and st.number_input for user parameters.",
                                "Cache model loading using @st.cache_resource to prevent redundant disk I/O.",
                                "Render real-time prediction probability with gauge charts or progress bars.",
                                "Embed matplotlib SHAP waterfall plot explaining the individual prediction."
                            ],
                            concepts_tested=["Streamlit UI Components", "@st.cache_resource Optimization", "Interactive Model Inference", "Embedded SHAP Visualizations"],
                            expected_outcome="An intuitive, responsive web application for business users to test model predictions.",
                            optional_hints=["@st.cache_resource caches large objects like ML models once across all user sessions."]
                        ),
                        make_problem(
                            problem_id="dep-ds-prob-2",
                            title="High-Throughput Model Inference API with FastAPI",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Expose a machine learning model via an asynchronous FastAPI REST microservice with Pydantic request validation.",
                            problem_statement="Develop a production REST API with POST /predict and POST /predict-batch endpoints. Validate inputs with Pydantic schemas, return predicted classes with confidence scores, and include health check and model version metadata endpoints.",
                            requirements=[
                                "Define Pydantic request models with Field validation (ranges, allowed strings).",
                                "Load serialized Joblib model at app startup using FastAPI lifespan handler.",
                                "Implement POST /predict-batch accepting lists of records for vectorized throughput.",
                                "Write automated pytest tests verifying 200 OK responses and 422 Unprocessable Entity error handling."
                            ],
                            concepts_tested=["FastAPI Endpoints", "Pydantic Request Validation", "Lifespan Startup Model Loading", "Vectorized Batch Inference"],
                            expected_outcome="A production-ready prediction microservice capable of hundreds of requests per second.",
                            optional_hints=["Use lifespan(app: FastAPI) context manager to load the model into app.state."]
                        ),
                        make_problem(
                            problem_id="dep-ds-prob-3",
                            title="Dockerized Model Service with ONNX Runtime Acceleration",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Convert a Scikit-Learn / PyTorch model to ONNX format, serve with ONNX Runtime, and containerize with Docker.",
                            problem_statement="Export a trained model to open ONNX format, benchmark inference latency (targeting >3x speedup over Python interpreter), package the FastAPI application into a lightweight multi-stage Docker container running as a non-root user, and document deployment instructions.",
                            requirements=[
                                "Convert model using skl2onnx or torch.onnx.export.",
                                "Execute inference using onnxruntime.InferenceSession.",
                                "Benchmark latency: compare native Python model vs ONNX Runtime across 10,000 queries.",
                                "Create a minimal multi-stage Dockerfile based on python:3.11-slim with non-root app user."
                            ],
                            concepts_tested=["ONNX Model Conversion", "ONNX Runtime Acceleration", "Multi-Stage Docker Packaging", "Production Container Hardening"],
                            expected_outcome="An accelerated, portable Docker container delivering low-latency inferences in any cloud environment.",
                            optional_hints=["ONNX Runtime optimizes the execution graph with kernel fusions and hardware-specific vectorization."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

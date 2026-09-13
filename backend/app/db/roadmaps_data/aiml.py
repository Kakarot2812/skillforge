"""AI / ML Engineer roadmap definition with progressive practice problems and market demand integration."""
from typing import Any, Dict
from app.db.roadmaps_data.common import CANONICAL_ROLE_IDS, ROADMAP_IDS, make_problem, make_skill

AIML_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["ai-ml-engineer"],
    "slug": "ai-ml-engineer",
    "role_id": CANONICAL_ROLE_IDS["ai-ml-engineer"],
    "title": "AI / ML Engineer",
    "domain": "Artificial Intelligence & Machine Learning",
    "category": "Engineering",
    "description": "Master machine learning from foundations to production: scientific computing (NumPy, Pandas), classical algorithms (Scikit-Learn), deep learning (PyTorch), generative AI (Transformers, pgvector, RAG), and MLOps deployment (FastAPI, MLflow, Docker).",
    "version": "v2.0",
    "has_market_data": True,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Mathematical Foundations & Scientific Python",
            "description": "Core numerical computing, linear algebra, vectorization, and data manipulation.",
            "skills": [
                make_skill(
                    slug="python-aiml",
                    name="Python for Machine Learning",
                    canonical_slug="python",
                    difficulty="BEGINNER",
                    description="Idiomatic Python for scientific computing: Data structures, list comprehensions, lambda functions, object-oriented modeling, and virtual environment management.",
                    key_topics=["Python Memory Model & References", "List/Dict/Set Comprehensions", "Functional Tools (map, filter, lambda)", "Classes & Object-Oriented Modeling", "Virtual Environments (uv / venv / conda)"],
                    role_relevance="The universal language of artificial intelligence, deep learning frameworks, and data science research.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Python Official Documentation", "url": "https://docs.python.org/3/", "description": "Official Python documentation, standard library, and tutorials."},
                        {"type": "YOUTUBE", "title": "Python for Machine Learning — freeCodeCamp", "url": "https://www.youtube.com/watch?v=rfscVS0vtbw", "description": "Hands-on Python programming tutorial focused on algorithms and data structures."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="py-ai-prob-1",
                            title="Matrix Math with Pure Python",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement matrix multiplication and vector dot products using pure Python without external libraries.",
                            problem_statement="Write a function matrix_multiply(A: list, B: list) -> list that multiplies two 2D matrices using nested list comprehensions.",
                            requirements=[
                                "Validate that the number of columns in A equals the number of rows in B; raise ValueError if mismatched.",
                                "Compute the dot product for each row and column pair.",
                                "Return the resulting 2D matrix."
                            ],
                            concepts_tested=["Nested Loops", "List Comprehensions", "Input Validation", "Linear Algebra Basics"],
                            expected_outcome="Accurate matrix multiplication results matching analytical linear algebra solutions.",
                            optional_hints=["zip(*B) transposes matrix B into convenient columns."]
                        ),
                        make_problem(
                            problem_id="py-ai-prob-2",
                            title="Streaming Dataset Generator with Yield",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Process large datasets memory-efficiently using Python generators and custom iterators.",
                            problem_statement="Create an iterator class BatchDataset that reads a multi-gigabyte CSV line-by-line and yields fixed-size batches of preprocessed numeric vectors.",
                            requirements=[
                                "Implement a generator function using 'yield' that batches records into chunks of size N.",
                                "Handle memory efficiency so memory usage remains constant regardless of file size.",
                                "Normalize feature columns by scaling values between 0.0 and 1.0."
                            ],
                            concepts_tested=["Generators & yield", "Custom Iterators", "Memory Optimization", "Data Normalization"],
                            expected_outcome="Streamed batches consumed by ML training loops without loading entire files into RAM.",
                            optional_hints=["Generators yield one item at a time, keeping RAM consumption minimal."]
                        ),
                        make_problem(
                            problem_id="py-ai-prob-3",
                            title="Autograd Computation Graph Engine",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a micro-scale automatic differentiation scalar engine modeled after PyTorch autograd.",
                            problem_statement="Create a Value class that tracks operations (+, *, tanh) and computes partial derivatives using the chain rule via backward().",
                            requirements=[
                                "Implement a Value(data, _children, _op) class with overloaded __add__ and __mul__ operators.",
                                "Maintain a computation graph of parent and child nodes.",
                                "Implement backward() traversing the topological graph in reverse to compute gradients (adjoints)."
                            ],
                            concepts_tested=["Automatic Differentiation (Autograd)", "Computation Graphs", "Operator Overloading", "Topological Sort", "Backpropagation"],
                            expected_outcome="A functioning micrograd-style scalar engine capable of running gradient descent on a simple neuron.",
                            optional_hints=["Review Karpathy's micrograd for the topological sorting backward implementation."]
                        ),
                    ],
                ),
                make_skill(
                    slug="numpy-scientific",
                    name="NumPy & Scientific Computing",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="High-performance numerical computing: N-dimensional arrays (ndarray), vectorization, broadcasting rules, indexing, slicing, and linear algebra operations.",
                    key_topics=["ndarray Creation & Data Types", "Vectorized Array Operations", "Broadcasting Rules & Dimension Matching", "Advanced Slicing & Boolean Masking", "Linear Algebra (np.linalg.inv, np.dot, svd)"],
                    role_relevance="Provides the underlying C-accelerated array structures and mathematical operators powering all modern deep learning frameworks.",
                    prerequisites=["python-aiml"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "NumPy Official Documentation", "url": "https://numpy.org/doc/stable/", "description": "Official guides for array creation, broadcasting, indexing, and mathematical functions."},
                        {"type": "YOUTUBE", "title": "NumPy Crash Course — Keith Galli", "url": "https://www.youtube.com/watch?v=GB9ByLh482Y", "description": "In-depth tutorial on multidimensional arrays, vectorization, and math routines."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="np-prob-1",
                            title="Vectorized Distance Matrix Computation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Compute Euclidean distances between two sets of vectors without Python loops.",
                            problem_statement="Write a function euclidean_distances(X, Y) that computes all pairwise distances between N points in X and M points in Y using NumPy broadcasting.",
                            requirements=[
                                "Take arrays X (shape: N, D) and Y (shape: M, D).",
                                "Reshape arrays using np.newaxis or broadcasting: (N, 1, D) - (1, M, D).",
                                "Compute Euclidean distance along the last axis without any for loops."
                            ],
                            concepts_tested=["Broadcasting Rules", "np.newaxis", "Vectorized Calculations", "Euclidean Distance"],
                            expected_outcome="A 100x speedup compared to nested Python loops for large point clouds.",
                            optional_hints=["np.sqrt(np.sum((X[:, np.newaxis, :] - Y[np.newaxis, :, :]) ** 2, axis=-1))."]
                        ),
                        make_problem(
                            problem_id="np-prob-2",
                            title="Image Filtering with 2D Convolution",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement image edge detection using 2D matrix convolution and sliding windows.",
                            problem_statement="Write a 2D convolution function that applies a Sobel or Gaussian filter to a 2D grayscale image array using stride tricks or sliding windows.",
                            requirements=[
                                "Take a 2D image matrix and a 3x3 kernel matrix.",
                                "Extract image patches and compute the element-wise dot product with the kernel.",
                                "Apply edge padding ('same' padding) so output dimensions match input dimensions."
                            ],
                            concepts_tested=["2D Convolution", "Sliding Windows", "Edge Padding", "Kernel Filtering"],
                            expected_outcome="Edge-detected output image array highlighting horizontal and vertical intensity gradients.",
                            optional_hints=["np.pad(image, pad_width=1, mode='constant') handles edge padding cleanly."]
                        ),
                        make_problem(
                            problem_id="np-prob-3",
                            title="Principal Component Analysis (PCA) from Scratch",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement dimensionality reduction from first principles using SVD or Eigendecomposition.",
                            problem_statement="Build a custom PCA class that centers data, computes the covariance matrix, and projects features onto top K principal components using np.linalg.eigh.",
                            requirements=[
                                "Standardize features to zero mean.",
                                "Compute the covariance matrix: (X.T @ X) / (N - 1).",
                                "Compute eigenvalues and eigenvectors using np.linalg.eigh and sort descending.",
                                "Project data onto top K eigenvectors and compute explained variance ratio."
                            ],
                            concepts_tested=["Covariance Matrix", "Eigendecomposition (np.linalg.eigh)", "Singular Value Decomposition (SVD)", "Dimensionality Reduction", "Explained Variance"],
                            expected_outcome="Dimensionality reduction matching scikit-learn's PCA output within 1e-5 numerical precision.",
                            optional_hints=["Sort eigenvalues using np.argsort()[::-1]."]
                        ),
                    ],
                ),
                make_skill(
                    slug="pandas-aiml",
                    name="Pandas & Data Manipulation",
                    canonical_slug="pandas",
                    difficulty="BEGINNER",
                    description="Tabular data processing: DataFrames, Series, missing data handling, group aggregations, merging, and time series transformations.",
                    key_topics=["DataFrames & Series Manipulation", "Missing Data Imputation & Cleaning (dropna, fillna)", "Group Aggregations (groupby, agg, transform)", "Merging & Reshaping (merge, join, pivot_table)", "Time Series Indexing & Resampling"],
                    role_relevance="The universal standard for data preparation, feature engineering, and exploratory data analysis in ML pipelines.",
                    prerequisites=["python-aiml", "numpy-scientific"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Pandas Documentation", "url": "https://pandas.pydata.org/docs/", "description": "Official reference for DataFrames, indexing, aggregations, and I/O."},
                        {"type": "YOUTUBE", "title": "Pandas Full Tutorial — Keith Galli", "url": "https://www.youtube.com/watch?v=vmEHCJofslg", "description": "Hands-on guide to data filtering, aggregations, and cleaning with Pandas."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="pd-prob-1",
                            title="Dataset Cleaning & Imputation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Clean a messy real-world tabular dataset and handle missing values.",
                            problem_statement="Clean a housing dataset containing missing values, incorrect data types, and duplicate rows.",
                            requirements=[
                                "Identify missing values using df.isnull().sum().",
                                "Impute numeric missing values with median and categorical missing values with mode.",
                                "Drop duplicate rows and convert date strings to proper datetime objects."
                            ],
                            concepts_tested=["Missing Data (fillna, dropna)", "Data Type Casting", "Deduplication", "Datetime Parsing"],
                            expected_outcome="A clean DataFrame with zero null values ready for downstream statistical modeling.",
                            optional_hints=["Use df['col'].fillna(df['col'].median()) for numeric columns."]
                        ),
                        make_problem(
                            problem_id="pd-prob-2",
                            title="Multi-Level Group Aggregations & Pivot Tables",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Analyze customer behavior across cohorts using groupby and pivot tables.",
                            problem_statement="Compute cohort retention metrics and rolling 7-day average sales grouped by region and product category.",
                            requirements=[
                                "Group by ['region', 'category'] and compute multiple aggregates (mean, sum, count) using .agg().",
                                "Create a pivot_table showing monthly revenue by customer acquisition cohort.",
                                "Compute rolling 7-day average revenue per region using df.groupby('region')['revenue'].rolling(7).mean()."
                            ],
                            concepts_tested=["groupby().agg()", "pivot_table", "Rolling Window Aggregations", "Cohort Analysis"],
                            expected_outcome="A multi-dimensional analytical summary revealing customer spending trends.",
                            optional_hints=["Reset index using .reset_index() after grouping for clean tabular export."]
                        ),
                        make_problem(
                            problem_id="pd-prob-3",
                            title="High-Performance Feature Engineering Pipeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Engineer time-based and interaction features on 1M+ rows using vectorized operations and memory optimization.",
                            problem_statement="Build a feature engineering pipeline that downcasts numeric datatypes to reduce memory usage by 60%+ and generates lag features.",
                            requirements=[
                                "Downcast float64 to float32 and int64 to int16/int32 using pd.to_numeric(downcast=...).",
                                "Create lag features (t-1, t-7, t-30) for forecasting using groupby('item_id')['sales'].shift().",
                                "Calculate target encoding with out-of-fold regularization to prevent data leakage."
                            ],
                            concepts_tested=["Memory Optimization (Downcasting)", "Lag & Lead Features (shift)", "Target Encoding", "Data Leakage Prevention"],
                            expected_outcome="A feature-rich DataFrame with significantly reduced memory footprint, optimized for fast model training.",
                            optional_hints=["Never compute target encoding on the test set; apply mappings learned on train only."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Classical Machine Learning & Validation",
            "description": "Supervised and unsupervised learning, feature pipelines, hyperparameter optimization, and rigorous statistical evaluation.",
            "skills": [
                make_skill(
                    slug="scikit-learn-ml",
                    name="Classical Machine Learning with Scikit-Learn",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Supervised and unsupervised algorithms: Linear/Logistic Regression, Decision Trees, Random Forests, Gradient Boosting (XGBoost/LightGBM), K-Means Clustering, and Scikit-Learn Pipelines.",
                    key_topics=["Supervised vs Unsupervised Learning", "Linear & Logistic Regression", "Ensemble Methods (Random Forest, Gradient Boosting)", "Preprocessing & ColumnTransformer Pipelines", "Hyperparameter Tuning (GridSearchCV, RandomizedSearchCV)"],
                    role_relevance="The foundation of practical industry ML; tabular data in production is predominantly solved with tree-based models and pipelines.",
                    prerequisites=["pandas-aiml", "numpy-scientific"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Scikit-Learn Official Documentation", "url": "https://scikit-learn.org/stable/", "description": "Official guides, tutorials, and API documentation for classical machine learning."},
                        {"type": "YOUTUBE", "title": "Machine Learning with Scikit-Learn — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0B5eIE_1vpU", "description": "Full course covering classification, regression, clustering, and evaluation pipelines."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="sklearn-prob-1",
                            title="Binary Classification with Logistic Regression",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Train and evaluate a baseline classification model on tabular data.",
                            problem_statement="Build a customer churn prediction model using Logistic Regression with train-test split and feature scaling.",
                            requirements=[
                                "Split data into train and test sets (80/20) using train_test_split with a random seed.",
                                "Scale numeric features using StandardScaler fit only on training data.",
                                "Train LogisticRegression and report accuracy and confusion matrix."
                            ],
                            concepts_tested=["train_test_split", "StandardScaler", "LogisticRegression", "Accuracy Score", "Confusion Matrix"],
                            expected_outcome="A baseline model predicting customer churn with verified test accuracy.",
                            optional_hints=["Always fit scalers on training data only to prevent data leakage."]
                        ),
                        make_problem(
                            problem_id="sklearn-prob-2",
                            title="End-to-End Scikit-Learn Preprocessing Pipeline",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Build an automated ColumnTransformer pipeline handling numeric scaling and one-hot encoding.",
                            problem_statement="Create a reproducible Pipeline combining OneHotEncoder for categoricals, SimpleImputer for missing values, and a RandomForestClassifier.",
                            requirements=[
                                "Use ColumnTransformer to apply distinct transformations to numeric vs categorical columns.",
                                "Combine preprocessor and RandomForestClassifier into a unified sklearn.pipeline.Pipeline.",
                                "Fit on raw training data and call pipeline.predict() directly on raw unseen test inputs."
                            ],
                            concepts_tested=["Pipeline", "ColumnTransformer", "OneHotEncoder", "SimpleImputer", "RandomForestClassifier"],
                            expected_outcome="An atomic, serialized pipeline that transforms raw input data into predictions in a single step.",
                            optional_hints=["Pipelines eliminate feature mismatch bugs between training and production inference."]
                        ),
                        make_problem(
                            problem_id="sklearn-prob-3",
                            title="Gradient Boosting with Hyperparameter Search & CV",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Tune an ensemble gradient boosted model using Stratified K-Fold cross-validation.",
                            problem_statement="Train a GradientBoostingClassifier or XGBoost model, optimizing hyperparameters via RandomizedSearchCV with StratifiedKFold cross-validation.",
                            requirements=[
                                "Use StratifiedKFold(n_splits=5) to preserve class balance across validation folds.",
                                "Define hyperparameter search space (n_estimators, max_depth, learning_rate, subsample).",
                                "Execute RandomizedSearchCV optimizing for ROC-AUC score.",
                                "Evaluate the best estimator on a held-out test set and report precision-recall curves."
                            ],
                            concepts_tested=["Gradient Boosting", "StratifiedKFold Cross-Validation", "RandomizedSearchCV", "Hyperparameter Optimization", "ROC-AUC"],
                            expected_outcome="A fully tuned ensemble model achieving superior classification performance without overfitting.",
                            optional_hints=["Use scoring='roc_auc' when dealing with imbalanced binary classification."]
                        ),
                    ],
                ),
                make_skill(
                    slug="model-evaluation-metrics",
                    name="Model Evaluation, Validation & Metrics",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Rigorous evaluation of machine learning systems: Precision, Recall, F1-score, ROC-AUC, PR-AUC, Confusion Matrix, Bias-Variance tradeoff, and Data Leakage prevention.",
                    key_topics=["Confusion Matrix & Error Analysis", "Precision vs Recall Tradeoff & F1-Score", "ROC Curve & Area Under Curve (ROC-AUC)", "Precision-Recall AUC for Imbalanced Classes", "Cross-Validation Strategies & Data Leakage Prevention"],
                    role_relevance="Prevents deploying misleading or overfitted models by measuring genuine generalization performance.",
                    prerequisites=["scikit-learn-ml"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Scikit-Learn Model Evaluation Guide", "url": "https://scikit-learn.org/stable/modules/model_evaluation.html", "description": "Official guide to scoring metrics, cross-validation, and validation curves."},
                        {"type": "YOUTUBE", "title": "ROC and AUC Explained — StatQuest", "url": "https://www.youtube.com/watch?v=4jRBRDbJemM", "description": "Clear conceptual breakdown of sensitivity, specificity, ROC curves, and AUC."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="metrics-prob-1",
                            title="Classification Report & Confusion Matrix Analysis",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Calculate and interpret precision, recall, and F1-score across imbalanced classes.",
                            problem_statement="Evaluate a fraud detection model where fraudulent transactions represent only 1% of total records.",
                            requirements=[
                                "Compute accuracy, precision, recall, and F1-score using sklearn.metrics.",
                                "Plot a ConfusionMatrixDisplay and analyze false positives vs false negatives.",
                                "Explain why 99% accuracy is completely deceptive for this dataset."
                            ],
                            concepts_tested=["Accuracy Paradox", "Precision & Recall", "F1-Score", "Confusion Matrix", "Imbalanced Classification"],
                            expected_outcome="A thorough diagnostic report revealing whether the model accurately detects minority fraud cases.",
                            optional_hints=["When fraudulent cases are rare, a trivial model predicting 'not fraud' 100% of the time gets 99% accuracy."]
                        ),
                        make_problem(
                            problem_id="metrics-prob-2",
                            title="Threshold Tuning with Precision-Recall Curves",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Tune classification decision thresholds to optimize business cost tradeoffs.",
                            problem_statement="Find the optimal decision probability threshold to maximize recall at a minimum acceptable precision threshold of 80%.",
                            requirements=[
                                "Extract predicted probabilities using model.predict_proba(X_test)[:, 1].",
                                "Calculate precision-recall curve using precision_recall_curve().",
                                "Locate the exact threshold where precision >= 0.80 while maximizing recall.",
                                "Implement custom prediction logic based on the selected threshold."
                            ],
                            concepts_tested=["Decision Thresholds", "predict_proba", "precision_recall_curve", "Cost-Benefit Tradeoffs"],
                            expected_outcome="Custom threshold decision boundaries tailored to specific business risk tolerances.",
                            optional_hints=["Default threshold of 0.5 is rarely optimal for asymmetric cost problems."]
                        ),
                        make_problem(
                            problem_id="metrics-prob-3",
                            title="Audit & Eliminate Temporal Data Leakage",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Detect, diagnose, and fix subtle data leakage in a time-series forecasting model.",
                            problem_statement="Audit a stock or sales prediction model showing unrealistically high 99% accuracy caused by future information leaking into past training records.",
                            requirements=[
                                "Identify temporal data leakage caused by random train_test_split on time-series data.",
                                "Refactor validation using TimeSeriesSplit (rolling origin / walk-forward validation).",
                                "Verify that feature normalization and aggregations use only data from prior time windows.",
                                "Report true out-of-sample forecast accuracy."
                            ],
                            concepts_tested=["Data Leakage Detection", "TimeSeriesSplit", "Walk-Forward Validation", "Temporal Train/Test Split", "Realistic Error Bounds"],
                            expected_outcome="Elimination of artificial data leakage, yielding honest, deployable forecast accuracy metrics.",
                            optional_hints=["Never use random shuffling on time-series datasets."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Deep Learning & Neural Networks",
            "description": "Deep neural networks with PyTorch, GPU acceleration, backpropagation, and transformer architectures.",
            "skills": [
                make_skill(
                    slug="pytorch-deeplearning",
                    name="PyTorch",
                    canonical_slug="pytorch",
                    difficulty="INTERMEDIATE",
                    description="Deep learning framework: Tensors, autograd, torch.nn.Module, loss functions, optimizers, DataLoader, and GPU acceleration (CUDA).",
                    key_topics=["PyTorch Tensors & GPU Acceleration (.to('cuda'))", "Defining Neural Networks with torch.nn.Module", "Loss Functions & Optimizers (SGD, AdamW)", "Custom Dataset & DataLoader Classes", "Training Loops, Validation & Early Stopping"],
                    role_relevance="The dominant research and industry deep learning framework powering modern neural networks and AI models globally.",
                    prerequisites=["numpy-scientific", "model-evaluation-metrics"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PyTorch Official Tutorials", "url": "https://pytorch.org/tutorials/", "description": "Official guides from PyTorch basics to advanced neural network architectures."},
                        {"type": "YOUTUBE", "title": "PyTorch for Deep Learning — freeCodeCamp", "url": "https://www.youtube.com/watch?v=V_xro1bcAuA", "description": "Complete hands-on course covering tensors, neural networks, computer vision, and training loops."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="pytorch-prob-1",
                            title="Multi-Layer Perceptron (MLP) Binary Classifier",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Build and train a simple neural network using torch.nn.Module and Adam optimizer.",
                            problem_statement="Build a 3-layer neural network in PyTorch to classify non-linearly separable data (e.g. moon dataset).",
                            requirements=[
                                "Subclass nn.Module and define layers (Linear, ReLU, Linear, Sigmoid).",
                                "Use BCELoss and torch.optim.Adam optimizer.",
                                "Run a training loop for 100 epochs, zeroing gradients with optimizer.zero_grad() and updating with loss.backward()."
                            ],
                            concepts_tested=["nn.Module", "Tensors & autograd", "optimizer.zero_grad()", "loss.backward()", "optimizer.step()"],
                            expected_outcome="A trained neural network model achieving >95% accuracy on non-linear synthetic data.",
                            optional_hints=["Always call optimizer.zero_grad() before loss.backward() to prevent gradient accumulation."]
                        ),
                        make_problem(
                            problem_id="pytorch-prob-2",
                            title="Custom Dataset & PyTorch Training Loop with Validation",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement a custom torch.utils.data.Dataset and a training loop with validation and early stopping.",
                            problem_statement="Create a custom Dataset loading tabular/image samples, wrapped in a DataLoader with batching and shuffling.",
                            requirements=[
                                "Implement __len__ and __getitem__ returning PyTorch tensors.",
                                "Wrap in DataLoader(batch_size=32, shuffle=True).",
                                "Implement validation evaluation inside 'with torch.no_grad():' and model.eval().",
                                "Save the best model checkpoint using torch.save(model.state_dict(), 'best_model.pt')."
                            ],
                            concepts_tested=["Custom Dataset", "DataLoader", "torch.no_grad()", "model.train() vs model.eval()", "Model Checkpointing"],
                            expected_outcome="A production-ready training and evaluation loop that prevents overfitting via early stopping.",
                            optional_hints=["model.eval() disables dropout and puts batchnorm into evaluation mode."]
                        ),
                        make_problem(
                            problem_id="pytorch-prob-3",
                            title="Convolutional Neural Network (CNN) with Transfer Learning",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Fine-tune a pretrained vision backbone (ResNet) on a custom image classification task.",
                            problem_statement="Load a pretrained ResNet18 model from torchvision.models, freeze feature extraction layers, and train a custom classification head.",
                            requirements=[
                                "Load pretrained weights and freeze convolutional backbone with param.requires_grad = False.",
                                "Replace model.fc with a custom Linear layer matching your target class count.",
                                "Apply data augmentation transforms (RandomHorizontalFlip, ColorJitter) on training data.",
                                "Train the custom head and evaluate on a held-out test dataset."
                            ],
                            concepts_tested=["Transfer Learning", "Freezing Layers (requires_grad)", "torchvision Models", "Data Augmentation", "Fine-Tuning"],
                            expected_outcome="High classification accuracy achieved with minimal training epochs by leveraging pretrained feature representations.",
                            optional_hints=["Unfreeze the last residual block for fine-tuning after training the head."]
                        ),
                    ],
                ),
                make_skill(
                    slug="transformers-llm-engineering",
                    name="Hugging Face Transformers & LLM Engineering",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Modern generative AI: Hugging Face Transformers, tokenization, pre-trained language models, embeddings extraction, and parameter-efficient fine-tuning (LoRA).",
                    key_topics=["Transformer Architecture (Self-Attention, Encoders, Decoders)", "Tokenization with AutoTokenizer", "Pretrained Models (BERT, Llama, Mistral) via AutoModel", "Generating Text & Sampling Strategies (temperature, top_p)", "Parameter-Efficient Fine-Tuning (PEFT / LoRA)"],
                    role_relevance="The core technology driving contemporary generative AI, large language models (LLMs), and semantic text analysis.",
                    prerequisites=["pytorch-deeplearning"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Hugging Face Transformers Documentation", "url": "https://huggingface.co/docs/transformers/index", "description": "Official guides for tokenizers, pipelines, pre-trained models, and fine-tuning."},
                        {"type": "YOUTUBE", "title": "Hugging Face Transformers Tutorial — freeCodeCamp", "url": "https://www.youtube.com/watch?v=GSt00LuQ6e0", "description": "Complete tutorial on tokenizers, pipelines, text classification, and fine-tuning BERT."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="hf-prob-1",
                            title="Zero-Shot Text Classification with Transformers",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Use pre-trained Hugging Face pipelines for sentiment analysis and zero-shot categorization.",
                            problem_statement="Build a customer ticket classifier that categorizes support queries into Billing, Bug, or Feature Request using a pre-trained zero-shot pipeline.",
                            requirements=[
                                "Instantiate a pipeline('zero-shot-classification') with a pre-trained model.",
                                "Classify incoming text against custom candidate labels.",
                                "Extract and format confidence scores."
                            ],
                            concepts_tested=["Hugging Face pipeline()", "Zero-Shot Classification", "Confidence Scores", "Inference Pipelines"],
                            expected_outcome="Accurate classification of customer queries without requiring any custom model training.",
                            optional_hints=["Use model='facebook/bart-large-mnli' or a lightweight distilled alternative."]
                        ),
                        make_problem(
                            problem_id="hf-prob-2",
                            title="Text Embeddings Generation & Semantic Similarity",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Generate dense vector representations of text documents and compute cosine similarity.",
                            problem_statement="Build a semantic duplicate question detector using an embedding model (e.g. sentence-transformers) to calculate cosine similarity between sentences.",
                            requirements=[
                                "Load a sentence transformer model or AutoModel with mean-pooling.",
                                "Tokenize text with padding and truncation, converting to input_ids and attention_mask tensors.",
                                "Generate 768-dimensional normalized embeddings for a list of questions.",
                                "Compute cosine similarity matrix using PyTorch or NumPy, flagging pairs with similarity > 0.85."
                            ],
                            concepts_tested=["AutoTokenizer", "Dense Vector Embeddings", "Mean Pooling", "Cosine Similarity", "Semantic Search"],
                            expected_outcome="A functioning semantic similarity engine that detects duplicate questions even with completely different wording.",
                            optional_hints=["Sentence embeddings must apply mean pooling taking the attention mask into account."]
                        ),
                        make_problem(
                            problem_id="hf-prob-3",
                            title="Parameter-Efficient Fine-Tuning (PEFT / LoRA)",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Fine-tune a language model on custom domain data using Low-Rank Adaptation (LoRA).",
                            problem_statement="Fine-tune a base model for medical question answering using Hugging Face PEFT library with LoRA adapters.",
                            requirements=[
                                "Configure LoRA parameters using LoraConfig(r=8, lora_alpha=16, target_modules=['q_proj', 'v_proj']).",
                                "Wrap the base model with get_peft_model() and verify trainable parameters are < 1% of total parameters.",
                                "Train with SFTTrainer (TRL library) on a medical QA dataset.",
                                "Save the lightweight adapter weights and test generation."
                            ],
                            concepts_tested=["PEFT (Parameter-Efficient Fine-Tuning)", "LoRA (Low-Rank Adaptation)", "LoraConfig", "Adapter Weights", "SFTTrainer"],
                            expected_outcome="Domain-adapted language model producing medical responses without requiring expensive full-parameter fine-tuning.",
                            optional_hints=["LoRA freezes the base model weights and trains small low-rank adapter matrices."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Vector Search, RAG & MLOps Production",
            "description": "Vector indexing, Retrieval-Augmented Generation (RAG), FastAPI inference serving, and MLOps deployment.",
            "skills": [
                make_skill(
                    slug="pgvector-embeddings",
                    name="Vector Databases & Similarity Search with pgvector",
                    canonical_slug="pgvector",
                    difficulty="INTERMEDIATE",
                    description="Vector search engineering: pgvector PostgreSQL extension, vector indexing (HNSW, IVFFlat), distance metrics (L2, Cosine, Inner Product), and Retrieval-Augmented Generation (RAG).",
                    key_topics=["Vector Embeddings Storage (VECTOR type)", "Distance Metrics (Cosine <->, L2 <->, Inner Product <#>) ", "Indexing Algorithms: HNSW vs IVFFlat", "Hybrid Search (Keyword + Vector Similarity)", "Retrieval-Augmented Generation (RAG) Architecture"],
                    role_relevance="Enables LLMs to access private enterprise knowledge bases, eliminating hallucinations and grounding AI responses.",
                    prerequisites=["transformers-llm-engineering"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "pgvector GitHub Documentation", "url": "https://github.com/pgvector/pgvector", "description": "Official repository documentation covering installation, vector types, and HNSW indexes."},
                        {"type": "YOUTUBE", "title": "pgvector with PostgreSQL and Python Tutorial", "url": "https://www.youtube.com/watch?v=FDbLu_m7u-8", "description": "Hands-on guide to storing embeddings, creating HNSW indexes, and building RAG pipelines."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="pgvector-prob-1",
                            title="Vector Table Setup & Cosine Distance Queries",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Store embeddings in PostgreSQL and perform nearest-neighbor queries.",
                            problem_statement="Create a document chunks table with a 384-dimensional vector column and query top-3 most similar chunks to a query vector.",
                            requirements=[
                                "Enable pgvector extension with CREATE EXTENSION IF NOT EXISTS vector.",
                                "Create table document_chunks (id UUID, content TEXT, embedding vector(384)).",
                                "Query nearest neighbors using cosine distance operator '<=>' ordered ascending."
                            ],
                            concepts_tested=["CREATE EXTENSION vector", "VECTOR(384) Column", "Cosine Distance Operator (<=>)", "k-Nearest Neighbors (k-NN)"],
                            expected_outcome="Sub-second retrieval of semantically closest text passages from PostgreSQL.",
                            optional_hints=["The '<=>' operator calculates cosine distance: 1 - cosine_similarity."]
                        ),
                        make_problem(
                            problem_id="pgvector-prob-2",
                            title="HNSW Indexing for Sub-Millisecond Search",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Index 50,000+ vector embeddings using Hierarchical Navigable Small World (HNSW) graphs.",
                            problem_statement="Benchmark query speed on an unindexed vector table vs an HNSW-indexed table and tune m and ef_construction parameters.",
                            requirements=[
                                "Populate table with 50,000 synthetic vector rows.",
                                "Measure latency of unindexed exact k-NN query (Sequential Scan).",
                                "Create an HNSW index using 'CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)'.",
                                "Verify via EXPLAIN that query utilizes Index Scan, reducing latency by 90%+."
                            ],
                            concepts_tested=["HNSW Indexing", "m & ef_construction Parameters", "vector_cosine_ops", "Approximate Nearest Neighbors (ANN)", "EXPLAIN Plan Verification"],
                            expected_outcome="High-throughput Approximate Nearest Neighbor (ANN) search responding in single-digit milliseconds.",
                            optional_hints=["HNSW builds a multi-layer graph index for fast sub-linear search."]
                        ),
                        make_problem(
                            problem_id="pgvector-prob-3",
                            title="End-to-End Retrieval-Augmented Generation (RAG) System",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a production RAG pipeline: document chunking -> vector embedding -> pgvector retrieval -> LLM prompt generation.",
                            problem_statement="Build an API that answers questions about internal company policies by retrieving the top 3 relevant chunks from pgvector and generating a grounded answer.",
                            requirements=[
                                "Chunk source documents with overlap (chunk size 500 tokens, overlap 50).",
                                "Embed chunks and upsert into PostgreSQL with pgvector.",
                                "Upon receiving user query, embed query, retrieve top 3 chunks, and synthesize a contextual prompt.",
                                "Pass prompt to an LLM, instruct it to refuse answering if context does not contain the answer, and return response with source citations."
                            ],
                            concepts_tested=["RAG Pipeline Architecture", "Document Chunking with Overlap", "Context Injection", "Hallucination Mitigation", "Source Attribution"],
                            expected_outcome="An enterprise question-answering assistant answering accurately with verified source citations.",
                            optional_hints=["Instruct the LLM in system prompt: 'Answer using ONLY the provided context below. If unknown, say so.'"]
                        ),
                    ],
                ),
                make_skill(
                    slug="fastapi-model-serving",
                    name="Model Serving & Inference APIs with FastAPI",
                    canonical_slug="fastapi",
                    difficulty="INTERMEDIATE",
                    description="Production model serving: Async inference endpoints, batch inference, model lifecycle management (lifespan), Pydantic input schemas, and GPU memory management.",
                    key_topics=["FastAPI Lifespan Context Manager (Loading Models on Startup)", "Pydantic Schemas for AI Input & Output", "Dynamic Batching for GPU Inference Efficiency", "Async vs Threadpool Execution for Heavy ML Models", "Error Handling & Graceful Degradation"],
                    role_relevance="Connects trained AI models to web frontends, mobile apps, and microservices via low-latency HTTP APIs.",
                    prerequisites=["python-aiml", "transformers-llm-engineering"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "FastAPI Deployment Documentation", "url": "https://fastapi.tiangolo.com/deployment/", "description": "Official guides on deploying FastAPI services with Uvicorn and Gunicorn workers."},
                        {"type": "YOUTUBE", "title": "Deploy Machine Learning Models with FastAPI", "url": "https://www.youtube.com/watch?v=h5wLuVDr0oc", "description": "Practical walkthrough serving PyTorch and Scikit-Learn models via FastAPI."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="serving-prob-1",
                            title="Inference Endpoint with Lifespan Model Loading",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Load an ML model once during application startup and serve predictions.",
                            problem_statement="Build a FastAPI service that loads a sentiment analysis model during startup using lifespan, serving POST /predict.",
                            requirements=[
                                "Use @asynccontextmanager lifespan(app: FastAPI) to load model weights into app.state on startup.",
                                "Define PredictRequest and PredictResponse Pydantic schemas.",
                                "Implement POST /predict validating input and returning predicted class and confidence score."
                            ],
                            concepts_tested=["FastAPI Lifespan", "app.state", "Pydantic Schemas", "Model Loading on Boot"],
                            expected_outcome="An API endpoint with zero per-request model loading overhead.",
                            optional_hints=["Never load model weights inside the endpoint function itself."]
                        ),
                        make_problem(
                            problem_id="serving-prob-2",
                            title="CPU-Bound Inference in Threadpool",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Prevent CPU-intensive model inference from blocking the asynchronous event loop.",
                            problem_statement="Ensure that heavy CPU/GPU model computation runs in a worker threadpool without blocking concurrent I/O requests.",
                            requirements=[
                                "Use 'def predict(...)' instead of 'async def predict(...)' or use starlette.concurrency.run_in_threadpool.",
                                "Demonstrate that concurrent lightweight health-check requests return instantly while a heavy prediction executes.",
                                "Handle out-of-memory or timeout errors cleanly."
                            ],
                            concepts_tested=["Event Loop Non-blocking", "run_in_threadpool", "FastAPI Concurrency Model", "I/O Starvation Prevention"],
                            expected_outcome="A responsive API maintaining sub-10ms health check latency under heavy inference load.",
                            optional_hints=["Declaring an endpoint as synchronous 'def' tells FastAPI to run it in its external threadpool."]
                        ),
                        make_problem(
                            problem_id="serving-prob-3",
                            title="Dynamic Batching Inference Engine",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Implement micro-batching to aggregate concurrent requests into a single tensor batch for GPU throughput.",
                            problem_statement="Build an asynchronous queuing mechanism that batches incoming single-item requests over a 10ms window into a single matrix for batched inference.",
                            requirements=[
                                "Use an asyncio.Queue to collect incoming prediction requests.",
                                "Implement a background loop that flushes the queue every 10ms or when batch_size reaches 16.",
                                "Execute model.predict(batch) once for the whole batch and dispatch results back to individual request futures."
                            ],
                            concepts_tested=["Dynamic Batching", "asyncio.Queue", "GPU Throughput Optimization", "Future Resolution"],
                            expected_outcome="A 3-5x increase in throughput on GPU inference by saturating parallel tensor cores.",
                            optional_hints=["Use asyncio.Future to return individual results to waiting HTTP request handlers."]
                        ),
                    ],
                ),
                make_skill(
                    slug="mlops-lifecycle",
                    name="MLOps & Model Lifecycle with MLflow & Docker",
                    canonical_slug="docker",
                    difficulty="ADVANCED",
                    description="Production machine learning operations: Experiment tracking with MLflow, Model Registry, model versioning, containerizing inference services with Docker, and data drift monitoring.",
                    key_topics=["Experiment Tracking (Parameters, Metrics, Artifacts)", "MLflow Model Registry & Staging/Production Stages", "Packaging Models with Docker for Cloud Deployment", "Model Serialization (ONNX, TorchScript, BentoML)", "Monitoring Model Drift & Data Quality"],
                    role_relevance="Ensures reproducible experiments, auditable model deployments, and reliable production monitoring across model versions.",
                    prerequisites=["fastapi-model-serving"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "MLflow Official Documentation", "url": "https://mlflow.org/docs/latest/index.html", "description": "Official guides for experiment tracking, model registry, and deployments."},
                        {"type": "YOUTUBE", "title": "MLOps Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=-dJPoLm_gtE", "description": "Comprehensive tutorial covering MLflow, Docker containerization, and production model serving."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="mlops-prob-1",
                            title="Experiment Tracking with MLflow",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Log hyperparameters, evaluation metrics, and model artifacts with MLflow.",
                            problem_statement="Instrument a model training script with MLflow to log training loss, validation accuracy, learning rate, and the trained model file.",
                            requirements=[
                                "Initialize an MLflow experiment with mlflow.set_experiment('fraud-detection').",
                                "Log hyperparams with mlflow.log_params() and metrics per epoch with mlflow.log_metric().",
                                "Save the trained model artifact using mlflow.pytorch.log_model() or mlflow.sklearn.log_model()."
                            ],
                            concepts_tested=["MLflow Tracking", "mlflow.log_params", "mlflow.log_metric", "Model Artifacts", "MLflow UI"],
                            expected_outcome="Full visibility of historical training runs, metric curves, and artifacts in the MLflow UI.",
                            optional_hints=["Launch the visual dashboard using 'mlflow ui' in your terminal."]
                        ),
                        make_problem(
                            problem_id="mlops-prob-2",
                            title="Containerized Model Serving with Docker",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Package an ML model and FastAPI inference server into a portable Docker container.",
                            problem_statement="Create a Dockerfile that copies an ML model artifact, installs dependencies, and runs a FastAPI inference server.",
                            requirements=[
                                "Use a slim Python base image with PyTorch or ONNX runtime.",
                                "Copy the model weights into the container image or download from MLflow model registry on startup.",
                                "Configure HEALTHCHECK verifying that the model is loaded and responding to /health."
                            ],
                            concepts_tested=["Docker for Machine Learning", "Model Containerization", "Inference Environment Isolation", "Container Healthchecks"],
                            expected_outcome="A self-contained Docker container deployable to AWS ECS, EKS, or Google Cloud Run.",
                            optional_hints=["Use ONNX Runtime for lightweight, CPU-optimized model inference without installing full PyTorch."]
                        ),
                        make_problem(
                            problem_id="mlops-prob-3",
                            title="Automated Data & Model Drift Detection Pipeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Monitor incoming production data distributions and detect feature drift using statistical tests.",
                            problem_statement="Build a monitoring pipeline using Evidently AI or scipy.stats that compares production inference features against training baseline distributions.",
                            requirements=[
                                "Compute Kolmogorov-Smirnov (KS) test for continuous features and Chi-Square test for categorical features.",
                                "Flag features where p-value < 0.05 as statistically significant distribution drift.",
                                "Generate a drift report alerting when drift exceeds a tolerance threshold, triggering an automated retraining trigger."
                            ],
                            concepts_tested=["Data Drift Detection", "Kolmogorov-Smirnov Test", "Evidently AI / Scipy", "Model Degradation Monitoring", "Automated Retraining Triggers"],
                            expected_outcome="Proactive detection of silent model failure before degrading business operations.",
                            optional_hints=["Distribution drift occurs when real-world user behavior changes over time."]
                        ),
                    ],
                ),
            ],
        },
    ],
}

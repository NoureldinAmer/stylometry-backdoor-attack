# Style-Preserving Backdoor Attacks on Code Completion Models

This repository contains the implementation of our research on style-preserving backdoor attacks on code completion models through vulnerability injection, as detailed in our paper.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Dataset Preparation](#dataset-preparation)
- [Feature Extraction](#feature-extraction)
- [Running the Experiments](#running-the-experiments)
- [Reproducing Results](#reproducing-results)
- [Static Analysis Tools Setup](#static-analysis-tools-setup)

## Prerequisites

- Python 3.10.12 or higher
- NVIDIA GPU with CUDA support (tested with A100-SXM4-40GB)
- 83.5GB system RAM (minimum)
- Conda (recommended for environment management)

## Installation

1. Create and activate a conda environment:

```bash
conda create -n stylometry python=3.10.12
conda activate stylometry
```

2. Install required packages:

```bash
conda install -c conda-forge catboost xgboost semgrep snyk
conda install -r requirements.txt
```

## Project Structure

```
.
├── automated_vulnerability_injection.py  # Main vulnerability injection script
├── features/                            # Feature extraction modules
│   ├── feature.py                       # Base feature class
│   ├── features.py                      # Feature calculation logic
│   ├── layout.py                        # Layout-based features
│   ├── lexical.py                       # Lexical features
│   ├── syntactic.py                     # Syntactic features
│   ├── utils.py                         # Utility functions
│   └── __init__.py
├── models/                              # Pre-trained models
│   ├── catboost_stylometry_classifier.cbm
├── data/                                # Dataset directory
│   ├── gcj/                            # Google Code Jam dataset
│   └── github/                          # GitHub Java dataset
└── requirements.txt                     # Project dependencies
```

## Dataset Preparation

1. Google Code Jam Dataset:

```bash
# Create data directory
mkdir -p data/gcj

# Download GCJ dataset
wget https://zibada.guru/gcj/solutions.sqlar -P data/gcj/
```

2. GitHub Java Dataset:

```bash
# Create data directory
mkdir -p data/github

# Download and extract GitHub dataset
wget https://cyberlab.usask.ca/datasets/github.zip -P data/github/
cd data/github
unzip github.zip
```

## Feature Extraction

Our feature extraction process includes three main categories:

1. Layout Features:

- Number of tabs and spaces
- Empty lines ratio
- Whitespace patterns
- Brace placement style
- Tab vs. space indentation

2. Lexical Features:

- Word unigrams
- Keyword frequencies
- Token counts
- Comments analysis
- Function and parameter statistics

3. Syntactic Features:

- AST node depth
- Node bigrams
- Java keyword usage patterns
- AST node type frequencies

Features are extracted using the provided modules under the `features/` directory.

The `features` package contains a few useful functions:

- `calculate_features_for_files(files)`
  <br>This function calculates sets of features for the given source files.
  <br>Usage example: `samples = calculate_features_for_files(['A.java', B.java'])`
- `build_dataset(samples)`
  <br>Builds a pandas data frame from the given list of feature sets.
  <br>Usage example: `df = build_dataset(samples)`

## Running the Experiments

1. Train the stylometry classifier:

```python
from features import calculate_features_for_files, build_dataset
from catboost import CatBoostClassifier
import pandas as pd

# Load and process dataset
# Process code snippets
samples = calculate_features_for_files(code_snippets)
X = build_dataset(samples)

# Train model
model = CatBoostClassifier(
    iterations=500,
    learning_rate=0.2,
    depth=3,
    bootstrap_type='Bernoulli',
    subsample=0.7
)
model.fit(X, y)
```

2. Inject vulnerabilities:

```python
python automated_vulnerability_injection.py
```

## Static Analysis Tools Setup

### Semgrep Setup

1. Verify installation:

```bash
semgrep --version
```

### Snyk Code Setup

1. Authenticate with Snyk:

```bash
snyk auth
```

## File Preparation

First, run the file preparation script from `static_code_analysis.ipynb` to create the Java files from your vulnerability results CSV.

## Running Static Analysis

### Semgrep Analysis

1. Analyze original code base:

```bash
# Run analysis on original snippets
semgrep scan --config "p/java" snippets/original/ --output original_results.json --json
```

2. Analyze modified code with injected vulnerabilities:

```bash
# Run analysis on modified snippets
semgrep scan --config "p/java" snippets/modified/ --output modified_results.json --json
```

### Snyk Analysis

1. Analyze original code base:

```bash
# Scan original snippets
snyk code test snippets/original/ --json > original_snyk.json
```

2. Analyze modified code:

```bash
# Scan modified snippets
snyk code test snippets/modified/ --json > modified_snyk.json
```

## Comparing Results

The JSON output files can be analyzed to:

- Compare vulnerability counts between original and modified code
- Verify detection of injected vulnerabilities
- Calculate detection rates for each CWE type

## License

This project is licensed under the MIT License.

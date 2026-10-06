
import pandas as pd
import numpy as np

# Load the project datasets
cases = pd.read_csv("cases.csv")
evidence = pd.read_csv("evidence.csv")
features = pd.read_csv("features.csv")

# Display basic dataset information
print("=" * 50)
print("       MYSTERY MATRIX: CRIMINAL EVIDENCE ANALYSIS")
print("=" * 50)

print("\n1. CASE DATASET")
print("Rows and columns:", cases.shape)
print(cases.head())

print("\n2. EVIDENCE DATASET")
print("Rows and columns:", evidence.shape)
print(evidence.head())

print("\n3. FEATURE DATASET")
print("Rows and columns:", features.shape)
print(features.head())


# Select the 9 binary evidence features
feature_columns = [
    "physical",
    "biological",
    "digital",
    "documentary",
    "communication",
    "location",
    "forensic",
    "testimonial",
    "financial"
]

# Create the evidence-feature matrix
evidence_matrix = evidence[feature_columns].copy()

print("\n" + "=" * 50)
print("       EVIDENCE-FEATURE MATRIX")
print("=" * 50)

print("Matrix dimensions:", evidence_matrix.shape)
print("\nFirst 5 evidence rows:")
print(evidence_matrix.head())

# Check that all feature values are binary
is_binary = evidence_matrix.isin([0, 1]).all().all()
print("\nAre all feature values 0 or 1?", is_binary)

# Count the occurrences of each feature
print("\nFeature totals:")
print(evidence_matrix.sum())


# Combine case IDs with the binary feature matrix
analysis_matrix = evidence[["case_id", "evidence_id"] + feature_columns].copy()

print("\n" + "=" * 60)
print("       CASE-WISE EVIDENCE MATRIX")
print("=" * 60)

for case_id, group in analysis_matrix.groupby("case_id", sort=False):
    print(f"\nCase: {case_id}")
    print("Number of evidence items:", len(group))
    print(group[["evidence_id"] + feature_columns].to_string(index=False))

# Summarize feature totals for each case
case_feature_totals = analysis_matrix.groupby("case_id")[feature_columns].sum()

print("\n" + "=" * 60)
print("       FEATURE TOTALS BY CASE")
print("=" * 60)
print(case_feature_totals)


# Create a case-level feature matrix
case_matrix = (
    evidence.groupby("case_id")[feature_columns]
    .sum()
    .sort_index()
)

print("\n" + "=" * 60)
print("       CASE-LEVEL FEATURE MATRIX")
print("=" * 60)

print(case_matrix)

# Convert to a NumPy array for linear algebra
A = case_matrix.to_numpy(dtype=float)

print("\nMatrix dimensions:", A.shape)
print("\nNumPy matrix:")
print(A)


# Calculate the rank of the case-level matrix
matrix_rank = np.linalg.matrix_rank(A)

print("\n" + "=" * 60)
print("       MATRIX RANK ANALYSIS")
print("=" * 60)

print("Matrix dimensions:", A.shape)
print("Rank of case-level matrix:", matrix_rank)
print("Maximum possible rank:", min(A.shape))

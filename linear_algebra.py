import pandas as pd
import sympy as sp
import math

CASES_FILE = "cases.csv"
EVIDENCE_FILE = "evidence.csv"
FEATURES_FILE = "features.csv"

FEATURES = [
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


# ============================================================
# 1. LOAD DATA
# ============================================================

def load_data():
    cases = pd.read_csv(CASES_FILE)
    evidence = pd.read_csv(EVIDENCE_FILE)
    features = pd.read_csv(FEATURES_FILE)

    return cases, evidence, features


# ============================================================
# 2. VALIDATE DATA
# ============================================================

def validate_data(cases, evidence, features):

    print("\n========== DATA VALIDATION ==========\n")

    print("Number of cases:", len(cases))
    print("Number of evidence items:", len(evidence))
    print("Number of features:", len(features))

    print("\nEvidence per case:")

    counts = evidence.groupby("case_id").size()

    for case_id, count in counts.items():
        print(case_id, ":", count)

    missing = []

    for feature in FEATURES:
        if feature not in evidence.columns:
            missing.append(feature)

    if len(missing) == 0:
        print("\nAll 9 feature columns found.")
    else:
        print("\nMissing features:", missing)

    valid_values = evidence[FEATURES].isin([0, 1]).all().all()

    if valid_values:
        print("All feature values are 0/1.")
    else:
        print("ERROR: Some feature values are not 0/1.")

    unique_ids = evidence["evidence_id"].is_unique

    if unique_ids:
        print("All evidence IDs are unique.")
    else:
        print("ERROR: Duplicate evidence IDs found.")

    valid_case_ids = evidence["case_id"].isin(cases["case_id"]).all()

    if valid_case_ids:
        print("All evidence rows belong to valid cases.")
    else:
        print("ERROR: Invalid case IDs found.")

    print("\n=====================================\n")


# ============================================================
# 3. DISPLAY CASES
# ============================================================

def display_cases(cases):

    print("\n========== AVAILABLE CASES ==========\n")

    for _, row in cases.iterrows():
        print(row["case_id"], "->", row["case_name"])

    print("\n=====================================\n")


# ============================================================
# 4. GET CASE NAME
# ============================================================

def get_case_name(cases, case_id):

    result = cases[cases["case_id"] == case_id]

    if result.empty:
        return "Unknown Case"

    return result.iloc[0]["case_name"]


# ============================================================
# 5. BUILD EVIDENCE MATRIX
# ============================================================

def build_matrix(evidence, case_id):

    case_data = evidence[evidence["case_id"] == case_id].copy()

    if case_data.empty:
        print("No evidence found for", case_id)
        return None, None

    matrix_data = case_data[FEATURES]

    A = sp.Matrix(matrix_data.values.tolist())

    evidence_ids = case_data["evidence_id"].tolist()

    return A, evidence_ids


# ============================================================
# 6. DISPLAY MATRIX
# ============================================================

def display_matrix(A, evidence_ids):

    print("\n========== MATRIX ==========\n")

    print("Rows = Evidence items")
    print("Columns = 9 mathematical features")

    print("\nFeature order:")

    for i, feature in enumerate(FEATURES):
        print(i + 1, ".", feature)

    print("\nMatrix:\n")
    print(A)

    print("\nEvidence row mapping:\n")

    for i, evidence_id in enumerate(evidence_ids):
        print("Row", i + 1, "->", evidence_id)

    print("\n============================\n")


# ============================================================
# 7. RREF
# ============================================================

def calculate_rref(A):

    rref_matrix, pivot_columns = A.rref()

    return rref_matrix, pivot_columns


def display_rref(rref_matrix, pivot_columns):

    print("\n========== RREF ==========\n")

    print(rref_matrix)

    print("\nPivot columns:")

    if len(pivot_columns) == 0:

        print("No pivot columns.")

    else:

        for pivot in pivot_columns:
            print(
                "Column",
                pivot + 1,
                "->",
                FEATURES[pivot]
            )

    print("\n==========================\n")


# ============================================================
# 8. RANK
# ============================================================

def calculate_rank(A):

    return A.rank()


def display_rank(A):

    rank = calculate_rank(A)

    print("\n========== RANK ==========\n")

    print("Rank =", rank)
    print("Number of features =", len(FEATURES))
    print("Number of evidence items =", A.rows)

    print("\n==========================\n")

    return rank


# ============================================================
# 9. RANK OF ALL CASES
# ============================================================

def calculate_all_case_ranks(cases, evidence):

    results = []

    for case_id in cases["case_id"]:

        A, evidence_ids = build_matrix(
            evidence,
            case_id
        )

        if A is None:
            continue

        results.append({
            "case_id": case_id,
            "case_name": get_case_name(cases, case_id),
            "rows": A.rows,
            "columns": A.cols,
            "rank": A.rank()
        })

    return pd.DataFrame(results)


def display_all_case_ranks(result_df):

    print("\n========== RANK OF ALL CASES ==========\n")

    print(result_df.to_string(index=False))

    print("\n========================================\n")


def save_rank_results(result_df):

    result_df.to_csv(
        "rank_results.csv",
        index=False
    )

    print("Rank results saved to rank_results.csv")


# ============================================================
# 10. CREATE CASE FEATURE PROFILE
# ============================================================

def create_case_profiles(cases, evidence):

    profiles = {}

    for case_id in cases["case_id"]:

        case_data = evidence[
            evidence["case_id"] == case_id
        ]

        profile = []

        for feature in FEATURES:

            # If the feature occurs in at least one
            # evidence item, mark it as 1.
            if case_data[feature].max() == 1:
                profile.append(1)
            else:
                profile.append(0)

        profiles[case_id] = profile

    return profiles


# ============================================================
# 11. COSINE SIMILARITY
# ============================================================

def cosine_similarity(vector_a, vector_b):

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (
        magnitude_a * magnitude_b
    )


# ============================================================
# 12. CALCULATE SIMILARITY MATRIX
# ============================================================

def calculate_similarity_matrix(cases, evidence):

    profiles = create_case_profiles(
        cases,
        evidence
    )

    case_ids = cases["case_id"].tolist()

    similarity_matrix = []

    for case_a in case_ids:

        row = []

        for case_b in case_ids:

            similarity = cosine_similarity(
                profiles[case_a],
                profiles[case_b]
            )

            row.append(round(similarity, 4))

        similarity_matrix.append(row)

    result_df = pd.DataFrame(
        similarity_matrix,
        index=case_ids,
        columns=case_ids
    )

    return result_df, profiles


# ============================================================
# 13. DISPLAY SIMILARITY ANALYSIS
# ============================================================

def display_similarity_analysis(
    cases,
    similarity_df,
    profiles
):

    print("\n========== CASE FEATURE PROFILES ==========\n")

    for case_id, profile in profiles.items():

        print(
            case_id,
            "->",
            profile
        )

    print("\n========== COSINE SIMILARITY ==========\n")

    print(similarity_df.to_string())

    print("\nSimilarity interpretation:")
    print("1.0  = identical feature profiles")
    print("0.0  = no common features")

    print("\n========================================\n")


# ============================================================
# 14. SAVE SIMILARITY RESULTS
# ============================================================

def save_similarity_results(similarity_df):

    similarity_df.to_csv(
        "similarity_results.csv"
    )

    print(
        "Similarity results saved to similarity_results.csv"
    )


# ============================================================
# 15. MAIN PROGRAM
# ============================================================

def main():

    # Load data
    cases, evidence, features = load_data()

    # Validate data
    validate_data(
        cases,
        evidence,
        features
    )

    # Display cases
    display_cases(cases)

    # Ask user to select a case
    case_id = input(
        "Enter case ID (example C01): "
    ).strip().upper()

    if case_id not in cases["case_id"].values:

        print("\nInvalid case ID.")
        return

    # Build selected case matrix
    A, evidence_ids = build_matrix(
        evidence,
        case_id
    )

    # Display matrix
    display_matrix(
        A,
        evidence_ids
    )

    # RREF
    rref_matrix, pivot_columns = calculate_rref(A)

    display_rref(
        rref_matrix,
        pivot_columns
    )

    # Rank
    display_rank(A)

    # Rank comparison
    rank_df = calculate_all_case_ranks(
        cases,
        evidence
    )

    display_all_case_ranks(rank_df)

    save_rank_results(rank_df)

    # Similarity analysis
    similarity_df, profiles = calculate_similarity_matrix(
        cases,
        evidence
    )

    display_similarity_analysis(
        cases,
        similarity_df,
        profiles
    )

    save_similarity_results(
        similarity_df
    )


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":
    main()
import csv
from sympy import Matrix


FEATURE_NAMES = [
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


def load_evidence(filename):
    """
    Load the existing evidence dataset from a CSV file.
    """

    with open(filename, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    return rows


def build_matrix(evidence_rows):
    """
    Build a numerical matrix using the 9 feature columns.

    Each row represents one evidence item.
    Each column represents one feature.
    """

    matrix = []

    for row in evidence_rows:
        feature_row = []

        for feature in FEATURE_NAMES:
            feature_row.append(int(row[feature]))

        matrix.append(feature_row)

    return matrix


def split_matrix_by_case(evidence_rows):
    """
    Split the evidence matrix into separate matrices for each case.

    Each case gets its own matrix containing only
    the 9 numerical feature columns.
    """

    case_matrices = {}

    for row in evidence_rows:

        case_id = row["case_id"]

        feature_row = []

        for feature in FEATURE_NAMES:
            feature_row.append(int(row[feature]))

        if case_id not in case_matrices:
            case_matrices[case_id] = []

        case_matrices[case_id].append(feature_row)

    return case_matrices


def calculate_rref_rank_pivots(matrix):
    """
    Calculate the RREF, rank, and pivot columns of a matrix.
    """

    sympy_matrix = Matrix(matrix)

    rref_matrix, pivot_columns = sympy_matrix.rref()

    rank = len(pivot_columns)

    return rref_matrix, rank, pivot_columns


def get_pivot_features(pivot_columns):
    """
    Convert pivot column indices into feature names.
    """

    pivot_features = []

    for column in pivot_columns:
        pivot_features.append(FEATURE_NAMES[column])

    return pivot_features


def save_rank_results(results, filename):
    """
    Save rank and pivot-feature results to a CSV file.
    """

    with open(filename, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow([
            "case_id",
            "matrix_rows",
            "matrix_columns",
            "rank",
            "pivot_columns",
            "pivot_features"
        ])

        for result in results:
            writer.writerow([
                result["case_id"],
                result["matrix_rows"],
                result["matrix_columns"],
                result["rank"],
                result["pivot_columns"],
                result["pivot_features"]
            ])


if __name__ == "__main__":

    # ---------------------------------------
    # Load existing evidence dataset
    # ---------------------------------------

    evidence = load_evidence("evidence.csv")

    # ---------------------------------------
    # Build the complete 43 × 9 matrix
    # ---------------------------------------

    matrix = build_matrix(evidence)

    # ---------------------------------------
    # Split the matrix by case
    # ---------------------------------------

    case_matrices = split_matrix_by_case(evidence)

    # Store all Member 3 results
    results = []

    # ---------------------------------------
    # Full dataset
    # ---------------------------------------

    rref_matrix, rank, pivot_columns = \
        calculate_rref_rank_pivots(matrix)

    pivot_features = get_pivot_features(pivot_columns)

    results.append({
        "case_id": "FULL",
        "matrix_rows": len(matrix),
        "matrix_columns": len(matrix[0]),
        "rank": rank,
        "pivot_columns": ",".join(map(str, pivot_columns)),
        "pivot_features": ",".join(pivot_features)
    })

    print("FULL DATASET")
    print("Matrix size:", len(matrix), "×", len(matrix[0]))
    print("Rank:", rank)
    print("Pivot columns:", pivot_columns)
    print("Pivot features:", pivot_features)

    # ---------------------------------------
    # Individual cases
    # ---------------------------------------

    print("\nCASE RESULTS")

    for case_id, case_matrix in case_matrices.items():

        rref_matrix, rank, pivot_columns = \
            calculate_rref_rank_pivots(case_matrix)

        pivot_features = get_pivot_features(pivot_columns)

        results.append({
            "case_id": case_id,
            "matrix_rows": len(case_matrix),
            "matrix_columns": len(case_matrix[0]),
            "rank": rank,
            "pivot_columns": ",".join(map(str, pivot_columns)),
            "pivot_features": ",".join(pivot_features)
        })

        print("\n", case_id)
        print(
            "Matrix size:",
            len(case_matrix),
            "×",
            len(case_matrix[0])
        )
        print("Rank:", rank)
        print("Pivot columns:", pivot_columns)
        print("Pivot features:", pivot_features)

    # ---------------------------------------
    # Save Member 3 results
    # ---------------------------------------

    save_rank_results(
        results,
        "member3_rank_results.csv"
    )

    print("\nResults saved to member3_rank_results.csv")
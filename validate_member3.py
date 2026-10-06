import csv
import os
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


EXPECTED_CASE_SIZES = {
    "C01": 10,
    "C02": 8,
    "C03": 8,
    "C04": 9,
    "C05": 8
}


EXPECTED_RANKS = {
    "FULL": 9,
    "C01": 7,
    "C02": 4,
    "C03": 5,
    "C04": 6,
    "C05": 4
}


def load_evidence(filename):
    """Load the existing evidence CSV."""

    with open(filename, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def build_matrix(evidence_rows):
    """Build the numerical evidence matrix."""

    matrix = []

    for row in evidence_rows:
        feature_row = []

        for feature in FEATURE_NAMES:
            feature_row.append(int(row[feature]))

        matrix.append(feature_row)

    return matrix


def calculate_rank(matrix):
    """Calculate matrix rank using RREF."""

    sympy_matrix = Matrix(matrix)
    _, pivot_columns = sympy_matrix.rref()

    return len(pivot_columns)


def check_evidence_dataset(evidence):
    """Check the evidence dataset."""

    assert len(evidence) == 43, \
        f"Expected 43 evidence rows, found {len(evidence)}"

    for feature in FEATURE_NAMES:
        assert feature in evidence[0], \
            f"Missing feature column: {feature}"

    print("PASS: evidence.csv contains 43 evidence rows.")
    print("PASS: All 9 feature columns are present.")


def check_binary_values(evidence):
    """Check that all feature values are 0 or 1."""

    for row in evidence:

        for feature in FEATURE_NAMES:

            value = int(row[feature])

            assert value in [0, 1], \
                f"Invalid value {value} in feature {feature}"

    print("PASS: All feature values are binary 0/1.")


def check_case_sizes(evidence):
    """Check the number of evidence rows in each case."""

    case_counts = {}

    for row in evidence:

        case_id = row["case_id"]

        if case_id not in case_counts:
            case_counts[case_id] = 0

        case_counts[case_id] += 1

    assert case_counts == EXPECTED_CASE_SIZES, \
        f"Unexpected case sizes: {case_counts}"

    print("PASS: All case sizes are correct.")


def check_full_matrix(matrix):
    """Check the dimensions of the complete matrix."""

    assert len(matrix) == 43, \
        f"Expected 43 matrix rows, found {len(matrix)}"

    assert len(matrix[0]) == 9, \
        f"Expected 9 matrix columns, found {len(matrix[0])}"

    print("PASS: Full matrix dimensions are 43 × 9.")


def check_case_ranks(evidence):
    """Check the calculated rank of each case."""

    case_matrices = {}

    for row in evidence:

        case_id = row["case_id"]

        feature_row = []

        for feature in FEATURE_NAMES:
            feature_row.append(int(row[feature]))

        if case_id not in case_matrices:
            case_matrices[case_id] = []

        case_matrices[case_id].append(feature_row)

    for case_id, matrix in case_matrices.items():

        rank = calculate_rank(matrix)

        expected_rank = EXPECTED_RANKS[case_id]

        assert rank == expected_rank, \
            f"{case_id}: expected rank {expected_rank}, found {rank}"

    print("PASS: All case ranks match expected results.")


def check_full_rank(matrix):
    """Check the rank of the complete dataset."""

    rank = calculate_rank(matrix)

    assert rank == EXPECTED_RANKS["FULL"], \
        f"Expected full rank 9, found {rank}"

    print("PASS: Full dataset rank is 9.")


def check_output_file():
    """Check that Member 3 output file exists."""

    filename = "member3_rank_results.csv"

    assert os.path.exists(filename), \
        "member3_rank_results.csv was not found."

    print("PASS: member3_rank_results.csv exists.")


if __name__ == "__main__":

    print("====================================")
    print("MYSTERYMATRIX MEMBER 3 VALIDATION")
    print("====================================\n")

    evidence = load_evidence("evidence.csv")

    matrix = build_matrix(evidence)

    check_evidence_dataset(evidence)

    check_binary_values(evidence)

    check_case_sizes(evidence)

    check_full_matrix(matrix)

    check_full_rank(matrix)

    check_case_ranks(evidence)

    check_output_file()

    print("\n====================================")
    print("ALL MEMBER 3 CHECKS PASSED!")
    print("====================================")
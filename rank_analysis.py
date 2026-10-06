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
def get_pivot_features(pivot_columns):
    """
    Convert pivot column indices into feature names.
    """

    pivot_features = []

    for column in pivot_columns:
        pivot_features.append(FEATURE_NAMES[column])

    return pivot_features

def calculate_rank_from_rref(rref_matrix):
    """
    Calculate the rank of a matrix that is already in RREF.

    Rank = number of non-zero rows.
    """

    rank = 0

    for row in rref_matrix:
        if any(value != 0 for value in row):
            rank += 1

    return rank

def find_pivot_columns(rref_matrix):
    """
    Find pivot columns in an RREF matrix.

    In RREF, the pivot is the first non-zero
    entry in each non-zero row.
    """

    pivot_columns = []

    for row in rref_matrix:

        for column, value in enumerate(row):

            if value != 0:
                pivot_columns.append(column)
                break

    return pivot_columns


if __name__ == "__main__":

    rref = [
        [1, 0, 2, 0, 0, 0, 0, 0, 0],
        [0, 1, 3, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0]
    ]

    pivot_columns = find_pivot_columns(rref)
    rank = calculate_rank_from_rref(rref)
    pivot_features = get_pivot_features(pivot_columns)

    print("Pivot columns:", pivot_columns)
    print("Pivot features:", pivot_features)
    print("Rank:", rank)